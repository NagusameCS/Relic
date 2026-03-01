"""
Relic Web API — lightweight FastAPI server that exposes engine
functionality over HTTP so the browser-based UI can drive scans.

Run:  python -m relic.web.api
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from relic.core.config import load_config, RelicConfig
from relic.core.session import SessionManager
from relic.core.engine import Engine, EngineEvent, LogEvent, CommandEvent, OutputEvent, PlanEvent, FindingEvent
from relic.modules import ALL_MODULES, MODULE_CATEGORIES, list_modules, list_categories, module_count

log = logging.getLogger("relic.web")

# ── Globals ────────────────────────────────────────────────────────

_config: RelicConfig | None = None
_engine: Engine | None = None
_sessions: SessionManager | None = None
_ws_clients: list[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _engine, _sessions
    _config = load_config()
    _sessions = SessionManager(_config.session.workspace_dir)

    # Import LLM client — optional, may not have Ollama running
    try:
        from relic.llm.ollama_client import OllamaClient
        llm = OllamaClient(
            base_url=_config.llm.base_url,
            model=_config.llm.model,
            num_ctx=_config.llm.num_ctx,
        )
        await llm.ensure_model()
    except Exception as e:
        log.warning("LLM not available: %s", e)
        llm = None

    _engine = Engine(config=_config, session_manager=_sessions, llm_client=llm)
    _engine.on_event(_broadcast_event)

    log.info("Relic Web API ready")
    yield
    log.info("Relic Web API shutting down")


app = FastAPI(
    title="Relic",
    description="Relic Pentesting Automation — Web API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # GH Pages origin will vary
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────

class ObjectiveRequest(BaseModel):
    objective: str

class CommandRequest(BaseModel):
    command: str

class ScanRequest(BaseModel):
    module: str
    target: str
    params: dict[str, Any] = {}

class StatusResponse(BaseModel):
    status: str
    model: str | None = None
    scope: list[str] = []
    modules: int = 0
    categories: int = 0

class ModuleInfo(BaseModel):
    name: str
    description: str
    category: str


# ── WebSocket broadcast ───────────────────────────────────────────

def _broadcast_event(event: EngineEvent) -> None:
    """Serialize engine event and queue it for all WS clients."""
    payload: dict[str, Any] = {"type": type(event).__name__}
    if isinstance(event, LogEvent):
        payload["level"] = event.level
        payload["message"] = event.message
    elif isinstance(event, CommandEvent):
        payload["command"] = event.command
        payload["source"] = event.source
    elif isinstance(event, OutputEvent):
        payload["text"] = event.text
        payload["stream"] = event.stream
    elif isinstance(event, PlanEvent):
        payload["tasks"] = event.tasks
    elif isinstance(event, FindingEvent):
        payload["finding"] = event.finding

    for ws in list(_ws_clients):
        asyncio.ensure_future(_safe_send(ws, payload))


async def _safe_send(ws: WebSocket, data: dict) -> None:
    try:
        await ws.send_json(data)
    except Exception:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


# ── Routes ────────────────────────────────────────────────────────

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    cfg = _config
    return StatusResponse(
        status="running" if _engine else "not_initialized",
        model=cfg.llm.model if cfg else None,
        scope=cfg.scope.authorized_targets if cfg else [],
        modules=len(ALL_MODULES),
        categories=len(MODULE_CATEGORIES),
    )


@app.get("/api/modules")
async def get_modules():
    result = {}
    for cat, mods in MODULE_CATEGORIES.items():
        result[cat] = [
            {"name": cls.name, "description": cls.description, "category": cls.category}
            for cls in mods.values()
        ]
    return result


@app.get("/api/scope")
async def get_scope():
    cfg = _config
    return {
        "authorized_targets": cfg.scope.authorized_targets if cfg else [],
        "strict": cfg.scope.strict if cfg else True,
        "authorization_url": cfg.scope.authorization_url if cfg else "",
    }


@app.get("/api/sessions")
async def get_sessions():
    if not _sessions:
        return []
    return [
        {"id": s.id, "name": s.name, "target": s.target, "status": s.status}
        for s in _sessions.list_sessions()
    ]


@app.post("/api/objective")
async def run_objective(req: ObjectiveRequest):
    if not _engine:
        return {"error": "Engine not initialized"}
    asyncio.create_task(_engine.run_objective(req.objective))
    return {"status": "started", "objective": req.objective}


@app.post("/api/command")
async def run_command(req: CommandRequest):
    if not _engine:
        return {"error": "Engine not initialized"}
    output = await _engine.run_single_command(req.command)
    return {"command": req.command, "output": output}


@app.post("/api/scan")
async def run_scan(req: ScanRequest):
    if not _engine:
        return {"error": "Engine not initialized"}

    mod_cls = ALL_MODULES.get(req.module)
    if not mod_cls:
        return {"error": f"Module '{req.module}' not found"}

    mod = mod_cls()
    result = await mod.run(_engine, target=req.target, **req.params)
    return {
        "module": result.module,
        "success": result.success,
        "output": result.output,
        "findings": result.findings,
    }


@app.post("/api/stop")
async def stop_engine():
    if _engine:
        _engine.stop()
    return {"status": "stopped"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.append(ws)
    try:
        while True:
            data = await ws.receive_text()
            # Client can send commands via WS too
            if data.startswith("/cmd "):
                cmd = data[5:]
                if _engine:
                    output = await _engine.run_single_command(cmd)
                    await ws.send_json({"type": "OutputEvent", "text": output})
    except WebSocketDisconnect:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


# ── Entrypoint ────────────────────────────────────────────────────

def main():
    import uvicorn
    uvicorn.run(
        "relic.web.api:app",
        host="127.0.0.1",
        port=8746,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()

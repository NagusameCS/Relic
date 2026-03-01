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

class ScopeUpdateRequest(BaseModel):
    authorized_targets: list[str]
    authorization_url: str = ""

class ScanRequest(BaseModel):
    module: str
    target: str
    params: dict[str, Any] = {}

class ModelSwitchRequest(BaseModel):
    model: str

class ExplainRequest(BaseModel):
    error_text: str

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

# ── Model presets (name → specs) ──────────────────────────────────

MODEL_PRESETS = [
    {
        "id": "glm4-flash",
        "name": "GLM-4.7-Flash (30B-A3B)",
        "ollama": "glm4:latest",
        "size_gb": 19,
        "min_vram_gb": 6,
        "min_ram_gb": 16,
        "description": "Best quality. MoE architecture, only 3B active params. Needs 6 GB+ VRAM.",
        "tier": "recommended",
    },
    {
        "id": "gemma3-12b",
        "name": "Gemma 3 12B",
        "ollama": "gemma3:12b",
        "size_gb": 8,
        "min_vram_gb": 8,
        "min_ram_gb": 16,
        "description": "Strong reasoning. Dense 12B model. Needs 8 GB VRAM.",
        "tier": "high",
    },
    {
        "id": "gemma3-4b",
        "name": "Gemma 3 4B",
        "ollama": "gemma3:4b",
        "size_gb": 3.3,
        "min_vram_gb": 4,
        "min_ram_gb": 8,
        "description": "Lightweight. Good for 4 GB VRAM GPUs or CPU-only with 8 GB RAM.",
        "tier": "medium",
    },
    {
        "id": "qwen2.5-7b",
        "name": "Qwen 2.5 7B",
        "ollama": "qwen2.5:7b",
        "size_gb": 4.7,
        "min_vram_gb": 5,
        "min_ram_gb": 8,
        "description": "Balanced quality and speed. Good code understanding.",
        "tier": "medium",
    },
    {
        "id": "qwen2.5-3b",
        "name": "Qwen 2.5 3B",
        "ollama": "qwen2.5:3b",
        "size_gb": 2.0,
        "min_vram_gb": 2,
        "min_ram_gb": 4,
        "description": "Minimal specs. Runs on almost anything including CPU-only laptops.",
        "tier": "low",
    },
    {
        "id": "llama3.2-3b",
        "name": "Llama 3.2 3B",
        "ollama": "llama3.2:3b",
        "size_gb": 2.0,
        "min_vram_gb": 2,
        "min_ram_gb": 4,
        "description": "Meta's compact model. Fast inference on low-end hardware.",
        "tier": "low",
    },
    {
        "id": "phi3-mini",
        "name": "Phi-3.5 Mini 3.8B",
        "ollama": "phi3.5:latest",
        "size_gb": 2.2,
        "min_vram_gb": 3,
        "min_ram_gb": 4,
        "description": "Microsoft's efficient small model. Great for integrated GPUs.",
        "tier": "low",
    },
]


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


@app.put("/api/scope")
async def update_scope(req: ScopeUpdateRequest):
    if not _config:
        return {"error": "Not initialized"}
    _config.scope.authorized_targets = req.authorized_targets
    if req.authorization_url:
        _config.scope.authorization_url = req.authorization_url
    return {
        "authorized_targets": _config.scope.authorized_targets,
        "strict": _config.scope.strict,
        "authorization_url": _config.scope.authorization_url,
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


@app.get("/api/models")
async def get_models():
    """Return model presets and which ones are locally available."""
    available: set[str] = set()
    try:
        if _engine and _engine._llm:
            models = await _engine._llm.list_models()
            for m in models:
                n = m.get("name", "")
                available.add(n)
                available.add(n.split(":")[0])
    except Exception:
        pass

    active = _config.llm.model if _config else ""
    result = []
    for p in MODEL_PRESETS:
        entry = {**p}
        ollama_base = p["ollama"].split(":")[0]
        entry["installed"] = p["ollama"] in available or ollama_base in available
        entry["active"] = p["ollama"] == active or ollama_base == active.split(":")[0]
        result.append(entry)
    return result


@app.put("/api/model")
async def switch_model(req: ModelSwitchRequest):
    """Switch the active LLM model."""
    if not _engine or not _engine._llm:
        return {"error": "Engine or LLM not initialized"}

    # Find the preset
    preset = next((p for p in MODEL_PRESETS if p["id"] == req.model), None)
    ollama_name = preset["ollama"] if preset else req.model

    _engine._llm._active_model = ollama_name
    if _config:
        _config.llm.model = ollama_name

    return {"model": ollama_name, "status": "switched"}


@app.post("/api/report")
async def generate_report():
    """Use the LLM to generate a human-readable report from findings."""
    if not _engine or not _engine._llm:
        return {"error": "LLM not available"}

    # Collect findings from active session
    findings = []
    if _sessions:
        for sm in _sessions.list_sessions():
            s = _sessions.load_session(sm.id)
            if s:
                findings.extend(s.findings)

    if not findings:
        return {"report": "No findings to report. Run a scan first."}

    findings_text = "\n".join(
        f"- [{f.get('severity','?')}] {f.get('title','Untitled')}: {f.get('description','')}"
        for f in findings
    )

    prompt = (
        "You are a penetration testing report writer. Below are the raw findings "
        "from an automated security scan. Write a clear, professional executive "
        "summary report that:\n"
        "1. Summarises the overall security posture\n"
        "2. Lists each finding with severity, impact, and recommended remediation\n"
        "3. Prioritises the most critical issues first\n"
        "4. Uses clear non-technical language where possible\n\n"
        f"FINDINGS:\n{findings_text}\n\n"
        "Write the full report now:"
    )

    try:
        report = await _engine._llm.generate(prompt)
        return {"report": report}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/explain")
async def explain_error(req: ExplainRequest):
    """Use the LLM to explain an error message in plain English."""
    if not _engine or not _engine._llm:
        return {"error": "LLM not available"}

    prompt = (
        "You are a helpful security tool assistant. A user encountered the "
        "following error while using a pentesting tool. Explain what happened, "
        "why it occurred, and what they can do to fix it. Keep it concise and "
        "clear.\n\n"
        f"ERROR:\n{req.error_text}\n\n"
        "Explanation:"
    )

    try:
        explanation = await _engine._llm.generate(prompt)
        return {"explanation": explanation}
    except Exception as e:
        return {"error": str(e)}


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

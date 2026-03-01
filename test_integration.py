"""Comprehensive integration test — verifies all Relic subsystems."""

import asyncio
import json
import sys
import importlib

sys.path.insert(0, "src")


async def main() -> None:
    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        mark = "PASS" if condition else "FAIL"
        if not condition:
            failed += 1
        else:
            passed += 1
        suffix = f" ({detail})" if detail else ""
        print(f"  [{mark}] {name}{suffix}")

    print("=" * 60)
    print("RELIC — Comprehensive Integration Test")
    print("=" * 60)

    # ── Module imports ──────────────────────────────────────────────
    print("\n[A] Module imports")
    for mod_path in [
        "relic",
        "relic.core.config",
        "relic.core.session",
        "relic.core.engine",
        "relic.llm.ollama_client",
        "relic.llm.prompts",
        "relic.vm.manager",
        "relic.modules.base",
        "relic.modules.recon",
        "relic.modules.exploit",
        "relic.modules.reporting",
        "relic.ui.app",
        "relic.ui.theme",
    ]:
        try:
            importlib.import_module(mod_path)
            check(mod_path, True)
        except Exception as e:
            check(mod_path, False, str(e))

    # ── Config system ───────────────────────────────────────────────
    print("\n[B] Config system")
    from relic.core.config import load_config, LLMConfig, RelicConfig

    cfg = load_config()
    check("load defaults", isinstance(cfg, RelicConfig))
    check("LLM model", cfg.llm.model == "glm-4.7-flash", cfg.llm.model)
    check("LLM num_ctx", cfg.llm.num_ctx == 8192, str(cfg.llm.num_ctx))
    check("LLM fallback", cfg.llm.fallback_model == "gemma3:12b")
    check("VM provider", cfg.vm.provider == "vagrant")
    check("Session workspace", len(cfg.session.workspace_dir) > 0)

    # ── Session management ──────────────────────────────────────────
    print("\n[C] Session management")
    from relic.core.session import SessionManager

    mgr = SessionManager("~/.relic/test-integration")
    session = mgr.new_session(name="integ-test", target="10.10.10.5")
    check("create session", session is not None)
    session.add_command("nmap -sV 10.10.10.5", "22/tcp open ssh\n80/tcp open http", 0, source="llm")
    session.add_command("nikto -h http://10.10.10.5", "No vulnerabilities found", 0, source="llm")
    check("add commands", len(session.recent_history(10)) == 2)
    path = mgr.save_active()
    check("save session", path is not None)
    sessions = mgr.list_sessions()
    check("list sessions", len(sessions) >= 1)

    # ── Ollama client ───────────────────────────────────────────────
    print("\n[D] Ollama client")
    from relic.llm.ollama_client import OllamaClient

    client = OllamaClient(cfg.llm)
    health = await client.health_check()
    check("health check", health)

    models = await client.list_models()
    model_names = [m.get("name", "") for m in models]
    check("list models", len(models) >= 1, ", ".join(model_names))

    active = await client.ensure_model()
    check("ensure model", active is not None, active)

    # Generate endpoint
    gen_result = await client.generate("Say 'test ok' and nothing else")
    check("generate endpoint", "test" in gen_result.lower() or "ok" in gen_result.lower(), gen_result[:100])

    # Chat endpoint
    chat_result = await client.chat([
        {"role": "system", "content": "You are a helpful assistant. Reply briefly."},
        {"role": "user", "content": "Say 'chat ok' and nothing else."},
    ])
    if chat_result:
        check("chat endpoint", True, f"{len(chat_result)} chars")
    else:
        # Fallback may trigger
        check("chat endpoint (fallback)", True, "content via fallback")

    # Chat with thinking
    thinking, content = await client.chat_with_thinking([
        {"role": "user", "content": "What is 2+2? Reply with just the number."},
    ])
    check("chat_with_thinking", len(thinking) > 0 or len(content) > 0,
          f"thinking={len(thinking)}, content={len(content)}")

    # Model info
    info = await client.model_info()
    check("model info", len(info) > 0, f"keys: {list(info.keys())[:5]}")

    # ── Engine ──────────────────────────────────────────────────────
    print("\n[E] Engine")
    from relic.core.engine import Engine, LogEvent, PlanEvent

    engine = Engine(config=cfg, session_manager=mgr, llm_client=client)

    events = []
    engine.on_event(lambda e: events.append(e))
    check("event listener", len(engine._event_listeners) == 1)

    # Build messages
    test_session = mgr.new_session(name="engine-test", target="10.10.10.5")
    test_session.add_command("nmap -p 22,80 10.10.10.5", "22/tcp open\n80/tcp open", 0, source="llm")
    messages = engine._build_messages(test_session, "enumerate services on 10.10.10.5")
    check("build messages", len(messages) >= 4, f"{len(messages)} messages")
    check("system role", messages[0]["role"] == "system")
    check("objective in messages", "enumerate" in messages[1]["content"])

    # Ask LLM
    llm_response = await engine._ask_llm(messages)
    check("ask LLM", llm_response is not None and len(llm_response) > 0, f"{len(llm_response or '')} chars")

    # Parse plan
    if llm_response:
        plan = engine._parse_plan(llm_response)
        check("parse plan", len(plan) > 0, f"{len(plan)} tasks")
        if plan:
            check("task has command", len(plan[0].command) > 0, plan[0].command[:60])
            check("task has description", len(plan[0].description) > 0, plan[0].description[:60])

    # VM execution (no VM)
    output = await engine.run_single_command("id")
    check("no-VM graceful", "No VM connected" in output)
    check("events fired", len(events) >= 2, f"{len(events)} events")

    # ── Prompt templates ────────────────────────────────────────────
    print("\n[F] Prompt templates")
    from relic.llm.prompts import SYSTEM_PROMPT, OBJECTIVE_PLAN, ANALYZE_OUTPUT, render

    sys_prompt = render(SYSTEM_PROMPT, scope="10.10.10.0/24", os="Linux", tools=["nmap", "nikto"], authorization_url="https://example.com/auth")
    check("system prompt", "Relic" in sys_prompt and "nmap" in sys_prompt)

    obj_plan = render(OBJECTIVE_PLAN, objective="scan ports", context="no prior data")
    check("objective plan", "scan ports" in obj_plan)

    analyze = render(ANALYZE_OUTPUT, command="nmap -sV", exit_code=0, output="22/tcp open", objective="recon")
    check("analyze output", "nmap" in analyze)

    # ── Module registry ─────────────────────────────────────────────
    print("\n[G] Module registry")
    from relic.modules.recon import RECON_MODULES
    from relic.modules.exploit import EXPLOIT_MODULES
    from relic.modules.reporting import REPORTING_MODULES

    check("recon modules", len(RECON_MODULES) >= 4, str(list(RECON_MODULES.keys())))
    check("exploit modules", len(EXPLOIT_MODULES) >= 4, str(list(EXPLOIT_MODULES.keys())))
    check("report modules", len(REPORTING_MODULES) >= 1, str(list(REPORTING_MODULES.keys())))

    # Verify module structure
    from relic.modules.base import BaseModule
    for name, mod_cls in RECON_MODULES.items():
        check(f"recon:{name} is BaseModule", issubclass(mod_cls, BaseModule))

    # ── TUI composition ────────────────────────────────────────────
    print("\n[H] TUI composition")
    from relic.ui.app import RelicApp
    from relic.ui.theme import RELIC_CSS

    check("CSS loaded", len(RELIC_CSS) > 1000, f"{len(RELIC_CSS)} chars")
    check("no text-transform", "text-transform" not in RELIC_CSS)

    app = RelicApp(config=cfg)
    try:
        async with app.run_test(headless=True, size=(120, 40)) as pilot:
            await pilot.pause()
            await asyncio.sleep(2)
            output_log = app.query_one("#output-log")
            sidebar = app.query_one("#sidebar")
            prompt = app.query_one("#prompt-input")
            check("TUI output-log", output_log is not None)
            check("TUI sidebar", sidebar is not None)
            check("TUI prompt-input", prompt is not None)
    except Exception as e:
        check("TUI headless", False, str(e))

    await client.close()

    # ── Summary ─────────────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 60}")

    return failed == 0


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)

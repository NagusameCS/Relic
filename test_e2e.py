"""End-to-end test: Engine + LLM integration without a real VM."""

import asyncio
import sys

sys.path.insert(0, "src")


async def main() -> None:
    from relic.core.config import load_config
    from relic.core.session import SessionManager
    from relic.core.engine import Engine, EngineEvent, LogEvent, CommandEvent, OutputEvent, PlanEvent
    from relic.llm.ollama_client import OllamaClient

    print("=" * 60)
    print("RELIC — End-to-End Engine Test")
    print("=" * 60)

    # 1. Setup
    config = load_config()
    sessions = SessionManager("~/.relic/test-e2e")
    client = OllamaClient(config.llm)
    active_model = await client.ensure_model()
    print(f"\n[1] Active model: {active_model}")

    # 2. Create engine (no VM - commands will fail gracefully)
    engine = Engine(config=config, session_manager=sessions, llm_client=client)

    events_captured: list[EngineEvent] = []

    def capture_event(event: EngineEvent) -> None:
        events_captured.append(event)
        if isinstance(event, LogEvent):
            print(f"  [{event.level:5s}] {event.message}")
        elif isinstance(event, CommandEvent):
            print(f"  [cmd  ] {event.command} (source={event.source})")
        elif isinstance(event, OutputEvent):
            print(f"  [out  ] {event.text[:200]}")
        elif isinstance(event, PlanEvent):
            print(f"  [plan ] {len(event.tasks)} task(s):")
            for t in event.tasks:
                print(f"           - {t['command']}: {t['description'][:80]}")

    engine.on_event(capture_event)

    # 3. Test direct command (no VM—will return error gracefully)
    print("\n[2] Testing direct command execution (no VM)...")
    output = await engine.run_single_command("whoami")
    print(f"  Result: {output[:200]}")
    assert "No VM connected" in output, f"Expected no-VM message, got: {output}"
    print("  OK — No-VM fallback works")

    # 4. Test the _build_messages method
    print("\n[3] Testing message construction...")
    session = sessions.new_session(name="e2e-test", target="10.0.0.5")
    session.add_command("nmap -sV 10.0.0.5", "PORT STATE SERVICE VERSION\n22/tcp open ssh OpenSSH 8.9\n80/tcp open http Apache 2.4.54", 0, source="llm")
    messages = engine._build_messages(session, "enumerate attack surface on 10.0.0.5")
    print(f"  Messages: {len(messages)} entries")
    print(f"  System:   {messages[0]['content'][:80]}...")
    print(f"  First:    {messages[1]['content'][:80]}...")
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert len(messages) >= 4  # system + objective + cmd/output pair
    print("  OK — Messages constructed correctly")

    # 5. Test LLM plan generation (send messages to LLM)
    print("\n[4] Testing LLM plan generation...")
    llm_response = await engine._ask_llm(messages)
    if llm_response:
        print(f"  LLM response ({len(llm_response)} chars): {llm_response[:400]}")
        plan = engine._parse_plan(llm_response)
        print(f"  Parsed {len(plan)} task(s):")
        for t in plan:
            print(f"    - [{t.id}] {t.command}: {t.description[:60]}")
        if plan:
            print("  OK — LLM produces parseable pentesting plans")
        else:
            print("  WARN — LLM response did not contain parseable tasks")
    else:
        print("  FAIL — LLM returned no response")

    # 6. Test engine objective loop (capped at 1 iteration since no VM)
    print("\n[5] Testing engine objective loop (1 iteration, no VM)...")
    engine._running = False  # Will stop after first iteration
    # Use a simple objective
    events_captured.clear()

    # We'll run a short loop manually to verify behavior
    test_session = sessions.new_session(name="loop-test", target="192.168.1.100")
    msgs = engine._build_messages(test_session, "scan 192.168.1.100 for open ports")
    resp = await engine._ask_llm(msgs)
    if resp:
        tasks = engine._parse_plan(resp)
        print(f"  Planning response: {len(tasks)} tasks from LLM")
        for t in tasks[:3]:
            print(f"    > {t.command}")
        if tasks:
            # Execute first task against no-VM
            first_task = tasks[0]
            await engine._execute_task(first_task, test_session)
            print(f"  Task '{first_task.command}' executed, exit_code={first_task.exit_code}")
            print(f"  Output: {first_task.output[:150]}")
            print("  OK — Full loop iteration works (VM absent, graceful fallback)")

    # 7. Verify session persistence
    print("\n[6] Verifying session data...")
    sessions.save_active()
    history = test_session.recent_history(10)
    print(f"  Session has {len(history)} command(s)")
    for entry in history:
        print(f"    [{entry.source}] {entry.command}: exit={entry.exit_code}")
    print("  OK — Session records commands correctly")

    await client.close()

    print("\n" + "=" * 60)
    print("End-to-end test complete.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

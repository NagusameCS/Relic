"""Quick test: Verify Ollama connectivity, list models, and test generation."""
import asyncio
import sys
sys.path.insert(0, "src")

import httpx

async def main():
    print("=" * 60)
    print("RELIC — System Check")
    print("=" * 60)

    # 1. Check Ollama is running
    print("\n[1] Checking Ollama connectivity...")
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=10)
        models = r.json().get("models", [])
        print(f"    OK — Ollama is running")
        print(f"    Installed models:")
        for m in models:
            size_gb = m.get("size", 0) / (1024**3)
            print(f"      - {m['name']:30s} ({size_gb:.1f} GB)")
    except Exception as e:
        print(f"    FAIL — {e}")
        return

    # 2. Test generation with glm-4.7-flash (chat API)
    print("\n[2] Testing LLM chat (glm-4.7-flash)...")
    try:
        from relic.core.config import LLMConfig
        from relic.llm.ollama_client import OllamaClient

        config = LLMConfig(model="glm-4.7-flash", max_tokens=4096, num_ctx=8192, temperature=0.3)
        client = OllamaClient(config)

        # First ensure the model is available
        active = await client.ensure_model()
        print(f"    Active model: {active}")

        messages = [
            {"role": "system", "content": "You are a penetration testing assistant. Respond ONLY with JSON arrays."},
            {"role": "user", "content": (
                "Given an nmap scan showing port 22 (OpenSSH 8.9) and port 80 "
                "(Apache 2.4.54) open on target 10.0.0.5, what are the next 3 "
                "commands to run? Respond ONLY with: "
                '[{"command": "...", "description": "..."}]'
            )}
        ]
        print(f"    Sending chat request...")
        response = await client.chat(messages)
        print(f"    Response ({len(response)} chars):")
        print(f"    {response[:600]}")

        # Also test thinking mode
        print("\n    Testing thinking mode...")
        thinking, content = await client.chat_with_thinking(messages)
        print(f"    Thinking: {len(thinking)} chars")
        print(f"    Content:  {len(content)} chars")
        if thinking:
            print(f"    Thinking preview: {thinking[:200]}...")

        await client.close()
        print("    OK — LLM chat works")
    except Exception as e:
        print(f"    FAIL — {e}")

    # 3. Test all imports
    print("\n[3] Testing all module imports...")
    try:
        from relic.core.config import load_config, RelicConfig
        from relic.core.session import Session, SessionManager
        from relic.core.engine import Engine
        from relic.llm.ollama_client import OllamaClient
        from relic.llm.prompts import SYSTEM_PROMPT, OBJECTIVE_PLAN, render
        from relic.vm.manager import VMManager, VMInfo
        from relic.modules.recon import RECON_MODULES
        from relic.modules.exploit import EXPLOIT_MODULES
        from relic.modules.reporting import REPORTING_MODULES
        from relic.ui.app import RelicApp
        from relic.ui.theme import RELIC_CSS
        print(f"    OK — All imports successful")
        print(f"    Recon modules:  {list(RECON_MODULES.keys())}")
        print(f"    Exploit modules: {list(EXPLOIT_MODULES.keys())}")
        print(f"    Report modules:  {list(REPORTING_MODULES.keys())}")
    except Exception as e:
        print(f"    FAIL — {e}")
        import traceback
        traceback.print_exc()

    # 4. Test config loading
    print("\n[4] Testing config loading...")
    try:
        from relic.core.config import load_config
        cfg = load_config()
        print(f"    LLM: {cfg.llm.provider} @ {cfg.llm.base_url} model={cfg.llm.model}")
        print(f"    VM:  {cfg.vm.provider} image={cfg.vm.base_image}")
        print(f"    OK — Config loads correctly")
    except Exception as e:
        print(f"    FAIL — {e}")

    # 5. Test session management
    print("\n[5] Testing session management...")
    try:
        from relic.core.session import SessionManager
        mgr = SessionManager("~/.relic/test-sessions")
        session = mgr.new_session(name="test-run", target="127.0.0.1")
        session.add_command("whoami", "root", 0, source="user")
        session.add_command("id", "uid=0(root)", 0, source="user")
        path = mgr.save_active()
        print(f"    Session {session.meta.id} saved to {path}")
        sessions = mgr.list_sessions()
        print(f"    Listed {len(sessions)} session(s)")
        print(f"    OK — Session management works")
    except Exception as e:
        print(f"    FAIL — {e}")

    print("\n" + "=" * 60)
    print("All checks complete.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

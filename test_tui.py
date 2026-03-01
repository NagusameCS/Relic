"""Quick headless TUI test — verify RelicApp can be constructed and composed."""

import asyncio
import sys

sys.path.insert(0, "src")


async def main():
    from relic.ui.app import RelicApp

    print("[1] Creating RelicApp instance...")
    app = RelicApp()
    print(f"    Title: {app.TITLE}")
    print(f"    CSS loaded: {len(app.CSS)} chars")

    print("[2] Testing Textual headless mode...")
    try:
        async with app.run_test(headless=True, size=(120, 40)) as pilot:
            # Let the app mount and initialize
            await pilot.pause()
            await asyncio.sleep(3)  # Give time for LLM check

            # Verify key widgets exist
            output = app.query_one("#output-log")
            sidebar = app.query_one("#sidebar")
            input_w = app.query_one("#prompt-input")
            llm_status = app.query_one("#llm-status")

            print(f"    Output log: {type(output).__name__}")
            print(f"    Sidebar: {type(sidebar).__name__}")
            print(f"    Input: {type(input_w).__name__}")
            print(f"    LLM status: (widget present)")
            print("    OK — TUI composes and initializes correctly")

            # Test /help command
            input_w.value = "/help"
            await pilot.press("enter")
            await pilot.pause()
            print("    OK — /help command processed")

    except Exception as e:
        print(f"    FAIL — {e}")
        import traceback
        traceback.print_exc()

    print("\nTUI test complete.")


if __name__ == "__main__":
    asyncio.run(main())

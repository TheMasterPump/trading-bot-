"""
Quick test to verify AI Trading Engine connects and analyzes tokens
"""
import asyncio
import sys
from ai_trading_engine import get_ai_engine

async def test_engine():
    print("[TEST] Starting AI Trading Engine test...", flush=True)

    engine = get_ai_engine()
    print(f"[TEST] Engine created: {engine}", flush=True)
    print(f"[TEST] Engine has {len(engine.active_bots)} active bots", flush=True)

    # Start engine (will connect to WebSocket)
    print("[TEST] Starting engine...", flush=True)

    # Run for 15 seconds then stop
    try:
        await asyncio.wait_for(engine.start(), timeout=15)
    except asyncio.TimeoutError:
        print("[TEST] Test completed (15s timeout reached)", flush=True)
    except KeyboardInterrupt:
        print("[TEST] Test interrupted", flush=True)

    print(f"[TEST] Tokens analyzed: {engine.tokens_analyzed}", flush=True)
    print(f"[TEST] Signals generated: {engine.signals_sent}", flush=True)
    print("[TEST] AI Engine test complete!", flush=True)

if __name__ == "__main__":
    print("[TEST] Python version:", sys.version, flush=True)
    asyncio.run(test_engine())

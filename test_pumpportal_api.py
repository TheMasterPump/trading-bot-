"""
Test minimal pour PumpPortal API
Pour identifier si l'API fonctionne ou si le code est cassé
"""
import asyncio
import json
import websockets

async def test_api():
    uri = "wss://pumpportal.fun/api/data"

    print("[CONNECTING] to PumpPortal...")
    async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
        # Subscribe to new tokens
        await ws.send(json.dumps({"method": "subscribeNewToken"}))
        print("[SUBSCRIBED] to new tokens\n")

        tokens_subscribed = []
        message_count = 0

        async for message in ws:
            try:
                data = json.loads(message)
                tx_type = data.get('txType')
                message_count += 1

                print(f"[MSG #{message_count}] Type: {tx_type}")

                if tx_type == 'create':
                    mint = data.get('mint')
                    symbol = data.get('symbol', '???')
                    mc = data.get('marketCapSol', 0) * 200

                    print(f"  -> NEW TOKEN: {symbol} ({mint[:8]}...) @ ${mc:,.0f}")

                    # Subscribe to this token's trades
                    await ws.send(json.dumps({
                        "method": "subscribeTokenTrade",
                        "keys": [mint]
                    }))
                    tokens_subscribed.append(mint)
                    print(f"  -> SUBSCRIBED to trades for {symbol}")
                    print(f"  -> Total tokens subscribed: {len(tokens_subscribed)}")

                elif tx_type in ['buy', 'sell']:
                    mint = data.get('mint')
                    trader = data.get('traderPublicKey', 'unknown')[:8]
                    sol_amount = data.get('solAmount', 0)

                    print(f"  -> TRADE RECEIVED! {tx_type.upper()} {sol_amount:.2f} SOL by {trader}...")
                    print(f"  -> ✅ API IS WORKING - TRADES ARE BEING RECEIVED!")

                # Stop after 50 messages or first trade
                if message_count >= 50 or tx_type in ['buy', 'sell']:
                    print(f"\n[SUMMARY]")
                    print(f"  Messages received: {message_count}")
                    print(f"  Tokens subscribed: {len(tokens_subscribed)}")
                    if tx_type in ['buy', 'sell']:
                        print(f"  ✅ Trade messages ARE working!")
                    else:
                        print(f"  ❌ No trade messages received after {len(tokens_subscribed)} subscriptions")
                    break

            except Exception as e:
                print(f"[ERROR] {e}")
                continue

if __name__ == "__main__":
    try:
        asyncio.run(test_api())
    except KeyboardInterrupt:
        print("\n[STOPPED] Test interrupted")

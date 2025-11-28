"""
DEBUG - Subscribe to MULTIPLE tokens and capture first buy/sell message
"""
import asyncio
import json
import websockets
from datetime import datetime

async def debug_trades():
    uri = "wss://pumpportal.fun/api/data"

    async with websockets.connect(uri) as ws:
        # Subscribe to new tokens
        await ws.send(json.dumps({"method": "subscribeNewToken"}))
        print("[DEBUG] Listening for new tokens...\n")

        subscribed_tokens = []
        msg_count = 0
        max_subscriptions = 20  # Subscribe to first 20 tokens

        async for message in ws:
            msg_count += 1
            data = json.loads(message)

            # Subscribe to new tokens
            if len(subscribed_tokens) < max_subscriptions and data.get('txType') == 'create':
                mint = data.get('mint')
                symbol = data.get('symbol', '???')

                subscribed_tokens.append(mint)
                print(f"[{len(subscribed_tokens)}/20] Subscribed to {symbol} ({mint[:8]}...)")

                await ws.send(json.dumps({
                    "method": "subscribeTokenTrade",
                    "keys": [mint]
                }))

                if len(subscribed_tokens) == max_subscriptions:
                    print(f"\n[SUBSCRIBED] to {max_subscriptions} tokens, waiting for trades...\n")

            # Display any buy/sell message we receive
            elif data.get('mint') in subscribed_tokens:
                tx_type = data.get('txType', 'N/A')

                if tx_type in ['buy', 'sell']:
                    print(f"{'='*80}")
                    print(f"TRADE MESSAGE CAPTURED - txType: {tx_type}")
                    print(f"{'='*80}")
                    print(json.dumps(data, indent=2))
                    print(f"{'='*80}\n")

                    # Stop after first trade captured
                    break

if __name__ == "__main__":
    asyncio.run(debug_trades())

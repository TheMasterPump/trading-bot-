"""
DEBUG - Subscribe à un token et affiche les messages de trades (buy/sell)
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
        print("[DEBUG] Listening for new tokens, will subscribe to first one...\n")

        first_mint = None
        msg_count = 0

        async for message in ws:
            msg_count += 1
            data = json.loads(message)

            # Premier token - subscribe à ses trades
            if first_mint is None and data.get('txType') == 'create':
                first_mint = data.get('mint')
                symbol = data.get('symbol', '???')
                print(f"[FOUND] Token: {symbol} (mint: {first_mint})")
                print(f"[SUBSCRIBING] to trades...")

                await ws.send(json.dumps({
                    "method": "subscribeTokenTrade",
                    "keys": [first_mint]
                }))
                print(f"[WAITING] for buy/sell messages...\n")

            # Afficher les trades de ce token
            elif first_mint and data.get('mint') == first_mint:
                tx_type = data.get('txType', 'N/A')

                if tx_type in ['buy', 'sell']:
                    print(f"{'='*80}")
                    print(f"TRADE MESSAGE - txType: {tx_type}")
                    print(f"{'='*80}")
                    print(json.dumps(data, indent=2))
                    print(f"{'='*80}\n")

                    # Arrêter après 3 trades
                    if msg_count >= 50:
                        break

if __name__ == "__main__":
    asyncio.run(debug_trades())

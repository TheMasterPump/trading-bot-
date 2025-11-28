"""
DEBUG - Affiche TOUS les champs des messages WebSocket
"""
import asyncio
import json
import websockets
from datetime import datetime

async def debug():
    uri = "wss://pumpportal.fun/api/data"

    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"method": "subscribeNewToken"}))
        print("[DEBUG] Listening for messages...\n")

        msg_count = 0
        async for message in ws:
            msg_count += 1

            try:
                data = json.loads(message)

                # Afficher message #5 et #10 en détail
                if msg_count in [5, 10, 15]:
                    print(f"\n{'='*80}")
                    print(f"MESSAGE #{msg_count}")
                    print(f"{'='*80}")
                    print(json.dumps(data, indent=2))
                    print(f"{'='*80}\n")

                # Afficher les autres en résumé
                elif msg_count % 5 == 0:
                    print(f"[Msg #{msg_count}] {data.get('symbol', '???')} | txType: {data.get('txType', 'N/A')}")

                if msg_count >= 20:
                    print("\n[DEBUG] 20 messages capturés, arrêt.")
                    break

            except Exception as e:
                print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(debug())

"""
Test de connexion WebSocket PumpPortal
"""
import asyncio
import websockets
import json
from datetime import datetime
import time

stats = {
    'connexions': 0,
    'deconnexions': 0,
    'messages_recus': 0,
    'temps_connexion': [],
    'start_time': None
}

async def test_websocket():
    print('='*80)
    print('TEST DE CONNEXION WEBSOCKET PUMPPORTAL')
    print('='*80)
    print('\nCe test va montrer:')
    print('  - Combien de temps la connexion reste stable')
    print('  - Combien de messages sont recus')
    print('  - Si les deconnexions sont frequentes')
    print('\nAppuyez sur Ctrl+C pour arreter\n')
    print('='*80)

    stats['start_time'] = time.time()

    while True:
        connection_start = time.time()

        try:
            print(f'\n[{datetime.now().strftime("%H:%M:%S")}] Connexion au WebSocket...')

            async with websockets.connect(
                "wss://pumpportal.fun/api/data",
                ping_interval=20,
                ping_timeout=30,
                close_timeout=10,
                max_size=10485760
            ) as ws:
                stats['connexions'] += 1

                await ws.send(json.dumps({"method": "subscribeNewToken"}))

                print(f'[{datetime.now().strftime("%H:%M:%S")}] OK Connecte!')

                msg_count = 0

                while True:
                    msg = await ws.recv()
                    msg_count += 1
                    stats['messages_recus'] += 1

                    if msg_count % 10 == 0:
                        print('.', end='', flush=True)

                    if msg_count % 50 == 0:
                        elapsed = time.time() - connection_start
                        print(f'\n  [{int(elapsed)}s] {msg_count} messages recus')

        except KeyboardInterrupt:
            print('\n\nTest arrete')
            break

        except Exception as e:
            connection_duration = time.time() - connection_start
            stats['temps_connexion'].append(connection_duration)
            stats['deconnexions'] += 1

            print(f'\n\n[{datetime.now().strftime("%H:%M:%S")}] DECONNEXION: {e}')
            print(f'  Duree: {connection_duration:.1f}s')
            print(f'  Messages recus: {msg_count}')

            total_time = time.time() - stats['start_time']
            avg_duration = sum(stats['temps_connexion']) / len(stats['temps_connexion'])

            print(f'\n  STATS:')
            print(f'  - Connexions: {stats["connexions"]}')
            print(f'  - Deconnexions: {stats["deconnexions"]}')
            print(f'  - Duree moyenne: {avg_duration:.1f}s')

            if avg_duration < 60:
                print(f'\n  PROBLEME: Connexion tres instable!')
                print(f'  -> C\'est le serveur PumpPortal')
            elif avg_duration < 300:
                print(f'\n  Connexion moyennement stable')
                print(f'  -> Normal pour PumpPortal')
            else:
                print(f'\n  Connexion stable')

            print(f'\n  Reconnexion dans 10s...')
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print('\n\nTest termine!')

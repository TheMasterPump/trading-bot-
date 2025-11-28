"""
BOT DÉTECTEUR D'ACCÉLÉRATION - Zone $7K-$15K
Détecte les tokens qui ACCÉLÈRENT leur pump dans la zone optimale
Calcule la vélocité ($/sec) et l'accélération
"""
import asyncio
import json
import websockets
from datetime import datetime
import time

SOL_PRICE_USD = 200
ENTRY_ZONE_MIN = 7000   # $7K
ENTRY_ZONE_MAX = 15000  # $15K

class AccelerationDetector:
    def __init__(self):
        self.tokens = {}  # {mint: {data, price_history, velocity}}

    async def handle_new_token(self, data):
        """Nouveau token détecté"""
        mint = data.get('mint')
        if not mint or mint in self.tokens:
            return

        symbol = data.get('symbol', '???')
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * SOL_PRICE_USD

        self.tokens[mint] = {
            'mint': mint,
            'symbol': symbol,
            'created_at': time.time(),
            'price_history': [{'mc': mc_usd, 'time': time.time()}],
            'in_entry_zone': False,
            'entry_zone_alerted': False,
            'acceleration_alerted': False,
            'trades': []
        }

    async def handle_trade(self, data):
        """Analyser chaque trade pour détecter l'accélération"""
        mint = data.get('mint')
        if not mint or mint not in self.tokens:
            return

        token = self.tokens[mint]
        tx_type = data.get('txType')

        if tx_type in ['buy', 'sell']:
            mc_sol = data.get('marketCapSol', 0)
            mc_usd = mc_sol * SOL_PRICE_USD
            current_time = time.time()

            # Ajouter à l'historique de prix
            token['price_history'].append({'mc': mc_usd, 'time': current_time})

            # Garder seulement les 30 dernières secondes
            token['price_history'] = [
                p for p in token['price_history']
                if current_time - p['time'] <= 30
            ]

            # Enregistrer le trade
            token['trades'].append({
                'type': tx_type,
                'mc': mc_usd,
                'time': current_time
            })

            age = current_time - token['created_at']

            # DÉTECTION: Token entre dans la zone d'entrée
            if ENTRY_ZONE_MIN <= mc_usd <= ENTRY_ZONE_MAX:
                if not token['in_entry_zone']:
                    token['in_entry_zone'] = True

                if not token['entry_zone_alerted'] and age >= 15:
                    # Calculer les métriques des 15 dernières secondes
                    metrics = self.calculate_metrics(token, 15)

                    if metrics['buy_ratio'] >= 0.65:  # 65%+ buys
                        token['entry_zone_alerted'] = True
                        print(f"\n🎯 [ENTRY ZONE] {token['symbol']} @ ${mc_usd:,.0f}")
                        print(f"   Age: {age:.0f}s | {metrics['txn']} txn | {metrics['buy_ratio']*100:.1f}% buys")

                # DÉTECTION D'ACCÉLÉRATION
                if len(token['price_history']) >= 3:
                    acceleration = self.calculate_acceleration(token)

                    if acceleration and acceleration['is_accelerating']:
                        if not token['acceleration_alerted']:
                            token['acceleration_alerted'] = True
                            metrics = self.calculate_metrics(token, 15)

                            print(f"\n🚀🚀 [ACCÉLÉRATION DÉTECTÉE] {token['symbol']} @ ${mc_usd:,.0f}")
                            print(f"   Vélocité: ${acceleration['velocity']:.0f}/sec (+{acceleration['accel_rate']:.0f}/sec²)")
                            print(f"   Gain 10s: +${acceleration['gain_10s']:,.0f} (+{acceleration['pct_10s']:.1f}%)")
                            print(f"   Trades 15s: {metrics['txn']} txn | {metrics['buy_ratio']*100:.1f}% buys | {metrics['traders']} traders")
                            print(f"   ⚡ SIGNAL D'ENTRÉE FORT!")

            else:
                token['in_entry_zone'] = False

    def calculate_metrics(self, token, window_seconds):
        """Calculer les métriques pour une fenêtre de temps"""
        current_time = time.time()
        created_at = token['created_at']

        trades_in_window = [
            t for t in token['trades']
            if (current_time - t['time']) <= window_seconds
        ]

        if not trades_in_window:
            return {'txn': 0, 'buys': 0, 'sells': 0, 'buy_ratio': 0, 'traders': 0}

        buys = [t for t in trades_in_window if t['type'] == 'buy']
        sells = [t for t in trades_in_window if t['type'] == 'sell']

        return {
            'txn': len(trades_in_window),
            'buys': len(buys),
            'sells': len(sells),
            'buy_ratio': len(buys)/len(trades_in_window) if trades_in_window else 0,
            'traders': len(trades_in_window)  # Approximation
        }

    def calculate_acceleration(self, token):
        """Calculer la vélocité et l'accélération"""
        history = token['price_history']

        if len(history) < 3:
            return None

        current_time = time.time()

        # Prix actuel et il y a 10 secondes
        current_price = history[-1]['mc']

        # Trouver le prix il y a ~10 secondes
        price_10s_ago = None
        for p in reversed(history):
            if current_time - p['time'] >= 10:
                price_10s_ago = p['mc']
                break

        if not price_10s_ago or price_10s_ago == 0:
            return None

        # Gain sur 10 secondes
        gain_10s = current_price - price_10s_ago
        pct_10s = (gain_10s / price_10s_ago) * 100

        # Vélocité actuelle ($/sec sur les 10 dernières secondes)
        velocity = gain_10s / 10

        # Trouver le prix il y a ~20 secondes pour calculer l'accélération
        price_20s_ago = None
        for p in reversed(history):
            if current_time - p['time'] >= 20:
                price_20s_ago = p['mc']
                break

        if price_20s_ago and price_20s_ago > 0:
            # Vélocité il y a 10 secondes
            gain_20_to_10 = price_10s_ago - price_20s_ago
            velocity_10s_ago = gain_20_to_10 / 10

            # Taux d'accélération (changement de vélocité)
            accel_rate = (velocity - velocity_10s_ago)

            # Détection d'accélération:
            # - Gain de 10%+ sur 10 secondes
            # - Vélocité positive et en augmentation
            is_accelerating = (
                pct_10s >= 10 and  # Au moins 10% de gain
                velocity > 100 and  # Au moins $100/sec
                accel_rate > 0      # Accélération positive
            )

            return {
                'velocity': velocity,
                'accel_rate': accel_rate,
                'gain_10s': gain_10s,
                'pct_10s': pct_10s,
                'is_accelerating': is_accelerating
            }

        return {
            'velocity': velocity,
            'accel_rate': 0,
            'gain_10s': gain_10s,
            'pct_10s': pct_10s,
            'is_accelerating': pct_10s >= 15 and velocity > 100
        }

    async def connect_and_run(self):
        """Connexion WebSocket"""
        uri = "wss://pumpportal.fun/api/data"

        async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
            await ws.send(json.dumps({"method": "subscribeNewToken"}))
            print(f"[CONNECTED] Détecteur d'accélération - Zone ${ENTRY_ZONE_MIN:,} - ${ENTRY_ZONE_MAX:,}")
            print(f"Recherche de tokens qui ACCÉLÈRENT leur pump...\n")

            async for message in ws:
                try:
                    data = json.loads(message)

                    if data.get('txType') == 'create':
                        await self.handle_new_token(data)
                        await ws.send(json.dumps({
                            "method": "subscribeTokenTrade",
                            "keys": [data.get('mint')]
                        }))

                    elif data.get('txType') in ['buy', 'sell']:
                        await self.handle_trade(data)

                except Exception as e:
                    print(f"[ERROR] {e}")
                    continue

async def main():
    bot = AccelerationDetector()
    await bot.connect_and_run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOPPED] Bot arrêté")

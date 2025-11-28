"""
BOT COLLECTE 40K - Track les tokens qui atteignent $40K
Collecte les métriques précoces (30s, 1min, 5min) + résultat final
Objectif: Valider la formule sur tous les tokens à succès
"""
import asyncio
import json
import websockets
from datetime import datetime
import time

SOL_PRICE_USD = 200
TARGET_MC = 40000  # $40K - proche de la migration

class Track40KBot:
    def __init__(self):
        self.tokens = {}  # {mint: {data, timestamps, metrics}}
        self.tokens_at_40k = []  # Liste des tokens qui ont atteint 40K

    async def handle_new_token(self, data):
        """Nouveau token détecté"""
        mint = data.get('mint')
        if not mint or mint in self.tokens:
            return

        symbol = data.get('symbol', '???')
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * SOL_PRICE_USD

        # Enregistrer le token avec timestamp de création
        self.tokens[mint] = {
            'mint': mint,
            'symbol': symbol,
            'created_at': time.time(),
            'mc_initial': mc_usd,
            'mc_max': mc_usd,
            'trades': [],
            'snapshots': {
                '30s': None,
                '1min': None,
                '5min': None
            },
            'reached_40k': False,
            'reached_40k_at': None
        }

        print(f"[NEW] {symbol} @ ${mc_usd:,.0f}")

    async def handle_trade(self, data):
        """Enregistrer chaque trade"""
        mint = data.get('mint')
        if not mint or mint not in self.tokens:
            return

        token = self.tokens[mint]
        tx_type = data.get('txType')

        if tx_type in ['buy', 'sell']:
            trader = data.get('traderPublicKey')
            mc_sol = data.get('marketCapSol', 0)
            mc_usd = mc_sol * SOL_PRICE_USD

            # Update max MC
            if mc_usd > token['mc_max']:
                token['mc_max'] = mc_usd

            token['trades'].append({
                'type': tx_type,
                'trader': trader,
                'mc': mc_usd,
                'time': time.time()
            })

            # Calculer l'âge du token
            age = time.time() - token['created_at']

            # Snapshot à 30 secondes
            if age >= 30 and token['snapshots']['30s'] is None:
                snapshot = self.calculate_snapshot(token, 30)
                token['snapshots']['30s'] = snapshot
                print(f"  [30s] {token['symbol']}: {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 1 minute
            if age >= 60 and token['snapshots']['1min'] is None:
                snapshot = self.calculate_snapshot(token, 60)
                token['snapshots']['1min'] = snapshot
                print(f"  [1min] {token['symbol']}: {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 5 minutes
            if age >= 300 and token['snapshots']['5min'] is None:
                snapshot = self.calculate_snapshot(token, 300)
                token['snapshots']['5min'] = snapshot
                print(f"  [5min] {token['symbol']}: {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Détection: Token atteint 40K pour la première fois
            if mc_usd >= TARGET_MC and not token['reached_40k']:
                token['reached_40k'] = True
                token['reached_40k_at'] = time.time()
                time_to_40k = token['reached_40k_at'] - token['created_at']

                # Créer le snapshot actuel si pas encore fait
                current_snapshot = self.calculate_snapshot(token, age)

                result = {
                    'symbol': token['symbol'],
                    'mint': mint,
                    'time_to_40k': time_to_40k,
                    'mc_at_40k': mc_usd,
                    'mc_max': token['mc_max'],
                    '30s': token['snapshots']['30s'],
                    '1min': token['snapshots']['1min'],
                    '5min': token['snapshots']['5min'],
                    'current': current_snapshot,
                    'timestamp': datetime.now().isoformat()
                }

                self.tokens_at_40k.append(result)

                print(f"\n{'='*80}")
                print(f"[40K REACHED] {token['symbol']} @ ${mc_usd:,.0f} in {time_to_40k:.0f}s")
                print(f"{'='*80}")

                if token['snapshots']['30s']:
                    print(f"  30s:  {token['snapshots']['30s']['txn']} txn | {token['snapshots']['30s']['buy_ratio']*100:.1f}% buys | {token['snapshots']['30s']['traders']} traders")
                else:
                    print(f"  30s:  Atteint avant 30s")

                if token['snapshots']['1min']:
                    print(f"  1min: {token['snapshots']['1min']['txn']} txn | {token['snapshots']['1min']['buy_ratio']*100:.1f}% buys | {token['snapshots']['1min']['traders']} traders")
                else:
                    print(f"  1min: {current_snapshot['txn']} txn | {current_snapshot['buy_ratio']*100:.1f}% buys")

                if token['snapshots']['5min']:
                    print(f"  5min: {token['snapshots']['5min']['txn']} txn | {token['snapshots']['5min']['buy_ratio']*100:.1f}% buys")

                print(f"\n  Temps jusqu'à 40K: {time_to_40k:.0f}s ({time_to_40k/60:.1f} min)")
                print(f"{'='*80}\n")

                # Sauvegarder dans un fichier JSON
                self.save_results()

                # Afficher la formule mise à jour
                if len(self.tokens_at_40k) >= 5:
                    self.display_formula()

    def calculate_snapshot(self, token, max_age):
        """Calculer les métriques pour une période"""
        created_at = token['created_at']
        trades_in_period = [t for t in token['trades'] if (t['time'] - created_at) <= max_age]

        if not trades_in_period:
            return {'txn': 0, 'buys': 0, 'sells': 0, 'buy_ratio': 0, 'traders': 0}

        buys = [t for t in trades_in_period if t['type'] == 'buy']
        sells = [t for t in trades_in_period if t['type'] == 'sell']
        unique_traders = len(set(t['trader'] for t in trades_in_period))

        return {
            'txn': len(trades_in_period),
            'buys': len(buys),
            'sells': len(sells),
            'buy_ratio': len(buys)/len(trades_in_period) if trades_in_period else 0,
            'traders': unique_traders
        }

    def save_results(self):
        """Sauvegarder les résultats dans un fichier JSON"""
        with open('tokens_40k_data.json', 'w') as f:
            json.dump(self.tokens_at_40k, f, indent=2)
        print(f"[SAVED] {len(self.tokens_at_40k)} tokens saved to tokens_40k_data.json")

    def display_formula(self):
        """Afficher la formule mathématique découverte"""
        print(f"\n\n{'='*80}")
        print(f"FORMULE MATHEMATIQUE - TOKENS À 40K+")
        print(f"{'='*80}")
        print(f"Échantillon: {len(self.tokens_at_40k)} tokens ayant atteint 40K+")

        # Filtrer les tokens qui ont des données complètes
        complete_tokens = [t for t in self.tokens_at_40k if t['1min'] is not None]

        if complete_tokens:
            print(f"\n[PATTERN MOYEN DES TOKENS À 40K]")

            # Calculer les moyennes
            avg_time = sum(t['time_to_40k'] for t in complete_tokens) / len(complete_tokens)

            # 30s
            tokens_30s = [t for t in complete_tokens if t['30s'] is not None]
            if tokens_30s:
                avg_30s_txn = sum(t['30s']['txn'] for t in tokens_30s) / len(tokens_30s)
                avg_30s_buy = sum(t['30s']['buy_ratio'] for t in tokens_30s) / len(tokens_30s)
                print(f"  30s:  {avg_30s_txn:.0f} txn | {avg_30s_buy*100:.1f}% buys")

            # 1min
            avg_1min_txn = sum(t['1min']['txn'] for t in complete_tokens) / len(complete_tokens)
            avg_1min_buy = sum(t['1min']['buy_ratio'] for t in complete_tokens) / len(complete_tokens)
            print(f"  1min: {avg_1min_txn:.0f} txn | {avg_1min_buy*100:.1f}% buys")

            # 5min
            tokens_5min = [t for t in complete_tokens if t['5min'] is not None]
            if tokens_5min:
                avg_5min_txn = sum(t['5min']['txn'] for t in tokens_5min) / len(tokens_5min)
                avg_5min_buy = sum(t['5min']['buy_ratio'] for t in tokens_5min) / len(tokens_5min)
                print(f"  5min: {avg_5min_txn:.0f} txn | {avg_5min_buy*100:.1f}% buys")

            print(f"\n  Temps moyen jusqu'à 40K: {avg_time:.0f}s ({avg_time/60:.1f} min)")

            print(f"\n[SEUILS RECOMMANDÉS POUR DÉTECTER UN RUNNER]")
            print(f"  - MIN 1min: {avg_1min_txn*0.7:.0f} txn")
            print(f"  - MIN buy ratio: {avg_1min_buy*0.9*100:.0f}%")

        print(f"{'='*80}\n")

        # Afficher la liste des tokens
        print("[LISTE DES TOKENS À 40K+]")
        for i, t in enumerate(self.tokens_at_40k[-10:], 1):
            time_str = f"{t['time_to_40k']:.0f}s" if t['time_to_40k'] < 120 else f"{t['time_to_40k']/60:.1f}min"
            txn_1min = t['1min']['txn'] if t['1min'] else "N/A"
            buy_1min = f"{t['1min']['buy_ratio']*100:.1f}%" if t['1min'] else "N/A"
            print(f"  {i}. {t['symbol']:12} | {txn_1min:>3} txn/min | {buy_1min:>5} buys | {time_str} to 40K")
        print()

    async def connect_and_run(self):
        """Connexion WebSocket"""
        uri = "wss://pumpportal.fun/api/data"

        async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
            # Subscribe to new tokens
            await ws.send(json.dumps({"method": "subscribeNewToken"}))
            print(f"[CONNECTED] Tracking tokens reaching $40K...")
            print(f"Target: ${TARGET_MC:,}")
            print(f"Data saved to: tokens_40k_data.json\n")

            async for message in ws:
                try:
                    data = json.loads(message)

                    # Nouveau token
                    if data.get('txType') == 'create':
                        await self.handle_new_token(data)
                        # Subscribe aux trades
                        await ws.send(json.dumps({
                            "method": "subscribeTokenTrade",
                            "keys": [data.get('mint')]
                        }))

                    # Trade
                    elif data.get('txType') in ['buy', 'sell']:
                        await self.handle_trade(data)

                except Exception as e:
                    print(f"[ERROR] {e}")
                    continue

async def main():
    bot = Track40KBot()
    await bot.connect_and_run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOPPED] Bot stopped")

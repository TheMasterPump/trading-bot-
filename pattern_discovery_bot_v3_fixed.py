"""
BOT DÉCOUVERTE DE PATTERN - Collecte temps réel
Enregistre: 10s, 15s, 20s, 30s, 1min, 2min, 3min, 5min, 8min, 10min
Complétion: 10 MINUTES (pour voir durée de vie complète)
Sauvegarder: Quand token atteint $25K OU 10min OU mort (pas de trade 3min)
Objectif: Trouver la formule mathématique des runners + détecter migrations
"""
import asyncio
import json
import websockets
from datetime import datetime
import time

SOL_PRICE_USD = 200

# === CHARGEMENT DES WALLETS DE BALEINES ===
WHALE_WALLETS = set()
try:
    import json
    with open('whale_wallets.json', 'r', encoding='utf-8') as f:
        whale_data = json.load(f)
        WHALE_WALLETS = {w['trackedWalletAddress'] for w in whale_data}
    print(f"[WHALE TRACKER] {len(WHALE_WALLETS)} wallets de baleines charges")
except Exception as e:
    print(f"[WARNING] Impossible de charger whale_wallets.json: {e}")


class PatternDiscoveryBot:
    def __init__(self):
        self.tokens = {}  # {mint: {data, timestamps, metrics}}
        self.completed_analysis = []
        self.alerts = []  # Alertes pour le dashboard

        self.whale_activity = {}  # {mint: {wallets, volume, timing}}
        self.data_file = 'bot_data.json'

        # CHARGER LES DONNEES EXISTANTES
        self.load_existing_data()

    def load_existing_data(self):
        """Charger les donnees existantes pour continuer l'accumulation"""
        import os
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Charger les analyses completees
                    self.completed_analysis = data.get('completed', [])
                    # Charger les alertes
                    self.alerts = data.get('alerts', [])

                    print(f"[CHARGEMENT] {len(self.completed_analysis)} tokens charges depuis la sauvegarde")
                    runners = [a for a in self.completed_analysis if a.get('is_runner', False)]
                    print(f"[CHARGEMENT] {len(runners)} runners deja enregistres")
            except Exception as e:
                print(f"[WARNING] Impossible de charger les donnees: {e}")
                print("[INFO] Demarrage avec donnees vierges")

    def save_data(self):
        """Sauvegarder les donnees pour le dashboard"""
        try:
            # Separer runners et flops
            runners = [a for a in self.completed_analysis if a.get('is_runner', False)]
            flops = [a for a in self.completed_analysis if not a.get('is_runner', False)]

            # Calculer les stats
            total_completed = len(self.completed_analysis)
            win_rate = (len(runners) / total_completed * 100) if total_completed > 0 else 0

            # GARDER TOUTES LES DONNEES pour l'entrainement AI
            data = {
                'tokens': [],  # Tokens en cours (on ne garde que ceux < 5min)
                'completed': self.completed_analysis,  # TOUS les tokens (pas seulement 50)
                'runners': runners,  # TOUS les runners
                'flops': flops,  # TOUS les flops
                'alerts': self.alerts[-100:],  # 100 dernieres alertes (pour pas surcharger)
                'stats': {
                    'total_tokens': total_completed,
                    'total_runners': len(runners),
                    'total_flops': len(flops),
                    'win_rate': win_rate
                }
            }

            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Save data: {e}")

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
            'trades': [],
            'price_history': [{'mc': mc_usd, 'time': time.time()}],  # Pour accélération
            'acceleration_alerted': False,  # Flag pour ne pas spammer
            'momentum_alerted': False,  # Flag pour signal momentum
            'runner_pattern_alerted': False,  # Flag pour RUNNER PATTERN
            'snapshots': {
                '10s': None,
                '15s': None,
                '20s': None,
                '30s': None,
                '1min': None,
                '2min': None,
                '3min': None,
                '5min': None,
                '8min': None,
                '10min': None,
                '20min': None
            },
            'early_runner_saved': False,  # Flag pour ne pas sauvegarder 2 fois
            'completed': False,  # Token terminé ?
            'last_trade_time': time.time(),  # Pour détecter mort
            'migration_detected': False  # Pour détecter migration $69K
        }

        print(f"\n[NEW TOKEN] {symbol} @ ${mc_usd:,.0f}")

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

            # NOUVELLES DONNÉES: Montant du trade
            sol_amount = data.get('solAmount', 0)
            token_amount = data.get('tokenAmount', 0)
            amount_usd = sol_amount * SOL_PRICE_USD if sol_amount else 0

            current_time = time.time()

            # Mettre à jour le temps du dernier trade (pour détecter mort)
            token['last_trade_time'] = current_time

            token['trades'].append({
                'type': tx_type,
                'trader': trader,
                'mc': mc_usd,
                'time': current_time,
                'amount_sol': sol_amount,
                'amount_usd': amount_usd,
                'token_amount': token_amount
            })

            # Mettre à jour l'historique de prix
            token['price_history'].append({'mc': mc_usd, 'time': current_time})
            # Garder seulement les 30 dernières secondes
            token['price_history'] = [
                p for p in token['price_history']
                if current_time - p['time'] <= 30
            ]

            # Calculer l'âge du token
            age = current_time - token['created_at']

            # ========== MIGRATION DETECTION ==========
            # Bonding curve complétée à ~$69K = MIGRATION vers PumpSwap !
            if mc_usd >= 69000 and not token['migration_detected'] and not token['completed']:
                token['migration_detected'] = True
                token['completed'] = True  # Marquer comme complété immédiatement

                # Créer les snapshots avec les données disponibles
                snapshot_10s = token['snapshots'].get('10s') or self.calculate_snapshot(token, 10)
                snapshot_15s = token['snapshots'].get('15s') or self.calculate_snapshot(token, 15)
                snapshot_20s = token['snapshots'].get('20s') or self.calculate_snapshot(token, 20)
                snapshot_30s = token['snapshots'].get('30s') or self.calculate_snapshot(token, 30)
                snapshot_1min = token['snapshots'].get('1min')
                snapshot_2min = token['snapshots'].get('2min')
                snapshot_3min = token['snapshots'].get('3min')
                snapshot_5min = token['snapshots'].get('5min')
                snapshot_8min = token['snapshots'].get('8min')
                snapshot_10min = token['snapshots'].get('10min')
                snapshot_20min = token['snapshots'].get('20min')

                # Assigner les MC aux snapshots existants
                if snapshot_10s:
                    snapshot_10s['mc'] = token['snapshots'].get('10s', {}).get('mc', mc_usd)
                if snapshot_15s:
                    snapshot_15s['mc'] = token['snapshots'].get('15s', {}).get('mc', mc_usd)
                if snapshot_20s:
                    snapshot_20s['mc'] = token['snapshots'].get('20s', {}).get('mc', mc_usd)
                if snapshot_30s:
                    snapshot_30s['mc'] = token['snapshots'].get('30s', {}).get('mc', mc_usd)

                # SAUVEGARDER LE TOKEN IMMÉDIATEMENT
                result = {
                    'symbol': token['symbol'],
                    'mint': mint,
                    '10s': snapshot_10s,
                    '15s': snapshot_15s,
                    '20s': snapshot_20s,
                    '30s': snapshot_30s,
                    '1min': snapshot_1min,
                    '2min': snapshot_2min,
                    '3min': snapshot_3min,
                    '5min': snapshot_5min,
                    '8min': snapshot_8min,
                    '10min': snapshot_10min,
                    '20min': snapshot_20min,
                    'final_mc': mc_usd,
                    'is_runner': True,
                    'pump_time': age,
                    'early_runner': True,
                    'migration_detected': True,
                    'migration_price': mc_usd
                }

                self.completed_analysis.append(result)

                print(f"\n{'='*80}")
                print(f"[MIGRATION!] {token['symbol']} @ ${mc_usd:,.0f} - BONDING CURVE COMPLETE!")
                print(f"Token migre vers PumpSwap - Pump majeur detecte!")
                print(f"Temps pour migration: {age:.1f}s")
                if snapshot_10s:
                    print(f"  10s:  {snapshot_10s['txn']} txn | {snapshot_10s['buy_ratio']*100:.1f}% buys")
                if snapshot_1min:
                    print(f"  1min: {snapshot_1min['txn']} txn | {snapshot_1min['buy_ratio']*100:.1f}% buys")
                if snapshot_5min:
                    print(f"  5min: {snapshot_5min['txn']} txn | {snapshot_5min['buy_ratio']*100:.1f}% buys")
                print(f"{'='*80}")

                self.alerts.append({
                    'type': 'migration',
                    'symbol': token['symbol'],
                    'mint': mint,
                    'message': f"MIGRATION RAYDIUM @ ${mc_usd:,.0f} en {age:.1f}s",
                    'timestamp': datetime.now().isoformat()
                })
                self.save_data()

            # ========== STRONG RUNNER DETECTION ($25K+) ==========
            # Si le token atteint $25K+ avant d'être complété, c'est un VRAI runner!
            if mc_usd >= 25000 and not token['completed'] and not token['early_runner_saved']:
                token['early_runner_saved'] = True

                # Créer les snapshots avec les données actuelles (seulement ceux qui n'existent pas)
                snapshot_10s = token['snapshots'].get('10s') or self.calculate_snapshot(token, 10)
                snapshot_15s = token['snapshots'].get('15s') or self.calculate_snapshot(token, 15)
                snapshot_20s = token['snapshots'].get('20s') or self.calculate_snapshot(token, 20)
                snapshot_30s = token['snapshots'].get('30s') or self.calculate_snapshot(token, 30)

                # Pour les snapshots plus longs, utiliser ce qui existe déjà ou None
                snapshot_1min = token['snapshots'].get('1min')
                snapshot_2min = token['snapshots'].get('2min')
                snapshot_3min = token['snapshots'].get('3min')
                snapshot_5min = token['snapshots'].get('5min')
                snapshot_8min = token['snapshots'].get('8min')
                snapshot_10min = token['snapshots'].get('10min')
                snapshot_20min = token['snapshots'].get('20min')

                snapshot_10s['mc'] = token['snapshots'].get('10s', {}).get('mc', mc_usd)
                snapshot_15s['mc'] = token['snapshots'].get('15s', {}).get('mc', mc_usd)
                snapshot_20s['mc'] = token['snapshots'].get('20s', {}).get('mc', mc_usd)
                snapshot_30s['mc'] = token['snapshots'].get('30s', {}).get('mc', mc_usd)

                result = {
                    'symbol': token['symbol'],
                    'mint': mint,
                    '10s': snapshot_10s,
                    '15s': snapshot_15s,
                    '20s': snapshot_20s,
                    '30s': snapshot_30s,
                    '1min': snapshot_1min,
                    '2min': snapshot_2min,
                    '3min': snapshot_3min,
                    '5min': snapshot_5min,
                    '8min': snapshot_8min,
                    '10min': snapshot_10min,
                    '20min': snapshot_20min,
                    'final_mc': mc_usd,
                    'is_runner': True,
                    'pump_time': age,  # Temps en secondes pour atteindre $25K
                    'early_runner': True,
                    'migration_detected': token['migration_detected']
                }

                self.completed_analysis.append(result)
                token['completed'] = True  # Marquer comme terminé pour ne pas resauvegarder

                print(f"\n{'='*80}")
                print(f"[STRONG RUNNER!] {token['symbol']} @ ${mc_usd:,.0f} en {age:.1f}s!")
                print(f"  10s:  {snapshot_10s['txn']} txn | {snapshot_10s['buy_ratio']*100:.1f}% buys | BigBuys: {snapshot_10s['big_buys_100']}")
                print(f"  15s:  {snapshot_15s['txn']} txn | {snapshot_15s['buy_ratio']*100:.1f}% buys | BigBuys: {snapshot_15s['big_buys_100']} | Whales: {snapshot_15s['big_buys_500']}")
                print(f"  30s:  {snapshot_30s['txn']} txn | {snapshot_30s['buy_ratio']*100:.1f}% buys | Vol: ${snapshot_30s['total_buy_volume']:.0f}")
                if snapshot_1min:
                    print(f"  1min: {snapshot_1min['txn']} txn | {snapshot_1min['buy_ratio']*100:.1f}% buys")
                if snapshot_5min:
                    print(f"  5min: {snapshot_5min['txn']} txn | {snapshot_5min['buy_ratio']*100:.1f}% buys")
                if token['migration_detected']:
                    print(f"  [MIGRATION DETECTEE!]")
                print(f"{'='*80}")

                # Alerte pour le dashboard
                self.alerts.append({
                    'type': 'early_runner',
                    'symbol': token['symbol'],
                    'mint': token['mint'],
                    'message': f"PUMP ULTRA-RAPIDE! ${mc_usd:,.0f} en {age:.1f}s | {snapshot_current['txn']} txn | {snapshot_current['buy_ratio']*100:.1f}% buys",
                    'timestamp': datetime.now().isoformat()
                })

                self.save_data()

                # Afficher formule si on a 10+ tokens
                if len(self.completed_analysis) >= 10:
                    self.display_formula()

            # DÉTECTION D'ACCÉLÉRATION dans la zone $7K-$15K
            if 7000 <= mc_usd <= 15000 and not token['acceleration_alerted'] and age >= 15:
                accel = self.detect_acceleration(token, mc_usd)
                if accel and accel['is_accelerating']:
                    token['acceleration_alerted'] = True
                    metrics = self.calculate_snapshot(token, 15)
                    print(f"\n🚀🚀 [ACCÉLÉRATION] {token['symbol']} @ ${mc_usd:,.0f}")
                    print(f"   Vélocité: ${accel['velocity']:.0f}/sec | Gain 10s: +${accel['gain_10s']:,.0f} (+{accel['pct_10s']:.1f}%)")
                    print(f"   Trades 15s: {metrics['txn']} txn | {metrics['buy_ratio']*100:.1f}% buys")
                    print(f"   ⚡ SIGNAL D'ENTRÉE FORT!")

                    # Alerte pour le dashboard
                    self.alerts.append({
                        'type': 'rocket',
                        'symbol': token['symbol'],
                        'message': f"Velocite: ${accel['velocity']:.0f}/sec | Gain 10s: +{accel['pct_10s']:.1f}% | {metrics['txn']} txn | {metrics['buy_ratio']*100:.1f}% buys",
                        'timestamp': datetime.now().isoformat()
                    })
                    self.save_data()

            # Snapshot à 10 secondes
            if age >= 10 and token['snapshots']['10s'] is None:
                snapshot = self.calculate_snapshot(token, 10)
                snapshot['mc'] = mc_usd
                token['snapshots']['10s'] = snapshot
                smart_info = f" | BigBuys: {snapshot['big_buys_100']}" if snapshot['big_buys_100'] > 0 else ""
                print(f"  [10s] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders{smart_info}")

            # Snapshot à 15 secondes
            if age >= 15 and token['snapshots']['15s'] is None:
                snapshot = self.calculate_snapshot(token, 15)
                snapshot['mc'] = mc_usd
                token['snapshots']['15s'] = snapshot
                smart_info = f" | BigBuys: {snapshot['big_buys_100']}" if snapshot['big_buys_100'] > 0 else ""
                whale_info = f" | Whales: {snapshot['big_buys_500']}" if snapshot['big_buys_500'] > 0 else ""
                print(f"  [15s] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders{smart_info}{whale_info}")

                # ALERTE HIGH BUY RATIO dans la zone optimale
                if 7000 <= mc_usd <= 15000 and not token['acceleration_alerted']:
                    if snapshot['buy_ratio'] >= 0.68 and snapshot['txn'] >= 50:
                        token['acceleration_alerted'] = True
                        print(f"\n[HIGH BUY RATIO] {token['symbol']} @ ${mc_usd:,.0f}")
                        print(f"   Buy Ratio: {snapshot['buy_ratio']*100:.1f}% | {snapshot['txn']} txn | {snapshot['traders']} traders")
                        print(f"   Big buys: {snapshot['big_buys_100']} >$100 | Whales: {snapshot['big_buys_500']} >$500")
                        print(f"   Zone optimale: $7K-$15K | SIGNAL D'ENTREE FORT!")

                        # Alerte pour le dashboard
                        self.alerts.append({
                            'type': 'diamond',
                            'symbol': token['symbol'],
                            'message': f"Buy Ratio: {snapshot['buy_ratio']*100:.1f}% | {snapshot['txn']} txn | 💰 {snapshot['big_buys_100']} big buys | Zone: $7K-$15K",
                            'timestamp': datetime.now().isoformat()
                        })
                        self.save_data()

                # ALERTE SMART MONEY DETECTED
                if snapshot.get('smart_money_count', 0) >= 3 and age >= 15:
                    print(f"\n[SMART MONEY DETECTED] {token['symbol']} @ ${mc_usd:,.0f}")
                    print(f"   {snapshot['smart_money_count']} wallets ont achete >$200 dans les 15 premieres secondes!")
                    print(f"   {snapshot['big_buys_100']} achats >$100 | {snapshot['big_buys_500']} whales >$500")
                    print(f"   Volume d'achat total: ${snapshot['total_buy_volume']:.0f}")

                    self.alerts.append({
                        'type': 'smart_money',
                        'symbol': token['symbol'],
                        'message': f"{snapshot['smart_money_count']} smart wallets | ${snapshot['total_buy_volume']:.0f} volume | {snapshot['big_buys_500']} whales",
                        'timestamp': datetime.now().isoformat()
                    })
                    self.save_data()

            # Snapshot à 20 secondes
            if age >= 20 and token['snapshots']['20s'] is None:
                snapshot = self.calculate_snapshot(token, 20)
                snapshot['mc'] = mc_usd
                token['snapshots']['20s'] = snapshot
                print(f"  [20s] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 30 secondes
            if age >= 30 and token['snapshots']['30s'] is None:
                snapshot = self.calculate_snapshot(token, 30)
                snapshot['mc'] = mc_usd
                token['snapshots']['30s'] = snapshot
                print(f"  [30s] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 1 minute
            if age >= 60 and token['snapshots']['1min'] is None:
                snapshot = self.calculate_snapshot(token, 60)
                snapshot['mc'] = mc_usd
                token['snapshots']['1min'] = snapshot
                print(f"  [1min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 2 minutes
            if age >= 120 and token['snapshots']['2min'] is None:
                snapshot = self.calculate_snapshot(token, 120)
                snapshot['mc'] = mc_usd
                token['snapshots']['2min'] = snapshot
                print(f"  [2min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 3 minutes
            if age >= 180 and token['snapshots']['3min'] is None:
                snapshot = self.calculate_snapshot(token, 180)
                snapshot['mc'] = mc_usd
                token['snapshots']['3min'] = snapshot
                print(f"  [3min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 5 minutes
            if age >= 300 and token['snapshots']['5min'] is None:
                snapshot = self.calculate_snapshot(token, 300)
                snapshot['mc'] = mc_usd
                token['snapshots']['5min'] = snapshot
                print(f"  [5min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 8 minutes
            if age >= 480 and token['snapshots']['8min'] is None:
                snapshot = self.calculate_snapshot(token, 480)
                snapshot['mc'] = mc_usd
                token['snapshots']['8min'] = snapshot
                print(f"  [8min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 10 minutes - NE PAS SAUVEGARDER AUTOMATIQUEMENT
            if age >= 600 and token['snapshots']['10min'] is None:
                snapshot = self.calculate_snapshot(token, 600)
                snapshot['mc'] = mc_usd
                token['snapshots']['10min'] = snapshot
                print(f"  [10min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 20 minutes - CONTINUER À TRACKER
            if age >= 1200 and token['snapshots']['20min'] is None:
                snapshot = self.calculate_snapshot(token, 1200)
                snapshot['mc'] = mc_usd
                token['snapshots']['20min'] = snapshot
                print(f"  [20min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

                # Afficher formule si on a 10+ tokens
                if len(self.completed_analysis) >= 10:
                    self.display_formula()

            # ===== VÉRIFICATION TOKEN MORT =====
            # Si pas de trade depuis 3 minutes ET pas encore complété, sauvegarder
            time_since_last_trade = current_time - token['last_trade_time']
            if time_since_last_trade >= 180 and not token['completed'] and age >= 60:
                # Token mort, sauvegarder ce qu'on a
                is_runner = mc_usd >= 25000

                result = {
                    'symbol': token['symbol'],
                    'mint': mint,
                    '10s': token['snapshots']['10s'],
                    '15s': token['snapshots']['15s'],
                    '20s': token['snapshots']['20s'],
                    '30s': token['snapshots']['30s'],
                    '1min': token['snapshots']['1min'],
                    '2min': token['snapshots']['2min'],
                    '3min': token['snapshots']['3min'],
                    '5min': token['snapshots']['5min'],
                    '8min': token['snapshots']['8min'],
                    '10min': token['snapshots']['10min'],
                    '20min': token['snapshots']['20min'],
                    'final_mc': mc_usd,
                    'is_runner': is_runner,
                    'early_runner': False,
                    'token_died': True,
                    'death_time': age,
                    'migration_detected': token['migration_detected']
                }

                self.completed_analysis.append(result)
                token['completed'] = True

                print(f"\n{'='*80}")
                print(f"[TOKEN MORT] {token['symbol']} @ {age:.0f}s -> ${mc_usd:,.0f} {'RUNNER' if is_runner else 'FLOP'}")
                print(f"  Pas de trade depuis 3 minutes")
                print(f"{'='*80}")

                self.save_data()

    def calculate_snapshot(self, token, max_age):
        """Calculer les métriques pour une période"""
        created_at = token['created_at']
        trades_in_period = [t for t in token['trades'] if (t['time'] - created_at) <= max_age]

        if not trades_in_period:
            return {
                'txn': 0, 'buys': 0, 'sells': 0, 'buy_ratio': 0, 'traders': 0,
                'big_buys_100': 0, 'big_buys_300': 0, 'big_buys_500': 0,
                'avg_buy_size': 0, 'total_buy_volume': 0, 'total_sell_volume': 0,
                'smart_money_count': 0
            }

        buys = [t for t in trades_in_period if t['type'] == 'buy']
        sells = [t for t in trades_in_period if t['type'] == 'sell']
        unique_traders = len(set(t['trader'] for t in trades_in_period))

        # WALLET INTELLIGENCE: Comptage des gros achats
        big_buys_100 = len([b for b in buys if b.get('amount_usd', 0) >= 100])
        big_buys_300 = len([b for b in buys if b.get('amount_usd', 0) >= 300])
        big_buys_500 = len([b for b in buys if b.get('amount_usd', 0) >= 500])

        # Volume total
        total_buy_volume = sum(b.get('amount_usd', 0) for b in buys)
        total_sell_volume = sum(s.get('amount_usd', 0) for s in sells)

        # Taille moyenne d'achat
        avg_buy_size = total_buy_volume / len(buys) if buys else 0

        # SMART MONEY: Wallets qui achètent >$200 dans les premières secondes
        early_big_buyers = set()
        for t in buys:
            if (t['time'] - created_at) <= 15 and t.get('amount_usd', 0) >= 200:
                early_big_buyers.add(t['trader'])

        return {
            'txn': len(trades_in_period),
            'buys': len(buys),
            'sells': len(sells),
            'buy_ratio': len(buys)/len(trades_in_period) if trades_in_period else 0,
            'traders': unique_traders,
            # NOUVELLES MÉTRIQUES
            'big_buys_100': big_buys_100,
            'big_buys_300': big_buys_300,
            'big_buys_500': big_buys_500,
            'avg_buy_size': avg_buy_size,
            'total_buy_volume': total_buy_volume,
            'total_sell_volume': total_sell_volume,
            'smart_money_count': len(early_big_buyers),
            'whale_ratio': big_buys_500 / len(buys) if buys else 0  # % de whales
        }

    def detect_acceleration(self, token, current_mc):
        """Détecter l'accélération du pump"""
        history = token['price_history']

        if len(history) < 3:
            return None

        current_time = time.time()

        # Prix il y a ~10 secondes
        price_10s_ago = None
        for p in reversed(history):
            if current_time - p['time'] >= 10:
                price_10s_ago = p['mc']
                break

        if not price_10s_ago or price_10s_ago == 0:
            return None

        # Gain sur 10 secondes
        gain_10s = current_mc - price_10s_ago
        pct_10s = (gain_10s / price_10s_ago) * 100

        # Vélocité ($/sec)
        velocity = gain_10s / 10

        # Critères d'accélération:
        # - Au moins 8% de gain sur 10 secondes
        # - Vélocité d'au moins $100/sec
        is_accelerating = pct_10s >= 8 and velocity >= 100

        return {
            'velocity': velocity,
            'gain_10s': gain_10s,
            'pct_10s': pct_10s,
            'is_accelerating': is_accelerating
        }

    def detect_momentum(self, token, snapshot_1min):
        """Détecter un momentum soutenu (pression d'achat modérée mais constante)"""
        # Vérifier qu'on a le snapshot 15s
        snapshot_15s = token['snapshots'].get('15s')
        if not snapshot_15s:
            return None

        # Critère 1: Buy ratio entre 58-65% à 1min (modéré mais constant)
        buy_ratio = snapshot_1min['buy_ratio']
        if not (0.58 <= buy_ratio <= 0.65):
            return None

        # Critère 2: Croissance de volume (au moins 3x de 15s à 1min)
        volume_growth = snapshot_1min['txn'] / max(snapshot_15s['txn'], 1)
        if volume_growth < 3.0:
            return None

        # Critère 3: Buy ratio stable ou en augmentation (pas de chute)
        if buy_ratio < (snapshot_15s['buy_ratio'] - 0.05):  # Max 5% de baisse autorisée
            return None

        # Critère 4: Au moins 100 transactions à 1min
        if snapshot_1min['txn'] < 100:
            return None

        return {
            'volume_growth': volume_growth,
            'buy_ratio_change': buy_ratio - snapshot_15s['buy_ratio']
        }

    def detect_runner_pattern(self, token, snapshot_1min):
        """
        FILTRE OPTIMISÉ RUNNER basé sur l'analyse de win rate
        Critères stricts pour capturer uniquement les vrais runners
        """
        # Vérifier qu'on a les snapshots nécessaires
        snapshot_15s = token['snapshots'].get('15s')
        snapshot_30s = token['snapshots'].get('30s')

        if not snapshot_15s or not snapshot_30s:
            return None

        # TIER 1 - Filtre Initial @ 15s
        # Runners moyens: 23 txn, 15 traders, 47% buy ratio
        # On met des seuils légèrement plus bas pour ne pas être trop strict
        if snapshot_15s['txn'] < 20:  # Minimum 20 transactions
            return None
        if snapshot_15s['traders'] < 10:  # Minimum 10 traders (réduit de 12)
            return None
        if snapshot_15s['buy_ratio'] < 0.45:  # Minimum 45% buy ratio
            return None

        # TIER 2 - Abandon Précoce @ 30s
        # Vérifier que le volume continue de croître
        volume_growth_30s = snapshot_30s['txn'] / max(snapshot_15s['txn'], 1)
        if volume_growth_30s < 1.3:  # Volume doit au moins x1.3 en 15 secondes (ajusté)
            return None
        if snapshot_30s['buy_ratio'] < 0.35:  # Buy ratio ne doit pas chuter sous 35%
            return None

        # TIER 3 - Confirmation @ 1min
        # Runners moyens: 64 txn à 1min (vs 23 à 15s = 2.8x growth)
        if snapshot_1min['txn'] < 50:  # Minimum 50 transactions (réduit de 60)
            return None

        volume_growth_1min = snapshot_1min['txn'] / max(snapshot_15s['txn'], 1)
        if volume_growth_1min < 2.5:  # Volume doit au moins x2.5 de 15s à 1min
            return None

        # Buy ratio doit rester stable (pas de chute de plus de 20%)
        buy_ratio_drop = snapshot_15s['buy_ratio'] - snapshot_1min['buy_ratio']
        if buy_ratio_drop > 0.20:  # Max 20% de baisse autorisée (augmenté de 10%)
            return None

        # SI TOUS LES CRITÈRES SONT REMPLIS → RUNNER PATTERN DÉTECTÉ!
        return {
            'tier1_score': f"{snapshot_15s['txn']} txn, {snapshot_15s['traders']} traders, {snapshot_15s['buy_ratio']*100:.1f}% buys",
            'tier2_growth': f"Volume x{volume_growth_30s:.1f} @ 30s",
            'tier3_confirmation': f"Volume x{volume_growth_1min:.1f} @ 1min, {snapshot_1min['txn']} txn",
            'buy_ratio_stable': snapshot_1min['buy_ratio'] >= (snapshot_15s['buy_ratio'] - 0.20)
        }

    def display_formula(self):
        """Afficher la formule mathématique découverte"""
        runners = [a for a in self.completed_analysis if a['is_runner']]
        flops = [a for a in self.completed_analysis if not a['is_runner']]

        print(f"\n\n{'='*80}")
        print(f"FORMULE MATHEMATIQUE DECOUVERTE")
        print(f"{'='*80}")
        print(f"Echantillon: {len(runners)} runners / {len(flops)} flops")

        if runners:
            print(f"\n[RUNNERS - Pattern moyen]")

            # 10s stats (si disponible)
            runners_10s = [r for r in runners if r.get('10s') is not None]
            if runners_10s:
                avg_10s_txn = sum(r['10s']['txn'] for r in runners_10s) / len(runners_10s)
                avg_10s_buy = sum(r['10s']['buy_ratio'] for r in runners_10s) / len(runners_10s)
                print(f"  10s:  {avg_10s_txn:.1f} txn | {avg_10s_buy*100:.1f}% buys")

            # 15s stats (si disponible)
            runners_15s = [r for r in runners if r.get('15s') is not None]
            if runners_15s:
                avg_15s_txn = sum(r['15s']['txn'] for r in runners_15s) / len(runners_15s)
                avg_15s_buy = sum(r['15s']['buy_ratio'] for r in runners_15s) / len(runners_15s)
                print(f"  15s:  {avg_15s_txn:.1f} txn | {avg_15s_buy*100:.1f}% buys")

            # 20s stats (si disponible)
            runners_20s = [r for r in runners if r['20s'] is not None]
            if runners_20s:
                avg_20s_txn = sum(r['20s']['txn'] for r in runners_20s) / len(runners_20s)
                avg_20s_buy = sum(r['20s']['buy_ratio'] for r in runners_20s) / len(runners_20s)
                print(f"  20s:  {avg_20s_txn:.1f} txn | {avg_20s_buy*100:.1f}% buys")

            avg_30s_txn = sum(r['30s']['txn'] for r in runners) / len(runners)
            avg_30s_buy = sum(r['30s']['buy_ratio'] for r in runners) / len(runners)
            avg_1min_txn = sum(r['1min']['txn'] for r in runners) / len(runners)
            avg_1min_buy = sum(r['1min']['buy_ratio'] for r in runners) / len(runners)

            print(f"  30s:  {avg_30s_txn:.1f} txn | {avg_30s_buy*100:.1f}% buys")
            print(f"  1min: {avg_1min_txn:.1f} txn | {avg_1min_buy*100:.1f}% buys")

        if flops:
            print(f"\n[FLOPS - Pattern moyen]")

            # 10s stats (si disponible)
            flops_10s = [f for f in flops if f.get('10s') is not None]
            if flops_10s:
                avg_10s_txn = sum(f['10s']['txn'] for f in flops_10s) / len(flops_10s)
                avg_10s_buy = sum(f['10s']['buy_ratio'] for f in flops_10s) / len(flops_10s)
                print(f"  10s:  {avg_10s_txn:.1f} txn | {avg_10s_buy*100:.1f}% buys")

            # 15s stats (si disponible)
            flops_15s = [f for f in flops if f.get('15s') is not None]
            if flops_15s:
                avg_15s_txn = sum(f['15s']['txn'] for f in flops_15s) / len(flops_15s)
                avg_15s_buy = sum(f['15s']['buy_ratio'] for f in flops_15s) / len(flops_15s)
                print(f"  15s:  {avg_15s_txn:.1f} txn | {avg_15s_buy*100:.1f}% buys")

            # 20s stats (si disponible)
            flops_20s = [f for f in flops if f['20s'] is not None]
            if flops_20s:
                avg_20s_txn = sum(f['20s']['txn'] for f in flops_20s) / len(flops_20s)
                avg_20s_buy = sum(f['20s']['buy_ratio'] for f in flops_20s) / len(flops_20s)
                print(f"  20s:  {avg_20s_txn:.1f} txn | {avg_20s_buy*100:.1f}% buys")

            avg_30s_txn = sum(r['30s']['txn'] for r in flops) / len(flops)
            avg_30s_buy = sum(r['30s']['buy_ratio'] for r in flops) / len(flops)
            avg_1min_txn = sum(r['1min']['txn'] for r in flops) / len(flops)
            avg_1min_buy = sum(r['1min']['buy_ratio'] for r in flops) / len(flops)

            print(f"  30s:  {avg_30s_txn:.1f} txn | {avg_30s_buy*100:.1f}% buys")
            print(f"  1min: {avg_1min_txn:.1f} txn | {avg_1min_buy*100:.1f}% buys")

        print(f"{'='*80}\n")

    async def connect_and_run(self):
        """Connexion WebSocket"""
        uri = "wss://pumpportal.fun/api/data"

        async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
            # Subscribe to new tokens
            await ws.send(json.dumps({"method": "subscribeNewToken"}))
            print(f"[CONNECTED] Collecte de donnees en temps reel...")
            print(f"Objectif: Decouvrir la formule mathematique des runners\n")

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
    bot = PatternDiscoveryBot()
    await bot.connect_and_run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOPPED] Bot arrete")

"""
BOT DÉCOUVERTE DE PATTERN - Collecte temps réel
Enregistre: 10s, 15s, 20s, 30s, 1min, 2min, 3min, 5min, 8min, 10min
Complétion: 10 MINUTES (pour voir durée de vie complète)
Sauvegarder: Quand token atteint $25K OU 10min OU mort (pas de trade 3min)
Objectif: Trouver la formule mathématique des runners + détecter migrations

VERSION FIXÉE: Gestion robuste de l'encodage Unicode pour Windows
"""
import asyncio
import json
import websockets
from datetime import datetime
import time
import sys

# === FONCTION DE PROTECTION UNICODE POUR WINDOWS ===
def safe_print(msg):
    """Print avec protection contre les erreurs Unicode sur Windows"""
    try:
        print(msg)
    except UnicodeEncodeError:
        # Fallback: encoder en ASCII en ignorant les caractères problématiques
        safe_msg = msg.encode('ascii', 'ignore').decode('ascii')
        print(safe_msg)
    except Exception as e:
        # Dernier recours: afficher un message d'erreur simple
        print(f"[PRINT ERROR: {type(e).__name__}]")

# Configurer stdout pour UTF-8 si possible
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass  # Ignore si reconfigure n'est pas supporté

SOL_PRICE_USD = 200

# === CHARGEMENT DES WALLETS DE BALEINES ===
WHALE_WALLETS = set()
try:
    with open('whale_wallets.json', 'r', encoding='utf-8') as f:
        whale_data = json.load(f)
        WHALE_WALLETS = {w['trackedWalletAddress'] for w in whale_data}
    safe_print(f"[WHALE TRACKER] {len(WHALE_WALLETS)} wallets de baleines charges")
except Exception as e:
    safe_print(f"[WARNING] Impossible de charger whale_wallets.json: {e}")

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
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Charger les analyses completees
                    self.completed_analysis = data.get('completed', [])
                    # Charger les alertes
                    self.alerts = data.get('alerts', [])

                    safe_print(f"[CHARGEMENT] {len(self.completed_analysis)} tokens charges depuis la sauvegarde")
                    runners = [a for a in self.completed_analysis if a.get('is_runner', False)]
                    safe_print(f"[CHARGEMENT] {len(runners)} runners deja enregistres")
            except Exception as e:
                safe_print(f"[WARNING] Impossible de charger les donnees: {e}")
                safe_print("[INFO] Demarrage avec donnees vierges")

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
            # Tokens actifs (en cours d'analyse, pas encore completés)
            active_tokens = []
            for mint, token_data in self.tokens.items():
                age = time.time() - token_data.get('created_at', time.time())
                if age < 900:  # Garder seulement ceux < 15 minutes
                    active_tokens.append({
                        'mint': mint,
                        'symbol': token_data.get('symbol', 'N/A'),
                        'age_seconds': int(age),
                        'mc_initial': token_data.get('mc_initial', 0),
                        'mc_current': token_data.get('mc_current', 0),
                        'trade_count': len(token_data.get('trades', [])),
                        'snapshots': token_data.get('snapshots', {})
                    })

            data = {
                'tokens': active_tokens,  # Tokens en cours (< 15 min)
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

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            safe_print(f"[ERROR] Save data: {e}")

    async def handle_new_token(self, data):
        """Nouveau token détecté"""
        mint = data.get('mint')
        if not mint or mint in self.tokens:
            return

        # Utiliser le symbol ou les 8 premiers caractères du mint comme fallback
        symbol = data.get('symbol', '')
        if not symbol or symbol.strip() == '' or symbol == '???':
            symbol = f"[{mint[:8]}...]"

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
                '3s': None,
                '5s': None,
                '7s': None,
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
                '15min': None,
                '20min': None
            },
            'early_runner_saved': False,  # Flag pour ne pas sauvegarder 2 fois
            'completed': False,  # Token terminé ?
            'last_trade_time': time.time(),  # Pour détecter mort
            'migration_detected': False  # Pour détecter migration $69K
        }

        safe_print(f"\n[NEW TOKEN] {symbol} @ ${mc_usd:,.0f}")

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
            token['mc_current'] = mc_usd  # Pour le dashboard en temps réel

            # Calculer l'âge du token (nécessaire pour whale detection)
            age = current_time - token['created_at']

            token['trades'].append({
                'type': tx_type,
                'trader': trader,
                'mc': mc_usd,
                'time': current_time,
                'amount_sol': sol_amount,
                'amount_usd': amount_usd,
                'token_amount': token_amount,
                'is_whale': trader in WHALE_WALLETS
            })

            # Tracker l'activite des baleines
            if trader in WHALE_WALLETS:
                if mint not in self.whale_activity:
                    self.whale_activity[mint] = {
                        'wallets': [],
                        'total_volume_usd': 0,
                        'first_whale_entry_time': current_time
                    }
                if trader not in self.whale_activity[mint]['wallets']:
                    self.whale_activity[mint]['wallets'].append(trader)
                self.whale_activity[mint]['total_volume_usd'] += amount_usd

                safe_print(f"  [WHALE DETECTED] {token['symbol']} @ {age:.0f}s, MC=${mc_usd:,.0f}, {tx_type.upper()} ${amount_usd:.0f}")

            # Mettre à jour l'historique de prix
            token['price_history'].append({'mc': mc_usd, 'time': current_time})
            # Garder seulement les 30 dernières secondes
            token['price_history'] = [
                p for p in token['price_history']
                if current_time - p['time'] <= 30
            ]

            # ========== MIGRATION DETECTION ==========
            # Bonding curve complétée à ~$69K = MIGRATION vers PumpSwap !
            if mc_usd >= 69000 and not token['migration_detected'] and not token['completed']:
                token['migration_detected'] = True
                token['completed'] = True  # Marquer comme complété immédiatement

                # Créer les snapshots avec les données disponibles (incluant les nouveaux 3s, 5s, 7s)
                snapshot_3s = token['snapshots'].get('3s') or self.calculate_snapshot(token, 3)
                snapshot_5s = token['snapshots'].get('5s') or self.calculate_snapshot(token, 5)
                snapshot_7s = token['snapshots'].get('7s') or self.calculate_snapshot(token, 7)
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

                # Assigner les MC aux snapshots existants (incluant les nouveaux)
                if snapshot_3s:
                    snapshot_3s['mc'] = token['snapshots'].get('3s', {}).get('mc', mc_usd)
                if snapshot_5s:
                    snapshot_5s['mc'] = token['snapshots'].get('5s', {}).get('mc', mc_usd)
                if snapshot_7s:
                    snapshot_7s['mc'] = token['snapshots'].get('7s', {}).get('mc', mc_usd)
                if snapshot_10s:
                    snapshot_10s['mc'] = token['snapshots'].get('10s', {}).get('mc', mc_usd)
                if snapshot_15s:
                    snapshot_15s['mc'] = token['snapshots'].get('15s', {}).get('mc', mc_usd)
                if snapshot_20s:
                    snapshot_20s['mc'] = token['snapshots'].get('20s', {}).get('mc', mc_usd)
                if snapshot_30s:
                    snapshot_30s['mc'] = token['snapshots'].get('30s', {}).get('mc', mc_usd)

                # Calculer holders et traders
                holders_traders_data = self.calculate_holders_and_traders(token)
                whale_info = self.whale_activity.get(mint, {})

                # SAUVEGARDER LE TOKEN IMMÉDIATEMENT (incluant les nouveaux snapshots)
                result = {
                    'symbol': token['symbol'],
                    'mint': mint,
                    '3s': snapshot_3s,
                    '5s': snapshot_5s,
                    '7s': snapshot_7s,
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
                    'migration_price': mc_usd,
                    # === WHALE ACTIVITY ===
                    'whale_wallets_detected': whale_info.get('wallets', []),
                    'whale_count': len(whale_info.get('wallets', [])),
                    'whale_total_volume_usd': whale_info.get('total_volume_usd', 0),
                    # === HOLDERS & TRADERS ===
                    'top_10_holders': holders_traders_data['top_10_holders'],
                    'top_10_traders': holders_traders_data['top_10_traders'],
                    'supply_distribution': holders_traders_data['supply_distribution']
                }

                self.completed_analysis.append(result)

                safe_print(f"\n{'='*80}")
                safe_print(f"[MIGRATION PUMPSWAP!] {token['symbol']} @ ${mc_usd:,.0f} - BONDING CURVE COMPLETE!")
                safe_print(f"Token migre vers PumpSwap - Pump majeur detecte!")
                safe_print(f"Temps pour migration: {age:.1f}s")
                if snapshot_10s:
                    safe_print(f"  10s:  {snapshot_10s['txn']} txn | {snapshot_10s['buy_ratio']*100:.1f}% buys")
                if snapshot_1min:
                    safe_print(f"  1min: {snapshot_1min['txn']} txn | {snapshot_1min['buy_ratio']*100:.1f}% buys")
                if snapshot_5min:
                    safe_print(f"  5min: {snapshot_5min['txn']} txn | {snapshot_5min['buy_ratio']*100:.1f}% buys")
                safe_print(f"{'='*80}")

                self.alerts.append({
                    'type': 'migration',
                    'symbol': token['symbol'],
                    'mint': mint,
                    'message': f"MIGRATION PUMPSWAP @ ${mc_usd:,.0f} en {age:.1f}s",
                    'timestamp': datetime.now().isoformat()
                })
                self.save_data()

            # ========== STRONG RUNNER DETECTION ($40K+) ==========
            # Si le token atteint $40K+, afficher une alerte mais continuer à tracker jusqu'à 15min!
            if mc_usd >= 40000 and not token['completed'] and not token['early_runner_saved']:
                token['early_runner_saved'] = True

                # Juste afficher une alerte, mais NE PAS sauvegarder le token!
                # On continue à le tracker pour collecter TOUS les snapshots jusqu'à 15min
                snapshot_30s = token['snapshots'].get('30s')
                if snapshot_30s:
                    safe_print(f"\n{'='*80}")
                    safe_print(f"[STRONG RUNNER!] {token['symbol']} @ ${mc_usd:,.0f} en {age:.1f}s!")
                    safe_print(f"  Objectif: x4+ depuis $10K | Continuation du tracking...")
                    safe_print(f"{'='*80}")

                    # Alerte pour le dashboard
                    self.alerts.append({
                        'type': 'strong_runner',
                        'symbol': token['symbol'],
                        'mint': token['mint'],
                        'message': f"STRONG PUMP! ${mc_usd:,.0f} en {age:.1f}s - x4+ potentiel!",
                        'timestamp': datetime.now().isoformat()
                    })

            # DÉTECTION D'ACCÉLÉRATION dans la zone $7K-$15K
            if 7000 <= mc_usd <= 15000 and not token['acceleration_alerted'] and age >= 15:
                accel = self.detect_acceleration(token, mc_usd)
                if accel and accel['is_accelerating']:
                    token['acceleration_alerted'] = True
                    metrics = self.calculate_snapshot(token, 15)
                    safe_print(f"\n[ACCELERATION] {token['symbol']} @ ${mc_usd:,.0f}")
                    safe_print(f"   Velocite: ${accel['velocity']:.0f}/sec | Gain 10s: +${accel['gain_10s']:,.0f} (+{accel['pct_10s']:.1f}%)")
                    safe_print(f"   Trades 15s: {metrics['txn']} txn | {metrics['buy_ratio']*100:.1f}% buys")
                    safe_print(f"   SIGNAL D'ENTREE FORT!")

                    # Alerte pour le dashboard
                    self.alerts.append({
                        'type': 'rocket',
                        'symbol': token['symbol'],
                        'message': f"Velocite: ${accel['velocity']:.0f}/sec | Gain 10s: +{accel['pct_10s']:.1f}% | {metrics['txn']} txn | {metrics['buy_ratio']*100:.1f}% buys",
                        'timestamp': datetime.now().isoformat()
                    })
                    self.save_data()

            # Snapshot à 3 secondes (NOUVEAU - pour capturer le début)
            if age >= 3 and token['snapshots']['3s'] is None:
                snapshot = self.calculate_snapshot(token, 3)
                snapshot['mc'] = mc_usd
                token['snapshots']['3s'] = snapshot
                safe_print(f"  [3s] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 5 secondes (NOUVEAU)
            if age >= 5 and token['snapshots']['5s'] is None:
                snapshot = self.calculate_snapshot(token, 5)
                snapshot['mc'] = mc_usd
                token['snapshots']['5s'] = snapshot
                safe_print(f"  [5s] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 7 secondes (NOUVEAU)
            if age >= 7 and token['snapshots']['7s'] is None:
                snapshot = self.calculate_snapshot(token, 7)
                snapshot['mc'] = mc_usd
                token['snapshots']['7s'] = snapshot
                safe_print(f"  [7s] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 10 secondes
            if age >= 10 and token['snapshots']['10s'] is None:
                snapshot = self.calculate_snapshot(token, 10)
                snapshot['mc'] = mc_usd
                token['snapshots']['10s'] = snapshot
                smart_info = f" | BigBuys: {snapshot['big_buys_100']}" if snapshot['big_buys_100'] > 0 else ""
                safe_print(f"  [10s] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders{smart_info}")

            # Snapshot à 15 secondes
            if age >= 15 and token['snapshots']['15s'] is None:
                snapshot = self.calculate_snapshot(token, 15)
                snapshot['mc'] = mc_usd
                token['snapshots']['15s'] = snapshot
                smart_info = f" | BigBuys: {snapshot['big_buys_100']}" if snapshot['big_buys_100'] > 0 else ""
                whale_info_msg = f" | Whales: {snapshot['big_buys_500']}" if snapshot['big_buys_500'] > 0 else ""
                safe_print(f"  [15s] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders{smart_info}{whale_info_msg}")

                # ALERTE HIGH BUY RATIO dans la zone optimale
                if 7000 <= mc_usd <= 15000 and not token['acceleration_alerted']:
                    if snapshot['buy_ratio'] >= 0.68 and snapshot['txn'] >= 50:
                        token['acceleration_alerted'] = True
                        safe_print(f"\n[HIGH BUY RATIO] {token['symbol']} @ ${mc_usd:,.0f}")
                        safe_print(f"   Buy Ratio: {snapshot['buy_ratio']*100:.1f}% | {snapshot['txn']} txn | {snapshot['traders']} traders")
                        safe_print(f"   Big buys: {snapshot['big_buys_100']} >$100 | Whales: {snapshot['big_buys_500']} >$500")
                        safe_print(f"   Zone optimale: $7K-$15K | SIGNAL D'ENTREE FORT!")

                        # Alerte pour le dashboard
                        self.alerts.append({
                            'type': 'diamond',
                            'symbol': token['symbol'],
                            'message': f"Buy Ratio: {snapshot['buy_ratio']*100:.1f}% | {snapshot['txn']} txn | {snapshot['big_buys_100']} big buys | Zone: $7K-$15K",
                            'timestamp': datetime.now().isoformat()
                        })
                        self.save_data()

                # ALERTE SMART MONEY DETECTED
                if snapshot.get('smart_money_count', 0) >= 3 and age >= 15:
                    safe_print(f"\n[SMART MONEY DETECTED] {token['symbol']} @ ${mc_usd:,.0f}")
                    safe_print(f"   {snapshot['smart_money_count']} wallets ont achete >$200 dans les 15 premieres secondes!")
                    safe_print(f"   {snapshot['big_buys_100']} achats >$100 | {snapshot['big_buys_500']} whales >$500")
                    safe_print(f"   Volume d'achat total: ${snapshot['total_buy_volume']:.0f}")

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
                safe_print(f"  [20s] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 30 secondes
            if age >= 30 and token['snapshots']['30s'] is None:
                snapshot = self.calculate_snapshot(token, 30)
                snapshot['mc'] = mc_usd
                token['snapshots']['30s'] = snapshot
                safe_print(f"  [30s] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 1 minute
            if age >= 60 and token['snapshots']['1min'] is None:
                snapshot = self.calculate_snapshot(token, 60)
                snapshot['mc'] = mc_usd
                token['snapshots']['1min'] = snapshot
                safe_print(f"  [1min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 2 minutes
            if age >= 120 and token['snapshots']['2min'] is None:
                snapshot = self.calculate_snapshot(token, 120)
                snapshot['mc'] = mc_usd
                token['snapshots']['2min'] = snapshot
                safe_print(f"  [2min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 3 minutes
            if age >= 180 and token['snapshots']['3min'] is None:
                snapshot = self.calculate_snapshot(token, 180)
                snapshot['mc'] = mc_usd
                token['snapshots']['3min'] = snapshot
                safe_print(f"  [3min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 5 minutes
            if age >= 300 and token['snapshots']['5min'] is None:
                snapshot = self.calculate_snapshot(token, 300)
                snapshot['mc'] = mc_usd
                token['snapshots']['5min'] = snapshot
                safe_print(f"  [5min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 8 minutes
            if age >= 480 and token['snapshots']['8min'] is None:
                snapshot = self.calculate_snapshot(token, 480)
                snapshot['mc'] = mc_usd
                token['snapshots']['8min'] = snapshot
                safe_print(f"  [8min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 10 minutes
            if age >= 600 and token['snapshots']['10min'] is None:
                snapshot = self.calculate_snapshot(token, 600)
                snapshot['mc'] = mc_usd
                token['snapshots']['10min'] = snapshot
                safe_print(f"  [10min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

            # Snapshot à 15 minutes
            if age >= 900 and token['snapshots'].get('15min') is None:
                snapshot = self.calculate_snapshot(token, 900)
                snapshot['mc'] = mc_usd
                token['snapshots']['15min'] = snapshot
                safe_print(f"  [15min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

                # SAUVEGARDER LE TOKEN APRÈS 15 MINUTES!
                if not token['completed']:
                    # RUNNER = MC final >= $40K APRÈS 15 minutes (x4+ depuis $10K)
                    # FLOP = MC final < $40K (même s'il a atteint $40K+ avant et a dump)
                    is_runner = mc_usd >= 40000
                    holders_traders_data = self.calculate_holders_and_traders(token)
                    whale_info = self.whale_activity.get(mint, {})

                    # ========== CALCULER TOUTES LES MÉTRIQUES AVANCÉES POUR ML ==========
                    safe_print(f"  [ML METRICS] Calcul des métriques avancées pour {token['symbol']}...")
                    advanced_metrics = self.calculate_advanced_metrics(token)

                    result = {
                        'symbol': token['symbol'],
                        'mint': mint,
                        '3s': token['snapshots'].get('3s'),
                        '5s': token['snapshots'].get('5s'),
                        '7s': token['snapshots'].get('7s'),
                        '10s': token['snapshots'].get('10s'),
                        '15s': token['snapshots'].get('15s'),
                        '20s': token['snapshots'].get('20s'),
                        '30s': token['snapshots'].get('30s'),
                        '1min': token['snapshots'].get('1min'),
                        '2min': token['snapshots'].get('2min'),
                        '3min': token['snapshots'].get('3min'),
                        '5min': token['snapshots'].get('5min'),
                        '8min': token['snapshots'].get('8min'),
                        '10min': token['snapshots'].get('10min'),
                        '15min': token['snapshots'].get('15min'),
                        '20min': token['snapshots'].get('20min'),
                        'final_mc': mc_usd,
                        'is_runner': is_runner,
                        'pump_time': age,
                        'migration_detected': token['migration_detected'],
                        'whale_wallets_detected': whale_info.get('wallets', []),
                        'whale_count': len(whale_info.get('wallets', [])),
                        'whale_total_volume_usd': whale_info.get('total_volume_usd', 0),
                        'top_10_holders': holders_traders_data['top_10_holders'],
                        'top_10_traders': holders_traders_data['top_10_traders'],
                        'supply_distribution': holders_traders_data['supply_distribution'],
                        # NOUVELLES MÉTRIQUES ML
                        'ml_metrics': advanced_metrics
                    }

                    self.completed_analysis.append(result)
                    token['completed'] = True

                    safe_print(f"\n{'='*80}")
                    safe_print(f"[15MIN COMPLETE] {token['symbol']} @ ${mc_usd:,.0f} - {'RUNNER' if is_runner else 'FLOP'}")
                    safe_print(f"Duree de vie: 15 minutes | MC Final: ${mc_usd:,.0f}")
                    safe_print(f"Tous les snapshots collectes!")
                    safe_print(f"{'='*80}")

                    self.save_data()

            # Snapshot à 20 minutes - CONTINUER À TRACKER
            if age >= 1200 and token['snapshots']['20min'] is None:
                snapshot = self.calculate_snapshot(token, 1200)
                snapshot['mc'] = mc_usd
                token['snapshots']['20min'] = snapshot
                safe_print(f"  [20min] {token['symbol']}: ${mc_usd:,.0f} | {snapshot['txn']} txn | {snapshot['buy_ratio']*100:.1f}% buys | {snapshot['traders']} traders")

                # Afficher formule si on a 10+ tokens
                if len(self.completed_analysis) >= 10:
                    self.display_formula()

            # ===== VÉRIFICATION TOKEN MORT =====
            # Si pas de trade depuis 3 minutes ET pas encore complété, sauvegarder
            time_since_last_trade = current_time - token['last_trade_time']
            if time_since_last_trade >= 180 and not token['completed'] and age >= 60:
                # Token mort, sauvegarder ce qu'on a
                is_runner = mc_usd >= 25000

                # Calculer holders et traders
                holders_traders_data = self.calculate_holders_and_traders(token)
                whale_info = self.whale_activity.get(mint, {})

                result = {
                    'symbol': token['symbol'],
                    'mint': mint,
                    '3s': token['snapshots'].get('3s'),
                    '5s': token['snapshots'].get('5s'),
                    '7s': token['snapshots'].get('7s'),
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
                    'migration_detected': token['migration_detected'],
                    # === WHALE ACTIVITY ===
                    'whale_wallets_detected': whale_info.get('wallets', []),
                    'whale_count': len(whale_info.get('wallets', [])),
                    'whale_total_volume_usd': whale_info.get('total_volume_usd', 0),
                    # === HOLDERS & TRADERS ===
                    'top_10_holders': holders_traders_data['top_10_holders'],
                    'top_10_traders': holders_traders_data['top_10_traders'],
                    'supply_distribution': holders_traders_data['supply_distribution']
                }

                self.completed_analysis.append(result)
                token['completed'] = True

                safe_print(f"\n{'='*80}")
                safe_print(f"[TOKEN MORT] {token['symbol']} @ {age:.0f}s -> ${mc_usd:,.0f} {'RUNNER' if is_runner else 'FLOP'}")
                safe_print(f"  Pas de trade depuis 3 minutes")
                safe_print(f"{'='*80}")

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

        # WHALE METRICS
        whale_trades = [t for t in trades_in_period if t.get('is_whale', False)]
        whale_wallets_in_period = set(t['trader'] for t in whale_trades)
        whale_volume_usd = sum(t.get('amount_usd', 0) for t in whale_trades)

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
            'whale_ratio': big_buys_500 / len(buys) if buys else 0,  # % de whales
            # WHALE METRICS
            'whale_count': len(whale_wallets_in_period),
            'whale_volume_usd': whale_volume_usd,
            'whale_trades_ratio': len(whale_trades) / len(trades_in_period) if trades_in_period else 0,
            'whale_wallets': list(whale_wallets_in_period)[:10]
        }

    def calculate_holders_and_traders(self, token):
        """Calculer les top holders et traders d'un token"""
        trades = token.get('trades', [])

        # Dictionnaires pour tracking
        wallet_balances = {}  # {wallet: balance en tokens}
        wallet_volumes = {}   # {wallet: volume total en USD}
        wallet_buy_volume = {}
        wallet_sell_volume = {}

        # Process all trades
        for trade in trades:
            wallet = trade.get('trader', '')
            sol_amount = trade.get('amount_sol', 0)
            value_usd = trade.get('amount_usd', 0)
            is_buy = trade['type'] == 'buy'

            # Initialiser le wallet s'il n'existe pas
            if wallet not in wallet_balances:
                wallet_balances[wallet] = 0
                wallet_volumes[wallet] = 0
                wallet_buy_volume[wallet] = 0
                wallet_sell_volume[wallet] = 0

            # Mettre à jour le volume
            wallet_volumes[wallet] += value_usd

            if is_buy:
                wallet_balances[wallet] += sol_amount  # Approximation
                wallet_buy_volume[wallet] += value_usd
            else:
                wallet_balances[wallet] -= sol_amount
                wallet_sell_volume[wallet] += value_usd

        # Trier pour obtenir les tops
        top_holders = sorted(
            [(wallet, balance) for wallet, balance in wallet_balances.items() if balance > 0],
            key=lambda x: x[1],
            reverse=True
        )[:10]

        top_traders = sorted(
            [(wallet, volume, wallet_buy_volume[wallet], wallet_sell_volume[wallet])
             for wallet, volume in wallet_volumes.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Calculer la distribution
        total_balance = sum(balance for wallet, balance in wallet_balances.items() if balance > 0)
        top_3_balance = sum(balance for wallet, balance in top_holders[:3])
        top_5_balance = sum(balance for wallet, balance in top_holders[:5])
        top_10_balance = sum(balance for wallet, balance in top_holders[:10])

        return {
            'top_10_holders': [
                {
                    'wallet': wallet,
                    'balance': balance,
                    'is_whale': wallet in WHALE_WALLETS
                }
                for wallet, balance in top_holders
            ],
            'top_10_traders': [
                {
                    'wallet': wallet,
                    'total_volume_usd': volume,
                    'buy_volume_usd': buy_vol,
                    'sell_volume_usd': sell_vol,
                    'buy_sell_ratio': buy_vol / sell_vol if sell_vol > 0 else 0,
                    'is_whale': wallet in WHALE_WALLETS
                }
                for wallet, volume, buy_vol, sell_vol in top_traders
            ],
            'supply_distribution': {
                'total_holders': len([b for b in wallet_balances.values() if b > 0]),
                'top_3_percent': (top_3_balance / total_balance * 100) if total_balance > 0 else 0,
                'top_5_percent': (top_5_balance / total_balance * 100) if total_balance > 0 else 0,
                'top_10_percent': (top_10_balance / total_balance * 100) if total_balance > 0 else 0
            }
        }

    def calculate_advanced_metrics(self, token):
        """Calculer TOUTES les métriques avancées pour ML"""
        trades = token.get('trades', [])
        snapshots = token.get('snapshots', {})
        created_at = token['created_at']

        # ========== 1. PRICE VELOCITY & MOMENTUM ==========
        velocity_metrics = {}

        # Calculer vélocités entre snapshots
        snap_times = ['10s', '30s', '1min', '3min', '5min', '10min', '15min']
        snap_seconds = [10, 30, 60, 180, 300, 600, 900]

        velocities = []
        for i in range(len(snap_times) - 1):
            snap1 = snapshots.get(snap_times[i])
            snap2 = snapshots.get(snap_times[i+1])

            if snap1 and snap2 and snap1.get('mc') and snap2.get('mc'):
                mc1 = snap1['mc']
                mc2 = snap2['mc']
                time_diff = snap_seconds[i+1] - snap_seconds[i]
                velocity = (mc2 - mc1) / time_diff if time_diff > 0 else 0
                velocities.append(velocity)
                velocity_metrics[f'velocity_{snap_times[i]}_to_{snap_times[i+1]}'] = velocity

        velocity_metrics['peak_velocity'] = max(velocities) if velocities else 0
        velocity_metrics['avg_velocity'] = sum(velocities) / len(velocities) if velocities else 0

        # Accélération (changement de vélocité)
        if len(velocities) >= 2:
            acceleration = velocities[-1] - velocities[0]
            velocity_metrics['acceleration'] = acceleration
        else:
            velocity_metrics['acceleration'] = 0

        # Gain % depuis le début
        first_mc = snapshots.get('10s', {}).get('mc', 0)
        final_mc = snapshots.get('15min', {}).get('mc', 0)
        if first_mc > 0:
            velocity_metrics['gain_percent_from_start'] = ((final_mc - first_mc) / first_mc) * 100
        else:
            velocity_metrics['gain_percent_from_start'] = 0

        # ========== 2. TIMING TO MILESTONES ==========
        milestones = [10000, 20000, 30000, 40000, 50000, 69000]
        milestone_metrics = {}

        for milestone in milestones:
            time_to_milestone = None
            for trade in trades:
                if trade.get('mc', 0) >= milestone:
                    time_to_milestone = trade['time'] - created_at
                    break
            milestone_metrics[f'time_to_{milestone//1000}k'] = time_to_milestone

        # ========== 3. ATH & DRAWDOWN ==========
        all_mcs = [t.get('mc', 0) for t in trades]

        ath_metrics = {}
        if all_mcs:
            ath_mc = max(all_mcs)
            ath_metrics['ath_mc'] = ath_mc

            # Trouver le temps du ATH
            for trade in trades:
                if trade.get('mc') == ath_mc:
                    ath_metrics['ath_time'] = trade['time'] - created_at
                    break

            # Drawdown depuis ATH
            if ath_mc > 0 and final_mc > 0:
                drawdown = ((ath_mc - final_mc) / ath_mc) * 100
                ath_metrics['max_drawdown_percent'] = drawdown
                ath_metrics['drawdown_at_15min'] = drawdown
            else:
                ath_metrics['max_drawdown_percent'] = 0
                ath_metrics['drawdown_at_15min'] = 0

            # Volatilité (écart-type)
            import statistics
            if len(all_mcs) > 1:
                ath_metrics['volatility'] = statistics.stdev(all_mcs)
            else:
                ath_metrics['volatility'] = 0

            # Compter pumps et dumps
            num_pumps = 0
            num_dumps = 0
            for i in range(1, len(all_mcs)):
                pct_change = ((all_mcs[i] - all_mcs[i-1]) / all_mcs[i-1] * 100) if all_mcs[i-1] > 0 else 0
                if pct_change >= 20:
                    num_pumps += 1
                elif pct_change <= -30:
                    num_dumps += 1

            ath_metrics['num_pumps'] = num_pumps
            ath_metrics['num_dumps'] = num_dumps
        else:
            ath_metrics = {
                'ath_mc': 0, 'ath_time': None, 'max_drawdown_percent': 0,
                'drawdown_at_15min': 0, 'volatility': 0,
                'num_pumps': 0, 'num_dumps': 0
            }

        # ========== 4. WHALE BEHAVIOR TIMING ==========
        whale_timing = {}

        # Whale activity data
        mint = token['mint']
        whale_info = self.whale_activity.get(mint, {})

        if whale_info:
            whale_timing['first_whale_entry_time'] = whale_info.get('first_whale_entry_time', 0) - created_at

            # Trouver le MC quand la première whale est entrée
            first_whale_time = whale_info.get('first_whale_entry_time', 0)
            first_whale_mc = 0
            for trade in trades:
                if trade['time'] >= first_whale_time and trade.get('is_whale'):
                    first_whale_mc = trade.get('mc', 0)
                    break
            whale_timing['first_whale_entry_mc'] = first_whale_mc

            # Compter whales par tranche de prix
            whale_entry_before_10k = 0
            whale_entry_10k_to_20k = 0
            whale_entry_20k_to_40k = 0
            whale_exit_count = 0

            for trade in trades:
                if trade.get('is_whale'):
                    mc = trade.get('mc', 0)
                    if trade['type'] == 'buy':
                        if mc < 10000:
                            whale_entry_before_10k += 1
                        elif mc < 20000:
                            whale_entry_10k_to_20k += 1
                        elif mc < 40000:
                            whale_entry_20k_to_40k += 1
                    elif trade['type'] == 'sell':
                        whale_exit_count += 1

            whale_timing['whale_entry_before_10k'] = whale_entry_before_10k
            whale_timing['whale_entry_10k_to_20k'] = whale_entry_10k_to_20k
            whale_timing['whale_entry_20k_to_40k'] = whale_entry_20k_to_40k
            whale_timing['whale_exit_count'] = whale_exit_count
        else:
            whale_timing = {
                'first_whale_entry_time': None,
                'first_whale_entry_mc': 0,
                'whale_entry_before_10k': 0,
                'whale_entry_10k_to_20k': 0,
                'whale_entry_20k_to_40k': 0,
                'whale_exit_count': 0
            }

        # ========== 5. HOLDER CONVICTION ==========
        trader_behavior = {}

        # Analyser le comportement des traders
        trader_first_buy = {}
        trader_last_action = {}

        for trade in trades:
            trader = trade['trader']
            trade_time = trade['time']

            if trader not in trader_first_buy:
                if trade['type'] == 'buy':
                    trader_first_buy[trader] = trade_time

            trader_last_action[trader] = trade_time

        # Calculer hold times
        hold_times = []
        paper_hands = 0  # Vendent en <60s
        diamond_hands = 0  # Hold >300s avec >$500

        for trader in trader_first_buy:
            first_buy = trader_first_buy[trader]
            last_action = trader_last_action.get(trader, first_buy)
            hold_time = last_action - first_buy
            hold_times.append(hold_time)

            if hold_time < 60:
                paper_hands += 1
            elif hold_time > 300:
                # Vérifier si c'est un gros holder
                trader_volume = sum(t.get('amount_usd', 0) for t in trades if t['trader'] == trader and t['type'] == 'buy')
                if trader_volume > 500:
                    diamond_hands += 1

        trader_behavior['avg_hold_time'] = sum(hold_times) / len(hold_times) if hold_times else 0
        trader_behavior['paper_hands_count'] = paper_hands
        trader_behavior['diamond_hands_count'] = diamond_hands

        # Taux d'arrivée de nouveaux traders
        total_time = (trades[-1]['time'] - trades[0]['time']) if len(trades) > 1 else 1
        unique_traders = len(set(t['trader'] for t in trades))
        trader_behavior['new_traders_per_second'] = unique_traders / total_time if total_time > 0 else 0

        # Ratio holders vs flippers
        holders = sum(1 for t in hold_times if t > 180)  # Hold >3min
        trader_behavior['holder_ratio'] = holders / len(hold_times) if hold_times else 0

        # Combiner toutes les métriques
        return {
            **velocity_metrics,
            **milestone_metrics,
            **ath_metrics,
            **whale_timing,
            **trader_behavior
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

    def display_formula(self):
        """Afficher la formule mathématique découverte"""
        runners = [a for a in self.completed_analysis if a['is_runner']]
        flops = [a for a in self.completed_analysis if not a['is_runner']]

        safe_print(f"\n\n{'='*80}")
        safe_print(f"FORMULE MATHEMATIQUE DECOUVERTE")
        safe_print(f"{'='*80}")
        safe_print(f"Echantillon: {len(runners)} runners / {len(flops)} flops")

        if runners:
            safe_print(f"\n[RUNNERS - Pattern moyen]")

            # 10s stats (si disponible)
            runners_10s = [r for r in runners if r.get('10s') is not None]
            if runners_10s:
                avg_10s_txn = sum(r['10s']['txn'] for r in runners_10s) / len(runners_10s)
                avg_10s_buy = sum(r['10s']['buy_ratio'] for r in runners_10s) / len(runners_10s)
                safe_print(f"  10s:  {avg_10s_txn:.1f} txn | {avg_10s_buy*100:.1f}% buys")

            # 15s stats (si disponible)
            runners_15s = [r for r in runners if r.get('15s') is not None]
            if runners_15s:
                avg_15s_txn = sum(r['15s']['txn'] for r in runners_15s) / len(runners_15s)
                avg_15s_buy = sum(r['15s']['buy_ratio'] for r in runners_15s) / len(runners_15s)
                safe_print(f"  15s:  {avg_15s_txn:.1f} txn | {avg_15s_buy*100:.1f}% buys")

            # 20s stats (si disponible)
            runners_20s = [r for r in runners if r['20s'] is not None]
            if runners_20s:
                avg_20s_txn = sum(r['20s']['txn'] for r in runners_20s) / len(runners_20s)
                avg_20s_buy = sum(r['20s']['buy_ratio'] for r in runners_20s) / len(runners_20s)
                safe_print(f"  20s:  {avg_20s_txn:.1f} txn | {avg_20s_buy*100:.1f}% buys")

            avg_30s_txn = sum(r['30s']['txn'] for r in runners) / len(runners)
            avg_30s_buy = sum(r['30s']['buy_ratio'] for r in runners) / len(runners)
            avg_1min_txn = sum(r['1min']['txn'] for r in runners) / len(runners)
            avg_1min_buy = sum(r['1min']['buy_ratio'] for r in runners) / len(runners)

            safe_print(f"  30s:  {avg_30s_txn:.1f} txn | {avg_30s_buy*100:.1f}% buys")
            safe_print(f"  1min: {avg_1min_txn:.1f} txn | {avg_1min_buy*100:.1f}% buys")

        if flops:
            safe_print(f"\n[FLOPS - Pattern moyen]")

            # 10s stats (si disponible)
            flops_10s = [f for f in flops if f.get('10s') is not None]
            if flops_10s:
                avg_10s_txn = sum(f['10s']['txn'] for f in flops_10s) / len(flops_10s)
                avg_10s_buy = sum(f['10s']['buy_ratio'] for f in flops_10s) / len(flops_10s)
                safe_print(f"  10s:  {avg_10s_txn:.1f} txn | {avg_10s_buy*100:.1f}% buys")

            # 15s stats (si disponible)
            flops_15s = [f for f in flops if f.get('15s') is not None]
            if flops_15s:
                avg_15s_txn = sum(f['15s']['txn'] for f in flops_15s) / len(flops_15s)
                avg_15s_buy = sum(f['15s']['buy_ratio'] for f in flops_15s) / len(flops_15s)
                safe_print(f"  15s:  {avg_15s_txn:.1f} txn | {avg_15s_buy*100:.1f}% buys")

            # 20s stats (si disponible)
            flops_20s = [f for f in flops if f['20s'] is not None]
            if flops_20s:
                avg_20s_txn = sum(f['20s']['txn'] for f in flops_20s) / len(flops_20s)
                avg_20s_buy = sum(f['20s']['buy_ratio'] for f in flops_20s) / len(flops_20s)
                safe_print(f"  20s:  {avg_20s_txn:.1f} txn | {avg_20s_buy*100:.1f}% buys")

            avg_30s_txn = sum(r['30s']['txn'] for r in flops) / len(flops)
            avg_30s_buy = sum(r['30s']['buy_ratio'] for r in flops) / len(flops)
            avg_1min_txn = sum(r['1min']['txn'] for r in flops) / len(flops)
            avg_1min_buy = sum(r['1min']['buy_ratio'] for r in flops) / len(flops)

            safe_print(f"  30s:  {avg_30s_txn:.1f} txn | {avg_30s_buy*100:.1f}% buys")
            safe_print(f"  1min: {avg_1min_txn:.1f} txn | {avg_1min_buy*100:.1f}% buys")

        safe_print(f"{'='*80}\n")

    async def periodic_save_task(self):
        """Sauvegarde périodique toutes les 30 secondes"""
        while True:
            await asyncio.sleep(30)
            self.save_data()

    async def connect_and_run(self):
        """Connexion WebSocket"""
        uri = "wss://pumpportal.fun/api/data"

        async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
            # Subscribe to new tokens
            await ws.send(json.dumps({"method": "subscribeNewToken"}))
            safe_print(f"[CONNECTED] Collecte de donnees en temps reel...")
            safe_print(f"Objectif: Decouvrir la formule mathematique des runners\n")

            # Lancer la sauvegarde périodique en arrière-plan
            asyncio.create_task(self.periodic_save_task())

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
                    safe_print(f"[ERROR] {e}")
                    continue

async def main():
    bot = PatternDiscoveryBot()
    await bot.connect_and_run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        safe_print("\n[STOPPED] Bot arrete")

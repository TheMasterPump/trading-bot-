"""
LIVE DASHBOARD BOT V2 - Avec Surveillance Continue
Surveille les tokens qui commencent en dessous de $9.5k et achète quand ils montent
"""
import asyncio
import json
import websockets
from datetime import datetime, timedelta
import random
import os
import requests

# COULEURS ANSI - Style Bleu
class Colors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    GRAY = '\033[90m'
    BRIGHT_BLUE = '\033[38;5;39m'

# CONFIG
OPTIMAL_WINDOW = {
    'min_mc': 9500,
    'max_mc': 13000,
    'migration_mc': 69000,
}

BUY_AMOUNT_SOL = 2.5
SOL_PRICE_USD = 200
WATCH_DURATION_MINUTES = 30  # Surveiller tokens pendant 30 min max

class Position:
    def __init__(self, token_data, buy_sol):
        self.mint = token_data['mint']
        self.symbol = token_data['symbol']
        self.name = token_data['name']
        self.entry_mc = token_data['market_cap_usd']
        self.entry_sol = buy_sol
        self.entry_price = token_data.get('price_sol', 0.00001)
        self.entry_time = datetime.now()
        self.entry_tokens = buy_sol / self.entry_price if self.entry_price > 0 else 0
        self.score = token_data['score']
        self.current_mc = self.entry_mc
        self.migrated = False
        self.sold = False
        self.exit_sol = 0
        self.profit_sol = 0
        self.roi_pct = 0

    def update_mc(self, new_mc):
        self.current_mc = new_mc

    def calculate_unrealized(self):
        multiplier = self.current_mc / self.entry_mc
        unrealized_exit = self.entry_sol * multiplier
        unrealized_profit = unrealized_exit - self.entry_sol
        unrealized_roi = (multiplier - 1) * 100
        return {
            'multiplier': multiplier,
            'exit': unrealized_exit,
            'profit': unrealized_profit,
            'roi': unrealized_roi
        }


class LiveDashboardBot:
    def __init__(self):
        self.wallet_sol = 100.0
        self.start_wallet = 100.0
        self.seen_tokens = set()
        self.seen_above_8k = set()  # Tokens déjà vus >= $8K
        self.all_tokens = {}  # {mint: {mc_usd, symbol, txnCount, holders, ...}}
        self.watch_list = {}  # NOUVEAU: Tokens en dessous de $9.5k à surveiller
        self.open_positions = {}
        self.completed_trades = []
        self.total_profit_sol = 0
        self.tokens_scanned = 0
        self.tokens_bought = 0
        self.tokens_migrated = 0
        self.last_tokens = []
        self.running = True
        self.ws = None  # WebSocket connection

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_dashboard(self):
        """Affiche dashboard avec watch list"""
        self.clear_screen()

        now = datetime.now().strftime('%H:%M:%S')

        print(f"{Colors.BRIGHT_BLUE}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}       LIVE TRADING BOT DASHBOARD V2 - {now}{Colors.RESET}")
        print(f"{Colors.BRIGHT_BLUE}{'=' * 80}{Colors.RESET}")

        # WALLET
        print(f"\n{Colors.BLUE}[WALLET]{Colors.RESET}")
        print(f"  {Colors.CYAN}Current:{Colors.RESET} {self.wallet_sol:.2f} SOL (${self.wallet_sol * SOL_PRICE_USD:,.0f})")
        pnl_color = Colors.GREEN if self.total_profit_sol >= 0 else Colors.RED
        print(f"  {Colors.CYAN}P&L:{Colors.RESET} {pnl_color}{self.total_profit_sol:+.4f} SOL (${self.total_profit_sol * SOL_PRICE_USD:+.2f}){Colors.RESET}")

        change_pct = ((self.wallet_sol - self.start_wallet) / self.start_wallet) * 100
        change_color = Colors.GREEN if change_pct >= 0 else Colors.RED
        print(f"  {Colors.CYAN}Change:{Colors.RESET} {change_color}{change_pct:+.1f}%{Colors.RESET}")

        # STATISTICS
        print(f"\n{Colors.BLUE}[STATISTICS]{Colors.RESET}")
        print(f"  {Colors.CYAN}Scanned:{Colors.RESET} {self.tokens_scanned}")
        print(f"  {Colors.CYAN}Watching:{Colors.RESET} {Colors.YELLOW}{len(self.watch_list)}{Colors.RESET}")  # NOUVEAU
        print(f"  {Colors.CYAN}Bought:{Colors.RESET} {self.tokens_bought}")
        print(f"  {Colors.CYAN}Migrated:{Colors.RESET} {self.tokens_migrated}")

        if self.completed_trades:
            winners = [t for t in self.completed_trades if t.profit_sol > 0]
            win_rate = (len(winners) / len(self.completed_trades)) * 100
            wr_color = Colors.GREEN if win_rate >= 70 else Colors.YELLOW if win_rate >= 50 else Colors.RED
            print(f"  {Colors.CYAN}Win Rate:{Colors.RESET} {wr_color}{win_rate:.0f}% ({len(winners)}/{len(self.completed_trades)}){Colors.RESET}")

        # WATCH LIST - NOUVEAU
        if self.watch_list:
            print(f"\n{Colors.BLUE}[WATCH LIST]{Colors.RESET} {Colors.GRAY}(Tokens below $9.5k){Colors.RESET}")
            sorted_watch = sorted(self.watch_list.items(), key=lambda x: x[1]['last_mc'], reverse=True)[:5]
            for mint, info in sorted_watch:
                age_sec = (datetime.now() - info['first_seen']).total_seconds()
                age_min = int(age_sec / 60)
                mc = info['last_mc']
                symbol = info['data'].get('symbol', '???')

                # Progress bar vers $9.5k
                progress = min(mc / OPTIMAL_WINDOW['min_mc'], 1.0)
                bar_width = 20
                filled = int(bar_width * progress)
                bar = '█' * filled + '░' * (bar_width - filled)

                print(f"  {Colors.YELLOW}{symbol:8s}{Colors.RESET} ${mc:6,.0f} [{bar}] {progress*100:.0f}% - {age_min}m")

        # OPEN POSITIONS
        if self.open_positions:
            print(f"\n{Colors.BLUE}[OPEN POSITIONS]{Colors.RESET}")
            for mint, pos in self.open_positions.items():
                unrealized = pos.calculate_unrealized()

                # Progress bar vers migration
                progress = min(pos.current_mc / OPTIMAL_WINDOW['migration_mc'], 1.0)
                bar_width = 20
                filled = int(bar_width * progress)
                bar = '█' * filled + '░' * (bar_width - filled)

                roi_color = Colors.GREEN if unrealized['roi'] >= 0 else Colors.RED

                print(f"  {Colors.CYAN}{pos.symbol:8s}{Colors.RESET} ${pos.current_mc:6,.0f} [{bar}] {roi_color}{unrealized['roi']:+.0f}%{Colors.RESET}")

        # RECENT TRADES
        if self.completed_trades:
            print(f"\n{Colors.BLUE}[RECENT TRADES]{Colors.RESET}")
            for trade in self.completed_trades[-3:]:
                status_color = Colors.GREEN if trade.profit_sol > 0 else Colors.RED
                status = "WIN" if trade.profit_sol > 0 else "LOSS"
                print(f"  {Colors.CYAN}{trade.symbol:8s}{Colors.RESET} {status_color}{trade.profit_sol:+.2f} SOL ({trade.roi_pct:+.0f}%) - {status}{Colors.RESET}")

        # RECENT SCANS
        if self.last_tokens:
            print(f"\n{Colors.BLUE}[RECENT SCANS]{Colors.RESET}")
            for token in self.last_tokens[-5:]:
                status = token['status']
                status_color = Colors.GREEN if 'BOUGHT' in status else Colors.YELLOW if 'WINDOW' in status else Colors.GRAY
                print(f"  {status_color}{token['symbol']:8s}{Colors.RESET} ${token['mc']:6,.0f} - {status}")

        print(f"\n{Colors.BRIGHT_BLUE}{'=' * 80}{Colors.RESET}")

    def calculate_score(self, token_data):
        score = 0
        breakdown = {}

        # Transactions/Volume (0-40 pts) - PERMISSIF pour early tokens
        txn = token_data.get('txnCount', 0)
        txn_score = 0
        if txn >= 100: txn_score = 40      # Très actif
        elif txn >= 50: txn_score = 35     # Actif
        elif txn >= 30: txn_score = 30     # Bon volume
        elif txn >= 20: txn_score = 25     # Volume correct
        elif txn >= 10: txn_score = 20     # Volume moyen (AUGMENTÉ)
        elif txn >= 5: txn_score = 15      # Early stage (AUGMENTÉ)
        elif txn >= 3: txn_score = 10      # Très early (NOUVEAU)
        elif txn >= 1: txn_score = 5       # Just launched (NOUVEAU)
        score += txn_score
        breakdown['txn'] = txn_score

        # Initial Buy (0-20 pts) - 0-2 SOL acceptable, >2 SOL = red flag
        init = token_data.get('initialBuy', 0)
        init_score = 0
        if init > 2: init_score = 0        # RED FLAG: Dev farmer (>2 SOL)
        elif init >= 1: init_score = 20    # OPTIMAL (1-2 SOL)
        elif init >= 0.5: init_score = 15  # Bon (0.5-1 SOL)
        elif init >= 0.2: init_score = 10  # Acceptable (0.2-0.5 SOL)
        else: init_score = 5               # Acceptable (0-0.2 SOL, dev confiant)
        score += init_score
        breakdown['init'] = init_score

        # MC Position (0-20 pts) - Potentiel de gain
        mc = token_data.get('market_cap_usd', 0)
        mc_score = 0
        if OPTIMAL_WINDOW['min_mc'] <= mc <= OPTIMAL_WINDOW['max_mc']:
            if mc <= 10500: mc_score = 20
            elif mc <= 11500: mc_score = 15
            else: mc_score = 10
        score += mc_score
        breakdown['mc'] = mc_score

        # Early Bonus (0-15 pts) - NOUVEAU! Tous tokens WebSocket sont frais
        early_bonus = 15
        score += early_bonus
        breakdown['early'] = early_bonus

        # Social Bonus (0-10 pts) - Nice to have, pas obligatoire
        social = 0
        if token_data.get('twitter'): social += 4
        if token_data.get('telegram'): social += 3
        if token_data.get('website'): social += 3
        score += social
        breakdown['social'] = social

        # Quick Bundle Check (Penalty 0 to -20 pts) - NOUVEAU!
        holders = token_data.get('holderCount', 0)
        bundle_penalty = 0
        if holders > 10 and txn > 0:
            ratio = txn / holders
            if ratio < 1.3:    # Très suspect (presque 1 txn par holder)
                bundle_penalty = -20
                breakdown['bundle_warning'] = 'HIGH RISK'
            elif ratio < 1.5:  # Suspect
                bundle_penalty = -10
                breakdown['bundle_warning'] = 'MEDIUM RISK'
        score += bundle_penalty
        if bundle_penalty < 0:
            breakdown['bundle_penalty'] = bundle_penalty

        return {
            'total': max(0, min(score, 100)),
            'breakdown': breakdown,
            'should_buy': score >= 40,  # BAISSÉ de 50 à 40
            'confidence': 'HIGH' if score >= 60 else 'MEDIUM' if score >= 40 else 'LOW'
        }

    async def buy_token(self, token_data):
        if self.wallet_sol < BUY_AMOUNT_SOL:
            return None

        position = Position(token_data, BUY_AMOUNT_SOL)
        self.wallet_sol -= BUY_AMOUNT_SOL
        self.open_positions[position.mint] = position
        self.tokens_bought += 1

        self.last_tokens.append({
            'symbol': position.symbol,
            'mc': position.entry_mc,
            'score': position.score['total'],
            'status': f'BOUGHT {BUY_AMOUNT_SOL} SOL'
        })

        # Simulate migration (70% chance)
        if random.random() < 0.70:
            delay = random.uniform(10, 30)
            asyncio.create_task(self.simulate_migration(position, delay))

        return position

    async def simulate_migration(self, position, delay):
        await asyncio.sleep(delay)

        if position.mint not in self.open_positions:
            return

        position.update_mc(OPTIMAL_WINDOW['migration_mc'])
        await self.execute_multi_sell(position)

    async def execute_multi_sell(self, position):
        multiplier = position.current_mc / position.entry_mc
        slippage = 0.98 + (random.random() * 0.04)
        actual_multiplier = multiplier * slippage

        exit_sol = position.entry_sol * actual_multiplier
        profit_sol = exit_sol - position.entry_sol
        roi_pct = (actual_multiplier - 1) * 100

        portions = 60
        for i in range(portions):
            await asyncio.sleep(0.01)

        position.sold = True
        position.migrated = True
        position.exit_sol = exit_sol
        position.profit_sol = profit_sol
        position.roi_pct = roi_pct

        self.wallet_sol += exit_sol
        self.total_profit_sol += profit_sol
        self.completed_trades.append(position)
        self.tokens_migrated += 1

        del self.open_positions[position.mint]

        self.last_tokens.append({
            'symbol': position.symbol,
            'mc': position.current_mc,
            'score': position.score['total'],
            'status': f'SOLD +{profit_sol:.2f} SOL ({roi_pct:+.0f}%)'
        })

    async def handle_trade(self, data):
        """Handle trade event - mise à jour prix en temps réel"""
        mint = data.get('mint')
        if not mint or mint not in self.all_tokens:
            return

        # Mettre à jour le market cap
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0

        token_info = self.all_tokens[mint]
        old_mc = token_info['mc_usd']
        token_info['mc_usd'] = mc_usd

        # Mettre à jour les stats
        if data.get('txnCount'):
            token_info['txnCount'] = data.get('txnCount')
        if data.get('newHolderCount'):
            token_info['holderCount'] = data.get('newHolderCount')

        # Afficher pumps intéressants
        if old_mc > 0 and mc_usd >= old_mc * 1.3:  # +30% pump
            print(f"🚀 {token_info['symbol']}: ${old_mc:,.0f} → ${mc_usd:,.0f} (+{((mc_usd/old_mc)-1)*100:.0f}%)")

        # Si atteint $5K et pas encore évalué
        if mc_usd >= 5000 and mint not in self.seen_above_8k:
            self.seen_above_8k.add(mint)
            await self.evaluate_token_above_8k(mint, token_info)

    async def evaluate_token_above_8k(self, mint, token_info):
        """Évaluer un token qui vient d'atteindre $7K"""
        mc_usd = token_info['mc_usd']
        symbol = token_info['symbol']
        name = token_info['name']
        holders = token_info['holderCount']

        print(f"\n{'='*80}")
        print(f"[TOKEN >= $7K] ${symbol} ({name})")
        print(f"{'='*80}")
        print(f"  Contract: {mint[:20]}...{mint[-10:]}")
        print(f"  MC: ${mc_usd:,.0f} | Holders: {holders} | Txns: {token_info['txnCount']}")
        print(f"  Init Buy: {token_info['initialBuy']:.2f} SOL")
        if token_info.get('twitter') or token_info.get('telegram') or token_info.get('website'):
            socials = []
            if token_info.get('twitter'): socials.append(f"Twitter: {token_info['twitter']}")
            if token_info.get('telegram'): socials.append(f"TG: {token_info['telegram']}")
            if token_info.get('website'): socials.append(f"Web: {token_info['website']}")
            print(f"  Socials: {' | '.join(socials)}")

        # Filtres de base
        if holders < 9:
            print(f"  [X] REJECTED: Not enough holders ({holders} < 9)")
            return

        if mc_usd < 2000:
            print(f"  [X] REJECTED: Not enough volume (${mc_usd:.0f} < $2K)")
            return

        # Scoring
        token_data = {
            'mint': mint,
            'symbol': symbol,
            'name': token_info['name'],
            'market_cap_usd': mc_usd,
            'price_sol': 0.00001,
            'txnCount': token_info['txnCount'],
            'initialBuy': token_info['initialBuy'],
            'holderCount': holders,
            'twitter': token_info.get('twitter'),
            'telegram': token_info.get('telegram'),
            'website': token_info.get('website'),
        }

        score = self.calculate_score(token_data)
        token_data['score'] = score

        print(f"  Score: {score['total']}/100 ({score['confidence']})")
        print(f"  Breakdown: {score['breakdown']}")

        if score['should_buy']:
            print(f"  [BUY] BUY SIGNAL!")
            await self.buy_token(token_data)
        else:
            print(f"  [X] REJECTED: Score too low ({score['total']} < 40)")

    async def process_token(self, data):
        """Process nouveau token OU trade du WebSocket"""
        if not isinstance(data, dict):
            return

        mint = data.get('mint')
        if not mint:
            return

        # Si déjà en position, skip
        if mint in self.open_positions:
            return

        tx_type = data.get('txType')

        # TRADE (buy/sell) sur un token existant
        if tx_type and tx_type != "create":
            await self.handle_trade(data)
            return

        # NOUVEAU TOKEN (txType == "create")
        if tx_type == "create":
            # Si déjà vu, skip
            if mint in self.seen_tokens:
                return

            # Données directement du WebSocket
            symbol = data.get('symbol', '???')
            name = data.get('name', 'Unknown')
            mc_sol = data.get('marketCapSol', 0)
            mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0
            sol_amount = data.get('solAmount', 0)
            holders = data.get('holderCount', 1)
            txn_count = data.get('txnCount', 1)
            twitter = data.get('twitter')
            telegram = data.get('telegram')
            website = data.get('website')

            # Stocker le token
            self.all_tokens[mint] = {
                'mint': mint,
                'symbol': symbol,
                'name': name,
                'mc_usd': mc_usd,
                'txnCount': txn_count,
                'initialBuy': sol_amount,  # Initial buy en SOL
                'holderCount': holders,
                'twitter': twitter,
                'telegram': telegram,
                'website': website,
            }

            # Afficher le token découvert
            print(f"\n[NEW TOKEN] ${symbol} ({name})")
            print(f"  Contract: {mint[:20]}...{mint[-10:]}")
            print(f"  MC: ${mc_usd:,.0f} | Init: {sol_amount:.2f} SOL | Holders: {holders} | Txns: {txn_count}")
            if twitter or telegram or website:
                socials = []
                if twitter: socials.append(f"Twitter: {twitter}")
                if telegram: socials.append(f"TG: {telegram}")
                if website: socials.append(f"Web: {website}")
                print(f"  Socials: {' | '.join(socials)}")

            # Compter et marquer comme vu
            self.tokens_scanned += 1
            self.seen_tokens.add(mint)

            # Si déjà >= $7K, évaluer immédiatement
            if mc_usd >= 7000:
                self.seen_above_8k.add(mint)
                await self.evaluate_token_above_8k(mint, self.all_tokens[mint])
            else:
                # Ajouter à la watch list pour surveillance continue
                self.watch_list[mint] = {
                    'symbol': symbol,
                    'name': name,
                    'mint': mint,
                    'first_seen': datetime.now(),
                    'last_mc': mc_usd,
                    'last_mc_change': datetime.now(),  # Dernière fois que le MC a changé
                    'stale_checks': 0,  # Nombre de fois qu'on a vu le même MC
                    'data': self.all_tokens[mint]
                }
                print(f"  -> Added to watch list (will monitor until $7K)")

    async def monitor_watch_list(self):
        """NOUVEAU: Surveille continuellement les tokens dans la watch list"""
        while self.running:
            await asyncio.sleep(1)  # Check every 1 second - RAPIDE pour catcher les pumps!

            if not self.watch_list:
                continue

            print(f"\n[WATCH LIST CHECK] Checking {len(self.watch_list)} tokens...")

            # Nettoyer les tokens trop vieux
            cutoff_time = datetime.now() - timedelta(minutes=WATCH_DURATION_MINUTES)
            to_remove = []

            for mint, info in list(self.watch_list.items()):
                # Supprimer si trop vieux
                if info['first_seen'] < cutoff_time:
                    to_remove.append(mint)
                    print(f"  [{info['symbol']}] Removed (too old)")
                    continue

                # APPEL API pour avoir le MC RÉEL actuel
                try:
                    response = requests.get(f'https://pumpportal.fun/api/trade-data?mint={mint}', timeout=5)
                    if response.status_code == 200:
                        api_data = response.json()
                        mc_sol = api_data.get('marketCapSol', 0)
                        current_mc = mc_sol * SOL_PRICE_USD if mc_sol else info['last_mc']

                        # DÉTECTION DE MOUVEMENT - Si le MC n'a pas changé, c'est un token MORT
                        mc_change_pct = abs(current_mc - info['last_mc']) / max(info['last_mc'], 1) * 100

                        if mc_change_pct < 1:  # Moins de 1% de changement = STALE
                            info['stale_checks'] += 1
                            print(f"  ${info['symbol']} - MC: ${current_mc:,.0f} (STALE {info['stale_checks']}/30)")

                            # Si pas de mouvement pendant 30 secondes, REMOVE
                            if info['stale_checks'] >= 30:
                                to_remove.append(mint)
                                print(f"  ❌ [{info['symbol']}] REMOVED - No movement for 30s (DEAD TOKEN)")
                                continue
                        else:
                            # Token bouge! Reset stale counter
                            info['stale_checks'] = 0
                            info['last_mc_change'] = datetime.now()
                            mc_change_sign = "📈" if current_mc > info['last_mc'] else "📉"
                            print(f"  {mc_change_sign} ${info['symbol']} - ${info['last_mc']:,.0f} → ${current_mc:,.0f} (+{mc_change_pct:.1f}%)")

                        # Mettre à jour les données
                        info['last_mc'] = current_mc
                        info['data'] = api_data
                    else:
                        current_mc = info['last_mc']
                        info['stale_checks'] += 1
                except Exception as e:
                    print(f"  [{info['symbol']}] API error: {e}")
                    current_mc = info['last_mc']
                    info['stale_checks'] += 1

                # Si >= $7K, évaluer pour achat
                if current_mc >= 7000:
                    # FILTRES DE BASE - Activité minimale requise
                    data = info['data']
                    holders = data.get('holderCount', 0)
                    volume_usd = data.get('usdMarketCap', current_mc)

                    if holders < 9 or volume_usd < 2000:
                        # Pas assez d'activité, continuer à monitorer
                        print(f"    Not enough activity (holders: {holders}, vol: ${volume_usd:.0f})")
                        continue

                    # Créer token_data à partir des données stockées
                    token_data = {
                        'mint': mint,
                        'symbol': data.get('symbol', '???'),
                        'name': data.get('name', 'Unknown'),
                        'market_cap_usd': current_mc,
                        'price_sol': data.get('vSolInBondingCurve', 0.00001) / max(data.get('vTokensInBondingCurve', 1), 1),
                        'twitter': data.get('twitter'),
                        'telegram': data.get('telegram'),
                        'website': data.get('website'),
                        'txnCount': data.get('txnCount', 0),
                        'initialBuy': data.get('initialBuy', 0),
                        'holderCount': holders,
                    }

                    score = self.calculate_score(token_data)
                    token_data['score'] = score

                    print(f"    Score: {score['total']}/100")

                    if score['should_buy']:
                        print(f"    [BUY] BUY from watch list!")
                        await self.buy_token(token_data)
                        to_remove.append(mint)
                        self.seen_tokens.add(mint)
                    else:
                        print(f"    [X] Score too low")
                        # Retirer aussi si score trop bas, pas besoin de continuer à surveiller
                        to_remove.append(mint)

            # Supprimer les tokens à retirer
            for mint in to_remove:
                if mint in self.watch_list:
                    del self.watch_list[mint]

    async def update_dashboard(self):
        """Met à jour le dashboard périodiquement"""
        while self.running:
            self.print_dashboard()
            await asyncio.sleep(2)

    async def run(self, duration_minutes=30):
        print("\nConnecting to WebSocket...")

        try:
            print("[CONNECTING] Attempting WebSocket connection...")
            async with websockets.connect('wss://pumpportal.fun/api/data') as ws:
                print("[CONNECTED] WebSocket connection established!")
                self.ws = ws  # Stocker pour subscribe aux trades

                subscribe_msg = {'method': 'subscribeNewToken'}
                await ws.send(json.dumps(subscribe_msg))
                print(f"[SUBSCRIBED] Sent: {subscribe_msg}")

                # Start tasks
                dashboard_task = asyncio.create_task(self.update_dashboard())
                watch_task = asyncio.create_task(self.monitor_watch_list())  # NOUVEAU

                start = datetime.now().timestamp()
                end = start + (duration_minutes * 60)

                print("[LISTENING] Waiting for messages...")

                while datetime.now().timestamp() < end:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(msg)
                        await self.process_token(data)

                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        continue

                self.running = False
                dashboard_task.cancel()
                watch_task.cancel()

        except Exception as e:
            print(f"[ERROR] {e}")
            self.running = False


async def main():
    print("\n" + "="*80)
    print("LIVE DASHBOARD BOT V2 - Avec Surveillance Continue")
    print("="*80)
    print(f"\nCette version surveille les tokens qui commencent en dessous de $9.5k")
    print(f"et achète automatiquement quand ils montent dans la fenêtre optimale!")
    print("\n" + "="*80 + "\n")

    duration = 30  # Durée par défaut: 30 minutes

    print(f"\n[STARTING] Monitoring for {duration} minutes with continuous tracking...\n")

    bot = LiveDashboardBot()
    await bot.run(duration_minutes=duration)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[STOPPED]")

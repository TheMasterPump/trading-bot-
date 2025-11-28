"""
COMPLETE TRADING BOT V2 - WebSocket avec Watch List
UN SEUL BOT qui fait tout le cycle:
1. Scan nouveaux tokens (WebSocket real-time)
2. Surveille tokens en dessous de $9.5k (WATCH LIST)
3. Achète quand ils montent dans $9.5k-$13k window
4. Monitor migration jusqu'à $69k
5. Vend en multi-sell automatiquement

wss://pumpportal.fun/api/data
"""
import asyncio
import json
import websockets
from datetime import datetime, timedelta
from collections import defaultdict
import random

# CONFIG
OPTIMAL_WINDOW = {
    'min_mc': 9500,
    'max_mc': 13000,
    'migration_mc': 69000,
}

BUY_AMOUNT_SOL = 2.5
SOL_PRICE_USD = 200
SIMULATION_MODE = True  # True = fake SOL, False = real trading

class Position:
    """Une position ouverte"""
    def __init__(self, token_data, buy_sol):
        self.mint = token_data['mint']
        self.symbol = token_data['symbol']
        self.name = token_data['name']
        self.entry_mc = token_data['market_cap_usd']
        self.entry_sol = buy_sol
        self.entry_price = token_data['price_sol']
        self.entry_time = datetime.now()
        self.entry_tokens = buy_sol / self.entry_price if self.entry_price > 0 else 0
        self.score = token_data['score']

        # Status
        self.current_mc = self.entry_mc
        self.migrated = False
        self.sold = False

        # Results
        self.exit_sol = 0
        self.profit_sol = 0
        self.roi_pct = 0

    def update_mc(self, new_mc):
        """Met à jour le market cap"""
        self.current_mc = new_mc

    def calculate_unrealized_pnl(self):
        """Calcule P&L non réalisé"""
        multiplier = self.current_mc / self.entry_mc
        unrealized_exit = self.entry_sol * multiplier
        unrealized_profit = unrealized_exit - self.entry_sol
        unrealized_roi = (multiplier - 1) * 100
        return {
            'multiplier': multiplier,
            'unrealized_exit': unrealized_exit,
            'unrealized_profit': unrealized_profit,
            'unrealized_roi': unrealized_roi
        }


class CompleteTradingBot:
    """Bot complet qui fait tout"""

    def __init__(self, simulation_mode=True):
        self.simulation = simulation_mode
        self.wallet_sol = 100.0 if simulation_mode else 0  # Fake wallet pour test

        # Tracking
        self.seen_tokens = set()
        self.watch_list = {}  # NOUVEAU: Tokens en dessous de $9.5k à surveiller
        self.open_positions = {}  # mint -> Position
        self.completed_trades = []
        self.total_profit_sol = 0

        # Stats
        self.tokens_scanned = 0
        self.tokens_bought = 0
        self.tokens_migrated = 0
        self.running = True  # NOUVEAU: Pour contrôler les tasks

    def calculate_score(self, token_data):
        """Score un token (0-100) - SYSTÈME OPTIMISÉ B+"""
        score = 0
        breakdown = {}

        # Transactions/Volume (0-40 pts) - PERMISSIF pour early tokens
        txn_count = token_data.get('txnCount', 0)
        txn_score = 0
        if txn_count >= 100: txn_score = 40
        elif txn_count >= 50: txn_score = 35
        elif txn_count >= 30: txn_score = 30
        elif txn_count >= 20: txn_score = 25
        elif txn_count >= 10: txn_score = 20   # AUGMENTÉ
        elif txn_count >= 5: txn_score = 15    # AUGMENTÉ
        elif txn_count >= 3: txn_score = 10    # NOUVEAU
        elif txn_count >= 1: txn_score = 5     # NOUVEAU
        score += txn_score
        breakdown['transactions'] = txn_score

        # Initial Buy (0-20 pts) - 0-2 SOL acceptable, >2 SOL = red flag
        initial = token_data.get('initialBuy', 0)
        init_score = 0
        if initial > 2: init_score = 0        # RED FLAG: Dev farmer (>2 SOL)
        elif initial >= 1: init_score = 20    # OPTIMAL (1-2 SOL)
        elif initial >= 0.5: init_score = 15  # Bon (0.5-1 SOL)
        elif initial >= 0.2: init_score = 10  # Acceptable (0.2-0.5 SOL)
        else: init_score = 5                  # Acceptable (0-0.2 SOL)
        score += init_score
        breakdown['initial_buy'] = init_score

        # MC Position (0-20 pts) - Potentiel de gain
        mc = token_data.get('market_cap_usd', 0)
        mc_score = 0
        if OPTIMAL_WINDOW['min_mc'] <= mc <= OPTIMAL_WINDOW['max_mc']:
            if mc <= 10500: mc_score = 20
            elif mc <= 11500: mc_score = 15
            else: mc_score = 10
        score += mc_score
        breakdown['mc_position'] = mc_score

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
        if holders > 10 and txn_count > 0:
            ratio = txn_count / holders
            if ratio < 1.3:    # Très suspect
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
        """Achète un token (simulation ou réel)"""

        if self.wallet_sol < BUY_AMOUNT_SOL:
            print(f"[!] Insufficient funds: {self.wallet_sol:.2f} SOL")
            return None

        position = Position(token_data, BUY_AMOUNT_SOL)
        self.wallet_sol -= BUY_AMOUNT_SOL
        self.open_positions[position.mint] = position
        self.tokens_bought += 1

        potential_roi = ((OPTIMAL_WINDOW['migration_mc'] / position.entry_mc) - 1) * 100

        print(f"\n{'='*70}")
        print(f"✅ {'SIMULATED ' if self.simulation else ''}BUY: {position.symbol}")
        print(f"{'='*70}")
        print(f"  Entry MC: ${position.entry_mc:,.0f}")
        print(f"  Amount: {BUY_AMOUNT_SOL:.2f} SOL (${BUY_AMOUNT_SOL * SOL_PRICE_USD:.2f})")
        print(f"  Tokens: {position.entry_tokens:,.0f}")
        print(f"  Score: {position.score['total']}/100 ({position.score['confidence']})")
        print(f"  Potential ROI: {potential_roi:+.0f}% if migrates")
        print(f"  Wallet: {self.wallet_sol:.2f} SOL remaining")
        print(f"  Open positions: {len(self.open_positions)}")
        print(f"{'='*70}\n")

        return position

    async def check_migration(self, position):
        """Vérifie si un token a migré"""
        # Migration si MC >= $69k
        if position.current_mc >= OPTIMAL_WINDOW['migration_mc']:
            return True
        return False

    async def execute_multi_sell(self, position):
        """Exécute la vente en multi-portions"""

        print(f"\n{'='*70}")
        print(f"🚨 MIGRATION DETECTED - EXECUTING MULTI-SELL")
        print(f"{'='*70}")
        print(f"Token: {position.symbol}")
        print(f"Entry: ${position.entry_mc:,.0f} → Migration: ${position.current_mc:,.0f}")
        print(f"{'='*70}\n")

        # Calcul exit
        multiplier = position.current_mc / position.entry_mc
        slippage = 0.98 + (random.random() * 0.04)  # 98-102%
        actual_multiplier = multiplier * slippage

        exit_sol = position.entry_sol * actual_multiplier
        profit_sol = exit_sol - position.entry_sol
        roi_pct = (actual_multiplier - 1) * 100

        # Simulation multi-sell
        portions = 60
        sol_per_portion = exit_sol / portions

        print(f"Strategy:")
        print(f"  Portions: {portions}")
        print(f"  SOL/portion: {sol_per_portion:.4f}")
        print(f"  Duration: 60 seconds\n")

        print(f"Executing sells:")
        for i in range(portions):
            if (i + 1) % 15 == 0 or i == 0 or i == portions - 1:
                print(f"  [SELL {i+1}/{portions}] {sol_per_portion:.4f} SOL")
            await asyncio.sleep(0.02)  # Rapide pour simulation

        # Update position
        position.sold = True
        position.migrated = True
        position.exit_sol = exit_sol
        position.profit_sol = profit_sol
        position.roi_pct = roi_pct

        self.wallet_sol += exit_sol
        self.total_profit_sol += profit_sol
        self.completed_trades.append(position)
        self.tokens_migrated += 1

        # Remove from open positions
        del self.open_positions[position.mint]

        print(f"\n{'='*70}")
        print(f"TRADE COMPLETE")
        print(f"{'='*70}")
        print(f"{position.symbol} P&L:")
        print(f"  Entry: {position.entry_sol:.4f} SOL @ ${position.entry_mc:,.0f}")
        print(f"  Exit: {exit_sol:.4f} SOL @ ${position.current_mc:,.0f}")
        print(f"  Profit: {profit_sol:+.4f} SOL (${profit_sol * SOL_PRICE_USD:+.2f})")
        print(f"  ROI: {roi_pct:+.1f}%")
        print(f"  Multiplier: {actual_multiplier:.2f}x")

        if roi_pct >= 500:
            print(f"\n  🚀 EXCELLENT PROFIT!")
        elif roi_pct >= 300:
            print(f"\n  ✅ GREAT PROFIT!")
        elif roi_pct >= 100:
            print(f"\n  👍 GOOD PROFIT!")

        print(f"{'='*70}\n")

        return profit_sol

    async def process_new_token(self, data):
        """Process un nouveau token du WebSocket (AVEC WATCH LIST)"""

        if not isinstance(data, dict):
            return

        mint = data.get('mint')
        if not mint:
            return

        # Si déjà acheté ou en position, skip
        if mint in self.seen_tokens or mint in self.open_positions:
            return

        # Extract info
        symbol = data.get('symbol', '???')
        name = data.get('name', 'Unknown')
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0

        self.tokens_scanned += 1

        # CAS 1: Token EN DESSOUS de $9.5k - Ajouter à la watch list
        if mc_usd < OPTIMAL_WINDOW['min_mc'] and mc_usd >= 3000:  # Min $3k pour éviter spam
            if mint not in self.watch_list:
                self.watch_list[mint] = {
                    'data': data,
                    'first_seen': datetime.now(),
                    'last_mc': mc_usd,
                    'symbol': symbol
                }
                print(f"[WATCH] {symbol} @ ${mc_usd:,.0f} - Added to watch list (below $9.5k)")
            return

        # CAS 2: Token DANS la fenêtre optimale - Évaluer pour achat
        if OPTIMAL_WINDOW['min_mc'] <= mc_usd <= OPTIMAL_WINDOW['max_mc']:
            # FILTRES DE BASE - Activité minimale requise
            holders = data.get('holderCount', 0)
            volume_usd = data.get('usdMarketCap', mc_usd)

            if holders < 9:
                self.seen_tokens.add(mint)
                return  # Minimum 9 holders requis

            if volume_usd < 2000:
                self.seen_tokens.add(mint)
                return  # Minimum $2K volume requis

            # Marquer comme vu
            self.seen_tokens.add(mint)

            # Prepare data
            token_data = {
                'mint': mint,
                'symbol': symbol,
                'name': name,
                'market_cap_usd': mc_usd,
                'marketCapSol': mc_sol,
                'price_sol': data.get('vSolInBondingCurve', 0) / data.get('vTokensInBondingCurve', 1) if data.get('vTokensInBondingCurve') else 0,
                'twitter': data.get('twitter'),
                'telegram': data.get('telegram'),
                'website': data.get('website'),
                'txnCount': data.get('txnCount', 0),
                'initialBuy': data.get('initialBuy', 0),
                'holderCount': holders,
            }

            # Score
            score = self.calculate_score(token_data)
            token_data['score'] = score

            if score['should_buy']:
                print(f"\n[CANDIDATE] {symbol} - MC: ${mc_usd:,.0f} - Score: {score['total']}/100")
                await self.buy_token(token_data)

                # Retirer de la watch list si présent
                if mint in self.watch_list:
                    del self.watch_list[mint]

        # CAS 3: Token AU-DESSUS de $13k - Ignorer
        elif mc_usd > OPTIMAL_WINDOW['max_mc']:
            self.seen_tokens.add(mint)
            # Retirer de la watch list si présent
            if mint in self.watch_list:
                del self.watch_list[mint]

    async def update_position_mc(self, mint, new_mc_usd):
        """Met à jour le MC d'une position ouverte"""

        if mint not in self.open_positions:
            return

        position = self.open_positions[mint]
        old_mc = position.current_mc
        position.update_mc(new_mc_usd)

        # Check si migration
        if await self.check_migration(position):
            print(f"\n🚨 MIGRATION ALERT: {position.symbol} reached ${new_mc_usd:,.0f}!")
            await self.execute_multi_sell(position)

    async def monitor_positions(self):
        """Monitor toutes les positions ouvertes périodiquement"""

        while self.running:
            await asyncio.sleep(30)  # Check every 30s

            if not self.open_positions:
                continue

            print(f"\n[MONITORING] {len(self.open_positions)} open positions:")

            for mint, position in list(self.open_positions.items()):
                unrealized = position.calculate_unrealized_pnl()
                progress = (position.current_mc / OPTIMAL_WINDOW['migration_mc']) * 100

                print(f"  {position.symbol}: ${position.current_mc:,.0f} ({progress:.0f}% to migration) - Unrealized: {unrealized['unrealized_roi']:+.0f}%")

                # Check migration
                if await self.check_migration(position):
                    await self.execute_multi_sell(position)

    async def monitor_watch_list(self):
        """NOUVEAU: Surveille continuellement les tokens dans la watch list"""

        WATCH_DURATION_MINUTES = 30  # Surveiller pendant max 30 min

        while self.running:
            await asyncio.sleep(10)  # Check every 10 seconds

            if not self.watch_list:
                continue

            print(f"\n[WATCH LIST] Monitoring {len(self.watch_list)} tokens below $9.5k...")

            # Nettoyer les tokens trop vieux
            cutoff_time = datetime.now() - timedelta(minutes=WATCH_DURATION_MINUTES)
            to_remove = []

            for mint, info in list(self.watch_list.items()):
                # Supprimer si trop vieux
                if info['first_seen'] < cutoff_time:
                    print(f"  {info['symbol']}: Removed (too old - {WATCH_DURATION_MINUTES}+ minutes)")
                    to_remove.append(mint)
                    continue

                # Re-fetch current data via simulation (dans la vraie version, on ferait un API call)
                # Pour la simulation, on fait monter aléatoirement certains tokens
                if random.random() < 0.05:  # 5% chance par check (~30% par minute)
                    # Simuler une montée de MC
                    current_mc = info['last_mc'] * random.uniform(1.1, 1.5)
                    info['last_mc'] = current_mc

                    print(f"  {info['symbol']}: MC updated ${current_mc:,.0f}")

                    # Si maintenant dans la fenêtre, évaluer pour achat
                    if OPTIMAL_WINDOW['min_mc'] <= current_mc <= OPTIMAL_WINDOW['max_mc']:
                        print(f"  >>> {info['symbol']}: Entered optimal window! Evaluating...")

                        # FILTRES DE BASE - Activité minimale requise
                        data = info['data']
                        holders = data.get('holderCount', 0)
                        volume_usd = data.get('usdMarketCap', current_mc)

                        if holders < 9 or volume_usd < 2000:
                            print(f"  >>> Not enough activity (holders: {holders}, volume: ${volume_usd:.0f}), continuing to watch...")
                            continue

                        # Créer token_data à partir des données stockées
                        token_data = {
                            'mint': mint,
                            'symbol': data.get('symbol', '???'),
                            'name': data.get('name', 'Unknown'),
                            'market_cap_usd': current_mc,
                            'marketCapSol': current_mc / SOL_PRICE_USD,
                            'price_sol': data.get('vSolInBondingCurve', 0) / max(data.get('vTokensInBondingCurve', 1), 1),
                            'twitter': data.get('twitter'),
                            'telegram': data.get('telegram'),
                            'website': data.get('website'),
                            'txnCount': data.get('txnCount', 0),
                            'initialBuy': data.get('initialBuy', 0),
                            'holderCount': holders,
                        }

                        score = self.calculate_score(token_data)
                        token_data['score'] = score

                        print(f"  >>> Score: {score['total']}/100 ({score['confidence']})")

                        if score['should_buy']:
                            print(f"  >>> BUY SIGNAL from watch list!")
                            await self.buy_token(token_data)
                            to_remove.append(mint)
                            self.seen_tokens.add(mint)
                        else:
                            print(f"  >>> Score too low, continuing to watch...")

                    # Si au-dessus de la fenêtre, retirer
                    elif current_mc > OPTIMAL_WINDOW['max_mc']:
                        print(f"  {info['symbol']}: Removed (above $13k)")
                        to_remove.append(mint)
                        self.seen_tokens.add(mint)

            # Supprimer les tokens à retirer
            for mint in to_remove:
                if mint in self.watch_list:
                    del self.watch_list[mint]

    async def run(self, duration_minutes=60):
        """Lance le bot complet avec watch list"""

        print("\n" + "="*70)
        print("COMPLETE TRADING BOT V2 - Avec Watch List")
        print("="*70)
        print(f"Mode: {'SIMULATION (Fake SOL)' if self.simulation else 'REAL TRADING'}")
        print(f"Wallet: {self.wallet_sol:.2f} SOL")
        print(f"Target: ${OPTIMAL_WINDOW['min_mc']:,} - ${OPTIMAL_WINDOW['max_mc']:,}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"\nNOUVEAU: Surveille tokens en dessous de $9.5k et achète quand ils montent!")
        print("="*70)
        print("\nConnecting to WebSocket...")

        try:
            async with websockets.connect('wss://pumpportal.fun/api/data') as ws:
                # Subscribe
                await ws.send(json.dumps({'method': 'subscribeNewToken'}))
                print("[CONNECTED] Listening for new tokens...\n")

                # Start monitors in background
                monitor_task = asyncio.create_task(self.monitor_positions())
                watch_task = asyncio.create_task(self.monitor_watch_list())  # NOUVEAU

                # Listen for duration
                start_time = datetime.now().timestamp()
                end_time = start_time + (duration_minutes * 60)

                while datetime.now().timestamp() < end_time:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        data = json.loads(msg)

                        # Process token
                        await self.process_new_token(data)

                        # Update existing positions if data matches
                        if isinstance(data, dict) and data.get('mint'):
                            mint = data['mint']
                            if mint in self.open_positions:
                                mc_usd = data.get('marketCapSol', 0) * SOL_PRICE_USD
                                if mc_usd > 0:
                                    await self.update_position_mc(mint, mc_usd)

                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        continue

                # Stop tasks
                self.running = False
                monitor_task.cancel()
                watch_task.cancel()

                print(f"\n[DURATION COMPLETE] Ran for {duration_minutes} minutes")
                self.print_final_summary()

        except Exception as e:
            print(f"[ERROR] {e}")
            self.running = False

    def print_final_summary(self):
        """Affiche résumé final avec watch list"""

        print("\n\n" + "="*70)
        print("FINAL SUMMARY")
        print("="*70)

        print(f"\nTokens scanned: {self.tokens_scanned}")
        print(f"Watch list (below $9.5k): {len(self.watch_list)}")  # NOUVEAU
        print(f"Tokens bought: {self.tokens_bought}")
        print(f"Tokens migrated: {self.tokens_migrated}")
        print(f"Open positions: {len(self.open_positions)}")
        print(f"Completed trades: {len(self.completed_trades)}")

        if self.completed_trades:
            winners = [t for t in self.completed_trades if t.profit_sol > 0]
            win_rate = (len(winners) / len(self.completed_trades)) * 100

            print(f"\nWin rate: {len(winners)}/{len(self.completed_trades)} ({win_rate:.0f}%)")
            print(f"Total profit: {self.total_profit_sol:+.4f} SOL (${self.total_profit_sol * SOL_PRICE_USD:+.2f})")

            if self.simulation:
                print(f"Final wallet: {self.wallet_sol:.2f} SOL")

            avg_roi = sum(t.roi_pct for t in self.completed_trades) / len(self.completed_trades)
            print(f"Average ROI: {avg_roi:+.1f}%")

            if winners:
                avg_profit = sum(t.profit_sol for t in winners) / len(winners)
                print(f"Avg profit/winner: {avg_profit:.4f} SOL (${avg_profit * SOL_PRICE_USD:.2f})")

            print("\nCompleted trades:")
            for i, trade in enumerate(self.completed_trades, 1):
                status = "WIN" if trade.profit_sol > 0 else "LOSS"
                print(f"  [{i}] {trade.symbol}: {trade.profit_sol:+.4f} SOL ({trade.roi_pct:+.0f}%) - {status}")

        if self.open_positions:
            print(f"\nStill open ({len(self.open_positions)}):")
            for mint, pos in self.open_positions.items():
                unrealized = pos.calculate_unrealized_pnl()
                print(f"  {pos.symbol}: ${pos.current_mc:,.0f} - Unrealized: {unrealized['unrealized_roi']:+.0f}%")

        print("\n" + "="*70)

        if self.simulation:
            print("\nNote: This was a SIMULATION with fake SOL")
            print("Set SIMULATION_MODE = False for real trading")


async def main():
    print("\n=== COMPLETE TRADING BOT V2 - Avec Watch List ===\n")
    print("One bot that does everything:")
    print("  1. Scan new tokens (WebSocket)")
    print("  2. NOUVEAU: Watch tokens below $9.5k")
    print("  3. Buy when they enter $9.5k-$13k window")
    print("  4. Monitor migration to $69k")
    print("  5. Auto multi-sell after migration\n")
    print(">>> Résout le problème 'cliguer AI' - Capture les montées!\n")

    mode = input("Mode? (1=Simulation/Test, 2=Real): ").strip()
    simulation = mode != '2'

    if not simulation:
        print("\n⚠️  REAL TRADING MODE - USE REAL SOL ⚠️")
        confirm = input("Are you sure? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Cancelled")
            return

    duration = input(f"\nDuration in minutes (default 60): ").strip()
    try:
        duration = int(duration) if duration else 60
        duration = max(1, min(480, duration))
    except:
        duration = 60

    print(f"\n[STARTING] {'Simulation' if simulation else 'Real trading'} for {duration} minutes...\n")

    bot = CompleteTradingBot(simulation_mode=simulation)
    await bot.run(duration_minutes=duration)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[STOPPED] Interrupted by user")

"""
TEST COMPLET - Mode Simulation Automatique
Lance directement avec FAKE SOL pour tester
"""
import asyncio
import json
import websockets
from datetime import datetime
import random

# CONFIG
OPTIMAL_WINDOW = {
    'min_mc': 9500,
    'max_mc': 13000,
    'migration_mc': 69000,
}

BUY_AMOUNT_SOL = 2.5
SOL_PRICE_USD = 200

class Position:
    """Position"""
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
            'unrealized_exit': unrealized_exit,
            'unrealized_profit': unrealized_profit,
            'unrealized_roi': unrealized_roi
        }


class TestBot:
    """Bot de test"""

    def __init__(self):
        self.wallet_sol = 100.0
        self.seen_tokens = set()
        self.open_positions = {}
        self.completed_trades = []
        self.total_profit_sol = 0
        self.tokens_scanned = 0
        self.tokens_bought = 0
        self.tokens_migrated = 0

    def calculate_score(self, token_data):
        """Score (0-100) - SYSTÈME OPTIMISÉ B+"""
        score = 0
        breakdown = {}

        # Transactions/Volume (0-40 pts) - PERMISSIF pour early tokens
        txn = token_data.get('txnCount', 0)
        txn_score = 0
        if txn >= 100: txn_score = 40
        elif txn >= 50: txn_score = 35
        elif txn >= 30: txn_score = 30
        elif txn >= 20: txn_score = 25
        elif txn >= 10: txn_score = 20   # AUGMENTÉ
        elif txn >= 5: txn_score = 15    # AUGMENTÉ
        elif txn >= 3: txn_score = 10    # NOUVEAU
        elif txn >= 1: txn_score = 5     # NOUVEAU
        score += txn_score
        breakdown['txn'] = txn_score

        # Initial Buy (0-20 pts) - 0-2 SOL acceptable, >2 SOL = red flag
        init = token_data.get('initialBuy', 0)
        init_score = 0
        if init > 2: init_score = 0        # RED FLAG: Dev farmer (>2 SOL)
        elif init >= 1: init_score = 20    # OPTIMAL (1-2 SOL)
        elif init >= 0.5: init_score = 15  # Bon (0.5-1 SOL)
        elif init >= 0.2: init_score = 10  # Acceptable (0.2-0.5 SOL)
        else: init_score = 5               # Acceptable (0-0.2 SOL)
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
            if ratio < 1.3:
                bundle_penalty = -20
                breakdown['bundle_warning'] = 'HIGH RISK'
            elif ratio < 1.5:
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
        """Achète"""
        if self.wallet_sol < BUY_AMOUNT_SOL:
            return None

        position = Position(token_data, BUY_AMOUNT_SOL)
        self.wallet_sol -= BUY_AMOUNT_SOL
        self.open_positions[position.mint] = position
        self.tokens_bought += 1

        potential_roi = ((OPTIMAL_WINDOW['migration_mc'] / position.entry_mc) - 1) * 100

        print(f"\n{'='*70}")
        print(f"[BUY] SIMULATION: {position.symbol}")
        print(f"{'='*70}")
        print(f"  Entry MC: ${position.entry_mc:,.0f}")
        print(f"  Amount: {BUY_AMOUNT_SOL:.2f} SOL (${BUY_AMOUNT_SOL * SOL_PRICE_USD:.2f})")
        print(f"  Score: {position.score['total']}/100 ({position.score['confidence']})")
        print(f"  Potential ROI: {potential_roi:+.0f}%")
        print(f"  Wallet: {self.wallet_sol:.2f} SOL")
        print(f"  Open: {len(self.open_positions)}")
        print(f"{'='*70}\n")

        # Simulate migration later (70% chance)
        if random.random() < 0.70:
            # Schedule migration in 5-15 seconds
            delay = random.uniform(5, 15)
            asyncio.create_task(self.simulate_migration(position, delay))

        return position

    async def simulate_migration(self, position, delay):
        """Simule migration après délai"""
        await asyncio.sleep(delay)

        if position.mint not in self.open_positions:
            return

        # Simulate MC progression
        print(f"\n[{position.symbol}] MC progressing: ${position.entry_mc:,.0f} → ${OPTIMAL_WINDOW['migration_mc']:,}")
        position.update_mc(OPTIMAL_WINDOW['migration_mc'])

        # Trigger multi-sell
        await self.execute_multi_sell(position)

    async def execute_multi_sell(self, position):
        """Multi-sell"""
        print(f"\n{'='*70}")
        print(f">>> MIGRATION - MULTI-SELL: {position.symbol}")
        print(f"{'='*70}")

        multiplier = position.current_mc / position.entry_mc
        slippage = 0.98 + (random.random() * 0.04)
        actual_multiplier = multiplier * slippage

        exit_sol = position.entry_sol * actual_multiplier
        profit_sol = exit_sol - position.entry_sol
        roi_pct = (actual_multiplier - 1) * 100

        portions = 60
        sol_per = exit_sol / portions

        print(f"\nExecuting {portions} sells:")
        for i in range(portions):
            if (i + 1) % 20 == 0 or i == 0 or i == portions - 1:
                print(f"  [SELL {i+1}/{portions}]")
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

        print(f"\n{'='*70}")
        print(f"[OK] TRADE COMPLETE: {position.symbol}")
        print(f"{'='*70}")
        print(f"  Entry: {position.entry_sol:.4f} SOL @ ${position.entry_mc:,.0f}")
        print(f"  Exit: {exit_sol:.4f} SOL @ ${position.current_mc:,.0f}")
        print(f"  Profit: {profit_sol:+.4f} SOL (${profit_sol * SOL_PRICE_USD:+.2f})")
        print(f"  ROI: {roi_pct:+.1f}%")
        print(f"  Multiplier: {actual_multiplier:.2f}x")

        if roi_pct >= 500:
            print(f"\n  >> EXCELLENT!")
        elif roi_pct >= 300:
            print(f"\n  >> GREAT!")
        elif roi_pct >= 100:
            print(f"\n  >> GOOD!")

        print(f"{'='*70}\n")

    async def process_token(self, data):
        """Process token"""
        if not isinstance(data, dict):
            return

        mint = data.get('mint')
        if not mint or mint in self.seen_tokens:
            return

        self.seen_tokens.add(mint)
        self.tokens_scanned += 1

        symbol = data.get('symbol', '???')
        name = data.get('name', 'Unknown')
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0

        # Check window
        if not (OPTIMAL_WINDOW['min_mc'] <= mc_usd <= OPTIMAL_WINDOW['max_mc']):
            return

        # FILTRES DE BASE - Activité minimale requise
        holders = data.get('holderCount', 0)
        volume_usd = data.get('usdMarketCap', mc_usd)

        if holders < 9:
            return  # Minimum 9 holders requis

        if volume_usd < 2000:
            return  # Minimum $2K volume requis

        # Prepare
        token_data = {
            'mint': mint,
            'symbol': symbol,
            'name': name,
            'market_cap_usd': mc_usd,
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

        if score['should_buy']:
            print(f"\n[CANDIDATE] {symbol} - ${mc_usd:,.0f} - Score: {score['total']}/100")
            await self.buy_token(token_data)

    async def run(self, duration_minutes=3):
        """Run test"""
        print("\n" + "="*70)
        print("TEST COMPLET - MODE SIMULATION")
        print("="*70)
        print(f"Wallet: {self.wallet_sol:.2f} FAKE SOL")
        print(f"Target: ${OPTIMAL_WINDOW['min_mc']:,} - ${OPTIMAL_WINDOW['max_mc']:,}")
        print(f"Duration: {duration_minutes} minutes")
        print("="*70)
        print("\nConnecting to WebSocket...\n")

        try:
            async with websockets.connect('wss://pumpportal.fun/api/data') as ws:
                await ws.send(json.dumps({'method': 'subscribeNewToken'}))
                print("[CONNECTED] Listening...\n")

                start = datetime.now().timestamp()
                end = start + (duration_minutes * 60)

                while datetime.now().timestamp() < end:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(msg)
                        await self.process_token(data)

                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        continue

                print(f"\n[DURATION COMPLETE] {duration_minutes} minutes\n")

                # Wait for pending migrations
                if self.open_positions:
                    print(f"[WAITING] {len(self.open_positions)} positions still open, waiting for migrations...")
                    await asyncio.sleep(20)

                self.print_summary()

        except Exception as e:
            print(f"[ERROR] {e}")
            self.print_summary()

    def print_summary(self):
        """Summary"""
        print("\n" + "="*70)
        print("FINAL SUMMARY")
        print("="*70)

        print(f"\nTokens scanned: {self.tokens_scanned}")
        print(f"Tokens bought: {self.tokens_bought}")
        print(f"Tokens migrated: {self.tokens_migrated}")
        print(f"Still open: {len(self.open_positions)}")
        print(f"Completed: {len(self.completed_trades)}")

        if self.completed_trades:
            winners = [t for t in self.completed_trades if t.profit_sol > 0]
            win_rate = (len(winners) / len(self.completed_trades)) * 100

            print(f"\nWin rate: {len(winners)}/{len(self.completed_trades)} ({win_rate:.0f}%)")
            print(f"Total profit: {self.total_profit_sol:+.4f} SOL (${self.total_profit_sol * SOL_PRICE_USD:+.2f})")
            print(f"Final wallet: {self.wallet_sol:.2f} SOL")

            avg_roi = sum(t.roi_pct for t in self.completed_trades) / len(self.completed_trades)
            print(f"Average ROI: {avg_roi:+.1f}%")

            if winners:
                avg_profit = sum(t.profit_sol for t in winners) / len(winners)
                print(f"Avg profit/win: {avg_profit:.4f} SOL (${avg_profit * SOL_PRICE_USD:.2f})")

            print("\nTrades:")
            for i, t in enumerate(self.completed_trades, 1):
                status = "WIN" if t.profit_sol > 0 else "LOSS"
                print(f"  [{i}] {t.symbol}: {t.profit_sol:+.4f} SOL ({t.roi_pct:+.0f}%) - {status}")

        if self.open_positions:
            print(f"\nStill open:")
            for mint, pos in self.open_positions.items():
                unrealized = pos.calculate_unrealized()
                print(f"  {pos.symbol}: ${pos.current_mc:,.0f} - Unrealized: {unrealized['unrealized_roi']:+.0f}%")

        print("\n" + "="*70)
        print("TEST COMPLETE (FAKE SOL)")
        print("="*70 + "\n")


async def main():
    print("\n>>> STARTING TEST WITH FAKE SOL...\n")
    bot = TestBot()
    await bot.run(duration_minutes=3)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[STOPPED]")

"""
TEST SIMULATION - Paper Trading
Tester le système complet avec des FAUX SOL
Pour valider que tout fonctionne avant d'utiliser de l'argent réel
"""
import asyncio
import httpx
import json
from datetime import datetime, timedelta
import random

# SIMULATION CONFIG
SIMULATION_MODE = True
FAKE_WALLET_SOL = 100.0  # 100 SOL fictifs pour tester
SOL_PRICE_USD = 200.0
BUY_AMOUNT_SOL = 2.5  # Acheter 2.5 SOL par token

# OPTIMAL WINDOW (identique au vrai bot)
OPTIMAL_WINDOW = {
    'min_mc': 9500,
    'max_mc': 13000,
    'migration_mc': 69000,
}

class SimulatedPosition:
    """Position simulée pour paper trading"""
    def __init__(self, token_data, buy_sol):
        self.mint = token_data['mint']
        self.symbol = token_data.get('symbol', '???')
        self.name = token_data.get('name', 'Unknown')
        self.entry_mc = token_data['market_cap']
        self.entry_sol = buy_sol
        self.entry_price = token_data.get('price_sol', 0)
        self.entry_time = datetime.now()
        self.entry_tokens = buy_sol / self.entry_price if self.entry_price > 0 else 0
        self.score = token_data.get('score', 0)
        self.migrated = False
        self.sold = False
        self.exit_sol = 0
        self.profit_sol = 0
        self.roi_pct = 0

    def calculate_potential_roi(self):
        """Calcule ROI potentiel si migration"""
        multiplier = OPTIMAL_WINDOW['migration_mc'] / self.entry_mc
        potential_exit = self.entry_sol * multiplier
        potential_profit = potential_exit - self.entry_sol
        potential_roi = (multiplier - 1) * 100
        return {
            'multiplier': multiplier,
            'exit_sol': potential_exit,
            'profit_sol': potential_profit,
            'roi_pct': potential_roi
        }


class SimulationTester:
    """Test complet du système en simulation"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.wallet_sol = FAKE_WALLET_SOL
        self.positions = []
        self.completed_trades = []
        self.total_profit_sol = 0

    async def scan_for_candidates(self):
        """Scan tokens dans optimal window (comme optimal_entry_bot.py)"""

        print("\n" + "="*70)
        print("PHASE 1: SCANNING FOR BUY OPPORTUNITIES")
        print("="*70)
        print(f"Target window: ${OPTIMAL_WINDOW['min_mc']:,} - ${OPTIMAL_WINDOW['max_mc']:,}")
        print(f"Available funds: {self.wallet_sol:.2f} SOL (${self.wallet_sol * SOL_PRICE_USD:.2f})")
        print("="*70)

        try:
            # Get tokens sorted by market cap
            url = "https://frontend-api.pump.fun/coins?limit=100&sort=usd_market_cap&order=ASC"
            response = await self.client.get(url)

            if response.status_code != 200:
                print(f"[!] API error: {response.status_code}")
                return []

            tokens = response.json()
            print(f"\n[+] Fetched {len(tokens)} tokens")

            candidates = []

            for token in tokens:
                # Skip if migrated
                if token.get('raydium_pool') or token.get('complete'):
                    continue

                mc = token.get('usd_market_cap', 0)

                # Must be in optimal window
                if not (OPTIMAL_WINDOW['min_mc'] <= mc <= OPTIMAL_WINDOW['max_mc']):
                    continue

                # Calculate age
                created_ts = token.get('created_timestamp', 0)
                age_hours = 0
                if created_ts:
                    age_hours = (datetime.now().timestamp() * 1000 - created_ts) / 3600000

                # Simple scoring
                score = 0

                # Social (0-30)
                if token.get('twitter'): score += 10
                if token.get('telegram'): score += 10
                if token.get('website'): score += 10

                # Volume (0-30)
                volume = token.get('volume_24h', 0)
                if volume >= 20000: score += 30
                elif volume >= 15000: score += 25
                elif volume >= 10000: score += 20
                elif volume >= 5000: score += 10

                # Holders (0-20)
                holders = token.get('holder_count', 0)
                if holders >= 100: score += 20
                elif holders >= 75: score += 17
                elif holders >= 50: score += 15
                elif holders >= 30: score += 12

                # Age (0-20)
                if age_hours < 4: score += 20
                elif age_hours < 8: score += 18
                elif age_hours < 12: score += 15
                elif age_hours < 24: score += 10

                # Only tokens with score >= 50 (permissive for testing)
                if score >= 50:
                    token_data = {
                        'mint': token['mint'],
                        'symbol': token.get('symbol', '???'),
                        'name': token.get('name', 'Unknown'),
                        'market_cap': mc,
                        'volume_24h': volume,
                        'holder_count': holders,
                        'age_hours': age_hours,
                        'score': score,
                        'price_sol': token.get('price_sol', 0),
                    }
                    candidates.append(token_data)

            print(f"\n[FOUND] {len(candidates)} candidates with score >= 50")

            # Sort by score
            candidates.sort(key=lambda x: x['score'], reverse=True)

            return candidates

        except Exception as e:
            print(f"[!] Error scanning: {e}")
            return []

    def simulate_buy(self, token_data):
        """Simule l'achat d'un token"""

        if self.wallet_sol < BUY_AMOUNT_SOL:
            print(f"[!] Insufficient funds: {self.wallet_sol:.2f} SOL < {BUY_AMOUNT_SOL:.2f} SOL")
            return None

        position = SimulatedPosition(token_data, BUY_AMOUNT_SOL)
        self.wallet_sol -= BUY_AMOUNT_SOL
        self.positions.append(position)

        potential = position.calculate_potential_roi()

        print(f"\n✅ SIMULATED BUY: {position.symbol}")
        print(f"  Entry MC: ${position.entry_mc:,.0f}")
        print(f"  Entry price: {position.entry_price:.10f} SOL")
        print(f"  Amount: {BUY_AMOUNT_SOL:.2f} SOL (${BUY_AMOUNT_SOL * SOL_PRICE_USD:.2f})")
        print(f"  Tokens: {position.entry_tokens:,.0f}")
        print(f"  Score: {position.score}/100")
        print(f"  Potential ROI if migrates: {potential['multiplier']:.1f}x (+{potential['roi_pct']:.0f}%)")
        print(f"  Remaining funds: {self.wallet_sol:.2f} SOL")

        return position

    async def simulate_migration_wait(self, position, simulate_success=True):
        """Simule l'attente de migration"""

        print(f"\n{'='*70}")
        print(f"PHASE 2: WAITING FOR MIGRATION - {position.symbol}")
        print(f"{'='*70}")
        print(f"Entry: ${position.entry_mc:,.0f} → Target: ${OPTIMAL_WINDOW['migration_mc']:,}")

        if simulate_success:
            # Simule une migration réussie
            print(f"Simulating token progression...")

            # Simulate progression steps
            steps = [
                (20, position.entry_mc * 1.5),
                (40, position.entry_mc * 2.5),
                (60, position.entry_mc * 4.0),
                (80, position.entry_mc * 5.5),
                (100, OPTIMAL_WINDOW['migration_mc']),
            ]

            for pct, mc in steps:
                current_multiplier = mc / position.entry_mc
                current_roi = (current_multiplier - 1) * 100
                print(f"  [{pct}%] MC: ${mc:,.0f} - Unrealized ROI: {current_roi:+.0f}%")
                await asyncio.sleep(0.5)  # Petit délai pour l'effet

            print(f"\n🚨 MIGRATION DETECTED! 🚨")
            print(f"  Token reached ${OPTIMAL_WINDOW['migration_mc']:,} market cap")
            print(f"  Raydium pool created")

            position.migrated = True
            return True
        else:
            # Simule un échec
            print(f"Simulating token decline...")
            await asyncio.sleep(1)

            final_mc = position.entry_mc * 0.5  # Token drops to 50%
            loss = (0.5 - 1) * 100

            print(f"\n❌ MIGRATION FAILED")
            print(f"  Token declined to ${final_mc:,.0f} market cap")
            print(f"  Unrealized loss: {loss:.0f}%")

            position.migrated = False
            return False

    async def simulate_multi_sell(self, position):
        """Simule la vente multi-portion"""

        print(f"\n{'='*70}")
        print(f"PHASE 3: EXECUTING MULTI-SELL - {position.symbol}")
        print(f"{'='*70}")

        # Calculate exit based on migration MC
        multiplier = OPTIMAL_WINDOW['migration_mc'] / position.entry_mc

        # Simulate slight slippage (98-102% of expected)
        slippage_factor = 0.98 + (random.random() * 0.04)
        actual_multiplier = multiplier * slippage_factor

        exit_sol = position.entry_sol * actual_multiplier
        profit_sol = exit_sol - position.entry_sol
        roi_pct = (actual_multiplier - 1) * 100

        # Simulate multi-sell execution
        portions = 60
        sol_per_portion = exit_sol / portions

        print(f"\nStrategy:")
        print(f"  Total tokens: {position.entry_tokens:,.0f}")
        print(f"  Sell portions: {portions}")
        print(f"  SOL per portion: {sol_per_portion:.4f}")
        print(f"  Duration: 60 seconds (simulated)")

        print(f"\nExecuting sells...")
        total_sold = 0
        for i in range(portions):
            total_sold += sol_per_portion
            if (i + 1) % 15 == 0 or i == 0 or i == portions - 1:
                print(f"  [SELL {i+1}/{portions}] Total: {total_sold:.4f} SOL")
            await asyncio.sleep(0.05)  # Fast simulation

        # Update position
        position.sold = True
        position.exit_sol = exit_sol
        position.profit_sol = profit_sol
        position.roi_pct = roi_pct

        # Update wallet
        self.wallet_sol += exit_sol
        self.total_profit_sol += profit_sol

        print(f"\n{'='*70}")
        print("MULTI-SELL COMPLETE")
        print(f"{'='*70}")
        print(f"\n{position.symbol} P&L:")
        print(f"  Entry: {position.entry_sol:.4f} SOL @ ${position.entry_mc:,.0f} MC")
        print(f"  Exit: {exit_sol:.4f} SOL @ ${OPTIMAL_WINDOW['migration_mc']:,} MC")
        print(f"  Profit: {profit_sol:+.4f} SOL (${profit_sol * SOL_PRICE_USD:+.2f})")
        print(f"  ROI: {roi_pct:+.1f}%")
        print(f"  Multiplier: {actual_multiplier:.2f}x")

        if roi_pct >= 500:
            print(f"\n  🚀 EXCELLENT PROFIT!")
        elif roi_pct >= 300:
            print(f"\n  ✅ GREAT PROFIT!")
        elif roi_pct >= 100:
            print(f"\n  👍 GOOD PROFIT!")

        # Save to completed trades
        self.completed_trades.append(position)

        return profit_sol

    async def simulate_stop_loss(self, position):
        """Simule un stop loss (token qui ne migre pas)"""

        print(f"\n{'='*70}")
        print(f"STOP LOSS TRIGGERED - {position.symbol}")
        print(f"{'='*70}")

        # Assume 50% loss
        loss_factor = 0.5
        exit_sol = position.entry_sol * loss_factor
        loss_sol = exit_sol - position.entry_sol
        roi_pct = (loss_factor - 1) * 100

        position.sold = True
        position.exit_sol = exit_sol
        position.profit_sol = loss_sol
        position.roi_pct = roi_pct

        self.wallet_sol += exit_sol
        self.total_profit_sol += loss_sol

        print(f"\n{position.symbol} P&L:")
        print(f"  Entry: {position.entry_sol:.4f} SOL")
        print(f"  Exit: {exit_sol:.4f} SOL (stop loss @ -50%)")
        print(f"  Loss: {loss_sol:.4f} SOL (${loss_sol * SOL_PRICE_USD:.2f})")
        print(f"  ROI: {roi_pct:.1f}%")

        self.completed_trades.append(position)

        return loss_sol

    async def run_full_simulation(self, num_tokens_to_buy=5):
        """Run simulation complète du cycle"""

        print("\n" + "="*70)
        print("SIMULATION TEST - PAPER TRADING")
        print("="*70)
        print(f"Testing complete cycle with FAKE SOL")
        print(f"Starting wallet: {FAKE_WALLET_SOL:.2f} SOL (${FAKE_WALLET_SOL * SOL_PRICE_USD:.2f})")
        print("="*70)

        # Phase 1: Scan and buy
        candidates = await self.scan_for_candidates()

        if not candidates:
            print("\n[!] No candidates found in optimal window")
            print("[!] This is normal - try again later or wait for more tokens")
            return

        print(f"\n{'='*70}")
        print(f"PHASE 1: BUYING TOKENS")
        print(f"{'='*70}")

        # Buy top candidates
        bought = 0
        for candidate in candidates[:num_tokens_to_buy]:
            if self.wallet_sol < BUY_AMOUNT_SOL:
                print(f"\n[!] Out of funds")
                break

            position = self.simulate_buy(candidate)
            if position:
                bought += 1

            if bought >= num_tokens_to_buy:
                break

        if bought == 0:
            print("\n[!] No tokens bought")
            return

        print(f"\n[BOUGHT] {bought} tokens")
        print(f"[WALLET] {self.wallet_sol:.2f} SOL remaining")

        # Phase 2 & 3: Simulate migration and selling
        print(f"\n{'='*70}")
        print(f"PHASE 2 & 3: MIGRATION + SELLING")
        print(f"{'='*70}")
        print(f"Simulating migration for {bought} tokens...")
        print(f"Expected: 70% migrate, 30% fail")

        for i, position in enumerate(self.positions):
            print(f"\n\n[TOKEN {i+1}/{len(self.positions)}] {position.symbol}")
            print("="*70)

            # Simulate 70% success rate
            will_migrate = random.random() < 0.70

            if will_migrate:
                # Simulate successful migration
                success = await self.simulate_migration_wait(position, simulate_success=True)

                if success:
                    # Multi-sell
                    await self.simulate_multi_sell(position)
            else:
                # Simulate failed migration (stop loss)
                await self.simulate_migration_wait(position, simulate_success=False)
                await asyncio.sleep(1)
                self.simulate_stop_loss(position)

        # Final summary
        await self.print_final_summary()

    async def print_final_summary(self):
        """Print final simulation results"""

        print("\n\n" + "="*70)
        print("SIMULATION RESULTS")
        print("="*70)

        total_trades = len(self.completed_trades)
        winners = [t for t in self.completed_trades if t.profit_sol > 0]
        losers = [t for t in self.completed_trades if t.profit_sol <= 0]

        win_rate = (len(winners) / total_trades * 100) if total_trades > 0 else 0
        total_invested = sum(t.entry_sol for t in self.completed_trades)
        total_returned = sum(t.exit_sol for t in self.completed_trades)

        print(f"\nStarting wallet: {FAKE_WALLET_SOL:.2f} SOL (${FAKE_WALLET_SOL * SOL_PRICE_USD:.2f})")
        print(f"Final wallet: {self.wallet_sol:.2f} SOL (${self.wallet_sol * SOL_PRICE_USD:.2f})")
        print(f"\nTotal trades: {total_trades}")
        print(f"Winners: {len(winners)} ({win_rate:.1f}%)")
        print(f"Losers: {len(losers)} ({100-win_rate:.1f}%)")

        print(f"\nTotal invested: {total_invested:.2f} SOL (${total_invested * SOL_PRICE_USD:.2f})")
        print(f"Total returned: {total_returned:.2f} SOL (${total_returned * SOL_PRICE_USD:.2f})")
        print(f"\nNet profit: {self.total_profit_sol:+.4f} SOL (${self.total_profit_sol * SOL_PRICE_USD:+.2f})")

        if total_trades > 0:
            avg_roi = sum(t.roi_pct for t in self.completed_trades) / total_trades
            print(f"Average ROI: {avg_roi:+.1f}%")

        if winners:
            avg_win = sum(t.profit_sol for t in winners) / len(winners)
            avg_win_roi = sum(t.roi_pct for t in winners) / len(winners)
            print(f"\nAverage profit per winner: {avg_win:.4f} SOL (${avg_win * SOL_PRICE_USD:.2f})")
            print(f"Average ROI per winner: {avg_win_roi:+.1f}%")

        if losers:
            avg_loss = sum(t.profit_sol for t in losers) / len(losers)
            avg_loss_roi = sum(t.roi_pct for t in losers) / len(losers)
            print(f"\nAverage loss per loser: {avg_loss:.4f} SOL (${avg_loss * SOL_PRICE_USD:.2f})")
            print(f"Average ROI per loser: {avg_loss_roi:.1f}%")

        print(f"\n{'='*70}")
        print("DETAILED RESULTS")
        print(f"{'='*70}")

        for i, trade in enumerate(self.completed_trades, 1):
            status = "WIN" if trade.profit_sol > 0 else "LOSS"
            print(f"\n[{i}] {trade.symbol} - {status}")
            print(f"  Entry: {trade.entry_sol:.4f} SOL @ ${trade.entry_mc:,.0f} MC")
            print(f"  Exit: {trade.exit_sol:.4f} SOL")
            print(f"  P&L: {trade.profit_sol:+.4f} SOL (${trade.profit_sol * SOL_PRICE_USD:+.2f})")
            print(f"  ROI: {trade.roi_pct:+.1f}%")
            print(f"  Score: {trade.score}/100")
            print(f"  Migrated: {'YES' if trade.migrated else 'NO'}")

        print(f"\n{'='*70}")
        print("SIMULATION COMPLETE")
        print(f"{'='*70}")

        if self.total_profit_sol > 0:
            print(f"\n✅ Profitable strategy! +{self.total_profit_sol:.4f} SOL (+${self.total_profit_sol * SOL_PRICE_USD:.2f})")
        else:
            print(f"\n❌ Unprofitable in this simulation. {self.total_profit_sol:.4f} SOL (${self.total_profit_sol * SOL_PRICE_USD:.2f})")

        print(f"\nNote: This is a SIMULATION with fake SOL")
        print(f"Results may vary with real trading")

    async def close(self):
        await self.client.aclose()


async def main():
    print("\n" + "="*70)
    print("TEST SIMULATION - PAPER TRADING")
    print("="*70)
    print("\nTest the complete system with FAKE SOL")
    print("This will:")
    print("  1. Scan for tokens in $9.5k-$13k window")
    print("  2. Simulate buying with fake SOL")
    print("  3. Simulate migration (70% success rate)")
    print("  4. Simulate multi-sell or stop-loss")
    print("  5. Calculate final P&L")
    print("\nNo real money involved - 100% simulation!")
    print("="*70)

    num_tokens = input(f"\nHow many tokens to simulate buying? (1-10, default 5): ").strip()

    try:
        num_tokens = int(num_tokens) if num_tokens else 5
        num_tokens = max(1, min(10, num_tokens))
    except:
        num_tokens = 5

    print(f"\n[STARTING] Simulation with {num_tokens} tokens...")

    tester = SimulationTester()

    try:
        await tester.run_full_simulation(num_tokens_to_buy=num_tokens)
    except KeyboardInterrupt:
        print("\n\n[!] Simulation interrupted")
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())

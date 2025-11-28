"""
AUTO MULTI-SELL BOT
Execute 60-87 sell portions AFTER migration is detected
Based on winning strategy: 90.9% win rate when applied

WORKFLOW:
1. Monitor positions bought in $9.5k-$13k window
2. Detect migration (MC ~$69k, Raydium pool created)
3. Auto-execute 60-87 sells over 1 hour
4. Track profit realization
"""
import asyncio
import httpx
import json
from datetime import datetime, timedelta
from collections import defaultdict

# Configuration
MIGRATION_THRESHOLD_MC = 65000  # Start watching at $65k
MIGRATION_CONFIRMED_MC = 69000  # Migration confirmed at $69k
SELL_PORTIONS = 60  # Number of sell transactions
SELL_DURATION_MINUTES = 60  # Duration of selling period
MIN_PORTION_SIZE = 0.01  # Minimum SOL per sell

class Position:
    """Track an open position"""
    def __init__(self, token_data):
        self.mint = token_data['mint']
        self.symbol = token_data.get('symbol', '???')
        self.name = token_data.get('name', 'Unknown')
        self.entry_mc = token_data['entry_mc']
        self.entry_sol = token_data['entry_sol']
        self.entry_tokens = token_data['entry_tokens']
        self.entry_time = token_data.get('entry_time', datetime.now())
        self.target_mc = MIGRATION_CONFIRMED_MC
        self.migration_detected = False
        self.sell_started = False
        self.portions_sold = 0
        self.total_portions = SELL_PORTIONS
        self.total_sold_sol = 0

    def calculate_expected_roi(self):
        """Calculate expected ROI if migration succeeds"""
        multiplier = self.target_mc / self.entry_mc
        roi_pct = (multiplier - 1) * 100
        expected_sol = self.entry_sol * multiplier
        expected_profit = expected_sol - self.entry_sol
        return {
            'multiplier': multiplier,
            'roi_pct': roi_pct,
            'expected_sol': expected_sol,
            'expected_profit': expected_profit
        }

    def get_portion_size(self):
        """Calculate size of each sell portion"""
        # Sell all tokens in equal portions
        return self.entry_tokens / self.total_portions


class MultiSellBot:
    """Automated multi-sell execution bot"""

    def __init__(self):
        self.positions = {}  # mint -> Position
        self.client = httpx.AsyncClient(timeout=30.0)

    async def load_positions(self, positions_file='open_positions.json'):
        """Load open positions from file"""
        try:
            with open(positions_file, 'r') as f:
                data = json.load(f)

            for pos_data in data.get('positions', []):
                position = Position(pos_data)
                self.positions[position.mint] = position

            print(f"[+] Loaded {len(self.positions)} open positions")
            return True

        except FileNotFoundError:
            print(f"[!] No positions file found: {positions_file}")
            print("[!] Create positions manually or use optimal_entry_bot.py")
            return False
        except Exception as e:
            print(f"[!] Error loading positions: {e}")
            return False

    async def check_token_status(self, mint):
        """Check current status of a token"""
        try:
            url = f"https://frontend-api.pump.fun/coins/{mint}"
            response = await self.client.get(url)

            if response.status_code == 200:
                token = response.json()
                return {
                    'market_cap': token.get('usd_market_cap', 0),
                    'raydium_pool': token.get('raydium_pool'),
                    'complete': token.get('complete', False),
                    'bonding_curve_pct': token.get('bonding_curve_pct', 0),
                    'price': token.get('price_sol', 0),
                }
            else:
                return None

        except Exception as e:
            print(f"[!] Error checking {mint}: {e}")
            return None

    async def detect_migration(self, position):
        """Check if token has migrated"""
        status = await self.check_token_status(position.mint)

        if not status:
            return False, None

        mc = status['market_cap']
        has_raydium = status['raydium_pool'] is not None
        is_complete = status['complete']

        # Migration confirmed if:
        # 1. Has Raydium pool, OR
        # 2. Complete flag is True, OR
        # 3. MC >= $69k
        if has_raydium or is_complete or mc >= MIGRATION_CONFIRMED_MC:
            return True, status

        # Pre-migration warning
        if mc >= MIGRATION_THRESHOLD_MC:
            return 'SOON', status

        return False, status

    async def execute_multi_sell(self, position, current_price):
        """Execute multi-sell strategy (SIMULATION)"""
        print(f"\n{'='*70}")
        print(f"EXECUTING MULTI-SELL: {position.symbol}")
        print(f"{'='*70}")

        portion_size = position.get_portion_size()
        interval = (SELL_DURATION_MINUTES * 60) / position.total_portions

        print(f"\nStrategy:")
        print(f"  Total tokens: {position.entry_tokens:,.0f}")
        print(f"  Sell portions: {position.total_portions}")
        print(f"  Tokens per portion: {portion_size:,.0f}")
        print(f"  Duration: {SELL_DURATION_MINUTES} minutes")
        print(f"  Interval: {interval:.1f} seconds")
        print(f"  Current price: {current_price:.10f} SOL")

        print(f"\n{'='*70}")
        print("SIMULATING SELLS (In production, this would execute real transactions)")
        print(f"{'='*70}")

        total_sold_sol = 0

        for i in range(position.total_portions):
            # In production: Execute actual sell transaction here
            # For now: Simulate

            # Simulate slight price variation during selling
            price_variation = 0.95 + (0.1 * (i / position.total_portions))  # Price may vary 95%-105%
            portion_price = current_price * price_variation
            portion_sol = portion_size * portion_price

            total_sold_sol += portion_sol
            position.portions_sold += 1
            position.total_sold_sol = total_sold_sol

            # Print every 10th portion to avoid spam
            if (i + 1) % 10 == 0 or i == 0 or i == position.total_portions - 1:
                print(f"[SELL {i+1}/{position.total_portions}] "
                      f"{portion_size:,.0f} tokens @ {portion_price:.10f} SOL "
                      f"= {portion_sol:.4f} SOL "
                      f"(Total: {total_sold_sol:.4f} SOL)")

            # Wait between portions (except last one)
            if i < position.total_portions - 1:
                await asyncio.sleep(interval)

        # Calculate final P&L
        profit_sol = total_sold_sol - position.entry_sol
        roi_pct = (profit_sol / position.entry_sol) * 100

        print(f"\n{'='*70}")
        print("MULTI-SELL COMPLETE")
        print(f"{'='*70}")
        print(f"\n{position.symbol} P&L:")
        print(f"  Entry: {position.entry_sol:.4f} SOL @ ${position.entry_mc:,.0f} MC")
        print(f"  Exit: {total_sold_sol:.4f} SOL (avg over {position.total_portions} sells)")
        print(f"  Profit: {profit_sol:.4f} SOL (${profit_sol * 200:.2f} @ $200/SOL)")
        print(f"  ROI: {roi_pct:+.1f}%")

        if roi_pct > 400:
            print(f"\n  >> EXCELLENT PROFIT! 🚀")
        elif roi_pct > 200:
            print(f"\n  >> GOOD PROFIT!")
        elif roi_pct > 0:
            print(f"\n  >> Profitable")
        else:
            print(f"\n  >> Loss")

        position.sell_started = True

        return {
            'sold_sol': total_sold_sol,
            'profit_sol': profit_sol,
            'roi_pct': roi_pct
        }

    async def monitor_positions(self, check_interval=30):
        """Monitor all positions and execute sells on migration"""

        print(f"\n{'='*70}")
        print("AUTO MULTI-SELL BOT - MONITORING")
        print(f"{'='*70}")
        print(f"Monitoring {len(self.positions)} open positions")
        print(f"Check interval: {check_interval}s")
        print(f"Migration threshold: ${MIGRATION_THRESHOLD_MC:,}")
        print(f"Migration confirmed: ${MIGRATION_CONFIRMED_MC:,}")
        print(f"{'='*70}")

        iteration = 0

        while True:
            iteration += 1
            print(f"\n\n[CHECK {iteration}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}")

            active_positions = [p for p in self.positions.values() if not p.sell_started]

            if not active_positions:
                print("\n[DONE] All positions closed")
                break

            for position in active_positions:
                print(f"\n[{position.symbol}]")
                print(f"  Entry: ${position.entry_mc:,.0f} MC")
                print(f"  Target: ${position.target_mc:,.0f} MC")

                # Check migration status
                migrated, status = await self.detect_migration(position)

                if not status:
                    print(f"  Status: ERROR - Could not fetch data")
                    continue

                current_mc = status['market_cap']
                current_price = status['price']
                has_pool = status['raydium_pool'] is not None

                print(f"  Current MC: ${current_mc:,.0f}")
                print(f"  Raydium pool: {'YES' if has_pool else 'NO'}")

                if migrated == True:
                    # MIGRATION DETECTED - EXECUTE SELLS
                    if not position.migration_detected:
                        position.migration_detected = True

                        print(f"\n🚨 MIGRATION DETECTED! 🚨")
                        print(f"  Token: {position.symbol}")
                        print(f"  Entry MC: ${position.entry_mc:,.0f}")
                        print(f"  Migration MC: ${current_mc:,.0f}")

                        expected = position.calculate_expected_roi()
                        print(f"  Expected ROI: {expected['roi_pct']:+.1f}%")
                        print(f"  Expected profit: {expected['expected_profit']:.4f} SOL")

                        print(f"\n[ACTION] Starting multi-sell in 5 seconds...")
                        await asyncio.sleep(5)

                        # Execute multi-sell
                        result = await self.execute_multi_sell(position, current_price)

                        # Save result
                        self.save_trade_result(position, result)

                elif migrated == 'SOON':
                    # Pre-migration warning
                    print(f"  ⚠️ PRE-MIGRATION: ${current_mc:,.0f} (approaching ${MIGRATION_CONFIRMED_MC:,})")
                    print(f"  Ready to sell when migration confirmed")

                else:
                    # Not migrated yet
                    progress = (current_mc / position.target_mc) * 100
                    print(f"  Progress: {progress:.1f}% to migration")

                    # Calculate current unrealized P&L
                    current_multiplier = current_mc / position.entry_mc
                    current_roi = (current_multiplier - 1) * 100
                    print(f"  Unrealized ROI: {current_roi:+.1f}%")

            # Wait before next check
            if active_positions:
                print(f"\n[WAITING] Next check in {check_interval}s...")
                await asyncio.sleep(check_interval)

        print(f"\n{'='*70}")
        print("MONITORING COMPLETE")
        print(f"{'='*70}")

        # Summary
        await self.print_summary()

    def save_trade_result(self, position, result):
        """Save completed trade result"""
        trade_data = {
            'timestamp': datetime.now().isoformat(),
            'mint': position.mint,
            'symbol': position.symbol,
            'name': position.name,
            'entry_mc': position.entry_mc,
            'entry_sol': position.entry_sol,
            'entry_time': position.entry_time.isoformat() if hasattr(position.entry_time, 'isoformat') else str(position.entry_time),
            'exit_sol': result['sold_sol'],
            'profit_sol': result['profit_sol'],
            'roi_pct': result['roi_pct'],
            'portions_sold': position.portions_sold,
            'strategy': 'multi_sell'
        }

        # Append to results file
        try:
            try:
                with open('completed_trades.json', 'r') as f:
                    data = json.load(f)
            except FileNotFoundError:
                data = {'trades': []}

            data['trades'].append(trade_data)

            with open('completed_trades.json', 'w') as f:
                json.dump(data, f, indent=2)

            print(f"\n[SAVED] Trade result saved to completed_trades.json")

        except Exception as e:
            print(f"[!] Error saving trade: {e}")

    async def print_summary(self):
        """Print summary of all trades"""
        try:
            with open('completed_trades.json', 'r') as f:
                data = json.load(f)

            trades = data.get('trades', [])

            if not trades:
                return

            print(f"\n{'='*70}")
            print("SESSION SUMMARY")
            print(f"{'='*70}")

            total_trades = len(trades)
            total_profit = sum(t['profit_sol'] for t in trades)
            avg_roi = sum(t['roi_pct'] for t in trades) / total_trades
            winners = [t for t in trades if t['profit_sol'] > 0]

            print(f"\nTotal trades: {total_trades}")
            print(f"Winners: {len(winners)}/{total_trades} ({len(winners)/total_trades*100:.1f}%)")
            print(f"Total profit: {total_profit:.4f} SOL (${total_profit * 200:.2f} @ $200/SOL)")
            print(f"Average ROI: {avg_roi:+.1f}%")

            print(f"\n{'='*70}")

        except Exception as e:
            print(f"[!] Could not generate summary: {e}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


async def create_example_positions():
    """Create example positions file for testing"""

    example_positions = {
        'generated_at': datetime.now().isoformat(),
        'description': 'Example positions for testing auto multi-sell bot',
        'positions': [
            {
                'mint': 'EXAMPLE1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                'symbol': 'TEST1',
                'name': 'Test Token 1',
                'entry_mc': 9500,
                'entry_sol': 2.0,
                'entry_tokens': 1000000,
                'entry_time': datetime.now().isoformat()
            },
            {
                'mint': 'EXAMPLE2xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                'symbol': 'TEST2',
                'name': 'Test Token 2',
                'entry_mc': 11000,
                'entry_sol': 2.5,
                'entry_tokens': 1200000,
                'entry_time': datetime.now().isoformat()
            }
        ]
    }

    with open('open_positions.json', 'w') as f:
        json.dump(example_positions, f, indent=2)

    print("[+] Created example positions file: open_positions.json")
    print("[!] Replace with real positions from optimal_entry_bot.py")


async def main():
    print("\n=== AUTO MULTI-SELL BOT ===\n")
    print("Execute 60-87 sell portions AFTER migration")
    print("Based on 90.9% win rate strategy\n")

    print("Modes:")
    print("1. Monitor existing positions")
    print("2. Create example positions file")

    choice = input("\nSelect mode (1 or 2): ").strip()

    if choice == '2':
        await create_example_positions()
        return

    # Monitor mode
    bot = MultiSellBot()

    # Load positions
    loaded = await bot.load_positions()

    if not loaded:
        print("\n[!] No positions to monitor")
        print("[!] Run optimal_entry_bot.py first to create positions")
        return

    # Start monitoring
    try:
        await bot.monitor_positions(check_interval=30)
    except KeyboardInterrupt:
        print("\n\n[!] Monitoring stopped by user")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())

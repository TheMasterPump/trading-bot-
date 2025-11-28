"""
LIVE DASHBOARD BOT
Interface en temps réel pour voir le bot travailler
"""
import asyncio
import json
import websockets
from datetime import datetime
import random
import os

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
        self.open_positions = {}
        self.completed_trades = []
        self.total_profit_sol = 0
        self.tokens_scanned = 0
        self.tokens_bought = 0
        self.tokens_migrated = 0
        self.last_tokens = []  # Derniers tokens scannés
        self.running = True

    def clear_screen(self):
        """Clear terminal"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_dashboard(self):
        """Affiche dashboard"""
        self.clear_screen()

        now = datetime.now().strftime('%H:%M:%S')

        print(f"{Colors.BRIGHT_BLUE}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}       LIVE TRADING BOT DASHBOARD - {now}{Colors.RESET}")
        print(f"{Colors.BRIGHT_BLUE}{'=' * 80}{Colors.RESET}")

        # Stats globales
        print(f"\n{Colors.BLUE}[WALLET]{Colors.RESET}")
        print(f"  {Colors.CYAN}Current:{Colors.RESET} {self.wallet_sol:.2f} SOL (${self.wallet_sol * SOL_PRICE_USD:,.0f})")
        pnl_color = Colors.GREEN if self.total_profit_sol >= 0 else Colors.RED
        print(f"  {Colors.CYAN}P&L:{Colors.RESET} {pnl_color}{self.total_profit_sol:+.4f} SOL (${self.total_profit_sol * SOL_PRICE_USD:+.2f}){Colors.RESET}")
        pnl_pct = ((self.wallet_sol - self.start_wallet) / self.start_wallet) * 100 if self.start_wallet > 0 else 0
        print(f"  {Colors.CYAN}Change:{Colors.RESET} {pnl_color}{pnl_pct:+.1f}%{Colors.RESET}")

        print(f"\n{Colors.BLUE}[STATISTICS]{Colors.RESET}")
        print(f"  {Colors.CYAN}Scanned:{Colors.RESET} {self.tokens_scanned} tokens")
        print(f"  {Colors.CYAN}Bought:{Colors.RESET} {self.tokens_bought} tokens")
        print(f"  {Colors.CYAN}Migrated:{Colors.RESET} {self.tokens_migrated} tokens")
        win_rate = (self.tokens_migrated / max(self.tokens_bought, 1)) * 100 if self.tokens_bought > 0 else 0
        win_color = Colors.GREEN if win_rate >= 70 else Colors.YELLOW if win_rate >= 50 else Colors.RED
        print(f"  {Colors.CYAN}Win Rate:{Colors.RESET} {win_color}{win_rate:.0f}%{Colors.RESET}" if self.tokens_bought > 0 else f"  {Colors.CYAN}Win Rate:{Colors.RESET} {Colors.GRAY}N/A{Colors.RESET}")

        # Positions ouvertes
        print(f"\n{Colors.BLUE}[OPEN POSITIONS]{Colors.RESET} {Colors.GRAY}({len(self.open_positions)}){Colors.RESET}")
        if self.open_positions:
            for mint, pos in list(self.open_positions.items())[:5]:  # Max 5
                unrealized = pos.calculate_unrealized()
                progress = (pos.current_mc / OPTIMAL_WINDOW['migration_mc']) * 100
                time_held = (datetime.now() - pos.entry_time).total_seconds() / 60

                roi_color = Colors.GREEN if unrealized['roi'] > 0 else Colors.RED
                progress_color = Colors.GREEN if progress >= 80 else Colors.YELLOW if progress >= 50 else Colors.CYAN

                print(f"  {Colors.BOLD}{pos.symbol:8s}{Colors.RESET} | MC: {Colors.CYAN}${pos.current_mc:>8,.0f}{Colors.RESET} | {progress_color}{progress:>5.1f}%{Colors.RESET} → $69k | U-ROI: {roi_color}{unrealized['roi']:>+6.0f}%{Colors.RESET} | {Colors.GRAY}{time_held:.0f}m{Colors.RESET}")
        else:
            print(f"  {Colors.GRAY}No open positions{Colors.RESET}")

        # Derniers trades complétés
        print(f"\n{Colors.BLUE}[RECENT TRADES]{Colors.RESET} {Colors.GRAY}({len(self.completed_trades)}){Colors.RESET}")
        if self.completed_trades:
            for trade in list(self.completed_trades)[-3:]:  # Last 3
                status_text = "WIN" if trade.profit_sol > 0 else "LOSS"
                status_color = Colors.GREEN if trade.profit_sol > 0 else Colors.RED
                profit_color = Colors.GREEN if trade.profit_sol > 0 else Colors.RED

                print(f"  {Colors.BOLD}{trade.symbol:8s}{Colors.RESET} | {profit_color}{trade.profit_sol:+.4f} SOL{Colors.RESET} ({profit_color}${trade.profit_sol * SOL_PRICE_USD:+.0f}{Colors.RESET}) | ROI: {profit_color}{trade.roi_pct:+.0f}%{Colors.RESET} | {status_color}{status_text}{Colors.RESET}")
        else:
            print(f"  {Colors.GRAY}No completed trades yet{Colors.RESET}")

        # Derniers tokens scannés
        print(f"\n{Colors.BLUE}[RECENT SCANS]{Colors.RESET}")
        if self.last_tokens:
            for token in self.last_tokens[-5:]:  # Last 5
                status = token.get('status', 'SCANNED')
                mc = token.get('mc', 0)
                symbol = token.get('symbol', '???')
                score = token.get('score', 0)

                score_color = Colors.GREEN if score >= 65 else Colors.YELLOW if score >= 50 else Colors.GRAY
                status_color = Colors.GREEN if 'BOUGHT' in status else Colors.CYAN if 'SOLD' in status else Colors.GRAY

                print(f"  {Colors.BOLD}{symbol:8s}{Colors.RESET} | MC: {Colors.CYAN}${mc:>8,.0f}{Colors.RESET} | Score: {score_color}{score:>3}/100{Colors.RESET} | {status_color}{status}{Colors.RESET}")
        else:
            print(f"  {Colors.GRAY}Waiting for tokens...{Colors.RESET}")

        print(f"\n{Colors.BRIGHT_BLUE}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.GRAY}Press Ctrl+C to stop{Colors.RESET}")
        print(f"{Colors.BRIGHT_BLUE}{'=' * 80}{Colors.RESET}")

    def calculate_score(self, token_data):
        score = 0

        # Social (0-30)
        if token_data.get('twitter'): score += 10
        if token_data.get('telegram'): score += 10
        if token_data.get('website'): score += 10

        # Transactions (0-30)
        txn = token_data.get('txnCount', 0)
        if txn >= 100: score += 30
        elif txn >= 50: score += 20
        elif txn >= 20: score += 10
        elif txn >= 10: score += 5

        # Initial buy (0-20)
        init = token_data.get('initialBuy', 0)
        if init >= 2: score += 20
        elif init >= 1: score += 10
        elif init >= 0.5: score += 5

        # MC position (0-20)
        mc = token_data.get('market_cap_usd', 0)
        if OPTIMAL_WINDOW['min_mc'] <= mc <= OPTIMAL_WINDOW['max_mc']:
            if mc <= 10500: score += 20
            elif mc <= 11500: score += 15
            else: score += 10

        return {
            'total': min(score, 100),
            'should_buy': score >= 50,
            'confidence': 'HIGH' if score >= 65 else 'MEDIUM' if score >= 50 else 'LOW'
        }

    async def buy_token(self, token_data):
        if self.wallet_sol < BUY_AMOUNT_SOL:
            return None

        position = Position(token_data, BUY_AMOUNT_SOL)
        self.wallet_sol -= BUY_AMOUNT_SOL
        self.open_positions[position.mint] = position
        self.tokens_bought += 1

        # Ajoute à l'historique
        self.last_tokens.append({
            'symbol': position.symbol,
            'mc': position.entry_mc,
            'score': position.score['total'],
            'status': f'BOUGHT {BUY_AMOUNT_SOL} SOL'
        })

        # Simulate migration (70% chance)
        if random.random() < 0.70:
            delay = random.uniform(10, 30)  # 10-30 secondes
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

        # Simulate selling (rapide)
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

        # Ajoute à l'historique
        self.last_tokens.append({
            'symbol': position.symbol,
            'mc': position.current_mc,
            'score': position.score['total'],
            'status': f'SOLD +{profit_sol:.2f} SOL ({roi_pct:+.0f}%)'
        })

    async def process_token(self, data):
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

        # Ajoute à l'historique (tous les tokens)
        self.last_tokens.append({
            'symbol': symbol,
            'mc': mc_usd,
            'score': 0,
            'status': 'SCANNED'
        })

        # Keep only last 20
        if len(self.last_tokens) > 20:
            self.last_tokens = self.last_tokens[-20:]

        # Check window
        if not (OPTIMAL_WINDOW['min_mc'] <= mc_usd <= OPTIMAL_WINDOW['max_mc']):
            return

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
        }

        score = self.calculate_score(token_data)
        token_data['score'] = score

        # Update last token entry
        if self.last_tokens:
            self.last_tokens[-1]['score'] = score['total']
            self.last_tokens[-1]['status'] = f"IN WINDOW - Score: {score['total']}"

        if score['should_buy']:
            await self.buy_token(token_data)

    async def update_dashboard(self):
        """Met à jour le dashboard périodiquement"""
        while self.running:
            self.print_dashboard()
            await asyncio.sleep(2)  # Update every 2 seconds

    async def run(self, duration_minutes=30):
        print("\nConnecting to WebSocket...")

        try:
            async with websockets.connect('wss://pumpportal.fun/api/data') as ws:
                await ws.send(json.dumps({'method': 'subscribeNewToken'}))

                # Start dashboard updater
                dashboard_task = asyncio.create_task(self.update_dashboard())

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

                self.running = False
                dashboard_task.cancel()

                # Final display
                print("\n\nSESSION TERMINEE\n")
                self.print_final_summary()

        except Exception as e:
            self.running = False
            print(f"\n[ERROR] {e}")

    def print_final_summary(self):
        print("=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)

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

        print("\n" + "=" * 80)


async def main():
    print("\n" + "="*80)
    print("  LIVE DASHBOARD TRADING BOT")
    print("="*80)
    print("\nMode: SIMULATION avec FAKE SOL")
    print("Target: $9,500 - $13,000 market cap")
    print("Duration: 30 minutes (Ctrl+C pour arrêter avant)")
    print("\nLe dashboard se met à jour toutes les 2 secondes...")
    print("\nDémarrage dans 3 secondes...\n")

    await asyncio.sleep(3)

    bot = LiveDashboardBot()
    await bot.run(duration_minutes=30)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[STOPPED] Arrêté par l'utilisateur")

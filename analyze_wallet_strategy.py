"""
WALLET STRATEGY ANALYZER
Analyse n'importe quel wallet pour reverse-engineer sa stratégie de trading
"""
import asyncio
import httpx
import json
from datetime import datetime, timedelta
from pathlib import Path
# Direct API key
HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"
from collections import defaultdict

class WalletStrategyAnalyzer:
    def __init__(self, wallet_address: str):
        self.wallet = wallet_address
        self.client = httpx.AsyncClient(timeout=60.0)
        self.transactions = []
        self.trades = []
        self.token_trades = defaultdict(list)

    async def fetch_all_transactions(self, limit=100):
        """Récupère toutes les transactions du wallet via Solana RPC"""
        print(f"\n[*] Fetching transactions for wallet: {self.wallet[:16]}...")

        # Helius Enhanced Transactions API
        url = "https://api.helius.xyz/v0/addresses/{}/transactions".format(self.wallet)
        headers = {
            "Content-Type": "application/json"
        }
        params = {
            "api-key": HELIUS_API_KEY
        }

        try:
            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                self.transactions = response.json()
                print(f"[+] Fetched {len(self.transactions)} transactions")
                return True
            else:
                print(f"[!] Helius API error: {response.status_code}")

                # Fallback: try to get from Solscan
                print("[*] Trying alternative method via public APIs...")
                return await self.fetch_via_solscan()

        except Exception as e:
            print(f"[!] Error: {e}")
            return await self.fetch_via_solscan()

    async def fetch_via_solscan(self):
        """Alternative: fetch via public APIs"""
        try:
            # Use Solscan public API
            url = f"https://public-api.solscan.io/account/transactions"
            params = {
                "account": self.wallet,
                "limit": 50
            }

            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                print(f"[+] Fetched {len(data)} transactions from Solscan")
                # Format to match our expected structure
                self.transactions = data
                return True
            else:
                print(f"[!] Solscan error: {response.status_code}")
                return False

        except Exception as e:
            print(f"[!] Solscan error: {e}")
            return False

    async def get_token_info_at_time(self, token_address: str):
        """Récupère les infos d'un token"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            response = await self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])
                if pairs:
                    return pairs[0]

            return None
        except:
            return None

    def parse_swap_transaction(self, tx):
        """Parse une transaction SWAP pour extraire les infos"""
        try:
            if tx.get('type') != 'SWAP':
                return None

            description = tx.get('description', '')
            timestamp = tx.get('timestamp')
            signature = tx.get('signature')

            # Extract tokens from native balances or token balances
            native_transfers = tx.get('nativeTransfers', [])
            token_transfers = tx.get('tokenTransfers', [])

            # Déterminer si c'est un achat ou une vente
            # Achat = SOL out, Token in
            # Vente = Token out, SOL in

            sol_change = 0
            token_info = None

            for transfer in native_transfers:
                if transfer.get('fromUserAccount') == self.wallet:
                    sol_change -= transfer.get('amount', 0) / 1e9
                elif transfer.get('toUserAccount') == self.wallet:
                    sol_change += transfer.get('amount', 0) / 1e9

            for transfer in token_transfers:
                if transfer.get('fromUserAccount') == self.wallet:
                    # Vente
                    token_info = {
                        'mint': transfer.get('mint'),
                        'amount': transfer.get('tokenAmount', 0),
                        'type': 'SELL'
                    }
                elif transfer.get('toUserAccount') == self.wallet:
                    # Achat
                    token_info = {
                        'mint': transfer.get('mint'),
                        'amount': transfer.get('tokenAmount', 0),
                        'type': 'BUY'
                    }

            if token_info:
                return {
                    'timestamp': timestamp,
                    'signature': signature,
                    'type': token_info['type'],
                    'token': token_info['mint'],
                    'token_amount': token_info['amount'],
                    'sol_amount': abs(sol_change),
                    'description': description
                }

            return None

        except Exception as e:
            return None

    def analyze_trades(self):
        """Analyse tous les trades"""
        print("\n[*] Parsing transactions...")

        for tx in self.transactions:
            trade = self.parse_swap_transaction(tx)
            if trade:
                self.trades.append(trade)
                self.token_trades[trade['token']].append(trade)

        print(f"[+] Identified {len(self.trades)} trades")
        print(f"[+] Across {len(self.token_trades)} unique tokens")

    async def calculate_trade_metrics(self):
        """Calcule les métriques de trading"""
        print("\n[*] Calculating trading metrics...")

        metrics = {
            'total_trades': len(self.trades),
            'unique_tokens': len(self.token_trades),
            'buys': len([t for t in self.trades if t['type'] == 'BUY']),
            'sells': len([t for t in self.trades if t['type'] == 'SELL']),
            'total_sol_spent': sum([t['sol_amount'] for t in self.trades if t['type'] == 'BUY']),
            'total_sol_received': sum([t['sol_amount'] for t in self.trades if t['type'] == 'SELL']),
            'avg_buy_size': 0,
            'avg_sell_size': 0,
            'completed_trades': [],
            'win_rate': 0,
            'avg_profit': 0,
            'avg_hold_time': 0,
            'entry_mcaps': [],
            'exit_mcaps': []
        }

        buys = [t for t in self.trades if t['type'] == 'BUY']
        sells = [t for t in self.trades if t['type'] == 'SELL']

        if buys:
            metrics['avg_buy_size'] = metrics['total_sol_spent'] / len(buys)

        if sells:
            metrics['avg_sell_size'] = metrics['total_sol_received'] / len(sells)

        # Analyser les trades complétés (buy + sell du même token)
        print("\n[*] Analyzing completed trades...")

        for token, token_trades in self.token_trades.items():
            token_buys = [t for t in token_trades if t['type'] == 'BUY']
            token_sells = [t for t in token_trades if t['type'] == 'SELL']

            # Match buys avec sells
            for buy in token_buys:
                for sell in token_sells:
                    if sell['timestamp'] > buy['timestamp']:
                        # Trade complété
                        profit_percent = ((sell['sol_amount'] - buy['sol_amount']) / buy['sol_amount']) * 100
                        hold_time_seconds = sell['timestamp'] - buy['timestamp']

                        # Récupérer les market caps
                        token_info = await self.get_token_info_at_time(token)

                        completed_trade = {
                            'token': token,
                            'buy_time': datetime.fromtimestamp(buy['timestamp']),
                            'sell_time': datetime.fromtimestamp(sell['timestamp']),
                            'buy_sol': buy['sol_amount'],
                            'sell_sol': sell['sol_amount'],
                            'profit_percent': profit_percent,
                            'hold_time_seconds': hold_time_seconds,
                            'hold_time_minutes': hold_time_seconds / 60,
                            'token_info': token_info
                        }

                        if token_info:
                            mcap = float(token_info.get('marketCap', 0))
                            completed_trade['current_mcap'] = mcap

                            # Estimation des entry/exit mcaps
                            # (approximation car on a pas les prix historiques exacts)
                            metrics['entry_mcaps'].append(mcap)
                            metrics['exit_mcaps'].append(mcap)

                        metrics['completed_trades'].append(completed_trade)
                        break

        # Calculer win rate et profit moyen
        if metrics['completed_trades']:
            winning_trades = [t for t in metrics['completed_trades'] if t['profit_percent'] > 0]
            metrics['win_rate'] = (len(winning_trades) / len(metrics['completed_trades'])) * 100
            metrics['avg_profit'] = sum([t['profit_percent'] for t in metrics['completed_trades']]) / len(metrics['completed_trades'])
            metrics['avg_hold_time'] = sum([t['hold_time_minutes'] for t in metrics['completed_trades']]) / len(metrics['completed_trades'])

            if metrics['entry_mcaps']:
                metrics['avg_entry_mcap'] = sum(metrics['entry_mcaps']) / len(metrics['entry_mcaps'])
            if metrics['exit_mcaps']:
                metrics['avg_exit_mcap'] = sum(metrics['exit_mcaps']) / len(metrics['exit_mcaps'])

        print(f"[+] Found {len(metrics['completed_trades'])} completed trades")

        return metrics

    def print_report(self, metrics):
        """Affiche le rapport d'analyse"""
        print("\n" + "=" * 70)
        print("WALLET STRATEGY ANALYSIS REPORT")
        print("=" * 70)
        print(f"Wallet: {self.wallet}")
        print("=" * 70)

        print(f"\n--- TRADING ACTIVITY ---")
        print(f"Total Trades: {metrics['total_trades']}")
        print(f"Unique Tokens: {metrics['unique_tokens']}")
        print(f"Buys: {metrics['buys']}")
        print(f"Sells: {metrics['sells']}")
        print(f"Completed Trades: {len(metrics['completed_trades'])}")

        print(f"\n--- POSITION SIZING ---")
        print(f"Total SOL Spent: {metrics['total_sol_spent']:.2f} SOL")
        print(f"Total SOL Received: {metrics['total_sol_received']:.2f} SOL")
        print(f"Net P&L: {metrics['total_sol_received'] - metrics['total_sol_spent']:+.2f} SOL")
        print(f"Average Buy Size: {metrics['avg_buy_size']:.3f} SOL")
        print(f"Average Sell Size: {metrics['avg_sell_size']:.3f} SOL")

        if metrics['completed_trades']:
            print(f"\n--- PERFORMANCE ---")
            print(f"Win Rate: {metrics['win_rate']:.1f}%")
            print(f"Average Profit: {metrics['avg_profit']:+.2f}%")
            print(f"Average Hold Time: {metrics['avg_hold_time']:.1f} minutes")

            if 'avg_entry_mcap' in metrics:
                print(f"\n--- ENTRY/EXIT STRATEGY ---")
                print(f"Average Entry Market Cap: ${metrics.get('avg_entry_mcap', 0):,.0f}")
                print(f"Average Exit Market Cap: ${metrics.get('avg_exit_mcap', 0):,.0f}")

            # Best and worst trades
            sorted_trades = sorted(metrics['completed_trades'], key=lambda x: x['profit_percent'], reverse=True)

            print(f"\n--- BEST TRADE ---")
            best = sorted_trades[0]
            print(f"Token: {best['token'][:16]}...")
            print(f"Profit: {best['profit_percent']:+.2f}%")
            print(f"Buy: {best['buy_sol']:.3f} SOL")
            print(f"Sell: {best['sell_sol']:.3f} SOL")
            print(f"Hold Time: {best['hold_time_minutes']:.1f} minutes")

            print(f"\n--- WORST TRADE ---")
            worst = sorted_trades[-1]
            print(f"Token: {worst['token'][:16]}...")
            print(f"Profit: {worst['profit_percent']:+.2f}%")
            print(f"Buy: {worst['buy_sol']:.3f} SOL")
            print(f"Sell: {worst['sell_sol']:.3f} SOL")
            print(f"Hold Time: {worst['hold_time_minutes']:.1f} minutes")

            # Recent trades
            print(f"\n--- RECENT 5 TRADES ---")
            for trade in sorted_trades[:5]:
                print(f"\nToken: {trade['token'][:16]}...")
                print(f"  Profit: {trade['profit_percent']:+.2f}%")
                print(f"  Hold: {trade['hold_time_minutes']:.1f} min")
                print(f"  Buy: {trade['buy_time'].strftime('%Y-%m-%d %H:%M')}")

        print("\n" + "=" * 70)

        # Détection de stratégie
        print("\n--- DETECTED STRATEGY ---")

        if metrics['avg_hold_time'] < 5:
            print("[STRATEGY] SCALPER - Very fast trades (<5min hold)")
        elif metrics['avg_hold_time'] < 30:
            print("[STRATEGY] DAY TRADER - Short-term trades (<30min hold)")
        else:
            print("[STRATEGY] SWING TRADER - Longer holds (>30min)")

        if metrics.get('avg_entry_mcap', 0) < 15000:
            print(f"[ENTRY] Early entry (avg ${metrics.get('avg_entry_mcap', 0):,.0f} mcap)")
            if 9000 <= metrics.get('avg_entry_mcap', 0) <= 13000:
                print("  -> OPTIMAL RANGE ($9k-$13k) - YOUR STRATEGY!")

        if metrics['win_rate'] > 60:
            print(f"[PERFORMANCE] High win rate ({metrics['win_rate']:.1f}%) - Selective strategy")
        elif metrics['win_rate'] < 40:
            print(f"[PERFORMANCE] Low win rate ({metrics['win_rate']:.1f}%) - Spray & pray strategy")

        if metrics['unique_tokens'] > metrics['completed_trades'] * 2:
            print("[BEHAVIOR] Enters many positions, completes few - High risk tolerance")

        print("=" * 70)

    def save_report(self, metrics):
        """Sauvegarde le rapport"""
        report_file = Path(__file__).parent / f"wallet_analysis_{self.wallet[:8]}.json"

        # Convert datetime objects to strings
        serializable_metrics = metrics.copy()
        serializable_metrics['completed_trades'] = []

        for trade in metrics['completed_trades']:
            t = trade.copy()
            t['buy_time'] = t['buy_time'].isoformat()
            t['sell_time'] = t['sell_time'].isoformat()
            serializable_metrics['completed_trades'].append(t)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_metrics, f, indent=2, ensure_ascii=False)

        print(f"\n[+] Report saved to: {report_file.name}")

    async def analyze(self):
        """Analyse complète"""
        success = await self.fetch_all_transactions(limit=1000)

        if not success:
            print("[!] Failed to fetch transactions")
            return

        self.analyze_trades()

        metrics = await self.calculate_trade_metrics()

        self.print_report(metrics)

        self.save_report(metrics)

        return metrics

    async def close(self):
        await self.client.aclose()


async def main():
    # Le wallet à analyser
    target_wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"

    print("\n" + "=" * 70)
    print("WALLET STRATEGY ANALYZER")
    print("Reverse-engineering trading strategies")
    print("=" * 70)

    analyzer = WalletStrategyAnalyzer(target_wallet)

    try:
        await analyzer.analyze()
    finally:
        await analyzer.close()


if __name__ == "__main__":
    asyncio.run(main())

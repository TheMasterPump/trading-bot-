"""
ANALYSE P&L PAR PÉRIODE
Calcule le vrai P&L d'un wallet sur 1 jour, 7 jours, 30 jours
"""
import asyncio
import httpx
import json
from datetime import datetime, timedelta
from collections import defaultdict

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

class WalletPnLAnalyzer:
    def __init__(self, wallet_address: str):
        self.wallet = wallet_address
        self.client = httpx.AsyncClient(timeout=60.0)
        self.transactions = []
        self.trades = []

    async def fetch_transactions(self, limit=200):
        """Récupère les transactions"""
        print(f"\n[*] Fetching {limit} transactions...")

        url = f"https://api.helius.xyz/v0/addresses/{self.wallet}/transactions"
        params = {
            "api-key": HELIUS_API_KEY,
            "limit": limit
        }

        response = await self.client.get(url, params=params)

        if response.status_code == 200:
            self.transactions = response.json()
            print(f"[+] Fetched {len(self.transactions)} transactions")
            return True
        else:
            print(f"[!] Error: {response.status_code}")
            return False

    def parse_trades(self):
        """Parse les trades"""
        for tx in self.transactions:
            if tx.get('type') != 'SWAP':
                continue

            timestamp = tx.get('timestamp')
            native_transfers = tx.get('nativeTransfers', [])
            token_transfers = tx.get('tokenTransfers', [])

            sol_change = 0
            token_info = None

            for transfer in native_transfers:
                if transfer.get('fromUserAccount') == self.wallet:
                    sol_change -= transfer.get('amount', 0) / 1e9
                elif transfer.get('toUserAccount') == self.wallet:
                    sol_change += transfer.get('amount', 0) / 1e9

            for transfer in token_transfers:
                if transfer.get('fromUserAccount') == self.wallet:
                    token_info = {'type': 'SELL', 'mint': transfer.get('mint')}
                elif transfer.get('toUserAccount') == self.wallet:
                    token_info = {'type': 'BUY', 'mint': transfer.get('mint')}

            if token_info:
                self.trades.append({
                    'timestamp': timestamp,
                    'datetime': datetime.fromtimestamp(timestamp),
                    'type': token_info['type'],
                    'token': token_info['mint'],
                    'sol_change': sol_change,
                    'signature': tx.get('signature')
                })

        print(f"[+] Parsed {len(self.trades)} trades")

    def calculate_pnl_by_period(self):
        """Calcule le P&L par période"""
        now = datetime.now()

        periods = {
            '1_day': now - timedelta(days=1),
            '7_days': now - timedelta(days=7),
            '30_days': now - timedelta(days=30),
            'all_time': datetime.fromtimestamp(0)
        }

        results = {}

        for period_name, start_date in periods.items():
            # Filtrer les trades de cette période
            period_trades = [t for t in self.trades if t['datetime'] >= start_date]

            if not period_trades:
                results[period_name] = {
                    'trades': 0,
                    'pnl_sol': 0,
                    'buys': 0,
                    'sells': 0
                }
                continue

            # Calculer P&L
            total_pnl = sum([t['sol_change'] for t in period_trades])
            buys = [t for t in period_trades if t['type'] == 'BUY']
            sells = [t for t in period_trades if t['type'] == 'SELL']

            sol_spent = abs(sum([t['sol_change'] for t in buys]))
            sol_received = sum([t['sol_change'] for t in sells])

            roi_percent = ((sol_received - sol_spent) / sol_spent * 100) if sol_spent > 0 else 0

            results[period_name] = {
                'trades': len(period_trades),
                'pnl_sol': total_pnl,
                'sol_spent': sol_spent,
                'sol_received': sol_received,
                'roi_percent': roi_percent,
                'buys': len(buys),
                'sells': len(sells),
                'start_date': start_date,
                'end_date': now
            }

        return results

    def print_pnl_report(self, results):
        """Affiche le rapport P&L"""
        print("\n" + "=" * 70)
        print("WALLET P&L ANALYSIS")
        print("=" * 70)
        print(f"Wallet: {self.wallet}")
        print("=" * 70)

        period_names = {
            '1_day': 'Last 24 Hours',
            '7_days': 'Last 7 Days',
            '30_days': 'Last 30 Days',
            'all_time': 'All Time'
        }

        for period_key in ['1_day', '7_days', '30_days', 'all_time']:
            data = results[period_key]

            print(f"\n--- {period_names[period_key].upper()} ---")
            print(f"Total Trades: {data['trades']}")
            print(f"Buys: {data['buys']}")
            print(f"Sells: {data['sells']}")

            if data['trades'] > 0:
                print(f"SOL Spent: {data['sol_spent']:.4f} SOL")
                print(f"SOL Received: {data['sol_received']:.4f} SOL")
                print(f"Net P&L: {data['pnl_sol']:+.4f} SOL")
                print(f"ROI: {data['roi_percent']:+.2f}%")

                # Estimation USD (SOL @ $200)
                sol_price = 200
                pnl_usd = data['pnl_sol'] * sol_price
                print(f"P&L (USD): ${pnl_usd:+,.2f}")
            else:
                print("No trades in this period")

        print("\n" + "=" * 70)

        # Analyse de tendance
        print("\n--- TREND ANALYSIS ---")

        if results['1_day']['trades'] > 0:
            daily_pnl = results['1_day']['pnl_sol']
            print(f"Daily P&L: {daily_pnl:+.4f} SOL (${daily_pnl * 200:+,.2f})")

            # Projection mensuelle
            monthly_projection = daily_pnl * 30
            print(f"Monthly Projection: {monthly_projection:+.4f} SOL (${monthly_projection * 200:+,.2f})")

        if results['all_time']['trades'] > 0:
            total_roi = results['all_time']['roi_percent']

            if total_roi > 0:
                print(f"\n[PROFITABLE] Overall ROI: +{total_roi:.2f}%")
            elif total_roi < -50:
                print(f"\n[HIGH LOSS] Overall ROI: {total_roi:.2f}%")
            else:
                print(f"\n[MODERATE LOSS] Overall ROI: {total_roi:.2f}%")

        print("=" * 70)

    async def analyze(self):
        """Analyse complète"""
        success = await self.fetch_transactions(limit=200)

        if not success:
            return

        self.parse_trades()

        results = self.calculate_pnl_by_period()

        self.print_pnl_report(results)

        return results

    async def close(self):
        await self.client.aclose()


async def main():
    target_wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"

    print("\n" + "=" * 70)
    print("WALLET P&L ANALYZER")
    print("Calculate real profits/losses over time")
    print("=" * 70)

    analyzer = WalletPnLAnalyzer(target_wallet)

    try:
        await analyzer.analyze()
    finally:
        await analyzer.close()


if __name__ == "__main__":
    asyncio.run(main())

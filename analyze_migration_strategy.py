"""
MIGRATION STRATEGY ANALYZER
Analyse la stratégie: Buy pre-migration, Sell post-migration
"""
import asyncio
import httpx
from datetime import datetime
from collections import defaultdict

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def get_all_swaps(wallet_address: str, limit=200):
    """Récupère TOUS les swaps (achats ET ventes)"""
    client = httpx.AsyncClient(timeout=60.0)

    print(f"\n[*] Fetching ALL swaps for wallet...")

    all_transactions = []
    before_signature = None

    for batch in range(5):  # Up to 500 transactions
        url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
        params = {
            "api-key": HELIUS_API_KEY,
            "limit": 100
        }

        if before_signature:
            params["before"] = before_signature

        try:
            response = await client.get(url, params=params)

            if response.status_code == 200:
                transactions = response.json()

                if not transactions:
                    break

                all_transactions.extend(transactions)
                before_signature = transactions[-1].get('signature')

                print(f"[+] Batch {batch + 1}: {len(transactions)} transactions (total: {len(all_transactions)})")

                if len(transactions) < 100:
                    break
            else:
                break

        except Exception as e:
            print(f"[!] Error: {e}")
            break

    await client.aclose()
    return all_transactions


def parse_all_swaps(transactions, wallet_address):
    """Parse TOUS les swaps en achats et ventes par token"""
    swaps_by_token = defaultdict(lambda: {'buys': [], 'sells': []})

    for tx in transactions:
        if tx.get('type') != 'SWAP':
            continue

        timestamp = tx.get('timestamp')
        signature = tx.get('signature')
        description = tx.get('description', '')

        # Analyser les transferts
        native_transfers = tx.get('nativeTransfers', [])
        token_transfers = tx.get('tokenTransfers', [])

        sol_change = 0
        token_info = None

        # Calculer le changement SOL
        for nt in native_transfers:
            if nt.get('fromUserAccount') == wallet_address:
                sol_change -= nt.get('amount', 0) / 1e9
            elif nt.get('toUserAccount') == wallet_address:
                sol_change += nt.get('amount', 0) / 1e9

        # Trouver le token
        for tt in token_transfers:
            if tt.get('fromUserAccount') == wallet_address:
                # VENTE
                token_info = {
                    'type': 'SELL',
                    'mint': tt.get('mint'),
                    'amount': tt.get('tokenAmount', 0)
                }
            elif tt.get('toUserAccount') == wallet_address:
                # ACHAT
                token_info = {
                    'type': 'BUY',
                    'mint': tt.get('mint'),
                    'amount': tt.get('tokenAmount', 0)
                }

        if not token_info:
            continue

        mint = token_info['mint']
        swap_data = {
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp),
            'sol_change': abs(sol_change),
            'token_amount': token_info['amount'],
            'signature': signature,
            'description': description
        }

        if token_info['type'] == 'BUY':
            swaps_by_token[mint]['buys'].append(swap_data)
        else:
            swaps_by_token[mint]['sells'].append(swap_data)

    return swaps_by_token


def match_buy_sell_pairs(swaps_by_token):
    """Matche les achats avec les ventes pour calculer P&L"""
    completed_trades = []

    for mint, swaps in swaps_by_token.items():
        buys = swaps['buys']
        sells = swaps['sells']

        if not buys:
            continue

        # Pour chaque achat, trouver une vente correspondante
        for buy in buys:
            # Trouver une vente après cet achat
            matching_sells = [s for s in sells if s['timestamp'] > buy['timestamp']]

            if matching_sells:
                # Prendre la première vente après cet achat
                sell = matching_sells[0]

                sol_invested = buy['sol_change']
                sol_received = sell['sol_change']

                pnl_sol = sol_received - sol_invested
                pnl_percent = ((sol_received - sol_invested) / sol_invested * 100) if sol_invested > 0 else 0

                hold_time_seconds = sell['timestamp'] - buy['timestamp']
                hold_time_minutes = hold_time_seconds / 60
                hold_time_hours = hold_time_minutes / 60

                completed_trades.append({
                    'mint': mint,
                    'buy_time': buy['datetime'],
                    'sell_time': sell['datetime'],
                    'sol_invested': sol_invested,
                    'sol_received': sol_received,
                    'pnl_sol': pnl_sol,
                    'pnl_percent': pnl_percent,
                    'hold_time_minutes': hold_time_minutes,
                    'hold_time_hours': hold_time_hours,
                    'buy_signature': buy['signature'],
                    'sell_signature': sell['signature']
                })

    return completed_trades


async def analyze_migration_strategy(wallet_address: str):
    """Analyse complète de la stratégie"""

    print("\n" + "=" * 70)
    print("MIGRATION STRATEGY ANALYZER")
    print("Buy pre-migration -> Sell post-migration")
    print("=" * 70)
    print(f"Wallet: {wallet_address}")
    print("=" * 70)

    # 1. Récupérer tous les swaps
    transactions = await get_all_swaps(wallet_address, limit=500)
    print(f"\n[+] Total transactions: {len(transactions)}")

    # 2. Parser tous les swaps
    print("\n[*] Parsing swaps...")
    swaps_by_token = parse_all_swaps(transactions, wallet_address)

    total_tokens = len(swaps_by_token)
    tokens_with_buys = sum(1 for s in swaps_by_token.values() if s['buys'])
    tokens_with_sells = sum(1 for s in swaps_by_token.values() if s['sells'])

    print(f"[+] Total unique tokens: {total_tokens}")
    print(f"[+] Tokens bought: {tokens_with_buys}")
    print(f"[+] Tokens sold: {tokens_with_sells}")

    # 3. Matcher achats/ventes
    print("\n[*] Matching buy/sell pairs...")
    completed_trades = match_buy_sell_pairs(swaps_by_token)
    print(f"[+] Completed trades: {len(completed_trades)}")

    if not completed_trades:
        print("\n[!] No completed trades found")
        print("[!] The wallet is still holding all tokens (no sells yet)")
        return

    # 4. Calculer les stats
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)

    total_invested = sum(t['sol_invested'] for t in completed_trades)
    total_received = sum(t['sol_received'] for t in completed_trades)
    net_pnl = total_received - total_invested
    roi = (net_pnl / total_invested * 100) if total_invested > 0 else 0

    sol_price = 200  # USD

    print(f"\nCompleted Trades: {len(completed_trades)}")
    print(f"Total Invested: {total_invested:.4f} SOL (${total_invested * sol_price:,.2f})")
    print(f"Total Received: {total_received:.4f} SOL (${total_received * sol_price:,.2f})")
    print(f"Net P&L: {net_pnl:+.4f} SOL (${net_pnl * sol_price:+,.2f})")
    print(f"ROI: {roi:+.2f}%")

    # Win rate
    wins = [t for t in completed_trades if t['pnl_sol'] > 0]
    losses = [t for t in completed_trades if t['pnl_sol'] <= 0]
    win_rate = (len(wins) / len(completed_trades) * 100) if completed_trades else 0

    print(f"\nWins: {len(wins)}")
    print(f"Losses: {len(losses)}")
    print(f"Win Rate: {win_rate:.1f}%")

    # Avg profit
    if wins:
        avg_win = sum(t['pnl_percent'] for t in wins) / len(wins)
        print(f"Average Win: +{avg_win:.2f}%")

    if losses:
        avg_loss = sum(t['pnl_percent'] for t in losses) / len(losses)
        print(f"Average Loss: {avg_loss:.2f}%")

    # Hold times
    avg_hold = sum(t['hold_time_hours'] for t in completed_trades) / len(completed_trades)
    print(f"\nAverage Hold Time: {avg_hold:.2f} hours")

    # Top performers
    print("\n" + "=" * 70)
    print("TOP 10 BEST TRADES")
    print("=" * 70)

    sorted_trades = sorted(completed_trades, key=lambda x: x['pnl_percent'], reverse=True)

    for i, trade in enumerate(sorted_trades[:10], 1):
        print(f"\n[{i}] Token: {trade['mint'][:16]}...")
        print(f"    Invested: {trade['sol_invested']:.4f} SOL")
        print(f"    Received: {trade['sol_received']:.4f} SOL")
        print(f"    P&L: {trade['pnl_sol']:+.4f} SOL ({trade['pnl_percent']:+.2f}%)")
        print(f"    Hold Time: {trade['hold_time_hours']:.2f} hours")
        print(f"    Buy: {trade['buy_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"    Sell: {trade['sell_time'].strftime('%Y-%m-%d %H:%M')}")

    print("\n" + "=" * 70)
    print("TOP 5 WORST TRADES")
    print("=" * 70)

    for i, trade in enumerate(sorted_trades[-5:], 1):
        print(f"\n[{i}] Token: {trade['mint'][:16]}...")
        print(f"    Invested: {trade['sol_invested']:.4f} SOL")
        print(f"    Received: {trade['sol_received']:.4f} SOL")
        print(f"    P&L: {trade['pnl_sol']:+.4f} SOL ({trade['pnl_percent']:+.2f}%)")
        print(f"    Hold Time: {trade['hold_time_hours']:.2f} hours")

    print("\n" + "=" * 70)

    # Projection
    if net_pnl > 0:
        print(f"\n[PROFITABLE STRATEGY]")
        print(f"If this strategy continues:")
        print(f"  - Daily P&L: ${(net_pnl / 7) * sol_price:,.2f}")
        print(f"  - Weekly P&L: ${net_pnl * sol_price:,.2f}")
        print(f"  - Monthly projection: ${(net_pnl * 4) * sol_price:,.2f}")

    print("=" * 70)


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"
    await analyze_migration_strategy(wallet)


if __name__ == "__main__":
    asyncio.run(main())

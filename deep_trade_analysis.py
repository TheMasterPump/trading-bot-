"""
DEEP TRADE ANALYSIS
Analyser chaque trade individuellement pour trouver les vraies performances
"""
import asyncio
import httpx
from datetime import datetime
from collections import defaultdict

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def get_all_transactions(wallet_address: str):
    """Recupere toutes les transactions"""
    client = httpx.AsyncClient(timeout=60.0)

    print(f"\n[*] Fetching ALL transactions...")

    all_transactions = []
    before_signature = None

    for batch in range(20):
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

                print(f"[+] Batch {batch + 1}: {len(transactions)} transactions")

                if len(transactions) < 100:
                    break
            else:
                break

        except Exception as e:
            print(f"[!] Error: {e}")
            break

    await client.aclose()
    return all_transactions


def analyze_each_swap(wallet_address: str, transactions):
    """Analyser CHAQUE swap individuellement"""

    print("\n" + "=" * 70)
    print("ANALYZING EACH SWAP INDIVIDUALLY")
    print("=" * 70)

    swaps_detailed = []

    for tx in transactions:
        if tx.get('type') != 'SWAP':
            continue

        timestamp = tx.get('timestamp')
        signature = tx.get('signature')
        description = tx.get('description', '')

        native_transfers = tx.get('nativeTransfers', [])
        token_transfers = tx.get('tokenTransfers', [])

        # Calculer SOL net movement pour CE swap
        sol_change = 0

        for nt in native_transfers:
            from_addr = nt.get('fromUserAccount')
            to_addr = nt.get('toUserAccount')
            amount = nt.get('amount', 0) / 1e9

            if from_addr == wallet_address:
                sol_change -= amount  # SOL OUT
            elif to_addr == wallet_address:
                sol_change += amount  # SOL IN

        # Identifier le token
        token_mint = None
        token_amount = 0
        is_buy = False
        is_sell = False

        for tt in token_transfers:
            if tt.get('toUserAccount') == wallet_address:
                # BUY
                is_buy = True
                token_mint = tt.get('mint')
                token_amount = tt.get('tokenAmount', 0)
            elif tt.get('fromUserAccount') == wallet_address:
                # SELL
                is_sell = True
                token_mint = tt.get('mint')
                token_amount = tt.get('tokenAmount', 0)

        if not token_mint:
            continue

        swap_data = {
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp),
            'signature': signature,
            'token_mint': token_mint,
            'token_amount': token_amount,
            'sol_change': sol_change,
            'is_buy': is_buy,
            'is_sell': is_sell,
            'description': description
        }

        swaps_detailed.append(swap_data)

    return swaps_detailed


def match_trades(swaps):
    """Matcher les achats et ventes pour calculer P&L"""

    print(f"\n[*] Matching {len(swaps)} swaps into buy/sell pairs...")

    # Grouper par token
    by_token = defaultdict(lambda: {'buys': [], 'sells': []})

    for swap in swaps:
        mint = swap['token_mint']
        if swap['is_buy']:
            by_token[mint]['buys'].append(swap)
        elif swap['is_sell']:
            by_token[mint]['sells'].append(swap)

    # Matcher et calculer P&L
    completed_trades = []

    for mint, data in by_token.items():
        buys = sorted(data['buys'], key=lambda x: x['timestamp'])
        sells = sorted(data['sells'], key=lambda x: x['timestamp'])

        # Simple matching: premier achat avec premiere vente
        for buy in buys:
            matching_sells = [s for s in sells if s['timestamp'] > buy['timestamp']]

            if matching_sells:
                sell = matching_sells[0]

                # Calculer P&L
                sol_spent = abs(buy['sol_change'])
                sol_received = abs(sell['sol_change'])

                # IMPORTANT: Si sol_change est negatif pour une vente, c'est qu'on a PAYE
                # Si positif, c'est qu'on a RECU
                if sell['sol_change'] < 0:
                    # On a paye des frais mais pas recu de SOL
                    sol_received = 0
                else:
                    sol_received = sell['sol_change']

                pnl_sol = sol_received - sol_spent
                pnl_usd = pnl_sol * 200

                if sol_spent > 0:
                    pnl_percent = (pnl_sol / sol_spent * 100)
                else:
                    pnl_percent = 0

                hold_time = sell['timestamp'] - buy['timestamp']

                completed_trades.append({
                    'mint': mint,
                    'buy_time': buy['datetime'],
                    'sell_time': sell['datetime'],
                    'sol_spent': sol_spent,
                    'sol_received': sol_received,
                    'pnl_sol': pnl_sol,
                    'pnl_usd': pnl_usd,
                    'pnl_percent': pnl_percent,
                    'hold_time_hours': hold_time / 3600,
                    'buy_sig': buy['signature'],
                    'sell_sig': sell['signature']
                })

    return completed_trades


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"

    print("\n" + "=" * 70)
    print("DEEP TRADE ANALYSIS")
    print("=" * 70)
    print(f"Wallet: {wallet}")
    print("=" * 70)

    # 1. Get all transactions
    transactions = await get_all_transactions(wallet)
    print(f"\n[+] Total transactions: {len(transactions)}")

    # 2. Analyze each swap
    swaps = analyze_each_swap(wallet, transactions)
    print(f"\n[+] Total swaps found: {len(swaps)}")

    buys = [s for s in swaps if s['is_buy']]
    sells = [s for s in swaps if s['is_sell']]

    print(f"[+] Buys: {len(buys)}")
    print(f"[+] Sells: {len(sells)}")

    # 3. Match trades
    completed_trades = match_trades(swaps)

    print(f"\n[+] Completed trades: {len(completed_trades)}")

    if not completed_trades:
        print("\n[!] No completed trades found")

        # Montrer quelques swaps en detail
        print("\n[*] Showing first 5 swaps for debugging:")
        for i, swap in enumerate(swaps[:5], 1):
            print(f"\n--- Swap #{i} ---")
            print(f"Type: {'BUY' if swap['is_buy'] else 'SELL'}")
            print(f"Token: {swap['token_mint'][:16]}...")
            print(f"Amount: {swap['token_amount']:,.0f}")
            print(f"SOL change: {swap['sol_change']:+.4f} SOL")
            print(f"Date: {swap['datetime'].strftime('%Y-%m-%d %H:%M:%S')}")

        return

    # 4. Show results
    print("\n" + "=" * 70)
    print("COMPLETED TRADES")
    print("=" * 70)

    total_invested = sum(t['sol_spent'] for t in completed_trades)
    total_received = sum(t['sol_received'] for t in completed_trades)
    total_pnl = sum(t['pnl_sol'] for t in completed_trades)

    print(f"\nTotal Invested: {total_invested:.4f} SOL (${total_invested * 200:,.2f})")
    print(f"Total Received: {total_received:.4f} SOL (${total_received * 200:,.2f})")
    print(f"Total P&L: {total_pnl:+.4f} SOL (${total_pnl * 200:+,.2f})")

    wins = [t for t in completed_trades if t['pnl_sol'] > 0]
    losses = [t for t in completed_trades if t['pnl_sol'] <= 0]

    print(f"\nWins: {len(wins)}")
    print(f"Losses: {len(losses)}")

    if completed_trades:
        win_rate = (len(wins) / len(completed_trades) * 100)
        print(f"Win Rate: {win_rate:.1f}%")

    # Top trades
    print("\n" + "=" * 70)
    print("TOP 10 TRADES")
    print("=" * 70)

    sorted_trades = sorted(completed_trades, key=lambda x: x['pnl_usd'], reverse=True)

    for i, trade in enumerate(sorted_trades[:10], 1):
        print(f"\n[{i}] {trade['mint'][:16]}...")
        print(f"    Spent: {trade['sol_spent']:.4f} SOL (${trade['sol_spent'] * 200:.2f})")
        print(f"    Received: {trade['sol_received']:.4f} SOL (${trade['sol_received'] * 200:.2f})")
        print(f"    P&L: {trade['pnl_sol']:+.4f} SOL (${trade['pnl_usd']:+.2f}) [{trade['pnl_percent']:+.1f}%]")
        print(f"    Buy: {trade['buy_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"    Sell: {trade['sell_time'].strftime('%Y-%m-%d %H:%M')}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

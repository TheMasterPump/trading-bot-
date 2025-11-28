"""
COMPLETE P&L CALCULATOR
Calculer le P&L complet avec matching parfait buy/sell
"""
import asyncio
import httpx
from datetime import datetime
from collections import defaultdict

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def get_all_transactions_deep(wallet_address: str):
    """Recupere TOUTES les transactions sans limite"""
    client = httpx.AsyncClient(timeout=60.0)

    print(f"\n[*] Fetching ALL transactions (deep scan)...")

    all_transactions = []
    before_signature = None

    for batch in range(100):  # Up to 10,000 transactions
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

                if batch % 5 == 0:
                    print(f"[+] Fetched {len(all_transactions)} transactions so far...")

                if len(transactions) < 100:
                    break
            else:
                break

        except Exception as e:
            print(f"[!] Error: {e}")
            break

    await client.aclose()
    return all_transactions


def parse_swap_with_balance_change(wallet_address: str, tx):
    """Parser un swap en utilisant nativeBalanceChange"""

    timestamp = tx.get('timestamp')
    signature = tx.get('signature')

    # Get SOL balance change
    sol_in = 0
    sol_out = 0

    account_data = tx.get('accountData', [])
    for acc in account_data:
        if acc.get('account') == wallet_address:
            balance_change = acc.get('nativeBalanceChange', 0) / 1e9

            if balance_change > 0:
                sol_in = balance_change
            elif balance_change < 0:
                sol_out = abs(balance_change)

    # Get token info
    token_transfers = tx.get('tokenTransfers', [])
    token_mint = None
    token_amount = 0
    is_buy = False
    is_sell = False

    for tt in token_transfers:
        if tt.get('toUserAccount') == wallet_address:
            is_buy = True
            token_mint = tt.get('mint')
            token_amount = tt.get('tokenAmount', 0)
        elif tt.get('fromUserAccount') == wallet_address:
            is_sell = True
            token_mint = tt.get('mint')
            token_amount = tt.get('tokenAmount', 0)

    if not token_mint:
        return None

    return {
        'timestamp': timestamp,
        'datetime': datetime.fromtimestamp(timestamp),
        'signature': signature,
        'token_mint': token_mint,
        'token_amount': token_amount,
        'is_buy': is_buy,
        'is_sell': is_sell,
        'sol_in': sol_in,
        'sol_out': sol_out
    }


def calculate_complete_pnl(wallet_address: str, transactions):
    """Calculer P&L complet avec matching"""

    print(f"\n[*] Parsing all swaps...")

    swaps = []
    for tx in transactions:
        if tx.get('type') == 'SWAP':
            parsed = parse_swap_with_balance_change(wallet_address, tx)
            if parsed:
                swaps.append(parsed)

    print(f"[+] Parsed {len(swaps)} swaps")

    # Group by token
    by_token = defaultdict(lambda: {'buys': [], 'sells': []})

    for swap in swaps:
        mint = swap['token_mint']
        if swap['is_buy']:
            by_token[mint]['buys'].append(swap)
        elif swap['is_sell']:
            by_token[mint]['sells'].append(swap)

    print(f"[+] Found {len(by_token)} unique tokens")

    # Match and calculate P&L for each token
    print(f"\n[*] Matching buy/sell pairs for each token...")

    token_results = []

    for mint, data in by_token.items():
        buys = sorted(data['buys'], key=lambda x: x['timestamp'])
        sells = sorted(data['sells'], key=lambda x: x['timestamp'])

        total_invested = sum(b['sol_out'] for b in buys)
        total_received = sum(s['sol_in'] for s in sells)

        pnl_sol = total_received - total_invested
        pnl_usd = pnl_sol * 200

        if total_invested > 0:
            roi_percent = (pnl_sol / total_invested * 100)
        else:
            roi_percent = 0

        token_results.append({
            'mint': mint,
            'buys': len(buys),
            'sells': len(sells),
            'invested': total_invested,
            'received': total_received,
            'pnl_sol': pnl_sol,
            'pnl_usd': pnl_usd,
            'roi_percent': roi_percent,
            'first_buy': buys[0]['datetime'] if buys else None,
            'last_sell': sells[-1]['datetime'] if sells else None
        })

    return token_results


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"

    print("=" * 70)
    print("COMPLETE P&L CALCULATOR")
    print("=" * 70)
    print(f"Wallet: {wallet}")
    print("=" * 70)

    # Get ALL transactions
    transactions = await get_all_transactions_deep(wallet)
    print(f"\n[+] Total transactions: {len(transactions)}")

    # Calculate P&L
    results = calculate_complete_pnl(wallet, transactions)

    # Sort by P&L
    results_sorted = sorted(results, key=lambda x: x['pnl_usd'], reverse=True)

    # Summary
    print("\n" + "=" * 70)
    print("COMPLETE P&L REPORT")
    print("=" * 70)

    total_invested = sum(r['invested'] for r in results)
    total_received = sum(r['received'] for r in results)
    total_pnl = sum(r['pnl_sol'] for r in results)

    print(f"\nTotal Tokens Traded: {len(results)}")
    print(f"Total Invested: {total_invested:.4f} SOL (${total_invested * 200:,.2f})")
    print(f"Total Received: {total_received:.4f} SOL (${total_received * 200:,.2f})")
    print(f"Total P&L: {total_pnl:+.4f} SOL (${total_pnl * 200:+,.2f})")

    if total_invested > 0:
        total_roi = (total_pnl / total_invested * 100)
        print(f"Total ROI: {total_roi:+.2f}%")

    winners = [r for r in results if r['pnl_usd'] > 0]
    losers = [r for r in results if r['pnl_usd'] <= 0]

    print(f"\nWinning trades: {len(winners)}")
    print(f"Losing trades: {len(losers)}")

    if results:
        win_rate = (len(winners) / len(results) * 100)
        print(f"Win rate: {win_rate:.1f}%")

    # Top 20 winners
    print("\n" + "=" * 70)
    print("TOP 20 BEST TRADES")
    print("=" * 70)

    for i, result in enumerate(results_sorted[:20], 1):
        print(f"\n[{i}] Token: {result['mint'][:16]}...")
        print(f"    Buys: {result['buys']} | Sells: {result['sells']}")
        print(f"    Invested: {result['invested']:.4f} SOL (${result['invested'] * 200:.2f})")
        print(f"    Received: {result['received']:.4f} SOL (${result['received'] * 200:.2f})")
        print(f"    P&L: {result['pnl_sol']:+.4f} SOL (${result['pnl_usd']:+.2f}) [{result['roi_percent']:+.1f}%]")

        if result['first_buy']:
            print(f"    First buy: {result['first_buy'].strftime('%Y-%m-%d %H:%M')}")
        if result['last_sell']:
            print(f"    Last sell: {result['last_sell'].strftime('%Y-%m-%d %H:%M')}")

    # Look for LIVEBEAR specifically
    print("\n" + "=" * 70)
    print("SEARCHING FOR LIVEBEAR TOKEN")
    print("=" * 70)

    livebear_mint = "8dwC2K6jeNFCE1ZBWcLqTbqGkvSghMkb1m5dpXYLpump"

    livebear_found = False
    for result in results:
        if result['mint'] == livebear_mint:
            livebear_found = True
            print(f"\n[FOUND] LIVEBEAR in trading history!")
            print(f"Invested: {result['invested']:.4f} SOL (${result['invested'] * 200:.2f})")
            print(f"Received: {result['received']:.4f} SOL (${result['received'] * 200:.2f})")
            print(f"P&L: ${result['pnl_usd']:+.2f}")
            break

    if not livebear_found:
        print(f"\n[!] LIVEBEAR token NOT found in trading history")
        print(f"[!] Token mint: {livebear_mint}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

"""
ANALYZE RAW TRANSACTIONS
Analyser les transactions brutes pour capturer TOUS les mouvements SOL
"""
import asyncio
import httpx
from datetime import datetime

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def get_raw_transactions(wallet_address: str):
    """Recupere les transactions avec parsing enriched"""
    client = httpx.AsyncClient(timeout=60.0)

    print(f"\n[*] Fetching enriched transactions...")

    all_transactions = []
    before_signature = None

    for batch in range(10):
        # Use enhanced transactions endpoint
        url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
        params = {
            "api-key": HELIUS_API_KEY,
            "limit": 100,
            "type": "SWAP"  # Only swaps
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

                print(f"[+] Batch {batch + 1}: {len(transactions)} swaps")

                if len(transactions) < 100:
                    break
            else:
                break

        except Exception as e:
            print(f"[!] Error: {e}")
            break

    await client.aclose()
    return all_transactions


def deep_analyze_swap(wallet_address: str, tx):
    """Analyser profondement un swap pour trouver TOUS les mouvements SOL"""

    signature = tx.get('signature')
    timestamp = tx.get('timestamp')
    tx_date = datetime.fromtimestamp(timestamp)

    # Get ALL accounts involved
    account_data = tx.get('accountData', [])
    native_transfers = tx.get('nativeTransfers', [])
    token_transfers = tx.get('tokenTransfers', [])

    # Calculate total SOL in/out
    total_sol_in = 0
    total_sol_out = 0

    # Method 1: From nativeTransfers
    for nt in native_transfers:
        from_addr = nt.get('fromUserAccount')
        to_addr = nt.get('toUserAccount')
        amount = nt.get('amount', 0) / 1e9

        if to_addr == wallet_address:
            total_sol_in += amount
        elif from_addr == wallet_address:
            total_sol_out += amount

    # Method 2: From account balances (pre/post)
    # This might capture changes that nativeTransfers misses
    for account in account_data:
        if account.get('account') == wallet_address:
            native_balance_change = account.get('nativeBalanceChange', 0) / 1e9

            if native_balance_change > 0:
                total_sol_in = max(total_sol_in, native_balance_change)
            elif native_balance_change < 0:
                total_sol_out = max(total_sol_out, abs(native_balance_change))

    # Identify token
    token_mint = None
    is_buy = False
    is_sell = False

    for tt in token_transfers:
        if tt.get('toUserAccount') == wallet_address:
            is_buy = True
            token_mint = tt.get('mint')
        elif tt.get('fromUserAccount') == wallet_address:
            is_sell = True
            token_mint = tt.get('mint')

    return {
        'signature': signature,
        'timestamp': timestamp,
        'datetime': tx_date,
        'token_mint': token_mint,
        'is_buy': is_buy,
        'is_sell': is_sell,
        'sol_in': total_sol_in,
        'sol_out': total_sol_out,
        'sol_net': total_sol_in - total_sol_out,
        'raw_tx': tx
    }


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"

    print("\n" + "=" * 70)
    print("RAW TRANSACTION ANALYZER")
    print("=" * 70)
    print(f"Wallet: {wallet}")
    print("=" * 70)

    # Get all transactions
    transactions = await get_raw_transactions(wallet)
    print(f"\n[+] Total swaps: {len(transactions)}")

    # Analyze each
    print("\n[*] Deep analyzing each swap...")

    analyzed = []
    total_sol_in = 0
    total_sol_out = 0

    for tx in transactions:
        result = deep_analyze_swap(wallet, tx)
        analyzed.append(result)

        total_sol_in += result['sol_in']
        total_sol_out += result['sol_out']

    # Show results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    buys = [a for a in analyzed if a['is_buy']]
    sells = [a for a in analyzed if a['is_sell']]

    print(f"\nBuys: {len(buys)}")
    print(f"Sells: {len(sells)}")

    print(f"\nTotal SOL IN: {total_sol_in:.4f} SOL (${total_sol_in * 200:,.2f})")
    print(f"Total SOL OUT: {total_sol_out:.4f} SOL (${total_sol_out * 200:,.2f})")
    print(f"Net P&L: {total_sol_in - total_sol_out:+.4f} SOL (${(total_sol_in - total_sol_out) * 200:+,.2f})")

    # Show some sells with SOL received
    print("\n" + "=" * 70)
    print("SELLS THAT RECEIVED SOL (if any)")
    print("=" * 70)

    sells_with_sol = [s for s in sells if s['sol_in'] > 0]

    if sells_with_sol:
        print(f"\n[+] Found {len(sells_with_sol)} sells that received SOL!")

        for i, sell in enumerate(sells_with_sol[:10], 1):
            print(f"\n[{i}] Token: {sell['token_mint'][:16] if sell['token_mint'] else 'Unknown'}...")
            print(f"    SOL received: {sell['sol_in']:.4f} SOL (${sell['sol_in'] * 200:.2f})")
            print(f"    Date: {sell['datetime'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    Signature: {sell['signature'][:32]}...")
    else:
        print("\n[!] NO sells received any SOL")
        print("[!] This suggests all tokens sold were worthless at time of sale")

    # Show buys
    print("\n" + "=" * 70)
    print("SAMPLE BUYS")
    print("=" * 70)

    for i, buy in enumerate(buys[:5], 1):
        print(f"\n[{i}] Token: {buy['token_mint'][:16] if buy['token_mint'] else 'Unknown'}...")
        print(f"    SOL spent: {buy['sol_out']:.4f} SOL")
        print(f"    Date: {buy['datetime'].strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

"""
FIND PAIR TRADES
Trouver les trades specifiques pour une paire donnee
"""
import asyncio
import httpx
from datetime import datetime

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def find_trades_for_pair(wallet_address: str, pair_address: str):
    """Trouver tous les trades pour une paire specifique"""
    client = httpx.AsyncClient(timeout=60.0)

    print(f"\n[*] Fetching all swaps...")

    url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
    params = {
        "api-key": HELIUS_API_KEY,
        "limit": 100,
        "type": "SWAP"
    }

    try:
        response = await client.get(url, params=params)

        if response.status_code == 200:
            transactions = response.json()

            print(f"[+] Fetched {len(transactions)} swaps")
            print(f"\n[*] Searching for transactions involving pair: {pair_address[:16]}...")

            # Find transactions involving this pair
            pair_transactions = []

            for tx in transactions:
                # Check if this pair is in the accounts
                account_data = tx.get('accountData', [])
                accounts = [acc.get('account') for acc in account_data]

                if pair_address in accounts:
                    pair_transactions.append(tx)

                # Also check in nativeTransfers
                native_transfers = tx.get('nativeTransfers', [])
                for nt in native_transfers:
                    if nt.get('fromUserAccount') == pair_address or nt.get('toUserAccount') == pair_address:
                        if tx not in pair_transactions:
                            pair_transactions.append(tx)
                        break

                # Check token transfers
                token_transfers = tx.get('tokenTransfers', [])
                for tt in token_transfers:
                    if tt.get('fromUserAccount') == pair_address or tt.get('toUserAccount') == pair_address:
                        if tx not in pair_transactions:
                            pair_transactions.append(tx)
                        break

            print(f"\n[+] Found {len(pair_transactions)} transactions with this pair!")

            if not pair_transactions:
                print(f"\n[!] No transactions found with pair {pair_address}")
                await client.aclose()
                return

            # Analyze each transaction
            print("\n" + "=" * 70)
            print("TRADES ON THIS PAIR")
            print("=" * 70)

            total_sol_spent = 0
            total_sol_received = 0

            for i, tx in enumerate(pair_transactions, 1):
                timestamp = tx.get('timestamp')
                signature = tx.get('signature')
                tx_date = datetime.fromtimestamp(timestamp)

                # Calculate SOL change
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

                # Determine if buy or sell
                token_transfers = tx.get('tokenTransfers', [])
                is_buy = any(tt.get('toUserAccount') == wallet_address for tt in token_transfers)
                is_sell = any(tt.get('fromUserAccount') == wallet_address for tt in token_transfers)

                # Get token info
                token_mint = None
                token_amount = 0
                for tt in token_transfers:
                    if tt.get('toUserAccount') == wallet_address or tt.get('fromUserAccount') == wallet_address:
                        token_mint = tt.get('mint')
                        token_amount = tt.get('tokenAmount', 0)
                        break

                trade_type = "BUY" if is_buy else "SELL" if is_sell else "UNKNOWN"

                print(f"\n[{i}] {trade_type} - {tx_date.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    Token: {token_mint[:16] if token_mint else 'Unknown'}...")
                print(f"    Amount: {token_amount:,.0f} tokens")

                if is_buy:
                    print(f"    SOL spent: {sol_out:.4f} SOL (${sol_out * 200:.2f})")
                    total_sol_spent += sol_out
                elif is_sell:
                    print(f"    SOL received: {sol_in:.4f} SOL (${sol_in * 200:.2f})")
                    total_sol_received += sol_in

                print(f"    Signature: {signature[:32]}...")

            # Summary
            print("\n" + "=" * 70)
            print("SUMMARY FOR THIS PAIR")
            print("=" * 70)

            buys = [tx for tx in pair_transactions if any(tt.get('toUserAccount') == wallet_address for tt in tx.get('tokenTransfers', []))]
            sells = [tx for tx in pair_transactions if any(tt.get('fromUserAccount') == wallet_address for tt in tx.get('tokenTransfers', []))]

            print(f"\nTotal trades: {len(pair_transactions)}")
            print(f"Buys: {len(buys)}")
            print(f"Sells: {len(sells)}")

            print(f"\nTotal SOL spent: {total_sol_spent:.4f} SOL (${total_sol_spent * 200:.2f})")
            print(f"Total SOL received: {total_sol_received:.4f} SOL (${total_sol_received * 200:.2f})")

            pnl_sol = total_sol_received - total_sol_spent
            pnl_usd = pnl_sol * 200

            print(f"\nP&L: {pnl_sol:+.4f} SOL (${pnl_usd:+,.2f})")

            if pnl_usd > 0:
                print(f"\n[PROFIT] +${pnl_usd:,.2f}")
            else:
                print(f"\n[LOSS] ${abs(pnl_usd):,.2f}")

        else:
            print(f"[!] Error: {response.status_code}")

    except Exception as e:
        print(f"[!] Error: {e}")

    await client.aclose()


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"
    pair = "6cc7nBAkjx936YmwSuwBrSPPKYwbA7Ht9xamfyQBqEGY"

    print("=" * 70)
    print("PAIR-SPECIFIC TRADE FINDER")
    print("=" * 70)
    print(f"Wallet: {wallet}")
    print(f"Pair: {pair}")
    print("=" * 70)

    await find_trades_for_pair(wallet, pair)


if __name__ == "__main__":
    asyncio.run(main())

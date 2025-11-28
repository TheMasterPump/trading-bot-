"""
ANALYZE SPECIFIC TOKEN
Regarder un token specifique dans les transactions du wallet
"""
import asyncio
import httpx
from datetime import datetime

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def analyze_specific_token(wallet_address: str, token_mint: str):
    """Analyse un token specifique"""
    client = httpx.AsyncClient(timeout=60.0)

    print("\n" + "=" * 70)
    print("SPECIFIC TOKEN ANALYZER")
    print("=" * 70)
    print(f"Wallet: {wallet_address}")
    print(f"Token: {token_mint}")
    print("=" * 70)

    # Get all transactions
    print("\n[*] Fetching all transactions...")

    all_transactions = []
    before_signature = None

    for batch in range(50):  # Fetch up to 5000 transactions
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

    print(f"[+] Total transactions: {len(all_transactions)}")

    # Filter transactions with this token
    print(f"\n[*] Filtering transactions for token {token_mint[:16]}...")

    token_transactions = []

    for tx in all_transactions:
        token_transfers = tx.get('tokenTransfers', [])

        for tt in token_transfers:
            if tt.get('mint') == token_mint:
                token_transactions.append(tx)
                break

    print(f"[+] Found {len(token_transactions)} transactions with this token")

    if not token_transactions:
        print("\n[!] No transactions found for this token")
        await client.aclose()
        return

    # Analyze each transaction
    print("\n" + "=" * 70)
    print("TRANSACTIONS DETAILS")
    print("=" * 70)

    total_bought = 0
    total_sold = 0
    sol_spent = 0
    sol_received = 0

    for i, tx in enumerate(token_transactions, 1):
        tx_type = tx.get('type')
        timestamp = tx.get('timestamp')
        signature = tx.get('signature')
        tx_date = datetime.fromtimestamp(timestamp)

        print(f"\n--- Transaction #{i} ---")
        print(f"Type: {tx_type}")
        print(f"Date: {tx_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Signature: {signature[:32]}...")

        # Token transfers
        token_transfers = tx.get('tokenTransfers', [])
        native_transfers = tx.get('nativeTransfers', [])

        for tt in token_transfers:
            if tt.get('mint') == token_mint:
                from_addr = tt.get('fromUserAccount', '')
                to_addr = tt.get('toUserAccount', '')
                amount = tt.get('tokenAmount', 0)

                if to_addr == wallet_address:
                    # ACHAT
                    print(f"[BUY] +{amount:,.0f} tokens")
                    total_bought += amount
                elif from_addr == wallet_address:
                    # VENTE
                    print(f"[SELL] -{amount:,.0f} tokens")
                    total_sold += amount

        # SOL movements
        print("\nSOL Movements:")
        for nt in native_transfers:
            from_addr = nt.get('fromUserAccount', '')
            to_addr = nt.get('toUserAccount', '')
            amount = nt.get('amount', 0) / 1e9

            from_label = "WALLET" if from_addr == wallet_address else from_addr[:16]
            to_label = "WALLET" if to_addr == wallet_address else to_addr[:16]

            if from_addr == wallet_address:
                print(f"  [OUT] {amount:.4f} SOL: {from_label} -> {to_label}")
                sol_spent += amount
            elif to_addr == wallet_address:
                print(f"  [IN] {amount:.4f} SOL: {from_label} -> {to_label}")
                sol_received += amount

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Bought: {total_bought:,.0f} tokens")
    print(f"Total Sold: {total_sold:,.0f} tokens")
    print(f"Net Tokens: {total_bought - total_sold:,.0f} tokens")
    print(f"\nSOL Spent: {sol_spent:.4f} SOL (${sol_spent * 200:,.2f})")
    print(f"SOL Received: {sol_received:.4f} SOL (${sol_received * 200:,.2f})")
    print(f"Net P&L: {sol_received - sol_spent:+.4f} SOL (${(sol_received - sol_spent) * 200:+,.2f})")

    if sol_received - sol_spent > 0:
        print(f"\n[PROFIT] This token made +${(sol_received - sol_spent) * 200:,.2f}")
    else:
        print(f"\n[LOSS] This token lost ${abs(sol_received - sol_spent) * 200:,.2f}")

    # Get current price
    print("\n[*] Getting current token price from DexScreener...")
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
        response = await client.get(url)

        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])

            if pairs:
                pair = pairs[0]
                price_usd = float(pair.get('priceUsd', 0))
                mcap = float(pair.get('marketCap', 0))
                liquidity = float(pair.get('liquidity', {}).get('usd', 0))

                print(f"\n[+] Current Price: ${price_usd:.8f}")
                print(f"[+] Market Cap: ${mcap:,.0f}")
                print(f"[+] Liquidity: ${liquidity:,.0f}")

                # Calculate current value of held tokens
                net_tokens = total_bought - total_sold
                if net_tokens > 0:
                    current_value = net_tokens * price_usd
                    print(f"\n[+] Tokens still held: {net_tokens:,.0f}")
                    print(f"[+] Current value: ${current_value:,.2f}")
            else:
                print("[!] No price data available")
        else:
            print("[!] Could not fetch price data")

    except Exception as e:
        print(f"[!] Error fetching price: {e}")

    print("\n" + "=" * 70)

    await client.aclose()


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"
    token = "8dwC2K6jeNFCE1ZBWcLqTbqGkvSghMkb1m5dpXYLpump"

    await analyze_specific_token(wallet, token)


if __name__ == "__main__":
    asyncio.run(main())

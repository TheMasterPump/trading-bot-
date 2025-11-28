"""
SEARCH LIVEBEAR IN ALL TRANSACTIONS
Chercher LIVEBEAR dans TOUS les types de transactions
"""
import asyncio
import httpx
from datetime import datetime

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"
LIVEBEAR_MINT = "8dwC2K6jeNFCE1ZBWcLqTbqGkvSghMkb1m5dpXYLpump"

async def search_token_in_all_tx(wallet_address: str, token_mint: str):
    """Chercher un token dans TOUTES les transactions"""
    client = httpx.AsyncClient(timeout=60.0)

    print(f"\n[*] Searching for token: {token_mint[:16]}...")
    print(f"    In wallet: {wallet_address[:16]}...")
    print(f"\n[*] Fetching ALL transaction types...")

    all_transactions = []
    before_signature = None

    # Fetch without type filter to get ALL transactions
    for batch in range(200):  # Up to 20,000 transactions!
        url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
        params = {
            "api-key": HELIUS_API_KEY,
            "limit": 100
            # NO type filter - get everything!
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

                if len(transactions) < 100:
                    break

                # Show progress every 10 batches
                if (batch + 1) % 10 == 0:
                    print(f"[+] Progress: {len(all_transactions)} transactions so far...")
            else:
                break

        except Exception as e:
            print(f"[!] Error: {e}")
            break

    print(f"\n[+] Fetched {len(all_transactions)} total transactions")

    # Count by type
    types = {}
    for tx in all_transactions:
        tx_type = tx.get('type', 'UNKNOWN')
        types[tx_type] = types.get(tx_type, 0) + 1

    print(f"\n[TRANSACTION TYPES]")
    for tx_type, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {tx_type}: {count}")

    # Search for LIVEBEAR in ALL transactions
    print(f"\n[*] Searching for LIVEBEAR token in all transactions...")

    found_transactions = []

    for tx in all_transactions:
        # Check in tokenTransfers
        token_transfers = tx.get('tokenTransfers', [])

        for tt in token_transfers:
            if tt.get('mint') == token_mint:
                found_transactions.append({
                    'tx': tx,
                    'transfer': tt
                })
                break

        # Also check in accountData
        account_data = tx.get('accountData', [])
        for acc in account_data:
            if acc.get('account') == token_mint:
                if tx not in [f['tx'] for f in found_transactions]:
                    found_transactions.append({
                        'tx': tx,
                        'transfer': None
                    })
                break

    print(f"[+] Found {len(found_transactions)} transactions with LIVEBEAR!")

    if found_transactions:
        print(f"\n[SUCCESS] LIVEBEAR FOUND!")
        print(f"=" * 70)

        for i, item in enumerate(found_transactions, 1):
            tx = item['tx']
            transfer = item['transfer']

            timestamp = tx.get('timestamp')
            tx_date = datetime.fromtimestamp(timestamp)
            tx_type = tx.get('type')
            signature = tx.get('signature')

            print(f"\n[{i}] {tx_type} - {tx_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    Signature: {signature[:32]}...")

            if transfer:
                from_addr = transfer.get('fromUserAccount', '')
                to_addr = transfer.get('toUserAccount', '')
                amount = transfer.get('tokenAmount', 0)

                if to_addr == wallet_address:
                    print(f"    [BUY] Received {amount:,.0f} LIVEBEAR")
                elif from_addr == wallet_address:
                    print(f"    [SELL] Sent {amount:,.0f} LIVEBEAR")

            # Check SOL movement
            account_data = tx.get('accountData', [])
            for acc in account_data:
                if acc.get('account') == wallet_address:
                    sol_change = acc.get('nativeBalanceChange', 0) / 1e9
                    if sol_change != 0:
                        print(f"    SOL change: {sol_change:+.4f} SOL (${sol_change * 200:+.2f})")

    else:
        print(f"\n[!] LIVEBEAR NOT FOUND in any transaction!")
        print(f"\n[DEBUG] Showing all token mints in transactions:")

        all_mints = set()
        for tx in all_transactions:
            token_transfers = tx.get('tokenTransfers', [])
            for tt in token_transfers:
                mint = tt.get('mint')
                if mint:
                    all_mints.add(mint)

        print(f"\n[+] Found {len(all_mints)} unique tokens")
        for i, mint in enumerate(sorted(all_mints)[:30], 1):
            print(f"  {i}. {mint}")

        # Check if LIVEBEAR mint is similar to any
        print(f"\n[*] Looking for similar mints to LIVEBEAR...")
        livebear_start = token_mint[:16]
        for mint in all_mints:
            if mint.startswith(livebear_start[:8]):
                print(f"  [SIMILAR] {mint}")

    await client.aclose()


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"

    print("=" * 70)
    print("SEARCH LIVEBEAR IN ALL TRANSACTIONS")
    print("=" * 70)
    print(f"Wallet: {wallet}")
    print(f"Target: LIVEBEAR")
    print(f"Mint: {LIVEBEAR_MINT}")
    print("=" * 70)

    await search_token_in_all_tx(wallet, LIVEBEAR_MINT)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

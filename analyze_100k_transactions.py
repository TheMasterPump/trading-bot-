"""
ANALYZE 100K TRANSACTIONS
Parser toutes les transactions pour trouver TOUS les tokens
"""
import asyncio
import httpx
import json
from datetime import datetime
from collections import defaultdict

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"
LIVEBEAR_MINT = "8dwC2K6jeNFCE1ZBWcLqTbqGkvSghMkb1m5dpXYLpump"

async def get_all_signatures(wallet_address: str):
    """Get all signatures"""
    client = httpx.AsyncClient(timeout=120.0)
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    print(f"\n[*] Fetching signatures...")

    all_signatures = []
    before = None

    for batch in range(200):  # Max signatures
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet_address, {"limit": 1000}]
        }

        if before:
            payload["params"][1]["before"] = before

        try:
            response = await client.post(rpc_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                result = data.get('result', [])
                if not result:
                    break

                all_signatures.extend(result)
                before = result[-1]['signature']

                if (batch + 1) % 10 == 0:
                    print(f"[+] {len(all_signatures)} signatures...")

                if len(result) < 1000:
                    break
        except:
            break

    print(f"\n[+] Total: {len(all_signatures)} signatures")
    await client.aclose()
    return all_signatures


async def parse_transaction_batch(signatures_batch, client, rpc_url):
    """Parse a batch of transactions"""
    results = []

    for sig_data in signatures_batch:
        signature = sig_data['signature']

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
            ]
        }

        try:
            response = await client.post(rpc_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                tx = data.get('result')
                if tx:
                    results.append({'signature': signature, 'tx': tx})
        except:
            pass

    return results


async def analyze_all_transactions(wallet_address: str):
    """Analyze all transactions"""

    print("=" * 70)
    print("ANALYZING 100K+ TRANSACTIONS")
    print("=" * 70)
    print(f"Wallet: {wallet_address}")
    print("=" * 70)

    # Get all signatures
    signatures = await get_all_signatures(wallet_address)

    if not signatures:
        print("\n[!] No signatures!")
        return

    print(f"\n[*] Parsing transactions in batches...")
    print(f"[*] This will take a while for {len(signatures)} transactions...")

    client = httpx.AsyncClient(timeout=60.0)
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    all_tokens = set()
    livebear_txs = []

    batch_size = 50
    total_batches = (len(signatures) + batch_size - 1) // batch_size

    for i in range(0, min(5000, len(signatures)), batch_size):  # Analyze first 5000
        batch = signatures[i:i + batch_size]
        batch_num = i // batch_size + 1

        results = await parse_transaction_batch(batch, client, rpc_url)

        for item in results:
            tx = item['tx']
            signature = item['signature']

            # Extract all token mints
            tx_json = json.dumps(tx)

            # Check for LIVEBEAR
            if LIVEBEAR_MINT in tx_json:
                print(f"\n[!!!] FOUND LIVEBEAR!")
                print(f"      Signature: {signature}")
                livebear_txs.append(item)

            # Extract tokens from postTokenBalances
            meta = tx.get('meta', {})
            post_balances = meta.get('postTokenBalances', [])

            for balance in post_balances:
                mint = balance.get('mint')
                if mint:
                    all_tokens.add(mint)

        if batch_num % 10 == 0:
            print(f"[+] Processed {batch_num}/{total_batches} batches ({len(all_tokens)} unique tokens found)")

    await client.aclose()

    # Results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total signatures: {len(signatures)}")
    print(f"Transactions analyzed: {min(5000, len(signatures))}")
    print(f"Unique tokens found: {len(all_tokens)}")

    if livebear_txs:
        print(f"\n[SUCCESS] Found {len(livebear_txs)} LIVEBEAR transactions!")
        for item in livebear_txs:
            print(f"\nSignature: {item['signature']}")
    else:
        print(f"\n[!] LIVEBEAR not found in first 5000 transactions")
        print(f"[!] Try expanding search or wallet address is wrong")

    print(f"\nAll tokens ({len(all_tokens)}):")
    for i, mint in enumerate(sorted(all_tokens)[:50], 1):
        is_livebear = " [LIVEBEAR]" if mint == LIVEBEAR_MINT else ""
        print(f"  {i}. {mint}{is_livebear}")

    print("\n" + "=" * 70)


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"
    await analyze_all_transactions(wallet)


if __name__ == "__main__":
    asyncio.run(main())

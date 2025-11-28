"""
GET ALL SIGNATURES VIA SOLANA RPC
Utiliser Solana RPC directement pour recuperer TOUTES les signatures
"""
import asyncio
import httpx
import json

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def get_all_signatures_rpc(wallet_address: str):
    """Recuperer toutes les signatures via Solana RPC"""
    client = httpx.AsyncClient(timeout=120.0)

    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    print(f"\n[*] Fetching ALL signatures via Solana RPC...")
    print(f"    Wallet: {wallet_address[:16]}...")

    all_signatures = []
    before = None

    for batch in range(100):  # Up to 100 batches
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                wallet_address,
                {
                    "limit": 1000  # Max 1000 per call
                }
            ]
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

                print(f"[+] Batch {batch + 1}: {len(result)} signatures (total: {len(all_signatures)})")

                if len(result) < 1000:
                    break
            else:
                print(f"[!] Error: {response.status_code}")
                break

        except Exception as e:
            print(f"[!] Error: {e}")
            break

    print(f"\n[+] Total signatures: {len(all_signatures)}")

    await client.aclose()
    return all_signatures


async def get_transaction_details(signature: str):
    """Recuperer les details d'une transaction"""
    client = httpx.AsyncClient(timeout=30.0)

    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0
            }
        ]
    }

    try:
        response = await client.post(rpc_url, json=payload)

        if response.status_code == 200:
            data = response.json()
            await client.aclose()
            return data.get('result')
        else:
            await client.aclose()
            return None

    except Exception as e:
        await client.aclose()
        return None


async def search_livebear_in_signatures(signatures, target_mint: str):
    """Chercher LIVEBEAR dans les signatures"""
    print(f"\n[*] Searching for LIVEBEAR in {len(signatures)} signatures...")
    print(f"    Target mint: {target_mint[:16]}...")

    found = []

    # Sample every 10th transaction to start
    sample_size = min(100, len(signatures))
    sample_indices = [int(i * len(signatures) / sample_size) for i in range(sample_size)]

    print(f"\n[*] Sampling {sample_size} transactions...")

    for i, idx in enumerate(sample_indices):
        sig_data = signatures[idx]
        signature = sig_data['signature']

        if (i + 1) % 10 == 0:
            print(f"    Checked {i + 1}/{sample_size}...")

        # Get transaction details
        tx_details = await get_transaction_details(signature)

        if not tx_details:
            continue

        # Search for LIVEBEAR in the transaction
        tx_json = json.dumps(tx_details)

        if target_mint in tx_json:
            print(f"\n[!!!] FOUND LIVEBEAR in transaction!")
            print(f"      Signature: {signature}")
            found.append({
                'signature': signature,
                'details': tx_details
            })

    if found:
        print(f"\n[+] Found {len(found)} transactions with LIVEBEAR!")
    else:
        print(f"\n[!] LIVEBEAR not found in sampled transactions")

    return found


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"
    livebear_mint = "8dwC2K6jeNFCE1ZBWcLqTbqGkvSghMkb1m5dpXYLpump"

    print("=" * 70)
    print("SOLANA RPC DEEP SCAN")
    print("=" * 70)
    print(f"Wallet: {wallet}")
    print(f"Target: LIVEBEAR")
    print("=" * 70)

    # Get all signatures
    signatures = await get_all_signatures_rpc(wallet)

    if not signatures:
        print("\n[!] No signatures found!")
        return

    # Search for LIVEBEAR
    found = await search_livebear_in_signatures(signatures, livebear_mint)

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)

    if found:
        print(f"\n[SUCCESS] Found {len(found)} LIVEBEAR transactions!")
        for item in found:
            print(f"\nSignature: {item['signature']}")
    else:
        print(f"\n[FAILED] LIVEBEAR not found")
        print(f"\nTotal signatures checked: {len(signatures)}")
        print(f"This means either:")
        print(f"  1. LIVEBEAR was never traded by this wallet")
        print(f"  2. The wallet address is incorrect")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

"""
ANALYZE WITH DEXSCREENER API
Combiner Helius (achats pre-migration) + DexScreener (ventes post-migration)
"""
import asyncio
import httpx
from datetime import datetime
from collections import defaultdict

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def get_helius_transactions(wallet_address: str):
    """Recupere les transactions Helius (achats pre-migration)"""
    client = httpx.AsyncClient(timeout=60.0)

    print(f"\n[*] Fetching transactions from Helius...")

    all_transactions = []
    before_signature = None

    for batch in range(10):
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

                if len(transactions) < 100:
                    break
            else:
                break

        except Exception as e:
            print(f"[!] Error: {e}")
            break

    await client.aclose()
    return all_transactions


async def get_token_info_dexscreener(token_mint: str):
    """Recuperer les infos d'un token depuis DexScreener"""
    client = httpx.AsyncClient(timeout=30.0)

    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
        response = await client.get(url)

        if response.status_code == 200:
            data = response.json()
            await client.aclose()
            return data
        else:
            await client.aclose()
            return None

    except Exception as e:
        await client.aclose()
        return None


async def get_wallet_profile_dexscreener(wallet_address: str):
    """Essayer de recuperer le profil wallet depuis DexScreener"""
    client = httpx.AsyncClient(timeout=30.0)

    # DexScreener n'a pas d'API publique pour les wallets
    # Mais on peut essayer quelques endpoints
    endpoints = [
        f"https://api.dexscreener.com/wallet/{wallet_address}",
        f"https://api.dexscreener.com/v1/wallet/{wallet_address}",
        f"https://api.dexscreener.com/latest/wallet/{wallet_address}",
    ]

    for endpoint in endpoints:
        try:
            print(f"\n[*] Trying: {endpoint[:50]}...")
            response = await client.get(endpoint)

            if response.status_code == 200:
                print(f"[+] Success! Got data from {endpoint}")
                data = response.json()
                await client.aclose()
                return data
            else:
                print(f"    Status: {response.status_code}")

        except Exception as e:
            print(f"    Error: {e}")
            continue

    await client.aclose()
    return None


async def analyze_tokens_with_dexscreener(wallet_address: str, transactions):
    """Analyser les tokens avec DexScreener"""

    print(f"\n[*] Extracting token mints from transactions...")

    # Get all unique tokens
    token_mints = set()

    for tx in transactions:
        if tx.get('type') != 'SWAP':
            continue

        token_transfers = tx.get('tokenTransfers', [])
        for tt in token_transfers:
            mint = tt.get('mint')
            if mint:
                token_mints.add(mint)

    print(f"[+] Found {len(token_mints)} unique tokens")

    # Check each token on DexScreener
    print(f"\n[*] Checking tokens on DexScreener...")

    token_data = {}

    for i, mint in enumerate(list(token_mints)[:20], 1):  # Limit to 20
        print(f"\n[{i}] Checking {mint[:16]}...")

        data = await get_token_info_dexscreener(mint)

        if data:
            pairs = data.get('pairs', [])

            if pairs:
                pair = pairs[0]
                name = pair.get('baseToken', {}).get('name', 'Unknown')
                symbol = pair.get('baseToken', {}).get('symbol', 'Unknown')
                price_usd = float(pair.get('priceUsd', 0))
                mcap = float(pair.get('marketCap', 0))
                dex = pair.get('dexId', 'Unknown')

                print(f"    Found: {name} ({symbol})")
                print(f"    DEX: {dex}")
                print(f"    Price: ${price_usd:.8f}")
                print(f"    Market Cap: ${mcap:,.0f}")

                token_data[mint] = {
                    'name': name,
                    'symbol': symbol,
                    'price_usd': price_usd,
                    'mcap': mcap,
                    'dex': dex,
                    'pair': pair
                }
            else:
                print(f"    No pairs found")
        else:
            print(f"    Not found on DexScreener")

        await asyncio.sleep(0.5)  # Rate limit

    return token_data


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"

    print("=" * 70)
    print("DEXSCREENER + HELIUS COMBINED ANALYSIS")
    print("=" * 70)
    print(f"Wallet: {wallet}")
    print("=" * 70)

    # Step 1: Try to get wallet profile from DexScreener
    print("\n[STEP 1] Trying to get wallet profile from DexScreener...")
    wallet_profile = await get_wallet_profile_dexscreener(wallet)

    if wallet_profile:
        print("\n[+] Got wallet profile!")
        print(wallet_profile)
    else:
        print("\n[!] No wallet profile API available")

    # Step 2: Get transactions from Helius
    print("\n[STEP 2] Getting transactions from Helius...")
    transactions = await get_helius_transactions(wallet)
    print(f"[+] Got {len(transactions)} transactions")

    # Step 3: Check tokens on DexScreener
    print("\n[STEP 3] Checking tokens on DexScreener...")
    token_data = await analyze_tokens_with_dexscreener(wallet, transactions)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Tokens found on DexScreener: {len(token_data)}")

    for mint, data in token_data.items():
        print(f"\n{data['name']} ({data['symbol']})")
        print(f"  DEX: {data['dex']}")
        print(f"  Market Cap: ${data['mcap']:,.0f}")

    print("\n" + "=" * 70)
    print("\n[NOTE] DexScreener API ne fournit pas l'historique des trades par wallet")
    print("[NOTE] Les profits sur DexScreener ($2,433) viennent probablement de leur interface web")
    print("[NOTE] qui calcule les trades en analysant les transactions on-chain")
    print("\n[SOLUTION] Utiliser Helius pour reconstruire les trades complets")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

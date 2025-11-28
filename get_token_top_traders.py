"""
GET TOKEN TOP TRADERS
Recuperer les top traders d'un token depuis differentes sources
"""
import asyncio
import httpx
import json

async def get_top_traders_birdeye(token_mint: str):
    """Essayer Birdeye API"""
    client = httpx.AsyncClient(timeout=30.0)

    print("\n[*] Trying Birdeye API for top traders...")

    url = f"https://public-api.birdeye.so/public/token_holder"
    params = {"address": token_mint}

    try:
        response = await client.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            print(f"[+] Birdeye data received!")
            print(json.dumps(data, indent=2)[:500])
        else:
            print(f"[!] Birdeye error: {response.status_code}")

    except Exception as e:
        print(f"[!] Error: {e}")

    await client.aclose()


async def get_token_holders_helius(token_mint: str):
    """Recuperer les holders via Helius"""
    client = httpx.AsyncClient(timeout=30.0)

    HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

    print("\n[*] Trying Helius for token holders...")

    # Try to get token metadata
    url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccounts",
        "params": {
            "mint": token_mint,
            "page": 1,
            "limit": 100
        }
    }

    try:
        response = await client.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            print(f"[+] Helius data received!")
            print(json.dumps(data, indent=2)[:500])
        else:
            print(f"[!] Helius error: {response.status_code}")

    except Exception as e:
        print(f"[!] Error: {e}")

    await client.aclose()


async def search_wallet_in_token_transactions(token_mint: str, wallet_to_find: str):
    """Chercher si un wallet a trade ce token via les transactions on-chain"""
    client = httpx.AsyncClient(timeout=60.0)

    HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

    print(f"\n[*] Searching for wallet {wallet_to_find[:16]}... in {token_mint[:16]}... transactions...")

    # Get token account for this mint
    url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    # Try to get token accounts
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenLargestAccounts",
        "params": [token_mint]
    }

    try:
        response = await client.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            result = data.get('result', {})
            value = result.get('value', [])

            print(f"[+] Found {len(value)} largest holders")

            for i, holder in enumerate(value[:10], 1):
                address = holder.get('address')
                amount = holder.get('amount')
                print(f"{i}. {address} - {amount} tokens")

                # Get owner of this token account
                owner_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getAccountInfo",
                    "params": [
                        address,
                        {"encoding": "jsonParsed"}
                    ]
                }

                owner_response = await client.post(url, json=owner_payload)
                if owner_response.status_code == 200:
                    owner_data = owner_response.json()
                    account_info = owner_data.get('result', {}).get('value', {}).get('data', {})

                    if isinstance(account_info, dict) and 'parsed' in account_info:
                        info = account_info['parsed'].get('info', {})
                        owner = info.get('owner')

                        if owner:
                            print(f"   Owner: {owner}")

                            if owner == wallet_to_find:
                                print(f"\n[!!!] FOUND THE WALLET!")
                                print(f"   Wallet {wallet_to_find[:16]}... holds {amount} tokens")

        else:
            print(f"[!] Error: {response.status_code}")

    except Exception as e:
        print(f"[!] Error: {e}")

    await client.aclose()


async def main():
    token = "8dwC2K6jeNFCE1ZBWcLqTbqGkvSghMkb1m5dpXYLpump"
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"

    print("=" * 70)
    print("TOKEN TOP TRADERS FINDER")
    print("=" * 70)
    print(f"Token: {token}")
    print(f"Looking for wallet: {wallet}")
    print("=" * 70)

    # Try different methods
    await get_top_traders_birdeye(token)
    await get_token_holders_helius(token)
    await search_wallet_in_token_transactions(token, wallet)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

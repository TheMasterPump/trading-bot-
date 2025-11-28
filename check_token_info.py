"""
CHECK TOKEN INFO
Verifier les infos d'un token specifique
"""
import asyncio
import httpx

async def check_token(token_mint: str):
    """Verifie les infos du token"""
    client = httpx.AsyncClient(timeout=30.0)

    print("\n" + "=" * 70)
    print("TOKEN INFO CHECKER")
    print("=" * 70)
    print(f"Token: {token_mint}")
    print("=" * 70)

    # DexScreener
    print("\n[*] Checking DexScreener...")
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
        response = await client.get(url)

        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs', [])

            if pairs:
                pair = pairs[0]

                print(f"\n[+] Token found!")
                print(f"Name: {pair.get('baseToken', {}).get('name', 'Unknown')}")
                print(f"Symbol: {pair.get('baseToken', {}).get('symbol', 'Unknown')}")
                print(f"Price: ${float(pair.get('priceUsd', 0)):.8f}")
                print(f"Market Cap: ${float(pair.get('marketCap', 0)):,.0f}")
                print(f"Liquidity: ${float(pair.get('liquidity', {}).get('usd', 0)):,.0f}")
                print(f"24h Volume: ${float(pair.get('volume', {}).get('h24', 0)):,.0f}")
                print(f"24h Change: {float(pair.get('priceChange', {}).get('h24', 0)):+.2f}%")
                print(f"DEX: {pair.get('dexId', 'Unknown')}")
                print(f"Pair: {pair.get('pairAddress', 'Unknown')}")

                # Transactions
                txns = pair.get('txns', {}).get('h24', {})
                print(f"\n24h Transactions:")
                print(f"  Buys: {txns.get('buys', 0)}")
                print(f"  Sells: {txns.get('sells', 0)}")
            else:
                print("[!] No pairs found for this token")
        else:
            print(f"[!] Error: {response.status_code}")

    except Exception as e:
        print(f"[!] Error: {e}")

    # Pump.fun API
    print("\n[*] Checking Pump.fun API...")
    try:
        url = f"https://frontend-api.pump.fun/coins/{token_mint}"
        response = await client.get(url)

        if response.status_code == 200:
            data = response.json()

            print(f"\n[+] Pump.fun token found!")
            print(f"Name: {data.get('name', 'Unknown')}")
            print(f"Symbol: {data.get('symbol', 'Unknown')}")
            print(f"Market Cap: ${float(data.get('market_cap', 0)):,.0f}")
            print(f"Virtual SOL Reserves: {float(data.get('virtual_sol_reserves', 0)) / 1e9:.4f} SOL")
            print(f"Virtual Token Reserves: {float(data.get('virtual_token_reserves', 0)):,.0f}")
            print(f"Complete (Migrated): {data.get('complete', False)}")
            print(f"Creator: {data.get('creator', 'Unknown')}")
        else:
            print(f"[!] Not a pump.fun token or not found (status: {response.status_code})")

    except Exception as e:
        print(f"[!] Error: {e}")

    print("\n" + "=" * 70)

    await client.aclose()


async def main():
    token = "8dwC2K6jeNFCE1ZBWcLqTbqGkvSghMkb1m5dpXYLpump"
    await check_token(token)


if __name__ == "__main__":
    asyncio.run(main())

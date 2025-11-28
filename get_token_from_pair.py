"""
GET TOKEN MINT FROM PAIR
Recuperer le vrai token mint depuis la pair address
"""
import asyncio
import httpx

async def get_token_from_pair(pair_address: str):
    """Get token mint from pair address"""
    client = httpx.AsyncClient(timeout=30.0)

    print(f"\n[*] Getting token info from pair: {pair_address}")

    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_address}"
        response = await client.get(url)

        if response.status_code == 200:
            data = response.json()
            pair = data.get('pair')

            if pair:
                base_token = pair.get('baseToken', {})
                quote_token = pair.get('quoteToken', {})

                print(f"\n[PAIR INFO]")
                print(f"Pair address: {pair.get('pairAddress')}")
                print(f"DEX: {pair.get('dexId')}")

                print(f"\n[BASE TOKEN] (the token being traded)")
                print(f"Address: {base_token.get('address')}")
                print(f"Name: {base_token.get('name')}")
                print(f"Symbol: {base_token.get('symbol')}")

                print(f"\n[QUOTE TOKEN] (usually SOL/USDC)")
                print(f"Address: {quote_token.get('address')}")
                print(f"Name: {quote_token.get('name')}")
                print(f"Symbol: {quote_token.get('symbol')}")

                print(f"\n[MARKET DATA]")
                print(f"Price USD: ${float(pair.get('priceUsd', 0)):.8f}")
                print(f"Market Cap: ${float(pair.get('marketCap', 0)):,.0f}")
                print(f"Liquidity: ${float(pair.get('liquidity', {}).get('usd', 0)):,.0f}")

                await client.aclose()
                return base_token.get('address')
        else:
            print(f"[!] Error: {response.status_code}")

    except Exception as e:
        print(f"[!] Error: {e}")

    await client.aclose()
    return None


async def main():
    pair = "6cc7nBAkjx936YmwSuwBrSPPKYwbA7Ht9xamfyQBqEGY"

    print("=" * 70)
    print("GET TOKEN MINT FROM PAIR")
    print("=" * 70)
    print(f"Pair: {pair}")
    print("=" * 70)

    token_mint = await get_token_from_pair(pair)

    if token_mint:
        print(f"\n[+] TRUE TOKEN MINT: {token_mint}")
        print(f"\n[*] This is the address to search for in wallet transactions!")
    else:
        print(f"\n[!] Could not get token mint from pair")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

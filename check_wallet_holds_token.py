"""
CHECK IF WALLET HOLDS TOKEN
Verifie si le wallet detient encore ce token
"""
import asyncio
import httpx

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def check_wallet_token_balance(wallet_address: str, token_mint: str):
    """Verifie si le wallet detient ce token"""
    client = httpx.AsyncClient(timeout=60.0)

    print("\n" + "=" * 70)
    print("WALLET TOKEN BALANCE CHECKER")
    print("=" * 70)
    print(f"Wallet: {wallet_address}")
    print(f"Token: {token_mint}")
    print("=" * 70)

    # Get token balances
    print("\n[*] Getting wallet token balances...")

    url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/balances"
    params = {"api-key": HELIUS_API_KEY}

    try:
        response = await client.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            tokens = data.get('tokens', [])

            print(f"[+] Wallet has {len(tokens)} tokens")

            # Search for our token
            found = False
            for token in tokens:
                if token.get('mint') == token_mint:
                    found = True
                    amount = token.get('amount', 0)

                    print(f"\n[+] TOKEN FOUND IN WALLET!")
                    print(f"Amount held: {amount:,.0f} tokens")

                    # Get current price
                    print(f"\n[*] Getting current price from DexScreener...")
                    price_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
                    price_response = await client.get(price_url)

                    if price_response.status_code == 200:
                        price_data = price_response.json()
                        pairs = price_data.get('pairs', [])

                        if pairs:
                            pair = pairs[0]
                            price_usd = float(pair.get('priceUsd', 0))
                            mcap = float(pair.get('marketCap', 0))

                            current_value_usd = amount * price_usd
                            current_value_sol = current_value_usd / 200

                            print(f"\n[TOKEN INFO]")
                            print(f"Name: {pair.get('baseToken', {}).get('name', 'Unknown')}")
                            print(f"Symbol: {pair.get('baseToken', {}).get('symbol', 'Unknown')}")
                            print(f"Current Price: ${price_usd:.8f}")
                            print(f"Current Market Cap: ${mcap:,.0f}")

                            print(f"\n[POSITION VALUE]")
                            print(f"Tokens held: {amount:,.0f}")
                            print(f"Current value: ${current_value_usd:,.2f}")
                            print(f"Current value: {current_value_sol:.4f} SOL")

                            # Calculate P&L if bought at 10k mcap
                            print(f"\n[P&L CALCULATION]")
                            print(f"If bought at $10,000 market cap:")
                            buy_price_at_10k = (10000 / mcap) * price_usd if mcap > 0 else 0
                            invested_value = amount * buy_price_at_10k
                            pnl = current_value_usd - invested_value
                            pnl_percent = (pnl / invested_value * 100) if invested_value > 0 else 0

                            print(f"  Buy price: ${buy_price_at_10k:.8f}")
                            print(f"  Invested: ${invested_value:,.2f}")
                            print(f"  Current value: ${current_value_usd:,.2f}")
                            print(f"  P&L: ${pnl:+,.2f} ({pnl_percent:+.2f}%)")

                            # Multiplier
                            multiplier = mcap / 10000 if mcap > 0 else 0
                            print(f"\n  Market cap went from $10k to ${mcap:,.0f}")
                            print(f"  Multiplier: {multiplier:.2f}x")

                    break

            if not found:
                print(f"\n[!] Token NOT found in wallet")
                print(f"[!] This wallet does NOT hold {token_mint}")

                # Show all tokens for reference
                print(f"\n[*] Wallet holds these tokens instead:")
                for i, token in enumerate(tokens[:10], 1):
                    print(f"  {i}. {token.get('mint', 'Unknown')[:32]}... ({token.get('amount', 0):,.0f})")

        else:
            print(f"[!] Error: {response.status_code}")

    except Exception as e:
        print(f"[!] Error: {e}")

    print("\n" + "=" * 70)

    await client.aclose()


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"
    token = "8dwC2K6jeNFCE1ZBWcLqTbqGkvSghMkb1m5dpXYLpump"

    await check_wallet_token_balance(wallet, token)


if __name__ == "__main__":
    asyncio.run(main())

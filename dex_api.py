"""
Alternative API using DexScreener (no Cloudflare protection)
"""
import httpx
import asyncio
from typing import Optional

def get_token_from_dexscreener(mint_address: str) -> Optional[dict]:
    """
    Get token data from DexScreener API
    This API is public and doesn't have Cloudflare protection
    """
    try:
        client = httpx.Client(timeout=10.0)

        # DexScreener API endpoint
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"

        response = client.get(url)

        if response.status_code == 200:
            data = response.json()

            # DexScreener returns pairs, find pump.fun pair
            if data and 'pairs' in data and len(data['pairs']) > 0:
                # Try to find pump.fun pair first
                pump_pair = None
                for pair in data['pairs']:
                    if 'pumpfun' in pair.get('dexId', '').lower() or \
                       'pump' in pair.get('dexId', '').lower():
                        pump_pair = pair
                        break

                # If no pump.fun pair, use first pair
                if not pump_pair and len(data['pairs']) > 0:
                    pump_pair = data['pairs'][0]

                if pump_pair:
                    # Convert to pump.fun format
                    return {
                        'mint': mint_address,
                        'name': pump_pair.get('baseToken', {}).get('name', 'Unknown'),
                        'symbol': pump_pair.get('baseToken', {}).get('symbol', 'Unknown'),
                        'usd_market_cap': float(pump_pair.get('marketCap', 0) or 0),
                        'price': float(pump_pair.get('priceUsd', 0) or 0),
                        'liquidity': float(pump_pair.get('liquidity', {}).get('usd', 0) or 0),
                        'complete': True,  # Assume complete if on DEX
                        'raydium_pool': pump_pair.get('pairAddress') if 'raydium' in pump_pair.get('dexId', '').lower() else None,
                        'creator': None,  # DexScreener doesn't provide creator
                        'twitter': None,
                        'telegram': None,
                        'website': pump_pair.get('info', {}).get('websites', [{}])[0].get('url') if pump_pair.get('info', {}).get('websites') else None,
                        'description': ''
                    }

        client.close()
        return None

    except Exception as e:
        print(f"DexScreener API error: {e}")
        return None


async def get_token_price(mint_address: str) -> Optional[float]:
    """
    Get current token market cap (in K) from DexScreener API
    Used by simulation mode to track prices in real-time
    Returns market cap in thousands (K)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()

                if data and 'pairs' in data and len(data['pairs']) > 0:
                    # Try to find pump.fun pair first
                    pump_pair = None
                    for pair in data['pairs']:
                        if 'pumpfun' in pair.get('dexId', '').lower() or \
                           'pump' in pair.get('dexId', '').lower():
                            pump_pair = pair
                            break

                    # If no pump.fun pair, use first pair
                    if not pump_pair and len(data['pairs']) > 0:
                        pump_pair = data['pairs'][0]

                    if pump_pair:
                        # Get market cap and convert to K
                        market_cap = float(pump_pair.get('marketCap', 0) or 0)
                        return market_cap / 1000  # Convert to K

            return None

    except Exception as e:
        print(f"Error fetching token price for {mint_address[:8]}: {e}")
        return None


def test_api():
    """Test the DexScreener API"""
    # Test with a known Solana token
    test_address = "So11111111111111111111111111111111111111112"  # Wrapped SOL

    print("Testing DexScreener API...")
    data = get_token_from_dexscreener(test_address)

    if data:
        print("[OK] API Works!")
        print(f"Token: {data.get('name')} ({data.get('symbol')})")
        print(f"Market Cap: ${data.get('usd_market_cap', 0):,.2f}")
        print(f"Liquidity: ${data.get('liquidity', 0):,.2f}")
    else:
        print("[ERROR] API Failed")


if __name__ == "__main__":
    test_api()

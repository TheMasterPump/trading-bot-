"""Analyze token liquidity and market metrics"""
try:
    import cloudscraper
    USE_CLOUDSCRAPER = True
except ImportError:
    import httpx
    USE_CLOUDSCRAPER = False

from typing import Optional, List
from dataclasses import dataclass
from config import RISK_THRESHOLDS
from metadata_fetcher import MetadataFetcher


@dataclass
class LiquidityAnalysis:
    """Results of liquidity analysis"""
    market_cap_usd: float
    liquidity_usd: float
    price_usd: float
    volume_24h: Optional[float]
    bonding_curve_complete: bool
    migrated_to_raydium: bool
    risk_score: int
    red_flags: List[str]


class LiquidityAnalyzer:
    """Analyzes token liquidity and market data"""

    def __init__(self, rpc_url: str = None):
        # Store RPC URL
        self.rpc_url = rpc_url

        if USE_CLOUDSCRAPER:
            self.scraper = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
            )
            self.client = None
        else:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://pump.fun/',
                'Origin': 'https://pump.fun'
            }
            self.client = httpx.Client(timeout=30.0, headers=headers, follow_redirects=True)
            self.scraper = None

        # Initialize blockchain metadata fetcher with RPC URL
        self.metadata_fetcher = MetadataFetcher(rpc_url=self.rpc_url)

    def get_token_data(self, mint_address: str) -> Optional[dict]:
        """Fetch token data from DexScreener API with blockchain metadata fallback"""
        # Get market data from DexScreener
        dex_data = self._get_from_dexscreener(mint_address)

        if not dex_data:
            return None

        # Enrich with blockchain metadata (twitter, telegram, website, description)
        blockchain_metadata = self._get_blockchain_metadata(mint_address)

        if blockchain_metadata:
            # Merge: Prioritize blockchain for social data (instant & accurate)
            if blockchain_metadata.get('twitter'):
                dex_data['twitter'] = blockchain_metadata['twitter']
            if blockchain_metadata.get('telegram'):
                dex_data['telegram'] = blockchain_metadata['telegram']
            if blockchain_metadata.get('website'):
                dex_data['website'] = blockchain_metadata['website']
            if blockchain_metadata.get('description'):
                dex_data['description'] = blockchain_metadata['description']

        return dex_data

    def _get_from_dexscreener(self, mint_address: str) -> Optional[dict]:
        """Fallback: Get data from DexScreener API"""
        try:
            import httpx
            client = httpx.Client(timeout=30.0, follow_redirects=True)
            url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
            response = client.get(url)

            if response.status_code == 200:
                data = response.json()
                if data and 'pairs' in data and len(data['pairs']) > 0:
                    pair = data['pairs'][0]  # Use first pair
                    dex_id = pair.get('dexId', '').lower()

                    # Check if on Raydium or PumpSwap (pump.fun's DEX)
                    raydium_pool = None
                    pumpswap_pool = None

                    if 'raydium' in dex_id:
                        raydium_pool = pair.get('pairAddress')
                    elif 'pump' in dex_id:
                        pumpswap_pool = pair.get('pairAddress')

                    # Extract social media from DexScreener
                    info = pair.get('info', {})
                    socials = info.get('socials', [])
                    websites = info.get('websites', [])

                    twitter_url = None
                    telegram_url = None
                    website_url = None

                    # Parse socials array
                    for social in socials:
                        social_type = social.get('type', '').lower()
                        social_url = social.get('url', '')

                        if social_type == 'twitter' or 'twitter.com' in social_url or 'x.com' in social_url:
                            twitter_url = social_url
                        elif social_type == 'telegram' or 't.me' in social_url:
                            telegram_url = social_url

                    # Get website
                    if websites and len(websites) > 0:
                        website_url = websites[0].get('url') if isinstance(websites[0], dict) else websites[0]

                    # Extract liquidity (can be null for some DEXs like PumpSwap)
                    liquidity_data = pair.get('liquidity')
                    liquidity_usd = 0
                    if liquidity_data:
                        if isinstance(liquidity_data, dict):
                            liquidity_usd = float(liquidity_data.get('usd', 0) or 0)
                        else:
                            liquidity_usd = float(liquidity_data or 0)

                    # Extract volume 24h
                    volume_data = pair.get('volume', {})
                    volume_24h = float(volume_data.get('h24', 0) or 0) if isinstance(volume_data, dict) else 0

                    # Extract transaction counts
                    txns_data = pair.get('txns', {})
                    txns_h24 = txns_data.get('h24', {}) if isinstance(txns_data, dict) else {}
                    buys = txns_h24.get('buys', 0) if isinstance(txns_h24, dict) else 0
                    sells = txns_h24.get('sells', 0) if isinstance(txns_h24, dict) else 0

                    # Extract price changes (for pump & dump detection)
                    price_change = pair.get('priceChange', {})
                    change_5m = float(price_change.get('m5', 0) or 0) if isinstance(price_change, dict) else 0
                    change_1h = float(price_change.get('h1', 0) or 0) if isinstance(price_change, dict) else 0
                    change_6h = float(price_change.get('h6', 0) or 0) if isinstance(price_change, dict) else 0
                    change_24h = float(price_change.get('h24', 0) or 0) if isinstance(price_change, dict) else 0

                    # Extract creation timestamp
                    created_at = pair.get('pairCreatedAt')  # Unix timestamp in milliseconds

                    client.close()
                    return {
                        'mint': mint_address,
                        'name': pair.get('baseToken', {}).get('name', 'Unknown'),
                        'symbol': pair.get('baseToken', {}).get('symbol', 'Unknown'),
                        'usd_market_cap': float(pair.get('marketCap', 0) or pair.get('fdv', 0) or 0),
                        'price': float(pair.get('priceUsd', 0) or 0),
                        'liquidity': liquidity_usd,
                        'volume_24h': volume_24h,
                        'txns': {
                            'h24': {
                                'buys': buys,
                                'sells': sells
                            }
                        },
                        'priceChange': {
                            'm5': change_5m,
                            'h1': change_1h,
                            'h6': change_6h,
                            'h24': change_24h
                        },
                        'complete': True,
                        'raydium_pool': raydium_pool,
                        'pumpswap_pool': pumpswap_pool,
                        'creator': None,
                        'twitter': twitter_url,
                        'telegram': telegram_url,
                        'website': website_url,
                        'description': '',
                        'created_timestamp': created_at
                    }
            client.close()
            return None
        except Exception as e:
            print(f"DexScreener fallback failed: {e}")
            return None

    def _get_blockchain_metadata(self, mint_address: str) -> Optional[dict]:
        """Get token metadata directly from Solana blockchain + IPFS"""
        try:
            metadata = self.metadata_fetcher.get_metadata(mint_address)

            if metadata:
                print(f"[DEBUG] Blockchain metadata found: twitter={metadata.get('twitter')}, telegram={metadata.get('telegram')}, website={metadata.get('website')}")
                return metadata

            print(f"[DEBUG] No blockchain metadata found for {mint_address}")
            return None

        except Exception as e:
            print(f"[WARNING] Blockchain metadata fetch failed (non-critical): {e}")
            # Return None so scan continues with DexScreener data only
            return None

    def analyze_liquidity(self, mint_address: str) -> LiquidityAnalysis:
        """Analyze token liquidity metrics"""

        token_data = self.get_token_data(mint_address)

        if not token_data:
            return LiquidityAnalysis(
                market_cap_usd=0,
                liquidity_usd=0,
                price_usd=0,
                volume_24h=None,
                bonding_curve_complete=False,
                migrated_to_raydium=False,
                risk_score=100,
                red_flags=["[!!] Cannot fetch token data - token may not exist"]
            )

        # Extract metrics
        market_cap = token_data.get("usd_market_cap", 0)
        price = token_data.get("price", 0)
        liquidity = token_data.get("liquidity", 0)
        volume_24h = token_data.get("volume_24h")
        complete = token_data.get("complete", False)
        raydium_pool = token_data.get("raydium_pool")
        pumpswap_pool = token_data.get("pumpswap_pool")  # PumpSwap (pump.fun DEX)

        # Calculate risk
        red_flags = []
        risk_score = 0

        # Check market cap
        if market_cap < 1000:
            red_flags.append("[!!] EXTREME LOW MCAP: Less than $1,000")
            risk_score += 40
        elif market_cap < 5000:
            red_flags.append("[!] Very low market cap: Less than $5,000")
            risk_score += 25

        # Check liquidity
        # NOTE: PumpSwap pools often don't report liquidity via DexScreener
        if liquidity < RISK_THRESHOLDS["MIN_LIQUIDITY_USD"]:
            if pumpswap_pool:
                # Reduce penalty for PumpSwap (liquidity data not available)
                red_flags.append(
                    f"[!] Liquidity data not available (PumpSwap pool)"
                )
                risk_score += 10  # Lower penalty
            else:
                red_flags.append(
                    f"[!!] LOW LIQUIDITY: Only ${liquidity:.2f} (easy to manipulate)"
                )
                risk_score += 35

        # Check bonding curve status
        if not complete:
            red_flags.append(
                "[!] Bonding curve not complete (more tokens can be minted)"
            )
            risk_score += 15

        # Check DEX migration (Raydium or PumpSwap are both OK)
        migrated = raydium_pool is not None or pumpswap_pool is not None
        # NOTE: Don't flag if on PumpSwap - it's pump.fun's official DEX!

        # Liquidity to market cap ratio
        if market_cap > 0:
            liq_ratio = (liquidity / market_cap) * 100
            if liq_ratio < 5:
                red_flags.append(
                    f"[!] LOW LIQUIDITY RATIO: Only {liq_ratio:.1f}% of mcap"
                )
                risk_score += 15

        return LiquidityAnalysis(
            market_cap_usd=market_cap,
            liquidity_usd=liquidity,
            price_usd=price,
            volume_24h=volume_24h,  # NOW available from DexScreener!
            bonding_curve_complete=complete,
            migrated_to_raydium=migrated,
            risk_score=min(risk_score, 100),
            red_flags=red_flags
        )

    def close(self):
        """Close HTTP client"""
        if self.client:
            self.client.close()
        if self.scraper:
            self.scraper.close()
        if self.metadata_fetcher:
            self.metadata_fetcher.close()

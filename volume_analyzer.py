"""
Analyze trading volume to detect wash trading and manipulation
"""
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class VolumeAnalysis:
    """Results from volume analysis"""
    volume_24h: float
    market_cap: float
    volume_to_mcap_ratio: float
    liquidity_to_volume_ratio: float
    buy_sell_ratio: float  # Ratio of buys to sells
    buy_volume_percentage: float  # NEW: % of volume that is buys
    small_trade_percentage: float  # NEW: % of trades that are small (bot pattern)
    unique_traders_24h: Optional[int]
    is_wash_trading: bool
    is_fake_volume: bool  # NEW: Volume is completely fake
    risk_score: int
    red_flags: List[str]


class VolumeAnalyzer:
    """Analyzes trading volume to detect manipulation"""

    @staticmethod
    def analyze_volume(token_data: dict, liquidity: float) -> VolumeAnalysis:
        """
        Analyze volume patterns to detect wash trading

        Wash trading indicators:
        - Volume >> Market Cap (10x+)
        - Very high volume but few unique traders
        - Suspicious buy/sell patterns
        """

        # Extract data
        market_cap = token_data.get("usd_market_cap", 0) or token_data.get("fdv", 0)

        # Try to get volume from different sources
        volume_24h = 0
        txns = token_data.get("txns", {})

        # Get volume from direct key (NEW from liquidity_analyzer)
        if "volume_24h" in token_data:
            volume_24h = float(token_data["volume_24h"] or 0)
        # Or from DexScreener volume object
        elif "volume" in token_data:
            volume_data = token_data["volume"]
            if isinstance(volume_data, dict):
                volume_24h = float(volume_data.get("h24", 0) or volume_data.get("24h", 0) or 0)
            else:
                volume_24h = float(volume_data or 0)

        # Get buy/sell counts
        h24_txns = txns.get("h24", {}) if txns else {}
        buys = h24_txns.get("buys", 0)
        sells = h24_txns.get("sells", 0)
        total_txns = buys + sells

        # Calculate ratios
        volume_to_mcap = (volume_24h / market_cap) if market_cap > 0 else 0
        liquidity_to_volume = (liquidity / volume_24h) if volume_24h > 0 else 0

        buy_sell_ratio = (buys / sells) if sells > 0 else 0

        # NEW: Calculate buy volume percentage
        buy_volume_pct = (buys / total_txns * 100) if total_txns > 0 else 0

        # NEW: Estimate small trade percentage (would need full tx data)
        # For now, use heuristic based on volume/txn ratio
        avg_trade_size = (volume_24h / total_txns) if total_txns > 0 else 0
        small_trade_pct = 0  # Placeholder

        # Detect wash trading and fake volume
        red_flags = []
        risk_score = 0
        is_wash_trading = False
        is_fake_volume = False

        # Volume to Market Cap ratio (IMPROVED thresholds)
        if volume_to_mcap > 100:
            red_flags.append(f"[!!] FAKE VOLUME: Volume is {volume_to_mcap:.0f}x market cap (IMPOSSIBLE!)")
            risk_score += 60
            is_wash_trading = True
            is_fake_volume = True
        elif volume_to_mcap > 50:
            red_flags.append(f"[!!] EXTREME WASH TRADING: Volume is {volume_to_mcap:.0f}x market cap")
            risk_score += 50
            is_wash_trading = True
        elif volume_to_mcap > 25:
            red_flags.append(f"[!!] WASH TRADING LIKELY: Volume is {volume_to_mcap:.0f}x market cap")
            risk_score += 40
            is_wash_trading = True
        elif volume_to_mcap > 15:
            red_flags.append(f"[!] Very suspicious volume: {volume_to_mcap:.0f}x market cap")
            risk_score += 30
        elif volume_to_mcap > 10:
            red_flags.append(f"[!] High volume ratio: {volume_to_mcap:.0f}x market cap")
            risk_score += 20

        # NEW: Liquidity to Volume ratio (more aggressive)
        if liquidity > 0 and volume_24h > 0:
            if liquidity_to_volume < 0.005 and volume_24h > 10000:
                red_flags.append(f"[!!] IMPOSSIBLE VOLUME: Too high for available liquidity")
                risk_score += 40
                is_fake_volume = True
            elif liquidity_to_volume < 0.02 and volume_24h > 5000:
                red_flags.append(f"[!] Volume too high for liquidity")
                risk_score += 25

        # NEW: Buy volume percentage (bot pattern detection)
        if buy_volume_pct > 85:
            red_flags.append(f"[!!] FAKE BUYING: {buy_volume_pct:.0f}% of trades are buys (manipulation!)")
            risk_score += 35
        elif buy_volume_pct < 15:
            red_flags.append(f"[!!] MASS SELLING: Only {buy_volume_pct:.0f}% buys (dump in progress!)")
            risk_score += 35
        elif buy_volume_pct > 75:
            red_flags.append(f"[!] Suspicious: {buy_volume_pct:.0f}% of trades are buys")
            risk_score += 20

        # Buy/Sell ratio (IMPROVED)
        if buy_sell_ratio > 10:
            red_flags.append(f"[!!] EXTREME BUY PRESSURE: {buy_sell_ratio:.1f}:1 buy/sell (manipulation!)")
            risk_score += 30
        elif buy_sell_ratio > 5:
            red_flags.append(f"[!] Very high buy/sell ratio: {buy_sell_ratio:.1f}:1")
            risk_score += 20
        elif buy_sell_ratio > 0 and buy_sell_ratio < 0.1:
            red_flags.append(f"[!!] DUMPING: {buy_sell_ratio:.2f}:1 buy/sell (mostly sells!)")
            risk_score += 30
        elif buy_sell_ratio > 0 and buy_sell_ratio < 0.3:
            red_flags.append(f"[!] More sells than buys: {buy_sell_ratio:.2f}:1")
            risk_score += 15

        # NEW: Low transaction count with high volume (fake volume)
        if total_txns > 0 and avg_trade_size > market_cap * 0.1:
            red_flags.append(f"[!!] SUSPICIOUS: Average trade size is {(avg_trade_size/market_cap*100):.0f}% of mcap")
            risk_score += 25

        # Volume too low
        if volume_24h < 500 and market_cap > 10000:
            red_flags.append(f"[!] Very low volume: ${volume_24h:.0f} (dead/abandoned?)")
            risk_score += 15
        elif volume_24h == 0 and market_cap > 5000:
            red_flags.append(f"[!!] NO VOLUME: Token appears dead")
            risk_score += 25

        return VolumeAnalysis(
            volume_24h=volume_24h,
            market_cap=market_cap,
            volume_to_mcap_ratio=volume_to_mcap,
            liquidity_to_volume_ratio=liquidity_to_volume,
            buy_sell_ratio=buy_sell_ratio,
            buy_volume_percentage=buy_volume_pct,
            small_trade_percentage=small_trade_pct,
            unique_traders_24h=None,  # Would need to count from transactions
            is_wash_trading=is_wash_trading,
            is_fake_volume=is_fake_volume,
            risk_score=min(risk_score, 100),
            red_flags=red_flags
        )

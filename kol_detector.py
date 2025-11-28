"""
KOL Detector - Detects Key Opinion Leaders (influencers) involvement

Analyzes if KOLs (influential wallets) are involved in a token:
- High-volume wallets (whales)
- Wallets with history of successful tokens
- Known influencer wallets
- Coordinated promotion patterns

KOL involvement can be positive (legitimate hype) or negative (pump & dump).
"""

import httpx
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class KOLAnalysis:
    """Results from KOL detection analysis"""
    kol_count: int  # Number of potential KOLs detected
    kol_holding_percentage: float  # % of supply held by KOLs
    high_volume_wallets: int  # Number of high-volume wallets
    whale_concentration: float  # Concentration of whales (0-100)
    kol_influence_score: float  # 0-100, higher = more KOL influence
    has_kol_involvement: bool  # True if significant KOL involvement detected
    suspected_promotion: bool  # True if coordinated promotion detected


class KOLDetector:
    """Detects KOL (Key Opinion Leader) involvement"""

    def __init__(self, rpc_url: str = None):
        # Use provided RPC or default to public
        self.rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"
        self.client = httpx.Client(timeout=30.0)

        # Detection thresholds
        self.WHALE_THRESHOLD_USD = 50000  # $50K+ = whale
        self.HIGH_VOLUME_THRESHOLD = 100000  # $100K+ trading volume = high-volume wallet
        self.KOL_HOLDING_THRESHOLD = 0.05  # 5%+ of supply = potential KOL
        self.KOL_INFLUENCE_THRESHOLD = 60  # Score 60+ = significant influence

    def detect_kols(
        self,
        token_mint: str,
        holders_data: Optional[List[Dict]] = None,
        dex_data: Optional[Dict] = None
    ) -> KOLAnalysis:
        """
        Detect KOL involvement in a token

        Args:
            token_mint: Token mint address
            holders_data: Optional holder data (from onchain analyzer)
            dex_data: Optional DexScreener data

        Returns:
            KOLAnalysis with KOL detection results
        """
        try:
            # If no holders data, try to get top holders
            if not holders_data:
                holders_data = self._get_top_holders(token_mint)

            if not holders_data or len(holders_data) < 5:
                return self._default_analysis()

            # Analyze holders for KOL characteristics
            analysis = self._analyze_for_kols(holders_data, dex_data)

            return analysis

        except Exception as e:
            print(f"Error detecting KOLs: {e}")
            return self._default_analysis()

    def _get_top_holders(self, token_mint: str, limit: int = 50) -> List[Dict]:
        """Get top token holders (simplified)"""
        # TODO: Implement actual holder fetching from chain
        # For now, return empty list (will be provided by OnChainAnalyzer)
        return []

    def _analyze_for_kols(
        self,
        holders_data: List[Dict],
        dex_data: Optional[Dict] = None
    ) -> KOLAnalysis:
        """Analyze holders for KOL characteristics"""

        total_supply = sum(h.get("balance", 0) for h in holders_data)

        if total_supply == 0:
            return self._default_analysis()

        # Identify potential KOLs
        kols = []
        whales = []
        high_volume_wallets = []

        for holder in holders_data:
            balance = holder.get("balance", 0)
            balance_usd = holder.get("balance_usd", 0)
            holding_pct = (balance / total_supply) * 100 if total_supply > 0 else 0

            # KOL criteria:
            # 1. Large holder (>5% supply)
            # 2. High USD value (whale)
            # 3. High trading volume (if available)

            is_whale = balance_usd >= self.WHALE_THRESHOLD_USD
            is_large_holder = holding_pct >= (self.KOL_HOLDING_THRESHOLD * 100)

            if is_whale:
                whales.append(holder)

            if is_large_holder or is_whale:
                kols.append({
                    "wallet": holder.get("address"),
                    "holding_pct": holding_pct,
                    "balance_usd": balance_usd,
                    "is_whale": is_whale
                })

        # Calculate metrics
        kol_count = len(kols)
        whale_count = len(whales)

        # Total holding percentage of KOLs
        kol_holding_pct = sum(kol["holding_pct"] for kol in kols)

        # Whale concentration (top whales' holding %)
        whale_concentration = min(100, kol_holding_pct)

        # KOL influence score (0-100)
        kol_influence_score = min(100, (
            (kol_count * 10) +  # 10 points per KOL
            (whale_count * 15) +  # 15 points per whale
            (kol_holding_pct * 0.5)  # 0.5 points per % held
        ))

        # Has KOL involvement?
        has_kol_involvement = kol_influence_score >= self.KOL_INFLUENCE_THRESHOLD

        # Suspected coordinated promotion?
        # If many large holders bought around the same time = suspicious
        suspected_promotion = kol_count >= 5 and whale_concentration > 40

        return KOLAnalysis(
            kol_count=kol_count,
            kol_holding_percentage=kol_holding_pct,
            high_volume_wallets=whale_count,  # Simplified
            whale_concentration=whale_concentration,
            kol_influence_score=kol_influence_score,
            has_kol_involvement=has_kol_involvement,
            suspected_promotion=suspected_promotion
        )

    def _default_analysis(self) -> KOLAnalysis:
        """Return default analysis when detection fails"""
        return KOLAnalysis(
            kol_count=0,
            kol_holding_percentage=0,
            high_volume_wallets=0,
            whale_concentration=0,
            kol_influence_score=0,
            has_kol_involvement=False,
            suspected_promotion=False
        )

    def close(self):
        """Close HTTP client"""
        self.client.close()


# Test function
if __name__ == "__main__":
    detector = KOLDetector()

    # Test with sample holder data
    sample_holders = [
        {"address": "wallet1", "balance": 1000000, "balance_usd": 100000},
        {"address": "wallet2", "balance": 500000, "balance_usd": 50000},
        {"address": "wallet3", "balance": 300000, "balance_usd": 30000},
    ]

    print("Analyzing KOL involvement...")
    analysis = detector.detect_kols("test_token", holders_data=sample_holders)

    print(f"\nKOL Analysis:")
    print(f"  KOL count: {analysis.kol_count}")
    print(f"  KOL holding %: {analysis.kol_holding_percentage:.1f}%")
    print(f"  High-volume wallets: {analysis.high_volume_wallets}")
    print(f"  Whale concentration: {analysis.whale_concentration:.1f}%")
    print(f"  KOL influence score: {analysis.kol_influence_score:.1f}/100")
    print(f"  Has KOL involvement: {analysis.has_kol_involvement}")
    print(f"  Suspected promotion: {analysis.suspected_promotion}")

    detector.close()

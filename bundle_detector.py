"""
Bundle Detector - Detects bundled transactions (manipulation indicator)

A "bundle" is when multiple wallets buy in the same block or within seconds.
This is a strong indicator of coordinated manipulation/insider activity.
"""

import httpx
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class BundleAnalysis:
    """Results from bundle detection analysis"""
    bundle_count: int  # Number of bundles detected
    bundled_wallets: int  # Number of wallets involved in bundles
    bundled_volume_usd: float  # Total volume from bundles
    bundle_percentage: float  # % of early buyers in bundles
    largest_bundle_size: int  # Largest bundle size (wallets)
    is_heavily_bundled: bool  # True if >30% of early buyers are bundled
    bundle_score: float  # 0-100, higher = more suspicious


class BundleDetector:
    """Detects bundled transactions on Solana"""

    def __init__(self, rpc_url: str = None):
        # Use provided RPC or default to public
        self.rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"
        self.client = httpx.Client(timeout=30.0)

        # Detection thresholds
        self.SAME_BLOCK_THRESHOLD = 0  # Same slot = bundle
        self.RAPID_BUY_THRESHOLD = 3  # Within 3 seconds = suspicious
        self.HEAVY_BUNDLE_THRESHOLD = 0.3  # >30% bundled = red flag

    def analyze_bundles(self, token_mint: str, creation_timestamp: Optional[int] = None) -> BundleAnalysis:
        """
        Analyze token for bundled transactions

        Args:
            token_mint: Token mint address
            creation_timestamp: Token creation time (to filter early buyers)

        Returns:
            BundleAnalysis with detection results
        """
        try:
            # Get early transactions (first 100)
            transactions = self._get_early_transactions(token_mint, limit=100)

            if not transactions or len(transactions) < 5:
                return self._default_analysis()

            # Group transactions by slot (block)
            slot_groups = self._group_by_slot(transactions)

            # Detect bundles
            bundles = self._detect_bundles(slot_groups)

            # Analyze bundle characteristics
            analysis = self._analyze_bundle_characteristics(bundles, transactions)

            return analysis

        except Exception as e:
            print(f"Error analyzing bundles: {e}")
            return self._default_analysis()

    def _get_early_transactions(self, token_mint: str, limit: int = 100) -> List[Dict]:
        """
        Get early transactions for a token

        Returns list of transactions with: wallet, slot, timestamp, amount
        """
        try:
            # Get token account transactions via Solana RPC
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    token_mint,
                    {"limit": limit}
                ]
            }

            response = self.client.post(self.rpc_url, json=payload)

            if response.status_code != 200:
                return []

            data = response.json()
            signatures = data.get("result", [])

            # Get transaction details
            transactions = []
            for sig_info in signatures[:50]:  # Limit to first 50 to avoid rate limits
                tx_details = self._get_transaction_details(sig_info["signature"])

                if tx_details:
                    transactions.append(tx_details)

            return transactions

        except Exception as e:
            print(f"Error fetching transactions: {e}")
            return []

    def _get_transaction_details(self, signature: str) -> Optional[Dict]:
        """Get transaction details from signature"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [
                    signature,
                    {"encoding": "json", "maxSupportedTransactionVersion": 0}
                ]
            }

            response = self.client.post(self.rpc_url, json=payload)

            if response.status_code != 200:
                return None

            data = response.json()
            result = data.get("result")

            if not result:
                return None

            # Extract relevant info
            slot = result.get("slot")
            block_time = result.get("blockTime")

            # Extract wallet from transaction
            meta = result.get("meta", {})
            transaction = result.get("transaction", {})
            message = transaction.get("message", {})
            account_keys = message.get("accountKeys", [])

            # First account is usually the signer (buyer)
            wallet = account_keys[0] if account_keys else None

            return {
                "signature": signature,
                "wallet": wallet,
                "slot": slot,
                "timestamp": block_time,
                "is_error": meta.get("err") is not None
            }

        except Exception as e:
            return None

    def _group_by_slot(self, transactions: List[Dict]) -> Dict[int, List[Dict]]:
        """Group transactions by slot (block)"""
        slot_groups = defaultdict(list)

        for tx in transactions:
            if tx.get("slot") and not tx.get("is_error"):
                slot_groups[tx["slot"]].append(tx)

        return dict(slot_groups)

    def _detect_bundles(self, slot_groups: Dict[int, List[Dict]]) -> List[Dict]:
        """
        Detect bundles from slot groups

        A bundle is when 2+ different wallets buy in the same slot
        """
        bundles = []

        for slot, transactions in slot_groups.items():
            # Get unique wallets in this slot
            wallets = list(set(tx["wallet"] for tx in transactions if tx.get("wallet")))

            # Bundle detected if 2+ different wallets in same slot
            if len(wallets) >= 2:
                bundles.append({
                    "slot": slot,
                    "wallets": wallets,
                    "size": len(wallets),
                    "transactions": transactions
                })

        return bundles

    def _analyze_bundle_characteristics(self, bundles: List[Dict], all_transactions: List[Dict]) -> BundleAnalysis:
        """Analyze bundle characteristics and calculate scores"""

        if not bundles:
            return self._default_analysis()

        # Count bundled wallets
        bundled_wallets = set()
        for bundle in bundles:
            bundled_wallets.update(bundle["wallets"])

        # Count unique wallets
        all_wallets = set(tx["wallet"] for tx in all_transactions if tx.get("wallet"))

        # Calculate metrics
        bundle_count = len(bundles)
        bundled_wallet_count = len(bundled_wallets)
        total_wallet_count = len(all_wallets)

        bundle_percentage = (bundled_wallet_count / total_wallet_count * 100) if total_wallet_count > 0 else 0

        largest_bundle_size = max(bundle["size"] for bundle in bundles) if bundles else 0

        # Is heavily bundled?
        is_heavily_bundled = bundle_percentage >= (self.HEAVY_BUNDLE_THRESHOLD * 100)

        # Calculate bundle score (0-100, higher = more suspicious)
        bundle_score = min(100, (
            (bundle_percentage * 0.4) +  # 40% weight on percentage
            (largest_bundle_size * 5) +  # 5 points per wallet in largest bundle
            (bundle_count * 2)  # 2 points per bundle detected
        ))

        return BundleAnalysis(
            bundle_count=bundle_count,
            bundled_wallets=bundled_wallet_count,
            bundled_volume_usd=0,  # TODO: Calculate actual volume
            bundle_percentage=bundle_percentage,
            largest_bundle_size=largest_bundle_size,
            is_heavily_bundled=is_heavily_bundled,
            bundle_score=bundle_score
        )

    def _default_analysis(self) -> BundleAnalysis:
        """Return default analysis when detection fails"""
        return BundleAnalysis(
            bundle_count=0,
            bundled_wallets=0,
            bundled_volume_usd=0,
            bundle_percentage=0,
            largest_bundle_size=0,
            is_heavily_bundled=False,
            bundle_score=0
        )

    def close(self):
        """Close HTTP client"""
        self.client.close()


# Test function
if __name__ == "__main__":
    detector = BundleDetector()

    # Test with a token
    test_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC for testing

    print(f"Analyzing bundles for: {test_token}")
    analysis = detector.analyze_bundles(test_token)

    print(f"\nBundle Analysis:")
    print(f"  Bundles detected: {analysis.bundle_count}")
    print(f"  Bundled wallets: {analysis.bundled_wallets}")
    print(f"  Bundle percentage: {analysis.bundle_percentage:.1f}%")
    print(f"  Largest bundle: {analysis.largest_bundle_size} wallets")
    print(f"  Heavily bundled: {analysis.is_heavily_bundled}")
    print(f"  Bundle score: {analysis.bundle_score:.1f}/100")

    detector.close()

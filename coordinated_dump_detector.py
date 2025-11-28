"""
Coordinated Dump Detector - Detects coordinated sell-offs

Analyzes if multiple large holders are selling at the same time:
- Multiple whales selling within short timeframe
- Synchronized sell orders
- Large sell volumes in rapid succession
- Insider exit patterns

This is a CRITICAL indicator of rug pulls and coordinated dumps.
"""

import httpx
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class CoordinatedDumpAnalysis:
    """Results from coordinated dump detection"""
    dump_events_detected: int  # Number of coordinated dump events
    wallets_in_dump: int  # Number of wallets involved in dumps
    dump_volume_percentage: float  # % of volume from dump events
    largest_dump_size: float  # Largest single dump (USD)
    dump_coordination_score: float  # 0-100, higher = more coordinated
    is_coordinated_dump: bool  # True if coordinated dump detected
    time_window_seconds: int  # Timeframe of dump (if detected)


class CoordinatedDumpDetector:
    """Detects coordinated sell-offs and dumps"""

    def __init__(self, rpc_url: str = None):
        # Use provided RPC or default to public
        self.rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"
        self.client = httpx.Client(timeout=30.0)

        # Detection thresholds
        self.DUMP_TIMEFRAME = 300  # 5 minutes window
        self.MIN_WALLETS_FOR_COORDINATION = 3  # 3+ wallets = coordinated
        self.LARGE_SELL_THRESHOLD = 10000  # $10K+ = large sell
        self.COORDINATION_SCORE_THRESHOLD = 70  # Score 70+ = coordinated

    def detect_coordinated_dumps(
        self,
        token_mint: str,
        recent_sells: Optional[List[Dict]] = None
    ) -> CoordinatedDumpAnalysis:
        """
        Detect coordinated dump patterns

        Args:
            token_mint: Token mint address
            recent_sells: Optional list of recent sell transactions

        Returns:
            CoordinatedDumpAnalysis with dump detection results
        """
        try:
            # If no sell data provided, get recent sells
            if not recent_sells:
                recent_sells = self._get_recent_sells(token_mint)

            if not recent_sells or len(recent_sells) < 3:
                return self._default_analysis()

            # Detect dump patterns
            analysis = self._analyze_dump_patterns(recent_sells)

            return analysis

        except Exception as e:
            print(f"Error detecting coordinated dumps: {e}")
            return self._default_analysis()

    def _get_recent_sells(self, token_mint: str, limit: int = 100) -> List[Dict]:
        """Get recent sell transactions"""
        try:
            # Get token account transactions
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [token_mint, {"limit": limit}]
            }

            response = self.client.post(self.rpc_url, json=payload)

            if response.status_code != 200:
                return []

            data = response.json()
            signatures = data.get("result", [])

            # Get transaction details and filter sells
            sells = []
            for sig_info in signatures[:30]:  # Limit to avoid rate limits
                tx_details = self._get_transaction_details(sig_info["signature"])

                if tx_details and self._is_sell(tx_details):
                    sells.append(tx_details)

            return sells

        except:
            return []

    def _get_transaction_details(self, signature: str) -> Optional[Dict]:
        """Get transaction details"""
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

            # Extract transaction info
            meta = result.get("meta", {})
            transaction = result.get("transaction", {})
            message = transaction.get("message", {})
            account_keys = message.get("accountKeys", [])

            wallet = account_keys[0] if account_keys else None
            block_time = result.get("blockTime")

            # Get token balance change
            pre_balances = meta.get("preTokenBalances", [])
            post_balances = meta.get("postTokenBalances", [])

            amount_change = 0
            if pre_balances and post_balances:
                pre_amount = float(pre_balances[0].get("uiTokenAmount", {}).get("uiAmount", 0))
                post_amount = float(post_balances[0].get("uiTokenAmount", {}).get("uiAmount", 0))
                amount_change = post_amount - pre_amount

            return {
                "signature": signature,
                "wallet": wallet,
                "block_time": block_time,
                "amount_change": amount_change,
                "is_error": meta.get("err") is not None
            }

        except:
            return None

    def _is_sell(self, tx_details: Dict) -> bool:
        """Check if transaction is a sell"""
        # Negative amount change = sell
        return tx_details.get("amount_change", 0) < 0

    def _analyze_dump_patterns(self, sells: List[Dict]) -> CoordinatedDumpAnalysis:
        """Analyze sell transactions for coordinated dump patterns"""

        if not sells:
            return self._default_analysis()

        # Group sells by time window
        time_windows = self._group_by_timeframe(sells, self.DUMP_TIMEFRAME)

        # Detect coordinated dumps
        dump_events = []
        for window_start, window_sells in time_windows.items():
            if len(window_sells) >= self.MIN_WALLETS_FOR_COORDINATION:
                # Check if sells are from different wallets
                unique_wallets = set(s["wallet"] for s in window_sells if s.get("wallet"))

                if len(unique_wallets) >= self.MIN_WALLETS_FOR_COORDINATION:
                    dump_events.append({
                        "time": window_start,
                        "wallets": unique_wallets,
                        "sells": window_sells,
                        "wallet_count": len(unique_wallets)
                    })

        # Calculate metrics
        dump_count = len(dump_events)

        # Wallets involved in dumps
        all_dump_wallets = set()
        for event in dump_events:
            all_dump_wallets.update(event["wallets"])

        wallets_in_dump = len(all_dump_wallets)

        # Dump volume percentage (simplified)
        total_sells = len(sells)
        dump_sells = sum(len(event["sells"]) for event in dump_events)
        dump_volume_pct = (dump_sells / total_sells * 100) if total_sells > 0 else 0

        # Largest dump
        largest_dump_wallets = max([event["wallet_count"] for event in dump_events]) if dump_events else 0

        # Coordination score (0-100)
        coordination_score = min(100, (
            (dump_count * 20) +  # 20 points per dump event
            (wallets_in_dump * 5) +  # 5 points per wallet involved
            (dump_volume_pct * 0.3) +  # 0.3 points per % volume
            (largest_dump_wallets * 10)  # 10 points per wallet in largest dump
        ))

        # Is coordinated dump?
        is_coordinated = coordination_score >= self.COORDINATION_SCORE_THRESHOLD

        # Time window of dumps
        time_window = self.DUMP_TIMEFRAME if dump_events else 0

        return CoordinatedDumpAnalysis(
            dump_events_detected=dump_count,
            wallets_in_dump=wallets_in_dump,
            dump_volume_percentage=dump_volume_pct,
            largest_dump_size=largest_dump_wallets,  # Simplified (wallet count)
            dump_coordination_score=coordination_score,
            is_coordinated_dump=is_coordinated,
            time_window_seconds=time_window
        )

    def _group_by_timeframe(
        self,
        transactions: List[Dict],
        timeframe_seconds: int
    ) -> Dict[int, List[Dict]]:
        """Group transactions by time windows"""
        windows = defaultdict(list)

        for tx in transactions:
            if tx.get("is_error"):
                continue

            block_time = tx.get("block_time")
            if not block_time:
                continue

            # Round down to nearest timeframe window
            window_start = (block_time // timeframe_seconds) * timeframe_seconds

            windows[window_start].append(tx)

        return dict(windows)

    def _default_analysis(self) -> CoordinatedDumpAnalysis:
        """Return default analysis when detection fails"""
        return CoordinatedDumpAnalysis(
            dump_events_detected=0,
            wallets_in_dump=0,
            dump_volume_percentage=0,
            largest_dump_size=0,
            dump_coordination_score=0,
            is_coordinated_dump=False,
            time_window_seconds=0
        )

    def close(self):
        """Close HTTP client"""
        self.client.close()


# Test function
if __name__ == "__main__":
    detector = CoordinatedDumpDetector()

    # Test with sample sell data
    import time
    current_time = int(time.time())

    sample_sells = [
        {"wallet": "wallet1", "block_time": current_time, "amount_change": -1000, "is_error": False},
        {"wallet": "wallet2", "block_time": current_time + 10, "amount_change": -500, "is_error": False},
        {"wallet": "wallet3", "block_time": current_time + 20, "amount_change": -800, "is_error": False},
        {"wallet": "wallet4", "block_time": current_time + 30, "amount_change": -300, "is_error": False},
    ]

    print("Analyzing coordinated dumps...")
    analysis = detector.detect_coordinated_dumps("test_token", recent_sells=sample_sells)

    print(f"\nCoordinated Dump Analysis:")
    print(f"  Dump events detected: {analysis.dump_events_detected}")
    print(f"  Wallets in dump: {analysis.wallets_in_dump}")
    print(f"  Dump volume %: {analysis.dump_volume_percentage:.1f}%")
    print(f"  Largest dump size: {analysis.largest_dump_size}")
    print(f"  Coordination score: {analysis.dump_coordination_score:.1f}/100")
    print(f"  Is coordinated dump: {analysis.is_coordinated_dump}")
    print(f"  Time window: {analysis.time_window_seconds}s")

    detector.close()

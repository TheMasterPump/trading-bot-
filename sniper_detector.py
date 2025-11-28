"""
Detect snipers and bundle buyers (insiders)
"""
import httpx
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict
from config import SOLANA_RPC_URL
from helius_api import HeliusAPI


@dataclass
class SniperAnalysis:
    """Results from sniper detection"""
    total_early_buyers: int  # Buyers in first minute
    sniper_count: int  # Buyers in first 10 seconds
    sniper_percentage: float
    instant_snipers: int  # NEW: Buyers in first 3 seconds (EXTREME red flag)
    instant_sniper_percentage: float  # NEW: Percentage of instant snipers
    bundle_transactions: int  # Transactions with multiple buyers
    bundle_wallets: int  # Wallets that bought in bundles
    suspected_insiders: int
    coordinated_buy_detected: bool  # NEW: Multiple wallets buying at exact same time
    wallet_clusters: List[List[str]]  # Groups of wallets with same purchase history
    cluster_count: int  # Number of wallet clusters detected
    cluster_wallets: int  # Total wallets in clusters
    risk_score: int
    red_flags: List[str]
    early_buyers: List[Dict]  # Details of early buyers


class SniperDetector:
    """Detects snipers and bundled buys (insider trading patterns)"""

    def __init__(self, rpc_url: str = SOLANA_RPC_URL):
        self.rpc_url = rpc_url
        self.client = httpx.Client(timeout=60.0)
        self.helius = HeliusAPI()

    def analyze_snipers(self, mint_address: str, token_creation_time: Optional[int] = None) -> SniperAnalysis:
        """
        SIMPLIFIED: Analyze early transactions to detect sniping patterns

        Instead of identifying specific wallets, counts total transactions in early periods
        This works with basic RPC without needing transaction parsing
        """
        try:
            # Get token creation time
            if not token_creation_time:
                token_creation_time = self._get_token_creation_time(mint_address)

            if not token_creation_time:
                return self._empty_analysis("Cannot determine token creation time")

            # Convert to seconds if in milliseconds
            if token_creation_time > 10000000000:
                token_creation_time = token_creation_time // 1000

            # Get all transactions for this token address
            transactions = self._get_token_transactions(mint_address, limit=1000)

            if not transactions:
                return self._empty_analysis("No transaction data available")

            # Count transactions by time period
            instant_txs = 0  # 0-3 seconds
            sniper_txs = 0   # 0-10 seconds
            early_txs = 0    # 0-60 seconds
            total_txs = 0

            timestamps_by_second = {}  # For coordinated detection

            for tx in transactions:
                tx_time = tx.get("blockTime")
                if not tx_time:
                    continue

                # Skip failed transactions
                if tx.get("err"):
                    continue

                total_txs += 1
                time_since_creation = tx_time - token_creation_time

                # Skip transactions before creation or way after
                if time_since_creation < 0:
                    continue

                # Count by time period
                if time_since_creation <= 3:
                    instant_txs += 1
                if time_since_creation <= 10:
                    sniper_txs += 1
                if time_since_creation <= 60:
                    early_txs += 1
                    # Track for coordinated buying
                    second = int(tx_time)
                    timestamps_by_second[second] = timestamps_by_second.get(second, 0) + 1

            # Calculate percentages (of early transactions, not all)
            instant_pct = (instant_txs / early_txs * 100) if early_txs > 0 else 0
            sniper_pct = (sniper_txs / early_txs * 100) if early_txs > 0 else 0
            early_pct = (early_txs / total_txs * 100) if total_txs > 0 else 0

            # Detect coordinated buying (many txs in same second)
            coordinated_buy = False
            max_per_second = max(timestamps_by_second.values()) if timestamps_by_second else 0
            if max_per_second >= 5:
                coordinated_buy = True

            # Determine risk
            red_flags = []
            risk_score = 0

            # Instant sniping (first 3 seconds)
            if instant_pct > 50:
                red_flags.append(f"[!!] EXTREME INSIDER TRADING: {instant_txs} transactions in first 3 seconds ({instant_pct:.0f}%)")
                risk_score += 60
            elif instant_pct > 30:
                red_flags.append(f"[!!] Instant sniping: {instant_txs} transactions in first 3 seconds ({instant_pct:.0f}%)")
                risk_score += 45
            elif instant_txs > 0:
                red_flags.append(f"[!] {instant_txs} transactions in first 3 seconds")
                risk_score += 20

            # Regular sniping (first 10 seconds)
            if sniper_pct > 60:
                red_flags.append(f"[!!] MASSIVE SNIPING: {sniper_txs} transactions in first 10 seconds ({sniper_pct:.0f}%)")
                risk_score += 50
            elif sniper_pct > 40:
                red_flags.append(f"[!!] Heavy sniping: {sniper_txs} transactions in first 10 seconds ({sniper_pct:.0f}%)")
                risk_score += 40
            elif sniper_pct > 25:
                red_flags.append(f"[!] Sniping detected: {sniper_txs} transactions in first 10 seconds ({sniper_pct:.0f}%)")
                risk_score += 25

            # Early trading concentration (first minute)
            if early_pct > 70 and total_txs > 20:
                red_flags.append(f"[!!] SUSPICIOUS: {early_pct:.0f}% of all trading happened in first minute")
                risk_score += 35

            # Coordinated buying
            if coordinated_buy:
                red_flags.append(f"[!!] COORDINATED BUYING: Up to {max_per_second} transactions in same second (bot script!)")
                risk_score += 45

            return SniperAnalysis(
                total_early_buyers=early_txs,  # Actually total early transactions
                sniper_count=sniper_txs,       # Transactions in first 10s
                sniper_percentage=sniper_pct,
                instant_snipers=instant_txs,   # Transactions in first 3s
                instant_sniper_percentage=instant_pct,
                bundle_transactions=0,
                bundle_wallets=0,
                suspected_insiders=instant_txs + sniper_txs,
                coordinated_buy_detected=coordinated_buy,
                wallet_clusters=[],
                cluster_count=0,
                cluster_wallets=0,
                risk_score=min(risk_score, 100),
                red_flags=red_flags,
                early_buyers=[]
            )

        except Exception as e:
            return self._empty_analysis(f"Error: {str(e)}")

    def _empty_analysis(self, message: str) -> SniperAnalysis:
        """Return empty analysis with error message"""
        return SniperAnalysis(
            total_early_buyers=0,
            sniper_count=0,
            sniper_percentage=0,
            instant_snipers=0,
            instant_sniper_percentage=0,
            bundle_transactions=0,
            bundle_wallets=0,
            suspected_insiders=0,
            coordinated_buy_detected=False,
            wallet_clusters=[],
            cluster_count=0,
            cluster_wallets=0,
            risk_score=0,
            red_flags=[f"[!] {message}"],
            early_buyers=[]
        )

    def _get_token_creation_time(self, mint_address: str) -> Optional[int]:
        """Get the timestamp when token was created"""
        try:
            # Get first transaction (token creation)
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    mint_address,
                    {"limit": 1}
                ]
            }

            response = self.client.post(self.rpc_url, json=payload, timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                signatures = data.get("result", [])

                if signatures and len(signatures) > 0:
                    return signatures[0].get("blockTime")

            return None

        except Exception:
            return None

    def _get_token_transactions(self, mint_address: str, limit: int = 1000) -> List[Dict]:
        """Get recent transactions for token"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    mint_address,
                    {"limit": limit}
                ]
            }

            response = self.client.post(self.rpc_url, json=payload, timeout=30.0)

            if response.status_code == 200:
                data = response.json()
                return data.get("result", [])

            return []

        except Exception:
            return []

    def _get_buyers_from_transaction(self, signature: str) -> List[str]:
        """
        Extract buyer addresses from a transaction
        Note: This is simplified - full implementation would parse transaction logs
        """
        try:
            # This would require parsing transaction data
            # For now, return empty list (would need full implementation)
            # Full implementation would use getTransaction and parse the accounts/logs
            return []

        except Exception:
            return []

    def _get_wallet_purchase_history(self, wallet_address: str, limit: int = 10) -> List[str]:
        """
        Get list of tokens purchased by this wallet using Helius
        Returns list of mint addresses
        """
        try:
            # Use Helius to get wallet's token accounts
            token_accounts = self.helius.get_token_accounts(wallet_address)

            # Extract mint addresses from accounts with balance > 0
            mints = []
            for account in token_accounts:
                parsed = account.get("account", {}).get("data", {}).get("parsed", {})
                info = parsed.get("info", {})
                mint = info.get("mint")
                token_amount = info.get("tokenAmount", {})
                ui_amount = token_amount.get("uiAmount", 0)

                # Only include tokens with balance > 0
                if mint and ui_amount and ui_amount > 0:
                    mints.append(mint)

                if len(mints) >= limit:
                    break

            return mints

        except Exception:
            return []

    def _detect_wallet_clusters(self, wallet_addresses: List[str]) -> Tuple[List[List[str]], int]:
        """
        Detect clusters of wallets that have the same purchase history
        Returns: (list of clusters, total wallets in clusters)

        A cluster is a group of 2+ wallets that have bought the same 3+ tokens
        """
        try:
            if len(wallet_addresses) < 2:
                return ([], 0)

            # Get purchase history for each wallet
            wallet_histories = {}

            # Limit to first 15 wallets for performance (API calls can be slow)
            for wallet in wallet_addresses[:15]:
                history = self._get_wallet_purchase_history(wallet, limit=10)
                if len(history) > 0:
                    wallet_histories[wallet] = set(history)

            # Need at least 2 wallets with history to compare
            if len(wallet_histories) < 2:
                return ([], 0)

            # Compare wallets to find clusters
            clusters = []
            processed = set()

            wallets_list = list(wallet_histories.keys())

            for i, wallet1 in enumerate(wallets_list):
                if wallet1 in processed:
                    continue

                cluster = [wallet1]
                history1 = wallet_histories[wallet1]

                # Need at least 3 tokens to form a meaningful cluster
                if len(history1) < 3:
                    continue

                for wallet2 in wallets_list[i+1:]:
                    if wallet2 in processed:
                        continue

                    history2 = wallet_histories[wallet2]

                    # Check overlap (if they have 3+ tokens in common)
                    common_tokens = history1.intersection(history2)

                    # Calculate overlap percentage
                    min_history_len = min(len(history1), len(history2))
                    overlap_pct = len(common_tokens) / min_history_len if min_history_len > 0 else 0

                    # Cluster if they have 3+ tokens in common OR >60% overlap
                    if len(common_tokens) >= 3 or overlap_pct >= 0.6:
                        cluster.append(wallet2)
                        processed.add(wallet2)

                if len(cluster) >= 2:
                    clusters.append(cluster)
                    processed.add(wallet1)

            total_wallets_in_clusters = sum(len(cluster) for cluster in clusters)

            return (clusters, total_wallets_in_clusters)

        except Exception as e:
            return ([], 0)

    def _detect_clusters_by_creator_pattern(self, wallet_addresses: List[str]) -> Tuple[List[List[str]], int]:
        """
        Fallback method: Detect clusters by analyzing if wallets bought from same creators
        This is used when we can't get full transaction history
        """
        try:
            # For now, return empty as this would require additional API calls
            # Full implementation would:
            # 1. For each wallet, get all their token holdings from pump.fun API
            # 2. Get the creator of each token
            # 3. Compare wallets that hold tokens from the same creators

            return ([], 0)

        except Exception:
            return ([], 0)

    def _detect_coordinated_buying(self, transactions: List[Dict]) -> bool:
        """
        Detect if multiple transactions happened at exact same timestamp
        This indicates bot/script buying (coordinated attack)
        """
        if len(transactions) < 3:
            return False

        from collections import Counter

        # Count transactions per timestamp
        timestamps = [tx.get("blockTime") for tx in transactions if tx.get("blockTime")]

        if len(timestamps) < 3:
            return False

        timestamp_counts = Counter(timestamps)

        # If 3+ transactions at exact same timestamp = coordinated
        max_same_time = max(timestamp_counts.values()) if timestamp_counts else 0

        return max_same_time >= 3

    def close(self):
        """Close HTTP clients"""
        self.client.close()
        self.helius.close()

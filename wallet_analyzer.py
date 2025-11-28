"""Detect fresh wallets and sybil attacks (dev's multiple wallets)"""
import httpx
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
from config import SOLANA_RPC_URL


@dataclass
class WalletInfo:
    """Information about a wallet"""
    address: str
    age_days: Optional[int]
    total_transactions: int
    tokens_held: int
    is_fresh: bool
    buys_same_creator: bool
    first_transaction_date: Optional[datetime]


@dataclass
class SybilAnalysis:
    """Results of sybil/fresh wallet analysis"""
    total_holders: int
    fresh_wallet_count: int
    fresh_wallet_percentage: float
    suspected_dev_wallets: int
    wallets_buying_same_creator: int
    batch_created_wallets: int  # Wallets created at similar time
    wallets_created_same_minute: int  # NEW: Wallets created in same minute (VERY suspicious)
    low_activity_wallets: int  # NEW: Wallets with <5 transactions
    never_sold_wallets: int  # NEW: Wallets that never sold anything (bot pattern)
    identical_balance_clusters: int  # NEW: Groups of wallets with identical balances
    risk_score: int
    red_flags: List[str]
    suspicious_wallets: List[WalletInfo]


class WalletAnalyzer:
    """Analyzes wallets for fresh wallet attacks and sybil patterns"""

    def __init__(self, rpc_url: str = SOLANA_RPC_URL):
        self.rpc_url = rpc_url
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://pump.fun/',
            'Origin': 'https://pump.fun'
        }
        self.client = httpx.Client(timeout=60.0, headers=headers, follow_redirects=True)

    def get_wallet_age(self, wallet_address: str) -> Optional[int]:
        """Get wallet age in days by finding first transaction"""
        age_days, _ = self.get_wallet_age_and_timestamp(wallet_address)
        return age_days

    def get_wallet_age_and_timestamp(self, wallet_address: str) -> tuple[Optional[int], Optional[int]]:
        """Get wallet age in days and first transaction timestamp"""
        try:
            print(f"[WALLET AGE] Checking wallet: {wallet_address[:8]}...")

            # Get recent signatures for wallet
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    wallet_address,
                    {"limit": 1000}  # Get up to 1000 transactions
                ]
            }

            response = self.client.post(self.rpc_url, json=payload)
            if response.status_code != 200:
                print(f"[WALLET AGE]  RPC error, status: {response.status_code}")
                return (None, None)

            data = response.json()
            signatures = data.get("result", [])

            if not signatures:
                print(f"[WALLET AGE]  No transactions (brand new wallet)")
                return (0, None)  # Brand new wallet, no transactions

            # Last signature = oldest transaction
            oldest_tx = signatures[-1]
            timestamp = oldest_tx.get("blockTime")

            if timestamp:
                first_tx_date = datetime.fromtimestamp(timestamp)
                age_days = (datetime.now() - first_tx_date).days

                print(f"[WALLET AGE]  First tx: {first_tx_date.strftime('%Y-%m-%d')}")
                print(f"[WALLET AGE]  Age: {age_days} days (total tx: {len(signatures)})")
                print(f"[WALLET AGE]  Is Fresh (<7d)? {age_days < 7}")

                return (age_days, timestamp)

            print(f"[WALLET AGE]  No blockTime in response")
            return (None, None)

        except Exception as e:
            print(f"[WALLET AGE]  ERROR: {e}")
            return (None, None)

    def get_wallet_transaction_count(self, wallet_address: str) -> int:
        """Get total transaction count for wallet"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    wallet_address,
                    {"limit": 1000}
                ]
            }

            response = self.client.post(self.rpc_url, json=payload)
            if response.status_code != 200:
                return 0

            data = response.json()
            signatures = data.get("result", [])
            return len(signatures)

        except Exception:
            return 0

    def check_creator_loyalty(
        self,
        wallet_address: str,
        creator_address: str
    ) -> bool:
        """Check if wallet only buys tokens from same creator"""
        try:
            # This would require checking all token purchases by wallet
            # and seeing if they're all from same creator
            # For now, we'll use pump.fun API if available

            response = self.client.get(
                f"https://frontend-api.pump.fun/coins/user-bought-coins/{wallet_address}",
                timeout=10.0
            )

            if response.status_code != 200:
                return False

            bought_tokens = response.json()

            if len(bought_tokens) < 2:
                return False

            # Check if majority (>80%) are from same creator
            same_creator_count = sum(
                1 for token in bought_tokens
                if token.get("creator") == creator_address
            )

            loyalty_percentage = (same_creator_count / len(bought_tokens)) * 100

            return loyalty_percentage > 80

        except Exception:
            return False

    def analyze_holders(
        self,
        holders: List[Dict],
        creator_address: str,
        mint_address: str
    ) -> SybilAnalysis:
        """Analyze holders for fresh wallets and sybil attacks"""

        total_holders = len(holders)
        fresh_wallets = []
        creation_times = []
        creation_timestamps = []  # NEW: Store exact timestamps
        suspected_dev_wallets = []
        wallets_buying_same_creator = 0
        low_activity_count = 0
        never_sold_count = 0
        wallet_balances = []  # NEW: Track balances for clustering

        red_flags = []
        risk_score = 0

        # Sample top holders for analysis (analyzing all can be slow/expensive)
        holders_to_check = holders[:50]  # Check top 50 holders

        for holder in holders_to_check:
            wallet_addr = holder.get("address") or holder.get("owner")
            if not wallet_addr:
                continue

            # Skip program accounts and known addresses
            if self._is_program_account(wallet_addr):
                continue

            # Get wallet age and creation timestamp
            age_days, first_tx_timestamp = self.get_wallet_age_and_timestamp(wallet_addr)

            # Get transaction count
            tx_count = self.get_wallet_transaction_count(wallet_addr)

            # Determine if fresh wallet
            is_fresh = False
            if age_days is not None:
                if age_days < 7:  # Less than 7 days old
                    is_fresh = True
                    fresh_wallets.append(wallet_addr)

                if age_days < 1:  # Less than 1 day
                    creation_times.append(wallet_addr)
                    if first_tx_timestamp:
                        creation_timestamps.append(first_tx_timestamp)

            # NEW: Check if VERY low activity (bot pattern)
            if tx_count < 5:
                low_activity_count += 1

            # Check if low activity (suspicious)
            is_low_activity = tx_count < 10

            # NEW: Track balance for clustering detection
            holder_balance = holder.get("balance") or holder.get("amount", 0)
            if holder_balance > 0:
                wallet_balances.append(float(holder_balance))

            # Check if only buys from same creator
            buys_same_creator = False
            if creator_address:
                buys_same_creator = self.check_creator_loyalty(
                    wallet_addr,
                    creator_address
                )
                if buys_same_creator:
                    wallets_buying_same_creator += 1
                    suspected_dev_wallets.append(wallet_addr)

            # Store suspicious wallet info
            if is_fresh or buys_same_creator or is_low_activity:
                wallet_info = WalletInfo(
                    address=wallet_addr,
                    age_days=age_days,
                    total_transactions=tx_count,
                    tokens_held=1,  # Would need to calculate
                    is_fresh=is_fresh,
                    buys_same_creator=buys_same_creator,
                    first_transaction_date=None
                )

        # Calculate metrics
        fresh_wallet_count = len(fresh_wallets)
        fresh_wallet_pct = (fresh_wallet_count / len(holders_to_check)) * 100
        batch_created = len(creation_times)

        # NEW: Detect wallets created in same minute (EXTREME red flag)
        same_minute_wallets = self._detect_same_minute_creation(creation_timestamps)

        # NEW: Detect identical balance clusters (bot pattern)
        identical_clusters = self._detect_identical_balances(wallet_balances)

        # Detect red flags
        if fresh_wallet_pct > 50:
            red_flags.append(
                f"[!!] FAKE HOLDERS: {fresh_wallet_pct:.0f}% are fresh wallets (<7 days)"
            )
            risk_score += 45

        elif fresh_wallet_pct > 30:
            red_flags.append(
                f"[!] Many fresh wallets: {fresh_wallet_pct:.0f}% are <7 days old"
            )
            risk_score += 30

        if batch_created > 10:
            red_flags.append(
                f"[!!] BATCH CREATION: {batch_created} wallets created in last 24h (dev wallets!)"
            )
            risk_score += 40

        # NEW: Same minute creation (EXTREME red flag)
        if same_minute_wallets > 5:
            red_flags.append(
                f"[!!] BOT CREATION DETECTED: {same_minute_wallets} wallets created in same minute!"
            )
            risk_score += 50  # HUGE red flag
        elif same_minute_wallets > 2:
            red_flags.append(
                f"[!] Suspicious: {same_minute_wallets} wallets created in same minute"
            )
            risk_score += 30

        if wallets_buying_same_creator > 5:
            red_flags.append(
                f"[!!] SYBIL ATTACK: {wallets_buying_same_creator} wallets only buy this creator's tokens"
            )
            risk_score += 35

        loyalty_pct = (wallets_buying_same_creator / len(holders_to_check)) * 100
        if loyalty_pct > 20:
            red_flags.append(
                f"[!] {loyalty_pct:.0f}% of holders are loyal to this creator (suspicious)"
            )
            risk_score += 25

        # NEW: Low activity wallets
        if low_activity_count > 10:
            red_flags.append(
                f"[!!] {low_activity_count} wallets have <5 transactions (likely bots)"
            )
            risk_score += 30

        # NEW: Identical balance clusters
        if identical_clusters > 3:
            red_flags.append(
                f"[!!] BOT PATTERN: {identical_clusters} clusters of wallets with identical balances"
            )
            risk_score += 35

        # Check for uniform distribution (sign of bot buying)
        if self._detect_uniform_distribution(holders):
            red_flags.append(
                "[!!] UNIFORM DISTRIBUTION: Holders have similar amounts (bot pattern)"
            )
            risk_score += 30

        return SybilAnalysis(
            total_holders=total_holders,
            fresh_wallet_count=fresh_wallet_count,
            fresh_wallet_percentage=fresh_wallet_pct,
            suspected_dev_wallets=len(suspected_dev_wallets),
            wallets_buying_same_creator=wallets_buying_same_creator,
            batch_created_wallets=batch_created,
            wallets_created_same_minute=same_minute_wallets,
            low_activity_wallets=low_activity_count,
            never_sold_wallets=never_sold_count,
            identical_balance_clusters=identical_clusters,
            risk_score=min(risk_score, 100),
            red_flags=red_flags,
            suspicious_wallets=[]  # Could populate this
        )

    def _is_program_account(self, address: str) -> bool:
        """Check if address is a known program account"""
        known_programs = [
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token Program
            "11111111111111111111111111111111",  # System Program
            "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",  # Pump.fun
        ]
        return address in known_programs

    def _detect_uniform_distribution(self, holders: List[Dict]) -> bool:
        """Detect if holders have suspiciously similar amounts (bot pattern)"""
        if len(holders) < 10:
            return False

        # Get balances of top 10-30 holders (skip whales)
        balances = []
        for holder in holders[10:30]:
            balance = holder.get("balance") or holder.get("amount", 0)
            if balance > 0:
                balances.append(float(balance))

        if len(balances) < 5:
            return False

        # Calculate coefficient of variation
        import statistics
        mean = statistics.mean(balances)
        if mean == 0:
            return False

        stdev = statistics.stdev(balances)
        cv = (stdev / mean) * 100

        # If CV < 20%, balances are very similar (suspicious)
        return cv < 20

    def _detect_same_minute_creation(self, timestamps: List[int]) -> int:
        """
        Detect how many wallets were created in the same minute
        This is EXTREMELY suspicious - indicates bot/script creation
        """
        if len(timestamps) < 2:
            return 0

        from collections import Counter

        # Round timestamps to nearest minute
        minutes = [ts // 60 for ts in timestamps]

        # Count wallets per minute
        minute_counts = Counter(minutes)

        # Find maximum wallets created in same minute
        max_same_minute = max(minute_counts.values()) if minute_counts else 0

        # Return count if >1 wallet in same minute
        return max_same_minute if max_same_minute > 1 else 0

    def _detect_identical_balances(self, balances: List[float]) -> int:
        """
        Detect clusters of wallets with identical or near-identical balances
        This indicates bot buying with same amount
        """
        if len(balances) < 5:
            return 0

        from collections import Counter

        # Round balances to avoid floating point issues
        rounded_balances = [round(b, 2) for b in balances if b > 0]

        if len(rounded_balances) < 5:
            return 0

        # Count identical balances
        balance_counts = Counter(rounded_balances)

        # Count how many groups have 3+ identical balances
        clusters = sum(1 for count in balance_counts.values() if count >= 3)

        return clusters

    def close(self):
        """Close HTTP client"""
        self.client.close()

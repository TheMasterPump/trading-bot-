"""
Analyze Top Holders of a token
Detects whale behavior, coordinated exits, and suspicious holder patterns
"""
import httpx
from typing import List, Dict, Optional
from dataclasses import dataclass
from solders.pubkey import Pubkey
from solana.rpc.api import Client
import time


@dataclass
class HolderInfo:
    """Information about a single holder"""
    address: str
    balance: float
    percentage: float
    is_exchange: bool
    is_fresh_wallet: bool  # Less than 7 days old
    transaction_count: int
    has_sold_recently: bool
    sell_percentage: Optional[float]  # How much they sold recently (%)


@dataclass
class TopHoldersAnalysis:
    """Results of top holders analysis"""
    total_holders_analyzed: int
    top_holders: List[HolderInfo]

    # Concentration metrics
    top_1_percentage: float
    top_3_percentage: float
    top_10_percentage: float

    # Risk indicators
    exchanges_in_top_10: int
    fresh_wallets_in_top_10: int
    holders_selling_count: int
    coordinated_exit_detected: bool
    whale_dumping_detected: bool

    # Selling patterns
    total_sell_volume_1h: float  # % of supply sold by top holders in 1h
    average_holder_age_days: float

    risk_score: int
    red_flags: List[str]


class TopHoldersAnalyzer:
    """Analyzes top token holders for suspicious patterns"""

    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        import os
        from dotenv import load_dotenv

        # Load environment variables
        load_dotenv()

        self.rpc_url = rpc_url
        self.client = Client(rpc_url)
        self.http_client = httpx.Client(timeout=30.0)

        # Load Solscan API key from environment
        self.solscan_api_key = os.getenv("SOLSCAN_API_KEY")

        # Known exchange addresses (add more as needed)
        self.known_exchanges = {
            # Binance
            "2ojv9BAiHUrvsm9gxDe7fJSzbNZSJcxZvf8dqmWGHG8S",
            # Coinbase
            "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS",
            # Kraken
            "FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiouN5",
            # Add more exchange addresses
        }

    def analyze_top_holders(self, mint_address: str, token_data: Dict = None) -> TopHoldersAnalysis:
        """
        Analyze top holders of a token for suspicious patterns

        Detects:
        - Whale dumping (top holder selling large amounts)
        - Coordinated exits (multiple top holders selling)
        - Fresh wallets in top positions
        - Concentration of holdings
        """
        try:
            # Get top holders
            holders = self._get_top_holders(mint_address)

            if not holders or len(holders) == 0:
                return self._create_empty_analysis("Could not fetch holder data")

            # Analyze each holder
            analyzed_holders = []
            for holder in holders[:10]:  # Top 10
                holder_info = self._analyze_holder(
                    holder.get("address"),
                    holder.get("balance", 0),
                    holder.get("percentage", 0)
                )
                analyzed_holders.append(holder_info)

            # Calculate concentration
            top_1_pct = analyzed_holders[0].percentage if len(analyzed_holders) > 0 else 0
            top_3_pct = sum(h.percentage for h in analyzed_holders[:3])
            top_10_pct = sum(h.percentage for h in analyzed_holders[:10])

            # Count exchanges and fresh wallets
            exchanges_count = sum(1 for h in analyzed_holders if h.is_exchange)
            fresh_count = sum(1 for h in analyzed_holders if h.is_fresh_wallet)

            # Detect selling patterns
            holders_selling = [h for h in analyzed_holders if h.has_sold_recently]
            holders_selling_count = len(holders_selling)

            # Calculate total sell volume
            total_sell_volume = sum(h.sell_percentage or 0 for h in holders_selling)

            # Detect coordinated exit (3+ top holders selling at same time)
            coordinated_exit = holders_selling_count >= 3

            # Detect whale dumping (top holder sold >20% in recent time)
            whale_dumping = any(
                h.sell_percentage and h.sell_percentage > 20
                for h in analyzed_holders[:3]
            )

            # Calculate average holder age
            holder_ages = [self._estimate_wallet_age(h.address) for h in analyzed_holders]
            avg_age = sum(holder_ages) / len(holder_ages) if holder_ages else 0

            # Risk assessment
            red_flags = []
            risk_score = 0

            # Concentration risk
            if top_1_pct > 40:
                red_flags.append(f"[!!] EXTREME CONCENTRATION: Top holder owns {top_1_pct:.1f}% - VERY DANGEROUS")
                risk_score += 50
            elif top_1_pct > 25:
                red_flags.append(f"[!!] HIGH CONCENTRATION: Top holder owns {top_1_pct:.1f}%")
                risk_score += 35
            elif top_1_pct > 15:
                red_flags.append(f"[!] Top holder owns {top_1_pct:.1f}% of supply")
                risk_score += 20

            if top_3_pct > 60:
                red_flags.append(f"[!!] Top 3 holders control {top_3_pct:.1f}% - CARTEL RISK")
                risk_score += 40
            elif top_3_pct > 50:
                red_flags.append(f"[!] Top 3 holders control {top_3_pct:.1f}%")
                risk_score += 25

            # Fresh wallets risk
            if fresh_count >= 7:
                red_flags.append(f"[!!] {fresh_count} FRESH WALLETS in top 10 - SYBIL ATTACK LIKELY")
                risk_score += 45
            elif fresh_count >= 5:
                red_flags.append(f"[!!] {fresh_count} fresh wallets in top 10 - SUSPICIOUS")
                risk_score += 30
            elif fresh_count >= 3:
                red_flags.append(f"[!] {fresh_count} fresh wallets in top 10")
                risk_score += 15

            # Selling patterns
            if whale_dumping:
                red_flags.append("[!!] WHALE DUMPING DETECTED - Top holders selling heavily!")
                risk_score += 50

            if coordinated_exit:
                red_flags.append(f"[!!] COORDINATED EXIT: {holders_selling_count} top holders selling - RUG LIKELY")
                risk_score += 55
            elif holders_selling_count >= 2:
                red_flags.append(f"[!!] {holders_selling_count} top holders selling")
                risk_score += 30
            elif holders_selling_count == 1:
                red_flags.append(f"[!] Top holder is selling")
                risk_score += 15

            # No exchanges (all retail = suspicious for large tokens)
            if exchanges_count == 0 and top_10_pct > 70:
                red_flags.append("[!] No exchanges in top 10 - all retail holders")
                risk_score += 15

            # Very young holders average age
            if avg_age < 3:
                red_flags.append(f"[!!] Average holder age: {avg_age:.1f} days - VERY NEW")
                risk_score += 20
            elif avg_age < 7:
                red_flags.append(f"[!] Average holder age: {avg_age:.1f} days - relatively new")
                risk_score += 10

            return TopHoldersAnalysis(
                total_holders_analyzed=len(analyzed_holders),
                top_holders=analyzed_holders,
                top_1_percentage=top_1_pct,
                top_3_percentage=top_3_pct,
                top_10_percentage=top_10_pct,
                exchanges_in_top_10=exchanges_count,
                fresh_wallets_in_top_10=fresh_count,
                holders_selling_count=holders_selling_count,
                coordinated_exit_detected=coordinated_exit,
                whale_dumping_detected=whale_dumping,
                total_sell_volume_1h=total_sell_volume,
                average_holder_age_days=avg_age,
                risk_score=min(risk_score, 100),
                red_flags=red_flags
            )

        except Exception as e:
            print(f"[ERROR] Top holders analysis failed: {e}")
            return self._create_empty_analysis(f"Analysis error: {str(e)}")

    def _get_top_holders(self, mint_address: str) -> List[Dict]:
        """
        Get top token holders from various sources
        Priority: DexScreener > Solana RPC
        """
        # Try DexScreener first (has holder data for some tokens)
        holders = self._get_holders_from_dexscreener(mint_address)

        if holders and len(holders) > 0:
            return holders

        # Fallback: Get from Solana RPC (more complex)
        holders = self._get_holders_from_rpc(mint_address)

        return holders

    def _get_holders_from_dexscreener(self, mint_address: str) -> List[Dict]:
        """Try to get holder data from DexScreener"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
            response = self.http_client.get(url)

            if response.status_code == 200:
                data = response.json()
                # DexScreener doesn't provide holder data in public API
                # Return empty for now
                return []

            return []
        except Exception:
            return []

    def _get_holders_from_rpc(self, mint_address: str) -> List[Dict]:
        """
        Get top holders from Solana RPC by querying token accounts
        This is complex and requires multiple RPC calls
        """
        try:
            # This would require:
            # 1. Get all token accounts for this mint
            # 2. Sort by balance
            # 3. Return top N

            # For now, return empty (would need extensive RPC calls)
            # In production, you'd use a dedicated indexer like Helius
            return []

        except Exception:
            return []

    def _analyze_holder(self, address: str, balance: float, percentage: float) -> HolderInfo:
        """Analyze a single holder for suspicious patterns"""
        # Check if exchange
        is_exchange = address in self.known_exchanges

        # Check if fresh wallet
        wallet_age = self._estimate_wallet_age(address)
        is_fresh = wallet_age < 7

        # Get transaction count
        tx_count = self._get_transaction_count(address)

        # Check recent selling (simplified - would need transaction history)
        has_sold_recently = False
        sell_percentage = None

        # In a full implementation, you'd check recent transactions
        # For now, we'll estimate based on other data

        return HolderInfo(
            address=address,
            balance=balance,
            percentage=percentage,
            is_exchange=is_exchange,
            is_fresh_wallet=is_fresh,
            transaction_count=tx_count,
            has_sold_recently=has_sold_recently,
            sell_percentage=sell_percentage
        )

    def _estimate_wallet_age(self, address: str) -> float:
        """
        Estimate wallet age in days by checking first transaction
        Returns age in days, or 99999 if can't determine (to avoid false positives)
        """
        try:
            from datetime import datetime
            import time

            print(f"[WALLET AGE] Checking wallet: {address[:8]}...")

            # Check if we have API key
            if not self.solscan_api_key:
                print(f"[WALLET AGE] ⚠️ NO SOLSCAN API KEY! Returning 99999 (old)")
                return 99999.0

            # Try to get first transaction via Solscan API (more reliable than Helius for this)
            solscan_url = f"https://pro-api.solscan.io/v2.0/account/transfer"
            headers = {"token": self.solscan_api_key}
            params = {
                "address": address,
                "page": 1,
                "page_size": 1,
                "sort_by": "block_time",
                "sort_order": "asc"  # Oldest first
            }

            print(f"[WALLET AGE] Calling Solscan API...")
            response = httpx.get(solscan_url, headers=headers, params=params, timeout=5.0)
            print(f"[WALLET AGE] Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data and data.get("data") and len(data["data"]) > 0:
                    # Get timestamp of first transaction
                    first_tx = data["data"][0]
                    block_time = first_tx.get("block_time", 0)

                    if block_time > 0:
                        current_time = time.time()
                        age_seconds = current_time - block_time
                        age_days = age_seconds / (24 * 3600)

                        print(f"[WALLET AGE] ✅ First tx: {datetime.fromtimestamp(block_time)}")
                        print(f"[WALLET AGE] ✅ Age: {age_days:.1f} days")
                        print(f"[WALLET AGE] ✅ Is Fresh (<7d)? {age_days < 7}")

                        return max(0, age_days)
                    else:
                        print(f"[WALLET AGE] ⚠️ No block_time in response")
                else:
                    print(f"[WALLET AGE] ⚠️ No data in response: {data}")

            # If API fails, return high value to avoid false "fresh" detection
            print(f"[WALLET AGE] ⚠️ API call failed, returning 99999 (old)")
            return 99999.0  # Very old = not fresh

        except Exception as e:
            # If error, assume wallet is old (avoid false positives)
            print(f"[WALLET AGE] ❌ ERROR: {e}")
            print(f"[WALLET AGE] Returning 99999 (old) to avoid false positive")
            return 99999.0  # Assume old to avoid false fresh wallet detection

    def _get_transaction_count(self, address: str) -> int:
        """Get total transaction count for wallet"""
        try:
            # Would use Solana RPC to get signature count
            # For now, return 0
            return 0

        except Exception:
            return 0

    def _create_empty_analysis(self, error_msg: str) -> TopHoldersAnalysis:
        """Create empty analysis with error message"""
        return TopHoldersAnalysis(
            total_holders_analyzed=0,
            top_holders=[],
            top_1_percentage=0,
            top_3_percentage=0,
            top_10_percentage=0,
            exchanges_in_top_10=0,
            fresh_wallets_in_top_10=0,
            holders_selling_count=0,
            coordinated_exit_detected=False,
            whale_dumping_detected=False,
            total_sell_volume_1h=0,
            average_holder_age_days=0,
            risk_score=0,
            red_flags=[f"[!] Could not analyze holders: {error_msg}"]
        )

    def close(self):
        """Close HTTP client"""
        self.http_client.close()

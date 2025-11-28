"""
Analyze token holders directly from Solana blockchain
Used when API data is not available
"""
import httpx
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from config import SOLANA_RPC_URL


@dataclass
class OnChainHolderAnalysis:
    """Results from on-chain holder analysis"""
    total_holders: int
    top_holder_percentage: float
    top_3_percentage: float  # NEW: Top 3 concentration
    top_10_percentage: float
    holders: List[Dict]
    fresh_wallet_count_top10: int  # Fresh wallets in top 10
    fresh_wallet_count_top20: int  # Fresh wallets in top 20

    # NEW: Exchange and whale detection
    exchanges_in_top_10: int  # Known exchanges in top 10
    whale_dumping_detected: bool  # Top holders selling heavily
    coordinated_exit_detected: bool  # Multiple top holders selling
    holders_selling_count: int  # How many top holders are selling
    average_holder_age_days: float  # Average age of top 10 holders

    # NEW: Risk assessment
    risk_score: int  # 0-100
    red_flags: List[str]  # Specific warnings

    can_analyze: bool
    error_message: Optional[str] = None


class OnChainAnalyzer:
    """Analyzes token data directly from Solana blockchain"""

    def __init__(self, rpc_url: str = SOLANA_RPC_URL):
        self.rpc_url = rpc_url
        self.client = httpx.Client(timeout=60.0)

        # Known exchange addresses (for identifying legitimate large holders)
        self.known_exchanges = {
            # Binance
            "2ojv9BAiHUrvsm9gxDe7fJSzbNZSJcxZvf8dqmWGHG8S",
            "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9",
            # Coinbase
            "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS",
            "GJRs4FwHtemZ5ZE9x3FNvJ8TMwitKTh21yxdRPqn7npE",
            # Kraken
            "FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiouN5",
            # Raydium Program
            "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1",
            # Pump.fun Program
            "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
            # Add more known addresses as needed
        }

    def get_token_holders(self, mint_address: str) -> OnChainHolderAnalysis:
        """
        Get token holders directly from blockchain
        This is slower but works when APIs are blocked
        """
        try:
            print(f"[ONCHAIN] Getting holders for {mint_address[:8]}...")

            # Get token supply first
            print(f"[ONCHAIN] Step 1: Getting token supply...")
            supply = self._get_token_supply(mint_address)
            print(f"[ONCHAIN] Supply: {supply}")

            if not supply:
                print(f"[ONCHAIN]  Cannot fetch token supply!")
                return OnChainHolderAnalysis(
                    total_holders=0,
                    top_holder_percentage=0,
                    top_3_percentage=0,
                    top_10_percentage=0,
                    holders=[],
                    fresh_wallet_count_top10=0,
                    fresh_wallet_count_top20=0,
                    exchanges_in_top_10=0,
                    whale_dumping_detected=False,
                    coordinated_exit_detected=False,
                    holders_selling_count=0,
                    average_holder_age_days=0,
                    risk_score=0,
                    red_flags=[],
                    can_analyze=False,
                    error_message="Cannot fetch token supply"
                )

            total_supply = supply

            # Get all token accounts for this mint
            print(f"[ONCHAIN] Step 2: Getting token accounts via getProgramAccounts...")
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getProgramAccounts",
                "params": [
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # SPL Token Program
                    {
                        "encoding": "jsonParsed",
                        "filters": [
                            {
                                "dataSize": 165  # Token account size
                            },
                            {
                                "memcmp": {
                                    "offset": 0,
                                    "bytes": mint_address
                                }
                            }
                        ]
                    }
                ]
            }

            response = self.client.post(self.rpc_url, json=payload, timeout=30.0)
            print(f"[ONCHAIN] Response status: {response.status_code}")

            if response.status_code != 200:
                print(f"[ONCHAIN]  RPC error: {response.status_code}")
                return OnChainHolderAnalysis(
                    total_holders=0,
                    top_holder_percentage=0,
                    top_3_percentage=0,
                    top_10_percentage=0,
                    holders=[],
                    fresh_wallet_count_top10=0,
                    fresh_wallet_count_top20=0,
                    exchanges_in_top_10=0,
                    whale_dumping_detected=False,
                    coordinated_exit_detected=False,
                    holders_selling_count=0,
                    average_holder_age_days=0,
                    risk_score=0,
                    red_flags=[],
                    can_analyze=False,
                    error_message=f"RPC error: {response.status_code}"
                )

            data = response.json()
            accounts = data.get("result", [])
            print(f"[ONCHAIN] Found {len(accounts)} token accounts")

            # Parse holders
            holders = []
            for account in accounts:
                try:
                    parsed = account["account"]["data"]["parsed"]
                    info = parsed["info"]
                    balance = float(info["tokenAmount"]["uiAmount"] or 0)

                    if balance > 0:
                        percentage = (balance / total_supply) * 100 if total_supply > 0 else 0
                        holders.append({
                            "address": info["owner"],
                            "balance": balance,
                            "percentage": percentage
                        })
                except (KeyError, ValueError, TypeError):
                    continue

            # Sort by balance descending
            holders.sort(key=lambda x: x["balance"], reverse=True)
            print(f"[ONCHAIN] Parsed {len(holders)} holders with balance > 0")

            # Calculate metrics
            total_holders = len(holders)
            top_holder_pct = holders[0]["percentage"] if holders else 0
            top_3_pct = sum(h["percentage"] for h in holders[:3])  # NEW
            top_10_pct = sum(h["percentage"] for h in holders[:10])

            # Enhanced analysis of top 20 holders (changed from 10 for better coverage, but still fast)
            fresh_count_top10 = 0
            fresh_count_top20 = 0
            exchanges_count = 0
            holders_selling = []
            holder_ages = []

            # Check top 20 for fresh wallets (faster than 50, more accurate than 10)
            for i, holder in enumerate(holders[:20]):
                address = holder["address"]

                # Check wallet age (with reduced timeout for speed)
                wallet_age = self._get_wallet_age_quick(address)
                holder["age_days"] = wallet_age
                holder["is_fresh"] = wallet_age is not None and wallet_age < 7

                if holder["is_fresh"]:
                    if i < 10:
                        fresh_count_top10 += 1
                    fresh_count_top20 += 1

                if wallet_age is not None:
                    holder_ages.append(wallet_age)
                else:
                    holder_ages.append(30)  # Default to 30 days if unknown

                # Check if exchange (only top 10 for speed)
                if i < 10:
                    is_exchange = self._is_exchange(address)
                    holder["is_exchange"] = is_exchange
                    if is_exchange:
                        exchanges_count += 1

                    # Check for selling patterns (for top 5 only - avoid too many RPC calls)
                    if i < 5:
                        has_sold, sell_pct = self._detect_selling_patterns(address, mint_address)
                        holder["has_sold_recently"] = has_sold
                        holder["sell_percentage"] = sell_pct

                        if has_sold:
                            holders_selling.append(holder)
                    else:
                        holder["has_sold_recently"] = False
                        holder["sell_percentage"] = None

            # NEW: Calculate selling metrics
            holders_selling_count = len(holders_selling)
            coordinated_exit = holders_selling_count >= 3  # 3+ top holders selling = coordinated
            whale_dumping = any(h.get("has_sold_recently", False) for h in holders[:3])  # Top 3 selling

            # NEW: Calculate average holder age
            avg_age = sum(holder_ages) / len(holder_ages) if holder_ages else 30.0

            # NEW: Calculate risk score and generate red flags
            risk_score, red_flags = self._calculate_risk_and_flags(
                holders=holders[:10],
                top_1_pct=top_holder_pct,
                top_3_pct=top_3_pct,
                top_10_pct=top_10_pct,
                exchanges_count=exchanges_count,
                fresh_count=fresh_count_top10,
                holders_selling_count=holders_selling_count,
                coordinated_exit=coordinated_exit,
                whale_dumping=whale_dumping,
                avg_age=avg_age
            )

            return OnChainHolderAnalysis(
                total_holders=total_holders,
                top_holder_percentage=top_holder_pct,
                top_3_percentage=top_3_pct,  # NEW
                top_10_percentage=top_10_pct,
                holders=holders[:20],  # Return top 20
                fresh_wallet_count_top10=fresh_count_top10,
                fresh_wallet_count_top20=fresh_count_top20,
                exchanges_in_top_10=exchanges_count,  # NEW
                whale_dumping_detected=whale_dumping,  # NEW
                coordinated_exit_detected=coordinated_exit,  # NEW
                holders_selling_count=holders_selling_count,  # NEW
                average_holder_age_days=avg_age,  # NEW
                risk_score=risk_score,  # NEW
                red_flags=red_flags,  # NEW
                can_analyze=True
            )

        except Exception as e:
            print(f"[ONCHAIN] EXCEPTION: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return OnChainHolderAnalysis(
                total_holders=0,
                top_holder_percentage=0,
                top_3_percentage=0,  # NEW
                top_10_percentage=0,
                holders=[],
                fresh_wallet_count_top10=0,
                    fresh_wallet_count_top20=0,
                exchanges_in_top_10=0,  # NEW
                whale_dumping_detected=False,  # NEW
                coordinated_exit_detected=False,  # NEW
                holders_selling_count=0,  # NEW
                average_holder_age_days=0,  # NEW
                risk_score=0,  # NEW
                red_flags=[],  # NEW
                can_analyze=False,
                error_message=str(e)
            )

    def _get_wallet_age_quick(self, wallet_address: str) -> Optional[int]:
        """Get wallet age quickly (limited signatures)"""
        try:
            from datetime import datetime

            print(f"[WALLET AGE QUICK] Checking wallet: {wallet_address[:8]}...")

            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    wallet_address,
                    {"limit": 1000}  # INCREASED to 1000 for better accuracy
                ]
            }

            response = self.client.post(self.rpc_url, json=payload, timeout=2.0)  # Reduced from 5s for speed

            if response.status_code == 200:
                data = response.json()
                signatures = data.get("result", [])

                if not signatures:
                    print(f"[WALLET AGE QUICK]  No transactions (brand new)")
                    return 0  # No transactions = very new wallet

                # Get oldest transaction from this sample
                oldest_tx = signatures[-1]
                timestamp = oldest_tx.get("blockTime")

                if timestamp:
                    first_tx_date = datetime.fromtimestamp(timestamp)
                    age_days = (datetime.now() - first_tx_date).days

                    print(f"[WALLET AGE QUICK]  TX count: {len(signatures)}")
                    print(f"[WALLET AGE QUICK]  Oldest tx: {first_tx_date.strftime('%Y-%m-%d')}")
                    print(f"[WALLET AGE QUICK]  Age: {age_days} days")
                    print(f"[WALLET AGE QUICK]  Is Fresh (<7d)? {age_days < 7}")

                    # WARNING if we hit the limit (might not be the real first tx)
                    if len(signatures) >= 1000:
                        print(f"[WALLET AGE QUICK]  WARNING: Wallet has 1000+ tx, age might be underestimated!")

                    return age_days

            print(f"[WALLET AGE QUICK]  RPC error or no blockTime")
            return None

        except Exception as e:
            print(f"[WALLET AGE QUICK]  ERROR: {e}")
            return None

    def _get_token_supply(self, mint_address: str) -> Optional[float]:
        """Get total token supply"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenSupply",
                "params": [mint_address]
            }

            response = self.client.post(self.rpc_url, json=payload, timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                supply = data.get("result", {}).get("value", {}).get("uiAmount")
                return float(supply) if supply else None

            return None

        except Exception:
            return None

    def _is_exchange(self, address: str) -> bool:
        """Check if address is a known exchange"""
        return address in self.known_exchanges

    def _detect_selling_patterns(self, address: str, mint_address: str) -> Tuple[bool, Optional[float]]:
        """
        Detect if a holder has been selling recently
        Returns: (has_sold_recently, sell_percentage)

        NOTE: This requires recent transaction history analysis
        For now, returns simplified estimation
        """
        try:
            # Get recent signatures for this address
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    address,
                    {"limit": 20}  # Last 20 transactions
                ]
            }

            response = self.client.post(self.rpc_url, json=payload, timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                signatures = data.get("result", [])

                # Check for recent transactions (last 1 hour)
                import time
                current_time = time.time()
                recent_txs = [
                    sig for sig in signatures
                    if sig.get("blockTime") and (current_time - sig.get("blockTime")) < 3600
                ]

                # If there are recent transactions, it might indicate selling
                # (simplified - full implementation would parse transaction details)
                if len(recent_txs) >= 3:
                    # Multiple transactions in last hour = possible selling
                    return True, None  # Can't determine exact % without parsing tx details

            return False, None

        except Exception:
            return False, None

    def _calculate_risk_and_flags(
        self,
        holders: List[Dict],
        top_1_pct: float,
        top_3_pct: float,
        top_10_pct: float,
        exchanges_count: int,
        fresh_count: int,
        holders_selling_count: int,
        coordinated_exit: bool,
        whale_dumping: bool,
        avg_age: float
    ) -> Tuple[int, List[str]]:
        """Calculate risk score and generate red flags"""
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

        # No exchanges (all retail = suspicious for concentrated tokens)
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

        return min(risk_score, 100), red_flags

    def close(self):
        """Close HTTP client"""
        self.client.close()

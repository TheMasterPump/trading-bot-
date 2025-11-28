"""
Buy/Sell Ratio Analyzer - Analyzes buy vs sell pressure

Analyzes recent transactions to calculate:
- Buy/sell ratio (% buys vs % sells)
- Unique buyers vs sellers
- Average buy/sell size
- Sell pressure score

This is CRITICAL for detecting sell-offs and dumps.
"""

import httpx
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class BuySellAnalysis:
    """Results from buy/sell ratio analysis"""
    buy_percentage: float  # % of transactions that are buys
    sell_percentage: float  # % of transactions that are sells
    buy_sell_ratio: float  # Ratio of buys to sells
    unique_buyers: int  # Number of unique buyers
    unique_sellers: int  # Number of unique sellers
    avg_buy_size_usd: float  # Average buy size in USD
    avg_sell_size_usd: float  # Average sell size in USD
    sell_pressure_score: float  # 0-100, higher = more sell pressure
    is_heavy_selloff: bool  # True if >70% sells
    total_transactions_analyzed: int  # Total txs analyzed


class BuySellRatioAnalyzer:
    """Analyzes buy/sell ratio from recent transactions"""

    def __init__(self, rpc_url: str = None):
        # Use provided RPC or default to public
        self.rpc_url = rpc_url or "https://api.mainnet-beta.solana.com"
        self.client = httpx.Client(timeout=30.0)

        # Detection thresholds
        self.HEAVY_SELLOFF_THRESHOLD = 0.7  # 70% sells = heavy selloff
        self.SAMPLE_SIZE = 100  # Number of recent transactions to analyze

    def analyze_buysell_ratio(self, token_mint: str, dex_data: Optional[Dict] = None) -> BuySellAnalysis:
        """
        Analyze buy/sell ratio for a token

        Args:
            token_mint: Token mint address
            dex_data: Optional DexScreener data for price context

        Returns:
            BuySellAnalysis with buy/sell metrics
        """
        try:
            # Get recent transactions
            transactions = self._get_recent_transactions(token_mint, limit=self.SAMPLE_SIZE)

            if not transactions or len(transactions) < 5:
                return self._default_analysis()

            # Classify transactions as buys or sells
            classified = self._classify_transactions(transactions, dex_data)

            # Analyze buy/sell characteristics
            analysis = self._analyze_buysell(classified)

            return analysis

        except Exception as e:
            print(f"Error analyzing buy/sell ratio: {e}")
            return self._default_analysis()

    def _get_recent_transactions(self, token_mint: str, limit: int = 100) -> List[Dict]:
        """Get recent transactions for a token"""
        try:
            # Get token account signatures
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

            # Get transaction details (sample to avoid rate limits)
            transactions = []
            for sig_info in signatures[:50]:  # Limit to 50 to avoid rate limits
                tx_details = self._get_transaction_details(sig_info["signature"])

                if tx_details:
                    transactions.append(tx_details)

            return transactions

        except Exception as e:
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

            # Get wallet (signer)
            wallet = account_keys[0] if account_keys else None

            # Get token balance changes to determine buy/sell
            post_balances = meta.get("postTokenBalances", [])
            pre_balances = meta.get("preTokenBalances", [])

            return {
                "signature": signature,
                "wallet": wallet,
                "pre_balances": pre_balances,
                "post_balances": post_balances,
                "block_time": result.get("blockTime"),
                "is_error": meta.get("err") is not None
            }

        except:
            return None

    def _classify_transactions(
        self,
        transactions: List[Dict],
        dex_data: Optional[Dict] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Classify transactions as buys or sells

        Returns: (buys, sells) tuple
        """
        buys = []
        sells = []

        for tx in transactions:
            if tx.get("is_error"):
                continue

            # Determine if buy or sell based on token balance change
            classification = self._classify_transaction(tx)

            if classification == "buy":
                buys.append(tx)
            elif classification == "sell":
                sells.append(tx)

        return buys, sells

    def _classify_transaction(self, tx: Dict) -> str:
        """
        Classify a single transaction as buy, sell, or unknown

        Logic: If wallet's token balance increased = buy, decreased = sell
        """
        try:
            pre_balances = tx.get("pre_balances", [])
            post_balances = tx.get("post_balances", [])

            # Compare first token account balance
            if pre_balances and post_balances:
                pre_amount = float(pre_balances[0].get("uiTokenAmount", {}).get("uiAmount", 0))
                post_amount = float(post_balances[0].get("uiTokenAmount", {}).get("uiAmount", 0))

                if post_amount > pre_amount:
                    return "buy"
                elif post_amount < pre_amount:
                    return "sell"

            return "unknown"

        except:
            return "unknown"

    def _analyze_buysell(self, classified: Tuple[List[Dict], List[Dict]]) -> BuySellAnalysis:
        """Analyze buy/sell characteristics"""

        buys, sells = classified

        total_txs = len(buys) + len(sells)

        if total_txs == 0:
            return self._default_analysis()

        # Calculate percentages
        buy_percentage = (len(buys) / total_txs) * 100
        sell_percentage = (len(sells) / total_txs) * 100

        # Buy/sell ratio
        buy_sell_ratio = len(buys) / len(sells) if sells else float('inf')

        # Count unique wallets
        unique_buyers = len(set(tx["wallet"] for tx in buys if tx.get("wallet")))
        unique_sellers = len(set(tx["wallet"] for tx in sells if tx.get("wallet")))

        # Average sizes (simplified - would need price data for USD)
        avg_buy_size_usd = 0  # TODO: Calculate with price data
        avg_sell_size_usd = 0  # TODO: Calculate with price data

        # Sell pressure score (0-100, higher = more sell pressure)
        sell_pressure_score = min(100, (
            (sell_percentage * 0.6) +  # 60% weight on sell percentage
            ((unique_sellers / max(unique_buyers, 1)) * 20) +  # 20% weight on seller/buyer ratio
            (20 if buy_sell_ratio < 0.5 else 0)  # 20 points if more than 2x sellers
        ))

        # Is heavy selloff?
        is_heavy_selloff = sell_percentage >= (self.HEAVY_SELLOFF_THRESHOLD * 100)

        return BuySellAnalysis(
            buy_percentage=buy_percentage,
            sell_percentage=sell_percentage,
            buy_sell_ratio=buy_sell_ratio,
            unique_buyers=unique_buyers,
            unique_sellers=unique_sellers,
            avg_buy_size_usd=avg_buy_size_usd,
            avg_sell_size_usd=avg_sell_size_usd,
            sell_pressure_score=sell_pressure_score,
            is_heavy_selloff=is_heavy_selloff,
            total_transactions_analyzed=total_txs
        )

    def _default_analysis(self) -> BuySellAnalysis:
        """Return default analysis when detection fails"""
        return BuySellAnalysis(
            buy_percentage=50,  # Assume 50/50 if unknown
            sell_percentage=50,
            buy_sell_ratio=1.0,
            unique_buyers=0,
            unique_sellers=0,
            avg_buy_size_usd=0,
            avg_sell_size_usd=0,
            sell_pressure_score=50,  # Neutral
            is_heavy_selloff=False,
            total_transactions_analyzed=0
        )

    def close(self):
        """Close HTTP client"""
        self.client.close()


# Test function
if __name__ == "__main__":
    analyzer = BuySellRatioAnalyzer()

    # Test with a token
    test_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC for testing

    print(f"Analyzing buy/sell ratio for: {test_token}")
    analysis = analyzer.analyze_buysell_ratio(test_token)

    print(f"\nBuy/Sell Analysis:")
    print(f"  Buy %: {analysis.buy_percentage:.1f}%")
    print(f"  Sell %: {analysis.sell_percentage:.1f}%")
    print(f"  Buy/Sell Ratio: {analysis.buy_sell_ratio:.2f}")
    print(f"  Unique buyers: {analysis.unique_buyers}")
    print(f"  Unique sellers: {analysis.unique_sellers}")
    print(f"  Sell pressure score: {analysis.sell_pressure_score:.1f}/100")
    print(f"  Heavy selloff: {analysis.is_heavy_selloff}")
    print(f"  Transactions analyzed: {analysis.total_transactions_analyzed}")

    analyzer.close()

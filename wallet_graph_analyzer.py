"""
Wallet Graph Analyzer - Detects connections between insider wallets

Analyzes relationships between wallets to detect:
- SOL transfers between wallets
- Shared token holdings
- Coordinated trading patterns
- Insider network clusters

This is a CRITICAL indicator of manipulation.
"""

import httpx
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class WalletGraphAnalysis:
    """Results from wallet graph analysis"""
    connected_wallet_pairs: int  # Number of connected wallet pairs
    network_size: int  # Size of largest connected network
    total_connections: int  # Total connections detected
    connection_score: float  # 0-100, higher = more suspicious
    has_insider_network: bool  # True if significant network detected
    avg_connections_per_wallet: float  # Average connections per wallet
    connection_types: Dict[str, int]  # Types of connections (SOL, tokens, etc.)


class WalletGraphAnalyzer:
    """Analyzes wallet connections to detect insider networks"""

    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        self.rpc_url = rpc_url
        self.client = httpx.Client(timeout=30.0)

        # Detection thresholds
        self.MIN_SOL_TRANSFER = 0.01  # Minimum SOL transfer to consider
        self.INSIDER_NETWORK_THRESHOLD = 3  # 3+ connected wallets = insider network
        self.HIGH_CONNECTION_SCORE = 70  # Score threshold for high suspicion

    def analyze_wallet_connections(
        self,
        token_mint: str,
        early_wallets: Optional[List[str]] = None
    ) -> WalletGraphAnalysis:
        """
        Analyze connections between early buyer wallets

        Args:
            token_mint: Token mint address
            early_wallets: List of early buyer wallet addresses (top 20-50)

        Returns:
            WalletGraphAnalysis with connection details
        """
        try:
            # If no wallets provided, get early buyers
            if not early_wallets:
                early_wallets = self._get_early_buyers(token_mint, limit=50)

            if not early_wallets or len(early_wallets) < 2:
                return self._default_analysis()

            # Build connection graph
            connections = self._build_connection_graph(early_wallets)

            # Analyze graph characteristics
            analysis = self._analyze_graph(connections, early_wallets)

            return analysis

        except Exception as e:
            print(f"Error analyzing wallet connections: {e}")
            return self._default_analysis()

    def _get_early_buyers(self, token_mint: str, limit: int = 50) -> List[str]:
        """Get list of early buyers for a token"""
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

            # Extract unique wallets from transactions
            wallets = set()
            for sig_info in signatures[:30]:  # Limit to avoid rate limits
                tx_details = self._get_transaction_details(sig_info["signature"])

                if tx_details and tx_details.get("wallet"):
                    wallets.add(tx_details["wallet"])

            return list(wallets)

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

            # Extract wallet
            transaction = result.get("transaction", {})
            message = transaction.get("message", {})
            account_keys = message.get("accountKeys", [])

            wallet = account_keys[0] if account_keys else None

            return {"wallet": wallet}

        except:
            return None

    def _build_connection_graph(self, wallets: List[str]) -> Dict[str, Set[str]]:
        """
        Build graph of connections between wallets

        Returns: Dict mapping wallet -> set of connected wallets
        """
        graph = defaultdict(set)

        # Check each pair of wallets for connections
        for i, wallet_a in enumerate(wallets):
            for wallet_b in wallets[i+1:]:
                # Check if wallets are connected
                connection_types = self._check_wallet_connection(wallet_a, wallet_b)

                if connection_types:
                    graph[wallet_a].add(wallet_b)
                    graph[wallet_b].add(wallet_a)

        return dict(graph)

    def _check_wallet_connection(self, wallet_a: str, wallet_b: str) -> List[str]:
        """
        Check if two wallets are connected

        Returns list of connection types: ['sol_transfer', 'shared_tokens', etc.]
        """
        connections = []

        # Check for SOL transfers between wallets
        if self._has_sol_transfer(wallet_a, wallet_b):
            connections.append('sol_transfer')

        # TODO: Add more connection checks:
        # - Shared token holdings (same obscure tokens)
        # - Transaction timing patterns (same second/block)
        # - Shared NFT holdings

        return connections

    def _has_sol_transfer(self, wallet_a: str, wallet_b: str) -> bool:
        """Check if wallet_a has transferred SOL to wallet_b (or vice versa)"""
        try:
            # Get recent transactions for wallet_a
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [wallet_a, {"limit": 100}]
            }

            response = self.client.post(self.rpc_url, json=payload)

            if response.status_code != 200:
                return False

            data = response.json()
            signatures = data.get("result", [])

            # Check each transaction for transfers to wallet_b
            for sig_info in signatures[:20]:  # Limit checks
                tx_details = self._get_full_transaction(sig_info["signature"])

                if tx_details and self._involves_both_wallets(tx_details, wallet_a, wallet_b):
                    return True

            return False

        except:
            return False

    def _get_full_transaction(self, signature: str) -> Optional[Dict]:
        """Get full transaction details"""
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
            return data.get("result")

        except:
            return None

    def _involves_both_wallets(self, tx_details: Dict, wallet_a: str, wallet_b: str) -> bool:
        """Check if transaction involves both wallets"""
        try:
            transaction = tx_details.get("transaction", {})
            message = transaction.get("message", {})
            account_keys = message.get("accountKeys", [])

            # Check if both wallets are in the transaction
            return wallet_a in account_keys and wallet_b in account_keys

        except:
            return False

    def _analyze_graph(self, graph: Dict[str, Set[str]], all_wallets: List[str]) -> WalletGraphAnalysis:
        """Analyze graph characteristics"""

        if not graph:
            return self._default_analysis()

        # Count connections
        total_connections = sum(len(connections) for connections in graph.values()) // 2
        connected_pairs = total_connections
        unique_connected_wallets = len(graph)

        # Find largest connected component (network)
        network_size = self._find_largest_network(graph)

        # Calculate average connections per wallet
        avg_connections = total_connections / len(all_wallets) if all_wallets else 0

        # Detect insider network
        has_insider_network = network_size >= self.INSIDER_NETWORK_THRESHOLD

        # Calculate connection score (0-100)
        connection_score = min(100, (
            (network_size * 15) +  # 15 points per wallet in largest network
            (connected_pairs * 10) +  # 10 points per connected pair
            (avg_connections * 20)  # 20 points per avg connection
        ))

        # Count connection types
        connection_types = {
            "sol_transfers": total_connections,  # Simplified for now
            "shared_tokens": 0,  # TODO: Implement
            "coordinated_timing": 0  # TODO: Implement
        }

        return WalletGraphAnalysis(
            connected_wallet_pairs=connected_pairs,
            network_size=network_size,
            total_connections=total_connections,
            connection_score=connection_score,
            has_insider_network=has_insider_network,
            avg_connections_per_wallet=avg_connections,
            connection_types=connection_types
        )

    def _find_largest_network(self, graph: Dict[str, Set[str]]) -> int:
        """Find size of largest connected component using DFS"""
        visited = set()
        max_network_size = 0

        def dfs(node: str) -> int:
            """Depth-first search to find connected component size"""
            if node in visited:
                return 0

            visited.add(node)
            size = 1

            for neighbor in graph.get(node, []):
                size += dfs(neighbor)

            return size

        # Find all connected components
        for wallet in graph:
            if wallet not in visited:
                network_size = dfs(wallet)
                max_network_size = max(max_network_size, network_size)

        return max_network_size

    def _default_analysis(self) -> WalletGraphAnalysis:
        """Return default analysis when detection fails"""
        return WalletGraphAnalysis(
            connected_wallet_pairs=0,
            network_size=0,
            total_connections=0,
            connection_score=0,
            has_insider_network=False,
            avg_connections_per_wallet=0,
            connection_types={}
        )

    def close(self):
        """Close HTTP client"""
        self.client.close()


# Test function
if __name__ == "__main__":
    analyzer = WalletGraphAnalyzer()

    # Test with a token
    test_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC for testing

    print(f"Analyzing wallet connections for: {test_token}")
    analysis = analyzer.analyze_wallet_connections(test_token)

    print(f"\nWallet Graph Analysis:")
    print(f"  Connected pairs: {analysis.connected_wallet_pairs}")
    print(f"  Network size: {analysis.network_size} wallets")
    print(f"  Total connections: {analysis.total_connections}")
    print(f"  Avg connections/wallet: {analysis.avg_connections_per_wallet:.2f}")
    print(f"  Insider network detected: {analysis.has_insider_network}")
    print(f"  Connection score: {analysis.connection_score:.1f}/100")

    analyzer.close()

"""
Helius Enhanced APIs for transaction parsing
https://docs.helius.dev/
"""
import httpx
from typing import List, Dict, Optional
from config import HELIUS_API_KEY


class HeliusAPI:
    """Wrapper for Helius Enhanced Transactions APIs"""

    def __init__(self):
        if not HELIUS_API_KEY:
            print("[Helius] Warning: No API key configured")

        self.api_key = HELIUS_API_KEY
        self.base_url = "https://api.helius.xyz/v0"
        self.client = httpx.Client(timeout=60.0)

    def get_parsed_transactions(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        """
        Get parsed transaction history for a wallet
        Returns human-readable transaction data
        """
        try:
            url = f"{self.base_url}/addresses/{wallet_address}/transactions"
            params = {
                "api-key": self.api_key,
                "limit": limit
            }

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"[Helius] transactions API returned {response.status_code}")
                return []

        except Exception as e:
            print(f"[Helius] Error fetching transactions: {e}")
            return []

    def parse_transaction(self, signature: str) -> Optional[Dict]:
        """
        Parse a single transaction by signature
        Returns detailed parsed transaction data
        """
        try:
            url = f"{self.base_url}/transactions"
            params = {"api-key": self.api_key}
            payload = {"transactions": [signature]}

            response = self.client.post(url, params=params, json=payload)

            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
            else:
                return None

        except Exception:
            return None

    def get_token_accounts(self, wallet_address: str) -> List[Dict]:
        """
        Get all SPL token accounts for a wallet
        """
        try:
            # Use Solana RPC through Helius
            from config import SOLANA_RPC_URL
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    wallet_address,
                    {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                    {"encoding": "jsonParsed"}
                ]
            }

            response = self.client.post(SOLANA_RPC_URL, json=payload)

            if response.status_code == 200:
                data = response.json()
                return data.get("result", {}).get("value", [])

            return []

        except Exception:
            return []

    def get_account_info(self, wallet_address: str) -> Optional[Dict]:
        """
        Get account info including creation time
        """
        try:
            from config import SOLANA_RPC_URL
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    wallet_address,
                    {"encoding": "jsonParsed"}
                ]
            }

            response = self.client.post(SOLANA_RPC_URL, json=payload)

            if response.status_code == 200:
                data = response.json()
                return data.get("result")

            return None

        except Exception:
            return None

    def get_signatures_for_address(self, address: str, limit: int = 1000) -> List[Dict]:
        """
        Get transaction signatures for an address
        """
        try:
            from config import SOLANA_RPC_URL
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    address,
                    {"limit": limit}
                ]
            }

            response = self.client.post(SOLANA_RPC_URL, json=payload)

            if response.status_code == 200:
                data = response.json()
                return data.get("result", [])

            return []

        except Exception:
            return []

    def close(self):
        """Close HTTP client"""
        self.client.close()

"""
Solscan API wrapper for fetching Solana blockchain data
"""
import httpx
from typing import List, Dict, Optional
from config import SOLSCAN_API_KEY

# Solscan has TWO APIs:
# 1. Public API (api.solscan.io) - Protected by Cloudflare, blocked for bots
# 2. Pro API (pro-api.solscan.io) - No Cloudflare, requires paid plan

# Try Pro API first if API key is provided
SOLSCAN_PRO_API_URL = "https://pro-api.solscan.io/v1.0"
SOLSCAN_PUBLIC_API_URL = "https://api.solscan.io"


class SolscanAPI:
    """Wrapper for Solscan API calls"""

    def __init__(self):
        headers = {
            'Accept': 'application/json',
        }

        if SOLSCAN_API_KEY:
            # Use Pro API if API key is provided
            headers['token'] = SOLSCAN_API_KEY
            base_url = SOLSCAN_PRO_API_URL
            print(f"[Solscan] Using Pro API with key: {SOLSCAN_API_KEY[:20]}...")
        else:
            # Use public API (will likely be blocked by Cloudflare)
            base_url = SOLSCAN_PUBLIC_API_URL
            print("[Solscan] No API key, using public API (may be blocked)")

        self.client = httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=30.0
        )
        self.use_pro_api = bool(SOLSCAN_API_KEY)

    def get_token_holders(self, token_address: str, limit: int = 100) -> List[Dict]:
        """
        Get token holders from Solscan
        Returns list of {address, amount, decimals, owner, rank}
        """
        try:
            if self.use_pro_api:
                # Pro API v1.0 endpoint
                endpoint = f"/token/holders"
            else:
                # Public API endpoint
                endpoint = f"/token/holders"

            response = self.client.get(
                endpoint,
                params={
                    "tokenAddress": token_address,  # Pro API uses tokenAddress
                    "page": 1,
                    "page_size": limit
                }
            )

            if response.status_code == 200:
                data = response.json()
                # Pro API returns different structure
                if self.use_pro_api:
                    return data.get("data", [])
                else:
                    return data.get("data", [])
            else:
                print(f"[Solscan] holders API returned {response.status_code}: {response.text[:200]}")

            return []

        except Exception as e:
            print(f"Error fetching holders from Solscan: {e}")
            return []

    def get_token_meta(self, token_address: str) -> Optional[Dict]:
        """
        Get token metadata from Solscan
        Returns token info including name, symbol, supply, etc.
        """
        try:
            response = self.client.get(f"/token/meta", params={"token": token_address})

            if response.status_code == 200:
                return response.json()

            return None

        except Exception:
            return None

    def get_account_transactions(self, wallet_address: str, limit: int = 50) -> List[Dict]:
        """
        Get transaction history for a wallet
        Returns list of transaction signatures with metadata
        """
        try:
            response = self.client.get(
                f"/account/transaction",
                params={
                    "address": wallet_address,
                    "limit": limit
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])

            return []

        except Exception:
            return []

    def get_token_transfer(self, token_address: str, limit: int = 100) -> List[Dict]:
        """
        Get recent token transfers
        Useful for finding early buyers and snipers
        """
        try:
            response = self.client.get(
                f"/token/transfer",
                params={
                    "address": token_address,
                    "limit": limit,
                    "offset": 0
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])

            return []

        except Exception:
            return []

    def get_account_tokens(self, wallet_address: str) -> List[Dict]:
        """
        Get all SPL tokens held by a wallet
        Returns list of token accounts with balances
        """
        try:
            response = self.client.get(
                f"/account/token-accounts",
                params={"address": wallet_address}
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])

            return []

        except Exception:
            return []

    def get_account_info(self, wallet_address: str) -> Optional[Dict]:
        """
        Get wallet account info including creation time
        """
        try:
            response = self.client.get(
                f"/account",
                params={"address": wallet_address}
            )

            if response.status_code == 200:
                return response.json()

            return None

        except Exception:
            return None

    def close(self):
        """Close HTTP client"""
        self.client.close()

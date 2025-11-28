"""
InsightX API wrapper for advanced token analysis
https://docs.insightx.network/
"""
import httpx
from typing import Optional, Dict
from config import INSIGHTX_API_KEY


class InsightXAPI:
    """Wrapper for InsightX Bubblemaps and Scanner APIs"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or INSIGHTX_API_KEY
        self.base_url = "https://api.insightx.network"
        self.client = httpx.Client(timeout=30.0)

    def get_distribution_metrics(self, token_address: str, network: str = "sol") -> Optional[Dict]:
        """
        Get token holder distribution metrics
        Returns: {gini, hhi, nakamoto, top_10_holder_concentration}

        - gini: Gini coefficient (0-1, higher = more inequality)
        - hhi: Herfindahl-Hirschman Index (concentration metric)
        - nakamoto: Minimum number of wallets to control 51%
        - top_10_holder_concentration: % held by top 10 holders
        """
        try:
            url = f"{self.base_url}/bubblemaps/v1/{network}/{token_address}/metrics/distribution"
            headers = {
                "X-API-Key": self.api_key,
                "accept": "application/json"
            }

            response = self.client.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()

            return None

        except Exception:
            return None

    def scan_token(self, token_address: str, network: str = "sol") -> Optional[Dict]:
        """
        Run comprehensive security scan on token
        Returns: {network, token, extensions, results}

        Includes:
        - Token metadata (name, symbol, logo, decimals, supply)
        - Social links
        - Token age
        - Extensions (Token2022, Metaplex)
        - Security analysis results
        """
        try:
            url = f"{self.base_url}/scanner/v1/tokens/{network}/{token_address}"
            headers = {
                "X-API-Key": self.api_key,
                "accept": "application/json"
            }

            response = self.client.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()

            return None

        except Exception:
            return None

    def get_sniper_metrics(self, token_address: str, network: str = "sol") -> Optional[Dict]:
        """
        Get sniper analysis metrics (if available)
        May return 404 for newer tokens
        """
        try:
            url = f"{self.base_url}/bubblemaps/v1/{network}/{token_address}/metrics/sniper"
            headers = {
                "X-API-Key": self.api_key,
                "accept": "application/json"
            }

            response = self.client.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()

            return None

        except Exception:
            return None

    def get_cluster_metrics(self, token_address: str, network: str = "sol") -> Optional[Dict]:
        """
        Get wallet cluster analysis (if available)
        May return 404 for newer tokens
        """
        try:
            url = f"{self.base_url}/bubblemaps/v1/{network}/{token_address}/metrics/cluster"
            headers = {
                "X-API-Key": self.api_key,
                "accept": "application/json"
            }

            response = self.client.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()

            return None

        except Exception:
            return None

    def close(self):
        """Close HTTP client"""
        self.client.close()

"""
VENOM Token Verifier
Checks if a Solana wallet holds the required amount of VENOM tokens
"""

import requests
from typing import Optional, Dict
from venom_config import (
    VENOM_TOKEN_ADDRESS,
    REQUIRED_VENOM_BALANCE,
    VENOM_DECIMALS,
    ENABLE_VENOM_VERIFICATION
)

class VenomTokenVerifier:
    """Verify VENOM token holdings on Solana blockchain"""

    def __init__(self):
        # Solana RPC endpoints (you can add more for redundancy)
        self.rpc_endpoints = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-api.projectserum.com",
        ]
        self.current_endpoint = 0

    def get_rpc_endpoint(self) -> str:
        """Get current RPC endpoint"""
        return self.rpc_endpoints[self.current_endpoint]

    def rotate_endpoint(self):
        """Switch to next RPC endpoint if current one fails"""
        self.current_endpoint = (self.current_endpoint + 1) % len(self.rpc_endpoints)

    def check_venom_balance(self, wallet_address: str) -> Dict:
        """
        Check if wallet has required VENOM tokens

        Args:
            wallet_address: Solana wallet public key

        Returns:
            dict with keys:
                - has_access: bool
                - balance: float (actual token balance)
                - required: float (required balance)
                - error: str (if any error occurred)
        """
        # If verification is disabled, grant access
        if not ENABLE_VENOM_VERIFICATION:
            return {
                'has_access': True,
                'balance': REQUIRED_VENOM_BALANCE,
                'required': REQUIRED_VENOM_BALANCE,
                'error': None,
                'verification_disabled': True
            }

        # Check if token address is configured
        if VENOM_TOKEN_ADDRESS == "PASTE_YOUR_VENOM_TOKEN_CONTRACT_ADDRESS_HERE":
            return {
                'has_access': True,  # Grant access if not configured yet
                'balance': 0,
                'required': REQUIRED_VENOM_BALANCE,
                'error': 'Token contract not configured',
                'token_not_configured': True
            }

        try:
            # Get token accounts for this wallet
            balance = self._get_token_balance(wallet_address)

            if balance is None:
                return {
                    'has_access': False,
                    'balance': 0,
                    'required': REQUIRED_VENOM_BALANCE,
                    'error': 'Could not fetch balance'
                }

            has_access = balance >= REQUIRED_VENOM_BALANCE

            return {
                'has_access': has_access,
                'balance': balance,
                'required': REQUIRED_VENOM_BALANCE,
                'error': None
            }

        except Exception as e:
            print(f"[VENOM] Error checking balance: {str(e)}")
            return {
                'has_access': False,
                'balance': 0,
                'required': REQUIRED_VENOM_BALANCE,
                'error': str(e)
            }

    def _get_token_balance(self, wallet_address: str) -> Optional[float]:
        """
        Fetch actual token balance from Solana blockchain

        Args:
            wallet_address: Solana wallet public key

        Returns:
            Token balance as float, or None if error
        """
        max_retries = len(self.rpc_endpoints)

        for attempt in range(max_retries):
            try:
                endpoint = self.get_rpc_endpoint()

                # Solana RPC call to get token accounts by owner
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        wallet_address,
                        {
                            "mint": VENOM_TOKEN_ADDRESS
                        },
                        {
                            "encoding": "jsonParsed"
                        }
                    ]
                }

                response = requests.post(
                    endpoint,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )

                if response.status_code != 200:
                    raise Exception(f"RPC returned status {response.status_code}")

                data = response.json()

                if 'error' in data:
                    raise Exception(f"RPC error: {data['error']}")

                # Parse the response
                result = data.get('result', {})
                token_accounts = result.get('value', [])

                if not token_accounts:
                    # No token account = 0 balance
                    return 0.0

                # Get balance from first token account (should only be one per mint)
                account_info = token_accounts[0]['account']['data']['parsed']['info']
                token_amount = account_info['tokenAmount']

                # Convert from raw amount to actual tokens
                balance = float(token_amount['uiAmount'])

                print(f"[VENOM] Wallet {wallet_address[:8]}... has {balance:,.0f} VENOM tokens")

                return balance

            except Exception as e:
                print(f"[VENOM] RPC attempt {attempt + 1} failed: {str(e)}")
                self.rotate_endpoint()

                if attempt == max_retries - 1:
                    # All endpoints failed
                    return None

        return None

    def format_balance_message(self, result: Dict) -> str:
        """Format a user-friendly message about their VENOM balance"""

        if result.get('verification_disabled'):
            return "⚠️ Token verification is currently disabled (testing mode)"

        if result.get('token_not_configured'):
            return "⚠️ VENOM token contract not yet configured"

        if result.get('error'):
            return f"❌ Error checking balance: {result['error']}"

        balance = result['balance']
        required = result['required']
        has_access = result['has_access']

        if has_access:
            return f"✅ Access granted! You have {balance:,.0f} VENOM tokens (required: {required:,.0f})"
        else:
            shortage = required - balance
            return f"❌ Access denied. You have {balance:,.0f} VENOM tokens. You need {shortage:,.0f} more tokens."


# Global verifier instance
_verifier = VenomTokenVerifier()

def check_venom_access(wallet_address: str) -> Dict:
    """
    Convenience function to check VENOM token access

    Args:
        wallet_address: Solana wallet public key

    Returns:
        Dictionary with verification results
    """
    return _verifier.check_venom_balance(wallet_address)

def format_venom_message(result: Dict) -> str:
    """
    Format verification result as user message

    Args:
        result: Result from check_venom_access()

    Returns:
        Formatted message string
    """
    return _verifier.format_balance_message(result)

"""Check mint and freeze authority for tokens"""
import httpx
from typing import Optional
from dataclasses import dataclass
from typing import List


@dataclass
class AuthorityAnalysis:
    """Results of authority analysis"""
    mint_authority_renounced: bool
    freeze_authority_renounced: bool
    mint_authority_address: Optional[str]
    freeze_authority_address: Optional[str]
    risk_score: int
    red_flags: List[str]


class AuthorityChecker:
    """Checks token mint and freeze authority"""

    def __init__(self):
        self.rpc_url = "https://api.mainnet-beta.solana.com"
        self.client = httpx.Client(timeout=10.0)

    def check_authority(self, mint_address: str) -> AuthorityAnalysis:
        """Check if mint and freeze authorities are renounced"""
        
        red_flags = []
        risk_score = 0

        try:
            # Get mint account info via RPC
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    mint_address,
                    {"encoding": "jsonParsed"}
                ]
            }

            response = self.client.post(self.rpc_url, json=payload)
            
            if response.status_code != 200:
                return AuthorityAnalysis(
                    mint_authority_renounced=False,
                    freeze_authority_renounced=False,
                    mint_authority_address=None,
                    freeze_authority_address=None,
                    risk_score=50,
                    red_flags=["[!] Could not verify authority status"]
                )

            data = response.json()
            
            if "result" not in data or not data["result"]:
                return AuthorityAnalysis(
                    mint_authority_renounced=False,
                    freeze_authority_renounced=False,
                    mint_authority_address=None,
                    freeze_authority_address=None,
                    risk_score=50,
                    red_flags=["[!] Token data not found"]
                )

            # Parse mint info
            parsed_info = data["result"]["value"]["data"]["parsed"]["info"]
            
            mint_authority = parsed_info.get("mintAuthority")
            freeze_authority = parsed_info.get("freezeAuthority")

            # Check mint authority
            mint_renounced = mint_authority is None
            if not mint_renounced:
                red_flags.append("[!!] DANGER: Mint Authority NOT renounced - Dev can create infinite tokens!")
                risk_score += 40

            # Check freeze authority  
            freeze_renounced = freeze_authority is None
            if not freeze_renounced:
                red_flags.append("[!!] DANGER: Freeze Authority NOT renounced - Dev can freeze wallets!")
                risk_score += 35

            return AuthorityAnalysis(
                mint_authority_renounced=mint_renounced,
                freeze_authority_renounced=freeze_renounced,
                mint_authority_address=mint_authority,
                freeze_authority_address=freeze_authority,
                risk_score=min(risk_score, 100),
                red_flags=red_flags
            )

        except Exception as e:
            print(f"Authority check error: {e}")
            return AuthorityAnalysis(
                mint_authority_renounced=False,
                freeze_authority_renounced=False,
                mint_authority_address=None,
                freeze_authority_address=None,
                risk_score=50,
                red_flags=["[!] Could not verify authority (RPC error)"]
            )

    def close(self):
        """Close HTTP client"""
        self.client.close()

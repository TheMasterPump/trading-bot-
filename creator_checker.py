"""Check creator wallet history for previous rug pulls"""
import httpx
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from config import SOLANA_RPC_URL, PUMPFUN_PROGRAM_ID


@dataclass
class TokenHistory:
    """Information about a token created by wallet"""
    mint: str
    name: Optional[str]
    symbol: Optional[str]
    created_at: Optional[datetime]
    final_market_cap: float
    still_active: bool
    potential_rug: bool


@dataclass
class CreatorAnalysis:
    """Results of creator wallet analysis"""
    total_tokens_created: int
    potential_rugs: int
    active_tokens: int
    rug_percentage: float
    risk_score: int
    red_flags: List[str]
    token_history: List[TokenHistory]


class CreatorChecker:
    """Analyzes creator wallet history"""

    def __init__(self, rpc_url: str = SOLANA_RPC_URL):
        self.rpc_url = rpc_url
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://pump.fun/',
            'Origin': 'https://pump.fun'
        }
        self.client = httpx.Client(timeout=30.0, headers=headers, follow_redirects=True)

    def get_creator_tokens(self, creator_address: str) -> List[Dict]:
        """Get all tokens created by a wallet address"""
        # This would need to query pump.fun API or parse transaction history
        # For now, this is a placeholder that would integrate with pump.fun API
        try:
            # You would replace this with actual pump.fun API call
            # Example: https://api.pump.fun/creator/{creator_address}/tokens
            response = self.client.get(
                f"https://frontend-api.pump.fun/coins/user-created-coins/{creator_address}",
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []

    def analyze_creator(self, creator_address: str) -> CreatorAnalysis:
        """Analyze creator's token history for rug patterns"""

        tokens = self.get_creator_tokens(creator_address)
        token_history = []
        potential_rugs = 0
        active_tokens = 0
        red_flags = []

        for token_data in tokens:
            try:
                # Parse token info
                mint = token_data.get("mint", "")
                name = token_data.get("name")
                symbol = token_data.get("symbol")
                market_cap = token_data.get("usd_market_cap", 0)

                # Check if token looks abandoned/rugged
                is_rug = self._is_potential_rug(token_data)
                is_active = market_cap > 1000  # Consider active if > $1k mcap

                if is_rug:
                    potential_rugs += 1
                if is_active:
                    active_tokens += 1

                token_history.append(TokenHistory(
                    mint=mint,
                    name=name,
                    symbol=symbol,
                    created_at=None,  # Would parse from timestamp
                    final_market_cap=market_cap,
                    still_active=is_active,
                    potential_rug=is_rug
                ))
            except Exception:
                continue

        # Calculate metrics
        total_tokens = len(token_history)
        rug_percentage = (potential_rugs / total_tokens * 100) if total_tokens > 0 else 0

        # Determine risk score (ENHANCED)
        risk_score = 0

        # Serial launcher detection (progressively worse)
        if total_tokens > 15:
            red_flags.append(f"[!!] EXTREME SERIAL LAUNCHER: Created {total_tokens} tokens - LIKELY SCAMMER")
            risk_score += 30
        elif total_tokens > 10:
            red_flags.append(f"[!] SERIAL LAUNCHER: Created {total_tokens} tokens")
            risk_score += 20
        elif total_tokens > 5:
            red_flags.append(f"[!] Multiple launches: {total_tokens} tokens created")
            risk_score += 10

        # Rug percentage detection (CRITICAL - most important signal)
        if rug_percentage > 80:
            red_flags.append(
                f"[!!] SERIAL RUGGER CONFIRMED: {rug_percentage:.0f}% of previous tokens RUGGED - DO NOT BUY!"
            )
            risk_score += 70  # Almost automatic fail
        elif rug_percentage > 60:
            red_flags.append(
                f"[!!] KNOWN RUGGER: {rug_percentage:.0f}% of previous tokens rugged"
            )
            risk_score += 55
        elif rug_percentage > 40:
            red_flags.append(
                f"[!!] HIGH RUG RATE: {rug_percentage:.0f}% of tokens failed"
            )
            risk_score += 40
        elif rug_percentage > 25:
            red_flags.append(
                f"[!] SUSPICIOUS HISTORY: {rug_percentage:.0f}% of tokens failed"
            )
            risk_score += 25

        # All previous tokens dead (EXTREME red flag)
        if total_tokens > 10 and active_tokens == 0:
            red_flags.append("[!!] ALL PREVIOUS TOKENS DEAD - SERIAL RUGGER - EXTREME DANGER")
            risk_score += 50
        elif total_tokens > 5 and active_tokens == 0:
            red_flags.append("[!!] ALL PREVIOUS TOKENS FAILED - AVOID!")
            risk_score += 40

        # Very few successful tokens (indicator of incompetence or scam)
        if total_tokens > 3 and active_tokens == 0:
            red_flags.append("[!] No successful previous tokens - high risk creator")
            risk_score += 20

        return CreatorAnalysis(
            total_tokens_created=total_tokens,
            potential_rugs=potential_rugs,
            active_tokens=active_tokens,
            rug_percentage=rug_percentage,
            risk_score=min(risk_score, 100),
            red_flags=red_flags,
            token_history=token_history[:10]  # Return latest 10
        )

    def _is_potential_rug(self, token_data: Dict) -> bool:
        """Determine if a token appears to be a rug pull"""
        market_cap = token_data.get("usd_market_cap", 0)

        # Get additional metrics if available
        liquidity = token_data.get("liquidity", 0)
        complete = token_data.get("complete", False)
        raydium_pool = token_data.get("raydium_pool")

        # CRITICAL: Token went to near-zero (definite rug)
        if market_cap < 100:
            return True

        # STRONG INDICATOR: Very low market cap + no liquidity
        if market_cap < 500 and liquidity < 100:
            return True

        # STRONG INDICATOR: Bonding curve complete but token crashed
        # (means it reached Raydium but then got dumped)
        if complete and raydium_pool and market_cap < 1000:
            return True

        # MODERATE INDICATOR: Token stuck in bonding curve with very low mcap
        # (creator likely abandoned it)
        if not complete and market_cap < 300:
            return True

        # Check for pump & dump pattern (if price change data available)
        price_change = token_data.get("priceChange", {})
        if isinstance(price_change, dict):
            change_24h = price_change.get("h24", 0)
            # If token lost >90% value in 24h, likely dumped
            if change_24h < -90:
                return True

        return False

    def close(self):
        """Close HTTP client"""
        self.client.close()

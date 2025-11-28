"""Check social media presence and legitimacy"""
import httpx
import re
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class SocialAnalysis:
    """Results of social media analysis"""
    has_website: bool
    has_twitter: bool
    has_telegram: bool
    twitter_followers: Optional[int]
    telegram_members: Optional[int]
    description_quality: str  # "good", "suspicious", "empty"
    risk_score: int
    red_flags: List[str]


class SocialChecker:
    """Analyzes social media presence"""

    def __init__(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://pump.fun/',
            'Origin': 'https://pump.fun'
        }
        self.client = httpx.Client(timeout=30.0, headers=headers, follow_redirects=True)

    def analyze_social(self, token_data: dict) -> SocialAnalysis:
        """Analyze social media presence from token metadata"""

        # Extract social links from token data
        twitter = token_data.get("twitter")
        telegram = token_data.get("telegram")
        website = token_data.get("website")
        description = token_data.get("description", "")

        # Update the has_* flags
        has_twitter = bool(twitter and twitter.strip())
        has_telegram = bool(telegram and telegram.strip())
        has_website = bool(website and website.strip())

        red_flags = []
        risk_score = 0

        # Social presence check - no alerts (not critical for rug detection)
        # User requested removal: social media alerts are not important for scam detection

        # Analyze description quality
        desc_quality = self._analyze_description(description)
        if desc_quality == "empty":
            red_flags.append("[!] No description provided")
            risk_score += 15
        elif desc_quality == "suspicious":
            red_flags.append("[!] Suspicious description (generic/scammy)")
            risk_score += 20

        # Check for suspicious URLs
        if self._has_suspicious_urls(website, twitter, telegram):
            red_flags.append("[!!] SUSPICIOUS URLs detected (possible phishing)")
            risk_score += 30

        return SocialAnalysis(
            has_website=has_website,
            has_twitter=has_twitter,
            has_telegram=has_telegram,
            twitter_followers=None,  # Would need Twitter API
            telegram_members=None,   # Would need Telegram API
            description_quality=desc_quality,
            risk_score=min(risk_score, 100),
            red_flags=red_flags
        )

    def _analyze_description(self, description: str) -> str:
        """Analyze description quality"""
        if not description or len(description.strip()) < 10:
            return "empty"

        # Check for common scam phrases
        scam_keywords = [
            "moon", "100x", "guaranteed", "get rich",
            "quick profit", "easy money", "lambo", "🚀🚀🚀",
            "next bitcoin", "millionaire"
        ]

        desc_lower = description.lower()
        scam_count = sum(1 for keyword in scam_keywords if keyword in desc_lower)

        if scam_count >= 3:
            return "suspicious"

        # Check if description has substance (not just emojis/hype)
        words = re.findall(r'\w+', description)
        if len(words) < 5:
            return "suspicious"

        return "good"

    def _has_suspicious_urls(
        self,
        website: Optional[str],
        twitter: Optional[str],
        telegram: Optional[str]
    ) -> bool:
        """Check for suspicious or malformed URLs"""

        urls = [u for u in [website, twitter, telegram] if u]

        for url in urls:
            # Check for common phishing patterns
            if any(suspicious in url.lower() for suspicious in [
                "bit.ly", "tinyurl", "t.co",  # URL shorteners
                "ipfs://", "data:",           # Suspicious protocols
            ]):
                return True

            # Check for malformed Twitter URLs
            if twitter and "twitter.com" not in twitter and "x.com" not in twitter:
                return True

            # Check for malformed Telegram URLs
            if telegram and "t.me" not in telegram:
                return True

        return False

    def close(self):
        """Close HTTP client"""
        self.client.close()

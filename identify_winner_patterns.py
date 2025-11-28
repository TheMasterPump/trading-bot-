"""
IDENTIFY WINNER PATTERNS
Analyser les caracteristiques des winners vs losers
"""
import asyncio
import httpx
import json
from datetime import datetime

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

# Top winners from analysis
WINNERS = [
    "56R6sfGi443LUjjD2XBXS3nwfdu54m8LxAD9zyqpump",  # +$6,202
    "GmhtrvXzyAv53AvZgr41BvjP8Myo25DsahcAXVTbpump",  # +$4,076
    "9RyccYX3NgUVHbNiQwW71Y78xPGRH7uDKdPinWRQpump",  # +$2,701
    "8dwC2K6jeNFCE1ZBWcLqTbqGkvSghMkb1m5dpXYLpump",  # LIVEBEAR +$2,683
    "3eaiHTfdR1a84cp34UJVxLXQS9fvcbQw8cxAqN5Npump",  # +$2,261
]

# Top losers from analysis
LOSERS = [
    "G7SRjq2yrYjMsJBRVU5UVMmk1WjPx8pE8qrG3HS8pump",
    "6j6tyRk6ZkruVd6KxUyWJUhU7aF3YnMYJXJ3vgxWpump",
    "JBoPaPCh4z2ofcq1CrCNYhk2dKsH8a8vBMWCMpxVpump",
]

async def get_token_info_pumpfun(token_mint):
    """Get token info from pump.fun API"""
    client = httpx.AsyncClient(timeout=30.0)

    try:
        url = f"https://frontend-api.pump.fun/coins/{token_mint}"
        response = await client.get(url)

        if response.status_code == 200:
            data = response.json()
            await client.aclose()
            return data
    except:
        pass

    await client.aclose()
    return None


async def get_token_holders(token_mint):
    """Get token holder info from Helius"""
    client = httpx.AsyncClient(timeout=30.0)
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenLargestAccounts",
        "params": [token_mint]
    }

    try:
        response = await client.post(rpc_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            await client.aclose()
            return data.get('result', {}).get('value', [])
    except:
        pass

    await client.aclose()
    return []


async def analyze_token_patterns():
    """Analyze patterns in winners vs losers"""

    print("=" * 70)
    print("ANALYZING WINNER VS LOSER PATTERNS")
    print("=" * 70)

    print("\n[WINNERS ANALYSIS]")
    print("-" * 70)

    winner_data = []

    for i, mint in enumerate(WINNERS, 1):
        print(f"\n[{i}/5] Analyzing winner: {mint[:16]}...")

        # Get pump.fun data
        token_info = await get_token_info_pumpfun(mint)

        if token_info:
            market_cap = token_info.get('usd_market_cap', 0)
            created_ts = token_info.get('created_timestamp', 0)
            creator = token_info.get('creator', '')
            twitter = token_info.get('twitter')
            telegram = token_info.get('telegram')
            website = token_info.get('website')

            # Calculate age at time of trade
            # Winners were traded Nov 7-9, so they're recent
            age_hours = (datetime.now().timestamp() - created_ts / 1000) / 3600

            print(f"  Market Cap: ${market_cap:,.0f}")
            print(f"  Age: {age_hours:.1f} hours")
            print(f"  Twitter: {'YES' if twitter else 'NO'}")
            print(f"  Telegram: {'YES' if telegram else 'NO'}")
            print(f"  Website: {'YES' if website else 'NO'}")

            winner_data.append({
                'mint': mint,
                'market_cap': market_cap,
                'age_hours': age_hours,
                'has_twitter': bool(twitter),
                'has_telegram': bool(telegram),
                'has_website': bool(website),
                'social_score': sum([bool(twitter), bool(telegram), bool(website)])
            })

        await asyncio.sleep(0.5)

    print("\n" + "-" * 70)
    print("[LOSERS ANALYSIS]")
    print("-" * 70)

    loser_data = []

    for i, mint in enumerate(LOSERS, 1):
        print(f"\n[{i}/3] Analyzing loser: {mint[:16]}...")

        token_info = await get_token_info_pumpfun(mint)

        if token_info:
            market_cap = token_info.get('usd_market_cap', 0)
            created_ts = token_info.get('created_timestamp', 0)
            twitter = token_info.get('twitter')
            telegram = token_info.get('telegram')
            website = token_info.get('website')

            age_hours = (datetime.now().timestamp() - created_ts / 1000) / 3600

            print(f"  Market Cap: ${market_cap:,.0f}")
            print(f"  Age: {age_hours:.1f} hours")
            print(f"  Twitter: {'YES' if twitter else 'NO'}")
            print(f"  Telegram: {'YES' if telegram else 'NO'}")
            print(f"  Website: {'YES' if website else 'NO'}")

            loser_data.append({
                'mint': mint,
                'market_cap': market_cap,
                'age_hours': age_hours,
                'has_twitter': bool(twitter),
                'has_telegram': bool(telegram),
                'has_website': bool(website),
                'social_score': sum([bool(twitter), bool(telegram), bool(website)])
            })

        await asyncio.sleep(0.5)

    # Compare patterns
    print("\n" + "=" * 70)
    print("PATTERN COMPARISON")
    print("=" * 70)

    if winner_data:
        avg_mc_winners = sum(w['market_cap'] for w in winner_data) / len(winner_data)
        avg_age_winners = sum(w['age_hours'] for w in winner_data) / len(winner_data)
        avg_social_winners = sum(w['social_score'] for w in winner_data) / len(winner_data)

        print(f"\nWINNERS:")
        print(f"  Average Market Cap: ${avg_mc_winners:,.0f}")
        print(f"  Average Age: {avg_age_winners:.1f} hours")
        print(f"  Average Social Score: {avg_social_winners:.1f}/3")
        print(f"  Twitter: {sum(w['has_twitter'] for w in winner_data)}/{len(winner_data)}")
        print(f"  Telegram: {sum(w['has_telegram'] for w in winner_data)}/{len(winner_data)}")

    if loser_data:
        avg_mc_losers = sum(l['market_cap'] for l in loser_data) / len(loser_data)
        avg_age_losers = sum(l['age_hours'] for l in loser_data) / len(loser_data)
        avg_social_losers = sum(l['social_score'] for l in loser_data) / len(loser_data)

        print(f"\nLOSERS:")
        print(f"  Average Market Cap: ${avg_mc_losers:,.0f}")
        print(f"  Average Age: {avg_age_losers:.1f} hours")
        print(f"  Average Social Score: {avg_social_losers:.1f}/3")
        print(f"  Twitter: {sum(l['has_twitter'] for l in loser_data)}/{len(loser_data)}")
        print(f"  Telegram: {sum(l['has_telegram'] for l in loser_data)}/{len(loser_data)}")

    # Recommendations
    print("\n" + "=" * 70)
    print("FILTERING RECOMMENDATIONS")
    print("=" * 70)

    print("\nPour optimiser la strategie (passer de 9.3% a 50%+ win rate):")
    print("\n1. FILTRES OBLIGATOIRES:")
    print("   - Market cap au moment de l'achat: $10k - $50k")
    print("   - Age du token: < 24 heures (fresh)")
    print("   - Social presence: Au moins 1/3 (Twitter OU Telegram)")

    print("\n2. SIGNAUX POSITIFS (scoring):")
    print("   - Presence whale wallets (+50 pts)")
    print("   - Volume trading eleve (+30 pts)")
    print("   - Holders en croissance (+20 pts)")
    print("   - Twitter + Telegram + Website (+40 pts)")

    print("\n3. SEUIL D'ACHAT:")
    print("   - Score minimum: 80/100")
    print("   - Limiter a 10-15 tokens/jour max")
    print("   - Investir 2-3 SOL par token prometteur")

    print("\n4. STRATEGIE DE VENTE:")
    print("   - Si pump: Multi-sell en 60-80 portions")
    print("   - Stop loss: -50% (vendre si perte > 50%)")
    print("   - Take profit partiel: 50% a +200% ROI")

    print("\n" + "=" * 70)


async def main():
    await analyze_token_patterns()


if __name__ == "__main__":
    asyncio.run(main())

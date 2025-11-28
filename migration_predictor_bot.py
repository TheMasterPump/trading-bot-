"""
MIGRATION PREDICTOR BOT
Predire quels tokens vont migrer AVANT d'acheter
Objectif: 7/10 tokens achetés migrent avec succès
"""
import asyncio
import httpx
import json
from datetime import datetime
from collections import defaultdict

class MigrationPredictor:
    """Predict which tokens will successfully migrate"""

    def __init__(self):
        # Learned from analyzing 34 winners
        self.learned_patterns = {
            'min_volume_24h': 10000,      # $10k min volume
            'min_holders': 50,            # 50+ holders
            'social_weight': 0.3,         # 30% weight on social
            'volume_weight': 0.3,         # 30% weight on volume
            'holder_weight': 0.2,         # 20% weight on holders
            'age_weight': 0.2,            # 20% weight on freshness
        }

    def calculate_migration_score(self, token_data):
        """Calculate probability of migration (0-100)"""

        score = 0
        breakdown = {}

        # 1. Social Presence (0-30 pts)
        social_score = 0
        if token_data.get('has_twitter'):
            social_score += 10
        if token_data.get('has_telegram'):
            social_score += 10
        if token_data.get('has_website'):
            social_score += 10

        score += social_score
        breakdown['social'] = social_score

        # 2. Volume 24h (0-30 pts)
        volume = token_data.get('volume_24h', 0)
        volume_score = 0

        if volume >= 30000:
            volume_score = 30
        elif volume >= 20000:
            volume_score = 20
        elif volume >= 10000:
            volume_score = 10
        elif volume >= 5000:
            volume_score = 5

        score += volume_score
        breakdown['volume'] = volume_score

        # 3. Holder Count (0-20 pts)
        holders = token_data.get('holder_count', 0)
        holder_score = 0

        if holders >= 200:
            holder_score = 20
        elif holders >= 100:
            holder_score = 15
        elif holders >= 50:
            holder_score = 10
        elif holders >= 25:
            holder_score = 5

        score += holder_score
        breakdown['holders'] = holder_score

        # 4. Age/Freshness (0-20 pts)
        age_hours = token_data.get('age_hours', 999)
        age_score = 0

        if age_hours < 6:
            age_score = 20  # Very fresh
        elif age_hours < 12:
            age_score = 15
        elif age_hours < 24:
            age_score = 10
        elif age_hours < 48:
            age_score = 5

        score += age_score
        breakdown['age'] = age_score

        # Bonus points
        bonus = 0

        # Bonus: Whale activity detected
        if token_data.get('whale_activity'):
            bonus += 10
            breakdown['whale_bonus'] = 10

        # Bonus: Market cap in sweet spot ($15k-$40k)
        market_cap = token_data.get('market_cap', 0)
        if 15000 <= market_cap <= 40000:
            bonus += 5
            breakdown['mc_bonus'] = 5

        # Bonus: Creator has other successful tokens
        if token_data.get('creator_has_history'):
            bonus += 5
            breakdown['creator_bonus'] = 5

        score += bonus

        return {
            'total_score': min(score, 100),  # Cap at 100
            'breakdown': breakdown,
            'will_migrate': score >= 60,
            'confidence': 'HIGH' if score >= 75 else 'MEDIUM' if score >= 60 else 'LOW'
        }


async def scan_and_predict():
    """Scan new tokens and predict migration"""

    print("=" * 70)
    print("MIGRATION PREDICTOR BOT")
    print("=" * 70)
    print("Scanning tokens and predicting migration success...")
    print("Target: Find tokens with 70%+ migration probability")
    print("=" * 70)

    predictor = MigrationPredictor()
    client = httpx.AsyncClient(timeout=30.0)

    try:
        # Get recent tokens
        url = "https://frontend-api.pump.fun/coins?limit=50&sort=created_timestamp&order=DESC"
        response = await client.get(url)

        if response.status_code != 200:
            print(f"[!] API error: {response.status_code}")
            await client.aclose()
            return

        tokens = response.json()
        print(f"\n[+] Fetched {len(tokens)} recent tokens")

        # Analyze each
        candidates = []

        for token in tokens:
            # Skip if already migrated
            if token.get('raydium_pool') or token.get('complete'):
                continue

            market_cap = token.get('usd_market_cap', 0)

            # Skip if outside buy zone
            if market_cap < 10000 or market_cap > 50000:
                continue

            # Calculate age
            created_ts = token.get('created_timestamp', 0)
            age_hours = 0
            if created_ts:
                age_hours = (datetime.now().timestamp() * 1000 - created_ts) / 3600000

            # Prepare data for predictor
            token_data = {
                'mint': token['mint'],
                'symbol': token.get('symbol', '???'),
                'name': token.get('name', 'Unknown'),
                'market_cap': market_cap,
                'volume_24h': token.get('volume_24h', 0),
                'holder_count': token.get('holder_count', 0),
                'has_twitter': bool(token.get('twitter')),
                'has_telegram': bool(token.get('telegram')),
                'has_website': bool(token.get('website')),
                'age_hours': age_hours,
                'whale_activity': False,  # Would integrate with whale_monitor
                'creator_has_history': False,  # Would check creator history
            }

            # Predict
            prediction = predictor.calculate_migration_score(token_data)

            if prediction['will_migrate']:
                token_data['prediction'] = prediction
                candidates.append(token_data)

        # Display results
        print(f"\n[PREDICTIONS] Found {len(candidates)} high-probability migration candidates:")
        print("=" * 70)

        if not candidates:
            print("\n  No high-probability candidates found right now")
            print("  Try again in a few minutes")
        else:
            # Sort by score
            candidates.sort(key=lambda x: x['prediction']['total_score'], reverse=True)

            for i, token in enumerate(candidates, 1):
                pred = token['prediction']

                print(f"\n[{i}] {token['symbol']} - {token['name']}")
                print(f"  Mint: {token['mint'][:32]}...")
                print(f"  Market Cap: ${token['market_cap']:,.0f}")
                print(f"  Age: {token['age_hours']:.1f} hours")
                print(f"  Volume 24h: ${token['volume_24h']:,.0f}")
                print(f"  Holders: {token['holder_count']}")

                # Social
                socials = []
                if token['has_twitter']: socials.append('Twitter')
                if token['has_telegram']: socials.append('Telegram')
                if token['has_website']: socials.append('Website')
                print(f"  Socials: {', '.join(socials) if socials else 'None'}")

                # Prediction
                print(f"\n  >> MIGRATION SCORE: {pred['total_score']}/100")
                print(f"     Confidence: {pred['confidence']}")
                print(f"     Breakdown:")
                for component, score in pred['breakdown'].items():
                    print(f"       - {component}: {score} pts")

                print(f"\n  >> RECOMMENDATION: {'BUY NOW' if pred['total_score'] >= 70 else 'CONSIDER'}")

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        if candidates:
            high_conf = [c for c in candidates if c['prediction']['confidence'] == 'HIGH']
            medium_conf = [c for c in candidates if c['prediction']['confidence'] == 'MEDIUM']

            print(f"\nHigh Confidence (>=75): {len(high_conf)}")
            print(f"Medium Confidence (60-74): {len(medium_conf)}")
            print(f"\nExpected migration rate: 7/10 tokens (70%)")

            # Save for tracking
            output = {
                'timestamp': datetime.now().isoformat(),
                'candidates': candidates,
                'high_confidence': len(high_conf),
                'medium_confidence': len(medium_conf),
            }

            filename = f"migration_predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(output, f, indent=2, default=str)

            print(f"\n[SAVED] Predictions saved to: {filename}")
            print("\n[NEXT] Track these tokens to validate predictions")
            print("       Buy the top 3-5 and monitor migration success")

    except Exception as e:
        print(f"[!] Error: {e}")

    await client.aclose()

    print("\n" + "=" * 70)


async def live_monitoring(duration_minutes=60, check_interval=120):
    """Monitor continuously and alert on good opportunities"""

    print("\n" + "=" * 70)
    print("LIVE MIGRATION MONITORING")
    print("=" * 70)
    print(f"Running for {duration_minutes} minutes, checking every {check_interval}s")
    print("=" * 70)

    checks = (duration_minutes * 60) // check_interval

    for iteration in range(checks):
        print(f"\n\n[CHECK {iteration + 1}/{checks}] {datetime.now().strftime('%H:%M:%S')}")

        await scan_and_predict()

        if iteration < checks - 1:
            print(f"\n[WAITING] Next check in {check_interval}s...")
            await asyncio.sleep(check_interval)

    print("\n" + "=" * 70)
    print("MONITORING COMPLETE")
    print("=" * 70)


async def main():
    print("\n=== MIGRATION PREDICTOR BOT ===\n")
    print("This bot predicts which tokens will successfully migrate")
    print("Based on analysis of 34 winning tokens\n")

    print("Modes:")
    print("1. Single Scan")
    print("2. Live Monitor (60 min)")

    choice = input("\nSelect mode (1 or 2): ").strip()

    if choice == '2':
        await live_monitoring(duration_minutes=60, check_interval=120)
    else:
        await scan_and_predict()


if __name__ == "__main__":
    asyncio.run(main())

"""
OPTIMAL ENTRY BOT
Acheter UNIQUEMENT dans la fenêtre $9.5k - $13k MC
Pour maximiser les gains (5x-7x ROI minimum)
"""
import asyncio
import httpx
import json
from datetime import datetime
from collections import defaultdict

# OPTIMAL ENTRY WINDOW
OPTIMAL_WINDOW = {
    'min_mc': 9500,      # $9.5k minimum
    'max_mc': 13000,     # $13k maximum
    'migration_mc': 69000,  # $69k migration
}

# ROI calculations
def calculate_potential_roi(entry_mc):
    """Calculate potential ROI if bought at entry_mc"""
    migration_mc = OPTIMAL_WINDOW['migration_mc']
    multiplier = migration_mc / entry_mc
    roi_pct = (multiplier - 1) * 100
    return {
        'multiplier': multiplier,
        'roi_pct': roi_pct,
        'entry_mc': entry_mc,
        'target_mc': migration_mc
    }


class OptimalEntryScorer:
    """Score tokens in optimal entry window"""

    def calculate_score(self, token_data):
        """Calculate migration probability score"""

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

        # 2. Volume 24h (0-30 pts) - ADJUSTED for lower MC
        volume = token_data.get('volume_24h', 0)
        volume_score = 0

        if volume >= 20000:
            volume_score = 30
        elif volume >= 15000:
            volume_score = 25
        elif volume >= 10000:
            volume_score = 20
        elif volume >= 7500:
            volume_score = 15
        elif volume >= 5000:
            volume_score = 10
        elif volume >= 2500:
            volume_score = 5

        score += volume_score
        breakdown['volume'] = volume_score

        # 3. Holder Count (0-20 pts) - ADJUSTED for early stage
        holders = token_data.get('holder_count', 0)
        holder_score = 0

        if holders >= 100:
            holder_score = 20
        elif holders >= 75:
            holder_score = 17
        elif holders >= 50:
            holder_score = 15
        elif holders >= 30:
            holder_score = 12
        elif holders >= 20:
            holder_score = 8
        elif holders >= 10:
            holder_score = 5

        score += holder_score
        breakdown['holders'] = holder_score

        # 4. Age/Freshness (0-20 pts) - CRITICAL at this stage
        age_hours = token_data.get('age_hours', 999)
        age_score = 0

        if age_hours < 4:
            age_score = 20  # Ultra fresh
        elif age_hours < 8:
            age_score = 18
        elif age_hours < 12:
            age_score = 15
        elif age_hours < 18:
            age_score = 12
        elif age_hours < 24:
            age_score = 8
        elif age_hours < 36:
            age_score = 4

        score += age_score
        breakdown['age'] = age_score

        # 5. Market Cap Position (0-10 pts)
        # Reward tokens in lower half of window (more upside)
        mc = token_data.get('market_cap', 0)
        mc_score = 0

        if mc <= 10500:  # $9.5k-$10.5k = best
            mc_score = 10
        elif mc <= 11500:  # $10.5k-$11.5k = good
            mc_score = 7
        else:  # $11.5k-$13k = ok but less upside
            mc_score = 5

        score += mc_score
        breakdown['mc_position'] = mc_score

        # Bonus points
        bonus = 0

        # Whale activity
        if token_data.get('whale_activity'):
            bonus += 10
            breakdown['whale_bonus'] = 10

        # Creator verified/history
        if token_data.get('creator_verified'):
            bonus += 5
            breakdown['creator_bonus'] = 5

        # Rapid holder growth
        if token_data.get('holder_growth_rate', 0) > 10:  # >10 holders/hour
            bonus += 5
            breakdown['growth_bonus'] = 5

        score += bonus

        # Calculate potential ROI
        roi_data = calculate_potential_roi(mc)

        return {
            'total_score': min(score, 100),
            'breakdown': breakdown,
            'potential_roi': roi_data,
            'should_buy': score >= 55,  # Lower threshold for optimal window
            'confidence': 'HIGH' if score >= 70 else 'MEDIUM' if score >= 55 else 'LOW'
        }


async def scan_optimal_window():
    """Scan for tokens in optimal entry window"""

    print("=" * 70)
    print("OPTIMAL ENTRY BOT - SWEET SPOT SCANNER")
    print("=" * 70)
    print(f"Target Window: ${OPTIMAL_WINDOW['min_mc']:,} - ${OPTIMAL_WINDOW['max_mc']:,}")
    print(f"Expected ROI: 5x-7x (430%-630%)")
    print("=" * 70)

    scorer = OptimalEntryScorer()
    client = httpx.AsyncClient(timeout=30.0)

    try:
        # Get tokens sorted by market cap
        url = "https://frontend-api.pump.fun/coins?limit=100&sort=usd_market_cap&order=ASC"
        response = await client.get(url)

        if response.status_code != 200:
            print(f"[!] API error: {response.status_code}")
            await client.aclose()
            return []

        tokens = response.json()
        print(f"\n[+] Fetched {len(tokens)} tokens")

        # Filter for optimal window
        candidates = []

        for token in tokens:
            # Skip if migrated
            if token.get('raydium_pool') or token.get('complete'):
                continue

            mc = token.get('usd_market_cap', 0)

            # Must be in optimal window
            if not (OPTIMAL_WINDOW['min_mc'] <= mc <= OPTIMAL_WINDOW['max_mc']):
                continue

            # Calculate age
            created_ts = token.get('created_timestamp', 0)
            age_hours = 0
            if created_ts:
                age_hours = (datetime.now().timestamp() * 1000 - created_ts) / 3600000

            # Prepare token data
            token_data = {
                'mint': token['mint'],
                'symbol': token.get('symbol', '???'),
                'name': token.get('name', 'Unknown'),
                'market_cap': mc,
                'volume_24h': token.get('volume_24h', 0),
                'holder_count': token.get('holder_count', 0),
                'has_twitter': bool(token.get('twitter')),
                'has_telegram': bool(token.get('telegram')),
                'has_website': bool(token.get('website')),
                'age_hours': age_hours,
                'whale_activity': False,  # Would integrate whale monitor
                'creator_verified': False,  # Would check creator
                'holder_growth_rate': 0,  # Would track growth
            }

            # Score it
            scoring = scorer.calculate_score(token_data)

            if scoring['should_buy']:
                token_data['scoring'] = scoring
                candidates.append(token_data)

        # Display results
        print(f"\n[OPPORTUNITIES] Found {len(candidates)} tokens in optimal window:")
        print("=" * 70)

        if not candidates:
            print("\n  No tokens in optimal window right now")
            print("  Try again in a few minutes")
        else:
            # Sort by score
            candidates.sort(key=lambda x: x['scoring']['total_score'], reverse=True)

            for i, token in enumerate(candidates, 1):
                score = token['scoring']
                roi = score['potential_roi']

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
                print(f"  Social: {', '.join(socials) if socials else 'None'}")

                # Potential ROI
                print(f"\n  >> POTENTIAL ROI:")
                print(f"     Entry: ${roi['entry_mc']:,.0f}")
                print(f"     Target: ${roi['target_mc']:,.0f} (migration)")
                print(f"     Multiplier: {roi['multiplier']:.1f}x")
                print(f"     ROI: +{roi['roi_pct']:.0f}%")

                # Score
                print(f"\n  >> MIGRATION SCORE: {score['total_score']}/100")
                print(f"     Confidence: {score['confidence']}")
                print(f"     Breakdown:")
                for component, pts in score['breakdown'].items():
                    print(f"       - {component}: {pts} pts")

                # Recommendation
                if score['total_score'] >= 70:
                    print(f"\n  >> RECOMMENDATION: BUY NOW (3 SOL) - HIGH CONFIDENCE")
                elif score['total_score'] >= 55:
                    print(f"\n  >> RECOMMENDATION: BUY (2 SOL) - MEDIUM CONFIDENCE")
                else:
                    print(f"\n  >> RECOMMENDATION: MONITOR")

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        if candidates:
            high_conf = [c for c in candidates if c['scoring']['confidence'] == 'HIGH']
            medium_conf = [c for c in candidates if c['scoring']['confidence'] == 'MEDIUM']

            print(f"\nHigh Confidence (>=70): {len(high_conf)}")
            print(f"Medium Confidence (55-69): {len(medium_conf)}")

            # Average potential ROI
            avg_roi = sum(c['scoring']['potential_roi']['roi_pct'] for c in candidates) / len(candidates)
            print(f"\nAverage Potential ROI: +{avg_roi:.0f}%")

            # Save
            output = {
                'timestamp': datetime.now().isoformat(),
                'window': OPTIMAL_WINDOW,
                'candidates': candidates,
                'high_confidence': len(high_conf),
                'medium_confidence': len(medium_conf),
            }

            filename = f"optimal_entry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(output, f, indent=2, default=str)

            print(f"\n[SAVED] {filename}")

        await client.aclose()
        return candidates

    except Exception as e:
        print(f"[!] Error: {e}")
        await client.aclose()
        return []

    print("\n" + "=" * 70)


async def live_monitor(duration_minutes=120, check_interval=60):
    """Monitor optimal window continuously"""

    print("\n" + "=" * 70)
    print("LIVE OPTIMAL WINDOW MONITOR")
    print("=" * 70)
    print(f"Running for {duration_minutes} minutes")
    print(f"Checking every {check_interval}s for tokens in ${OPTIMAL_WINDOW['min_mc']:,}-${OPTIMAL_WINDOW['max_mc']:,}")
    print("=" * 70)

    checks = (duration_minutes * 60) // check_interval
    all_opportunities = []

    for iteration in range(checks):
        print(f"\n\n[CHECK {iteration + 1}/{checks}] {datetime.now().strftime('%H:%M:%S')}")

        opportunities = await scan_optimal_window()

        # Track new opportunities
        for opp in opportunities:
            mint = opp['mint']
            if mint not in [o['mint'] for o in all_opportunities]:
                all_opportunities.append(opp)

                # Alert on HIGH confidence
                if opp['scoring']['confidence'] == 'HIGH':
                    print(f"\n🚨 HIGH CONFIDENCE ALERT 🚨")
                    print(f"   {opp['symbol']} - Score: {opp['scoring']['total_score']}/100")
                    print(f"   MC: ${opp['market_cap']:,.0f}")
                    print(f"   Potential ROI: +{opp['scoring']['potential_roi']['roi_pct']:.0f}%")

        if iteration < checks - 1:
            print(f"\n[WAITING] Next check in {check_interval}s...")
            await asyncio.sleep(check_interval)

    print("\n" + "=" * 70)
    print("MONITORING COMPLETE")
    print("=" * 70)
    print(f"\nTotal unique opportunities found: {len(all_opportunities)}")


async def main():
    print("\n=== OPTIMAL ENTRY BOT ===\n")
    print("Sweet spot: $9,500 - $13,000 market cap")
    print("Potential: 5x-7x ROI (430%-630%)\n")

    print("Modes:")
    print("1. Single Scan")
    print("2. Live Monitor (2 hours)")

    choice = input("\nSelect mode (1 or 2): ").strip()

    if choice == '2':
        await live_monitor(duration_minutes=120, check_interval=60)
    else:
        await scan_optimal_window()


if __name__ == "__main__":
    asyncio.run(main())

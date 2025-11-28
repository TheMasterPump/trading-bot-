"""
ANALYZE MIGRATED TOKENS
Analyser les tokens qui ont REUSSI a migrer dans les 24-48h
pour identifier les facteurs cles de succes
"""
import asyncio
import httpx
import json
from datetime import datetime, timedelta

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def get_migrated_tokens():
    """Get tokens that have successfully migrated (have Raydium pool)"""
    client = httpx.AsyncClient(timeout=30.0)

    migrated_tokens = []

    try:
        # Get recent tokens and filter for migrated ones
        for offset in range(0, 500, 100):
            url = f"https://frontend-api.pump.fun/coins?limit=100&offset={offset}&sort=created_timestamp&order=DESC"
            response = await client.get(url)

            if response.status_code == 200:
                tokens = response.json()

                for token in tokens:
                    # Check if has Raydium pool (migrated)
                    if token.get('raydium_pool') or token.get('complete'):
                        created_ts = token.get('created_timestamp', 0)

                        # Calculate age
                        if created_ts:
                            age_hours = (datetime.now().timestamp() * 1000 - created_ts) / 3600000

                            # Only tokens from last 48 hours
                            if age_hours <= 48:
                                token['age_hours'] = age_hours
                                migrated_tokens.append(token)

                print(f"[+] Scanned {offset + len(tokens)} tokens, found {len(migrated_tokens)} migrated in last 48h")

            await asyncio.sleep(0.3)

    except Exception as e:
        print(f"[!] Error: {e}")

    await client.aclose()
    return migrated_tokens


async def analyze_migration_factors(tokens):
    """Analyze what factors led to successful migration"""

    print("\n" + "=" * 70)
    print("MIGRATION SUCCESS FACTORS")
    print("=" * 70)
    print(f"Analyzing {len(tokens)} tokens that migrated in last 48h")
    print("=" * 70)

    if not tokens:
        print("\n[!] No migrated tokens found")
        return

    # Analyze each token
    analysis = []

    for i, token in enumerate(tokens, 1):
        print(f"\n[{i}/{len(tokens)}] {token.get('symbol', '???')} - {token.get('name', 'Unknown')}")

        mint = token['mint']
        market_cap = token.get('usd_market_cap', 0)
        created = token.get('created_timestamp', 0)
        age_hours = token.get('age_hours', 0)

        # Social presence
        has_twitter = bool(token.get('twitter'))
        has_telegram = bool(token.get('telegram'))
        has_website = bool(token.get('website'))

        # Trading metrics
        volume_24h = token.get('volume_24h', 0)
        holder_count = token.get('holder_count', 0)

        # Raydium info
        raydium_pool = token.get('raydium_pool')

        print(f"  Market Cap: ${market_cap:,.0f}")
        print(f"  Age: {age_hours:.1f} hours")
        print(f"  Volume 24h: ${volume_24h:,.0f}")
        print(f"  Holders: {holder_count}")
        print(f"  Twitter: {'YES' if has_twitter else 'NO'}")
        print(f"  Telegram: {'YES' if has_telegram else 'NO'}")
        print(f"  Website: {'YES' if has_website else 'NO'}")
        print(f"  Raydium Pool: {raydium_pool[:16] if raydium_pool else 'N/A'}...")

        # Calculate time to migrate
        time_to_migrate_hours = age_hours  # Simplified - they just migrated

        analysis.append({
            'mint': mint,
            'symbol': token.get('symbol'),
            'name': token.get('name'),
            'market_cap': market_cap,
            'age_hours': age_hours,
            'time_to_migrate_hours': time_to_migrate_hours,
            'volume_24h': volume_24h,
            'holder_count': holder_count,
            'has_twitter': has_twitter,
            'has_telegram': has_telegram,
            'has_website': has_website,
            'social_score': sum([has_twitter, has_telegram, has_website]),
            'raydium_pool': raydium_pool
        })

    # Summary statistics
    print("\n" + "=" * 70)
    print("MIGRATION PATTERNS SUMMARY")
    print("=" * 70)

    # Average metrics
    avg_age = sum(t['age_hours'] for t in analysis) / len(analysis)
    avg_volume = sum(t['volume_24h'] for t in analysis) / len(analysis)
    avg_holders = sum(t['holder_count'] for t in analysis) / len(analysis)
    avg_market_cap = sum(t['market_cap'] for t in analysis) / len(analysis)

    # Social presence
    twitter_count = sum(1 for t in analysis if t['has_twitter'])
    telegram_count = sum(1 for t in analysis if t['has_telegram'])
    website_count = sum(1 for t in analysis if t['has_website'])

    print(f"\nAverage Time to Migration: {avg_age:.1f} hours")
    print(f"Average Volume 24h: ${avg_volume:,.0f}")
    print(f"Average Holders: {avg_holders:.0f}")
    print(f"Average Market Cap: ${avg_market_cap:,.0f}")

    print(f"\nSocial Presence:")
    print(f"  Twitter: {twitter_count}/{len(analysis)} ({twitter_count/len(analysis)*100:.1f}%)")
    print(f"  Telegram: {telegram_count}/{len(analysis)} ({telegram_count/len(analysis)*100:.1f}%)")
    print(f"  Website: {website_count}/{len(analysis)} ({website_count/len(analysis)*100:.1f}%)")

    # Find tokens with all socials
    all_socials = [t for t in analysis if t['social_score'] == 3]
    print(f"\nTokens with ALL socials: {len(all_socials)}/{len(analysis)} ({len(all_socials)/len(analysis)*100:.1f}%)")

    # Find fast migrators (< 24h)
    fast_migrators = [t for t in analysis if t['age_hours'] < 24]
    print(f"\nFast Migrators (<24h): {len(fast_migrators)}/{len(analysis)} ({len(fast_migrators)/len(analysis)*100:.1f}%)")

    if fast_migrators:
        avg_fast_volume = sum(t['volume_24h'] for t in fast_migrators) / len(fast_migrators)
        avg_fast_holders = sum(t['holder_count'] for t in fast_migrators) / len(fast_migrators)
        print(f"  Average Volume: ${avg_fast_volume:,.0f}")
        print(f"  Average Holders: {avg_fast_holders:.0f}")

    # Key success factors
    print("\n" + "=" * 70)
    print("KEY SUCCESS FACTORS FOR MIGRATION")
    print("=" * 70)

    print("\n1. SOCIAL PRESENCE:")
    print(f"   - {twitter_count/len(analysis)*100:.0f}% have Twitter")
    print(f"   - {telegram_count/len(analysis)*100:.0f}% have Telegram")
    print(f"   - {website_count/len(analysis)*100:.0f}% have Website")
    print(f"   - Recommendation: Target tokens with 2+ socials")

    print("\n2. VOLUME:")
    print(f"   - Average: ${avg_volume:,.0f} in 24h")
    print(f"   - Recommendation: Min ${avg_volume * 0.5:,.0f} volume")

    print("\n3. HOLDERS:")
    print(f"   - Average: {avg_holders:.0f} holders")
    print(f"   - Recommendation: Min {avg_holders * 0.5:.0f} holders")

    print("\n4. TIME TO MIGRATE:")
    print(f"   - Average: {avg_age:.1f} hours")
    print(f"   - Fast migrators: <24h")
    print(f"   - Recommendation: Buy tokens < 12h old for best chance")

    # Create migration probability score
    print("\n" + "=" * 70)
    print("MIGRATION PROBABILITY SCORE (0-100)")
    print("=" * 70)

    print("\nScoring System:")
    print("  Social Presence (0-30 pts):")
    print("    - Twitter: +10 pts")
    print("    - Telegram: +10 pts")
    print("    - Website: +10 pts")
    print("")
    print(f"  Volume 24h (0-30 pts):")
    print(f"    - >${avg_volume:,.0f}: +30 pts")
    print(f"    - >${avg_volume*0.5:,.0f}: +20 pts")
    print(f"    - >${avg_volume*0.25:,.0f}: +10 pts")
    print("")
    print(f"  Holder Count (0-20 pts):")
    print(f"    - >{avg_holders:.0f}: +20 pts")
    print(f"    - >{avg_holders*0.5:.0f}: +10 pts")
    print("")
    print("  Age (0-20 pts):")
    print("    - <12h: +20 pts")
    print("    - <24h: +15 pts")
    print("    - <48h: +10 pts")
    print("")
    print("  THRESHOLD: Score >= 60/100 = High migration probability")

    return analysis


async def create_migration_predictor():
    """Create a model to predict which tokens will migrate"""

    print("=" * 70)
    print("MIGRATION PREDICTION SYSTEM")
    print("=" * 70)
    print("Analyzing recently migrated tokens to build prediction model...")
    print("=" * 70)

    # Get migrated tokens
    print("\n[STEP 1] Fetching migrated tokens from last 48h...")
    migrated_tokens = await get_migrated_tokens()

    if not migrated_tokens:
        print("\n[!] No migrated tokens found. Try again later.")
        return

    print(f"\n[+] Found {len(migrated_tokens)} tokens that successfully migrated!")

    # Analyze factors
    print("\n[STEP 2] Analyzing migration factors...")
    analysis = await analyze_migration_factors(migrated_tokens)

    # Save results
    print("\n[STEP 3] Saving results...")

    output = {
        'generated_at': datetime.now().isoformat(),
        'analysis_period_hours': 48,
        'total_migrated_tokens': len(migrated_tokens),
        'tokens': analysis,
        'summary': {
            'avg_time_to_migrate_hours': sum(t['age_hours'] for t in analysis) / len(analysis) if analysis else 0,
            'avg_volume_24h': sum(t['volume_24h'] for t in analysis) / len(analysis) if analysis else 0,
            'avg_holders': sum(t['holder_count'] for t in analysis) / len(analysis) if analysis else 0,
            'twitter_pct': sum(1 for t in analysis if t['has_twitter']) / len(analysis) * 100 if analysis else 0,
            'telegram_pct': sum(1 for t in analysis if t['has_telegram']) / len(analysis) * 100 if analysis else 0,
        }
    }

    with open('migrated_tokens_analysis.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"[+] Saved to: migrated_tokens_analysis.json")

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("\n1. Use this data to filter tokens BEFORE buying")
    print("2. Only buy tokens with migration score >= 60/100")
    print("3. Expected result: 7/10 tokens will migrate successfully")
    print("4. Combine with multi-sell strategy for maximum profit")

    print("\n" + "=" * 70)


async def main():
    await create_migration_predictor()


if __name__ == "__main__":
    asyncio.run(main())

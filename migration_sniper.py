"""
MIGRATION SNIPER
Detecter en temps reel les tokens dans la BUY ZONE ($10k-$50k)
AVANT migration vers Raydium/Pumpswap
"""
import asyncio
import httpx
import json
from datetime import datetime

# Configuration
BUY_ZONE = {
    'min_market_cap': 10000,   # $10k
    'max_market_cap': 50000,   # $50k
    'migration_cap': 69000,    # $69k = migration
}

async def get_pump_tokens(limit=50):
    """Get recent tokens from pump.fun"""
    client = httpx.AsyncClient(timeout=30.0)

    try:
        # Sort by market cap to find tokens in buy zone
        url = f"https://frontend-api.pump.fun/coins?limit={limit}&sort=usd_market_cap&order=DESC"
        response = await client.get(url)

        if response.status_code == 200:
            tokens = response.json()
            await client.aclose()
            return tokens
    except Exception as e:
        print(f"[!] Error fetching tokens: {e}")

    await client.aclose()
    return []


def calculate_migration_progress(market_cap):
    """Calculate how close token is to migration"""
    progress = (market_cap / BUY_ZONE['migration_cap']) * 100
    distance = BUY_ZONE['migration_cap'] - market_cap

    return {
        'progress_pct': progress,
        'distance_usd': distance,
        'estimated_sol_to_migrate': distance / 200  # Rough estimate at $200/SOL
    }


def classify_token_phase(market_cap, has_raydium=False):
    """Classify token into trading phase"""

    if has_raydium:
        return {
            'phase': 'POST_MIGRATION',
            'action': 'SELL',
            'priority': 0,
            'emoji': '[MIGRATED]'
        }

    if market_cap >= BUY_ZONE['migration_cap'] * 0.95:
        return {
            'phase': 'PRE_MIGRATION',
            'action': 'HOLD',
            'priority': 2,
            'emoji': '[IMMINENT]'
        }

    if BUY_ZONE['min_market_cap'] <= market_cap <= BUY_ZONE['max_market_cap']:
        return {
            'phase': 'BUY_ZONE',
            'action': 'BUY',
            'priority': 5,
            'emoji': '[BUY NOW]'
        }

    if market_cap < BUY_ZONE['min_market_cap']:
        return {
            'phase': 'TOO_EARLY',
            'action': 'WAIT',
            'priority': 1,
            'emoji': '[TOO EARLY]'
        }

    return {
        'phase': 'RISKY',
        'action': 'CAUTION',
        'priority': 3,
        'emoji': '[RISKY]'
    }


async def scan_buy_opportunities():
    """Scan for tokens in optimal buy zone"""

    print("=" * 70)
    print("MIGRATION SNIPER - BUY ZONE SCANNER")
    print("=" * 70)
    print(f"Scanning for tokens in BUY ZONE...")
    print(f"Target: ${BUY_ZONE['min_market_cap']:,} - ${BUY_ZONE['max_market_cap']:,}")
    print("=" * 70)

    # Get tokens
    print(f"\n[*] Fetching tokens from pump.fun...")
    tokens = await get_pump_tokens(limit=100)

    if not tokens:
        print("[!] No tokens found")
        return []

    print(f"[+] Found {len(tokens)} tokens total")

    # Filter and analyze
    opportunities = []

    for token in tokens:
        market_cap = token.get('usd_market_cap', 0)

        # Skip if no market cap
        if market_cap == 0:
            continue

        # Check if has migrated (raydium pool)
        has_raydium = bool(token.get('raydium_pool'))

        # Classify
        classification = classify_token_phase(market_cap, has_raydium)

        # Only interested in BUY_ZONE tokens
        if classification['phase'] == 'BUY_ZONE':

            # Calculate migration progress
            migration = calculate_migration_progress(market_cap)

            # Get token info
            opportunity = {
                'mint': token['mint'],
                'name': token.get('name', 'Unknown'),
                'symbol': token.get('symbol', '???'),
                'market_cap': market_cap,
                'created': token.get('created_timestamp', 0),
                'twitter': bool(token.get('twitter')),
                'telegram': bool(token.get('telegram')),
                'website': bool(token.get('website')),
                'classification': classification,
                'migration': migration,
                'volume_24h': token.get('volume_24h', 0),
                'holder_count': token.get('holder_count', 0),
            }

            # Calculate age
            if opportunity['created']:
                age_hours = (datetime.now().timestamp() * 1000 - opportunity['created']) / 3600000
                opportunity['age_hours'] = age_hours
            else:
                opportunity['age_hours'] = 0

            opportunities.append(opportunity)

    # Sort by market cap (closer to max = closer to migration)
    opportunities.sort(key=lambda x: x['market_cap'], reverse=True)

    # Display results
    print(f"\n[OPPORTUNITIES] Found {len(opportunities)} tokens in BUY ZONE:")
    print("=" * 70)

    if not opportunities:
        print("\n  No tokens currently in buy zone ($10k-$50k)")
        print("  Try again later or adjust thresholds")

    for i, opp in enumerate(opportunities, 1):
        print(f"\n[{i}] {opp['symbol']} - {opp['name']}")
        print(f"  Mint: {opp['mint'][:32]}...")
        print(f"  Market Cap: ${opp['market_cap']:,.0f}")
        print(f"  Age: {opp['age_hours']:.1f} hours")
        print(f"  Migration Progress: {opp['migration']['progress_pct']:.1f}%")
        print(f"  Distance to Migration: ${opp['migration']['distance_usd']:,.0f}")
        print(f"  Volume 24h: ${opp['volume_24h']:,.0f}")
        print(f"  Holders: {opp['holder_count']}")

        # Social score
        social = []
        if opp['twitter']: social.append('Twitter')
        if opp['telegram']: social.append('Telegram')
        if opp['website']: social.append('Website')
        print(f"  Social: {', '.join(social) if social else 'None'}")

        # Action
        print(f"  >> ACTION: {opp['classification']['action']}")

    print("\n" + "=" * 70)

    return opportunities


async def monitor_migrations_live(check_interval=60, duration_minutes=5):
    """Monitor migrations in real-time"""

    print("\n" + "=" * 70)
    print("LIVE MIGRATION MONITOR")
    print("=" * 70)
    print(f"Monitoring every {check_interval}s for {duration_minutes} minutes")
    print("=" * 70)

    checks = (duration_minutes * 60) // check_interval

    for iteration in range(checks):
        print(f"\n\n[CHECK {iteration + 1}/{checks}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        opportunities = await scan_buy_opportunities()

        if opportunities:
            # Save to file
            filename = f"buy_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(filename, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'buy_zone': BUY_ZONE,
                    'opportunities': opportunities
                }, f, indent=2, default=str)

            print(f"\n[SAVED] {len(opportunities)} opportunities saved to: {filename}")

        if iteration < checks - 1:
            print(f"\n[WAITING] Next check in {check_interval}s...")
            await asyncio.sleep(check_interval)

    print("\n" + "=" * 70)
    print("MONITORING COMPLETE")
    print("=" * 70)


async def main():
    # Single scan
    print("\n[MODE 1] Single Scan")
    opportunities = await scan_buy_opportunities()

    # Live monitoring (demo: 5 minutes)
    print("\n[MODE 2] Live Monitoring (5 min demo)")

    choice = input("\nRun live monitor? (y/n): ").lower()

    if choice == 'y':
        await monitor_migrations_live(check_interval=30, duration_minutes=5)
    else:
        print("\nSkipping live monitor")

    print("\n" + "=" * 70)
    print("MIGRATION SNIPER COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

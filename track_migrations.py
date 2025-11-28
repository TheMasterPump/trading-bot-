"""
TRACK MIGRATIONS EN TEMPS REEL
Detecter quand un token est proche de migrer de pump.fun vers pumpswap
Migration = ~$69k market cap (bonding curve completion)
"""
import asyncio
import httpx
import json
from datetime import datetime

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

# Les 34 winners du wallet concurrent (extrait de l'analyse)
WINNERS = [
    {"mint": "56R6sfGi443LUjjD2XBXS3nwfdu54m8LxAD9zyqpump", "profit": 6202.77, "roi": 1530},
    {"mint": "GmhtrvXzyAv53AvZgr41BvjP8Myo25DsahcAXVTbpump", "profit": 4076.91, "roi": 1006},
    {"mint": "9RyccYX3NgUVHbNiQwW71Y78xPGRH7uDKdPinWRQpump", "profit": 2701.74, "roi": 666},
    {"mint": "8dwC2K6jeNFCE1ZBWcLqTbqGkvSghMkb1m5dpXYLpump", "profit": 2683.79, "roi": 662},  # LIVEBEAR
    {"mint": "3eaiHTfdR1a84cp34UJVxLXQS9fvcbQw8cxAqN5Npump", "profit": 2261.20, "roi": 558},
    {"mint": "9XJ1FpdGVEMrRr7RWfHjN8f1eL7PkVYd1YBMJKLApump", "profit": 2251.82, "roi": 555},
    {"mint": "2dvRDyoSKCNNpSisoM8V9vJ3nF3yY7KQxPx6vM2Vpump", "profit": 2086.36, "roi": 515},
    {"mint": "8RSbsKW26WhHsFsMnjqSYwTwwLVfL9YCb6x3eVQ8pump", "profit": 1985.64, "roi": 490},
    {"mint": "8xTDsy1UFBYK1J37uWnZvD8LyJKqVx4xBYp2Ck7jpump", "profit": 1913.49, "roi": 472},
    {"mint": "H3rPPzcSUFdnHNEjE8P4aW9V5Ym2xLz3YK8wNxRVpump", "profit": 1822.51, "roi": 450},
]

# Seuils de migration pump.fun
MIGRATION_THRESHOLDS = {
    'bonding_curve_pct': 95,     # 95%+ de la bonding curve = proche migration
    'target_market_cap': 69000,  # ~$69k = migration
    'min_market_cap': 10000,     # $10k min pour acheter
    'max_market_cap': 50000,     # $50k max pour acheter (avant migration)
}


async def get_token_status(token_mint):
    """Get current status of a token from pump.fun"""
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


async def check_migration_status(token_data):
    """Check if token is close to migration"""
    if not token_data:
        return None

    market_cap = token_data.get('usd_market_cap', 0)

    # Check if raydium_pool exists (means already migrated)
    raydium_pool = token_data.get('raydium_pool')
    complete = token_data.get('complete', False)

    # Calculate bonding curve progress
    # pump.fun bonding curve completes at ~85 SOL / $69k
    bonding_progress = (market_cap / MIGRATION_THRESHOLDS['target_market_cap']) * 100

    status = {
        'market_cap': market_cap,
        'bonding_progress': bonding_progress,
        'is_migrated': bool(raydium_pool) or complete,
        'raydium_pool': raydium_pool,
        'distance_to_migration': MIGRATION_THRESHOLDS['target_market_cap'] - market_cap,
    }

    # Determine phase
    if status['is_migrated']:
        status['phase'] = 'POST_MIGRATION'
        status['action'] = 'SELL (multi-sell strategy)'
    elif bonding_progress >= 95:
        status['phase'] = 'PRE_MIGRATION (imminent)'
        status['action'] = 'HOLD (migration incoming)'
    elif MIGRATION_THRESHOLDS['min_market_cap'] <= market_cap <= MIGRATION_THRESHOLDS['max_market_cap']:
        status['phase'] = 'BUY_ZONE'
        status['action'] = 'BUY (optimal entry)'
    elif market_cap < MIGRATION_THRESHOLDS['min_market_cap']:
        status['phase'] = 'TOO_EARLY'
        status['action'] = 'WAIT'
    else:
        status['phase'] = 'RISKY_ZONE'
        status['action'] = 'CAUTION (close to migration)'

    return status


async def analyze_winner_migrations():
    """Analyze migration patterns from the 34 winners"""

    print("=" * 70)
    print("ANALYZING WINNER MIGRATION PATTERNS")
    print("=" * 70)
    print(f"Analyzing {len(WINNERS)} winning tokens...")
    print(f"Target: Understand WHEN they were bought relative to migration")
    print("=" * 70)

    results = []

    for i, winner in enumerate(WINNERS, 1):
        mint = winner['mint']
        profit = winner['profit']
        roi = winner['roi']

        print(f"\n[{i}/{len(WINNERS)}] {mint[:16]}... | Profit: ${profit:,.2f} | ROI: +{roi}%")

        # Get current status
        token_data = await get_token_status(mint)

        if not token_data:
            print(f"  [!] Token data not available (may be old/delisted)")
            continue

        # Check migration status
        status = await check_migration_status(token_data)

        if status:
            print(f"  Current Market Cap: ${status['market_cap']:,.0f}")
            print(f"  Bonding Progress: {status['bonding_progress']:.1f}%")
            print(f"  Status: {status['phase']}")
            print(f"  Is Migrated: {'YES' if status['is_migrated'] else 'NO'}")

            if status['is_migrated'] and status['raydium_pool']:
                print(f"  Raydium Pool: {status['raydium_pool'][:16]}...")

            results.append({
                'winner': winner,
                'current_status': status,
                'token_data': {
                    'name': token_data.get('name'),
                    'symbol': token_data.get('symbol'),
                    'created': token_data.get('created_timestamp'),
                }
            })

        await asyncio.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("MIGRATION PATTERN SUMMARY")
    print("=" * 70)

    migrated_count = sum(1 for r in results if r['current_status']['is_migrated'])

    print(f"\nTokens analyzed: {len(results)}")
    print(f"Currently migrated: {migrated_count}/{len(results)}")
    print(f"Still on bonding curve: {len(results) - migrated_count}/{len(results)}")

    # Average market caps
    if results:
        avg_current_mc = sum(r['current_status']['market_cap'] for r in results) / len(results)
        print(f"\nAverage current market cap: ${avg_current_mc:,.0f}")

    print("\n" + "=" * 70)
    print("KEY INSIGHTS")
    print("=" * 70)
    print("\n1. BUY ZONE: $10k - $50k market cap")
    print("   - Entry point AVANT la migration")
    print("   - Bonding curve: 14% - 72% complete")
    print("")
    print("2. MIGRATION TRIGGER: ~$69k market cap")
    print("   - Bonding curve 100% complete")
    print("   - Token graduates to Raydium/Pumpswap")
    print("")
    print("3. SELL ZONE: POST-MIGRATION")
    print("   - Multi-sell strategy (60-87 portions)")
    print("   - Price pumps after migration liquidity")
    print("")
    print("4. TIMING IS CRITICAL:")
    print("   - Too early (<$10k): Risque de rug/abandon")
    print("   - Buy zone ($10k-$50k): OPTIMAL ✓")
    print("   - Too late (>$50k): Proche migration, risque elevé")

    print("\n" + "=" * 70)

    return results


async def monitor_live_migrations(check_interval=60):
    """Monitor tokens in real-time for migration opportunities"""

    print("\n" + "=" * 70)
    print("LIVE MIGRATION MONITOR")
    print("=" * 70)
    print(f"Checking pump.fun for tokens in BUY ZONE...")
    print(f"Target: Market cap $10k - $50k")
    print("=" * 70)

    iteration = 0

    while iteration < 3:  # Demo: 3 checks
        iteration += 1
        print(f"\n[CHECK {iteration}] {datetime.now().strftime('%H:%M:%S')}")

        client = httpx.AsyncClient(timeout=30.0)

        try:
            # Get recent tokens
            url = "https://frontend-api.pump.fun/coins?limit=20&sort=created_timestamp&order=DESC"
            response = await client.get(url)

            if response.status_code == 200:
                tokens = response.json()

                buy_opportunities = []

                for token in tokens:
                    market_cap = token.get('usd_market_cap', 0)

                    # Check if in buy zone
                    if MIGRATION_THRESHOLDS['min_market_cap'] <= market_cap <= MIGRATION_THRESHOLDS['max_market_cap']:

                        status = await check_migration_status(token)

                        if status and status['phase'] == 'BUY_ZONE':
                            buy_opportunities.append({
                                'token': token,
                                'status': status
                            })

                if buy_opportunities:
                    print(f"\n[OPPORTUNITIES] Found {len(buy_opportunities)} tokens in BUY ZONE:")

                    for opp in buy_opportunities[:5]:  # Show top 5
                        t = opp['token']
                        s = opp['status']

                        print(f"\n  {t['symbol']}")
                        print(f"    Mint: {t['mint'][:16]}...")
                        print(f"    Market Cap: ${s['market_cap']:,.0f}")
                        print(f"    Distance to migration: ${s['distance_to_migration']:,.0f}")
                        print(f"    Bonding: {s['bonding_progress']:.1f}%")
                        print(f"    Action: {s['action']}")
                else:
                    print(f"  No tokens in optimal buy zone right now")

        except Exception as e:
            print(f"  [!] Error: {e}")

        await client.aclose()

        if iteration < 3:
            print(f"\n  Waiting {check_interval}s before next check...")
            await asyncio.sleep(check_interval)

    print("\n" + "=" * 70)


async def main():
    # Analyze historical winners
    print("\n[PHASE 1] Analyzing historical winners...")
    winner_results = await analyze_winner_migrations()

    # Monitor live
    print("\n[PHASE 2] Monitoring live migrations...")
    await monitor_live_migrations(check_interval=10)

    # Save results
    print("\n[SAVING RESULTS]")

    with open('winner_migrations.json', 'w') as f:
        json.dump({
            'analyzed_at': datetime.now().isoformat(),
            'winners': WINNERS,
            'migration_thresholds': MIGRATION_THRESHOLDS,
            'results': winner_results
        }, f, indent=2, default=str)

    print("  Saved to: winner_migrations.json")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

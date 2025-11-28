"""
ANALYZE PRE/POST MIGRATION STRATEGY
Utiliser 2 APIs : pump.fun pour achats pre-migration, DEX pour ventes post-migration
"""
import asyncio
import httpx
from datetime import datetime
from collections import defaultdict

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"

async def get_all_swaps(wallet_address: str):
    """Recupere tous les swaps"""
    client = httpx.AsyncClient(timeout=60.0)

    print(f"\n[*] Fetching all swaps...")

    all_transactions = []
    before_signature = None

    for batch in range(20):
        url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
        params = {
            "api-key": HELIUS_API_KEY,
            "limit": 100
        }

        if before_signature:
            params["before"] = before_signature

        try:
            response = await client.get(url, params=params)

            if response.status_code == 200:
                transactions = response.json()

                if not transactions:
                    break

                all_transactions.extend(transactions)
                before_signature = transactions[-1].get('signature')

                if len(transactions) < 100:
                    break
            else:
                break

        except Exception as e:
            print(f"[!] Error: {e}")
            break

    await client.aclose()
    return all_transactions


def identify_pump_fun_vs_raydium(tx):
    """Identifier si c'est pump.fun ou Raydium"""

    # Check program IDs
    account_data = tx.get('accountData', [])

    # Pump.fun program ID
    PUMPFUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

    # Raydium program IDs
    RAYDIUM_PROGRAMS = [
        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",  # Raydium AMM
        "5quBtoiQqxF9Jv6KYKctB59NT3gtJD2Y65kdnB1Uev3h",  # Raydium V4
    ]

    # Jupiter program ID
    JUPITER_PROGRAM = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"

    for acc in account_data:
        account = acc.get('account', '')

        if account == PUMPFUN_PROGRAM:
            return "PUMPFUN"

        if account in RAYDIUM_PROGRAMS:
            return "RAYDIUM"

        if account == JUPITER_PROGRAM:
            return "JUPITER"

    # Check description for hints
    description = tx.get('description', '').lower()

    if 'pump' in description:
        return "PUMPFUN"
    if 'raydium' in description:
        return "RAYDIUM"
    if 'jupiter' in description:
        return "JUPITER"

    return "UNKNOWN"


async def check_if_token_migrated(token_mint: str):
    """Verifier si un token a migre de pump.fun"""
    client = httpx.AsyncClient(timeout=30.0)

    try:
        # Check pump.fun API
        url = f"https://frontend-api.pump.fun/coins/{token_mint}"
        response = await client.get(url)

        if response.status_code == 200:
            data = response.json()
            is_complete = data.get('complete', False)

            await client.aclose()
            return is_complete  # True = migrated

        await client.aclose()
        return None  # Not a pump.fun token or error

    except Exception as e:
        await client.aclose()
        return None


async def analyze_pre_post_migration(wallet_address: str):
    """Analyser la strategie pre/post migration"""

    print("=" * 70)
    print("PRE/POST MIGRATION STRATEGY ANALYZER")
    print("=" * 70)
    print(f"Wallet: {wallet_address}")
    print("=" * 70)

    # Get all transactions
    transactions = await get_all_swaps(wallet_address)
    print(f"\n[+] Total transactions: {len(transactions)}")

    # Categorize by platform
    print("\n[*] Categorizing swaps by platform...")

    swaps_by_platform = defaultdict(list)

    for tx in transactions:
        if tx.get('type') != 'SWAP':
            continue

        platform = identify_pump_fun_vs_raydium(tx)
        swaps_by_platform[platform].append(tx)

    print("\n[PLATFORM BREAKDOWN]")
    for platform, swaps in swaps_by_platform.items():
        print(f"  {platform}: {len(swaps)} swaps")

    # Analyze each platform
    print("\n" + "=" * 70)
    print("ANALYZING BY PLATFORM")
    print("=" * 70)

    total_pnl = 0

    for platform, swaps in swaps_by_platform.items():
        print(f"\n--- {platform} ---")

        sol_spent = 0
        sol_received = 0

        buys = 0
        sells = 0

        for tx in swaps:
            # Get SOL change
            account_data = tx.get('accountData', [])
            for acc in account_data:
                if acc.get('account') == wallet_address:
                    balance_change = acc.get('nativeBalanceChange', 0) / 1e9

                    if balance_change > 0:
                        sol_received += balance_change
                        sells += 1
                    elif balance_change < 0:
                        sol_spent += abs(balance_change)
                        buys += 1

        pnl = sol_received - sol_spent
        pnl_usd = pnl * 200

        print(f"Buys: {buys}")
        print(f"Sells: {sells}")
        print(f"SOL spent: {sol_spent:.4f} SOL (${sol_spent * 200:.2f})")
        print(f"SOL received: {sol_received:.4f} SOL (${sol_received * 200:.2f})")
        print(f"P&L: {pnl:+.4f} SOL (${pnl_usd:+.2f})")

        total_pnl += pnl_usd

    # Overall summary
    print("\n" + "=" * 70)
    print("OVERALL STRATEGY SUMMARY")
    print("=" * 70)

    print(f"\nTotal P&L (all platforms): ${total_pnl:+.2f}")

    # Show detailed trades
    print("\n[*] Analyzing token-by-token...")

    # Group by token
    by_token = defaultdict(lambda: {'buys': [], 'sells': [], 'platforms': set()})

    for platform, swaps in swaps_by_platform.items():
        for tx in swaps:
            # Get token
            token_transfers = tx.get('tokenTransfers', [])

            for tt in token_transfers:
                mint = tt.get('mint')

                if tt.get('toUserAccount') == wallet_address:
                    # BUY
                    by_token[mint]['buys'].append({'tx': tx, 'platform': platform})
                    by_token[mint]['platforms'].add(platform)
                elif tt.get('fromUserAccount') == wallet_address:
                    # SELL
                    by_token[mint]['sells'].append({'tx': tx, 'platform': platform})
                    by_token[mint]['platforms'].add(platform)

    print(f"\n[+] Found {len(by_token)} unique tokens")

    # Find cross-platform trades (buy on pump.fun, sell on Raydium)
    print("\n" + "=" * 70)
    print("CROSS-PLATFORM TRADES")
    print("(Buy on PUMPFUN, Sell on RAYDIUM/JUPITER)")
    print("=" * 70)

    cross_platform_trades = []

    for mint, data in by_token.items():
        platforms = data['platforms']

        # Check if bought on pump.fun and sold elsewhere
        buy_platforms = set(b['platform'] for b in data['buys'])
        sell_platforms = set(s['platform'] for s in data['sells'])

        if 'PUMPFUN' in buy_platforms and ('RAYDIUM' in sell_platforms or 'JUPITER' in sell_platforms):
            cross_platform_trades.append({
                'mint': mint,
                'buy_platform': list(buy_platforms),
                'sell_platform': list(sell_platforms),
                'buys': len(data['buys']),
                'sells': len(data['sells'])
            })

    print(f"\n[+] Found {len(cross_platform_trades)} cross-platform trades!")

    if cross_platform_trades:
        print("\n[MIGRATION STRATEGY CONFIRMED]")
        for i, trade in enumerate(cross_platform_trades[:10], 1):
            print(f"\n{i}. Token: {trade['mint'][:16]}...")
            print(f"   Buy on: {', '.join(trade['buy_platform'])}")
            print(f"   Sell on: {', '.join(trade['sell_platform'])}")
            print(f"   Buys: {trade['buys']} | Sells: {trade['sells']}")

    print("\n" + "=" * 70)


async def main():
    wallet = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"
    await analyze_pre_post_migration(wallet)


if __name__ == "__main__":
    asyncio.run(main())

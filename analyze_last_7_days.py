"""
ANALYZE LAST 7 DAYS STRATEGY
Focus sur les 7 derniers jours pour identifier la strategie actuelle
"""
import asyncio
import httpx
import json
from datetime import datetime, timedelta
from collections import defaultdict

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"
WALLET = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"
SOL_PRICE = 200.0

async def get_recent_signatures(days=7):
    """Get signatures from last N days"""
    client = httpx.AsyncClient(timeout=120.0)
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    cutoff_time = int((datetime.now() - timedelta(days=days)).timestamp())

    print(f"\n[*] Fetching signatures from last {days} days...", flush=True)

    all_signatures = []
    before = None

    for batch in range(100):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [WALLET, {"limit": 1000}]
        }

        if before:
            payload["params"][1]["before"] = before

        try:
            response = await client.post(rpc_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                result = data.get('result', [])
                if not result:
                    break

                # Filter by time
                for sig in result:
                    if sig.get('blockTime', 0) >= cutoff_time:
                        all_signatures.append(sig)
                    else:
                        print(f"[+] Reached cutoff time. Total: {len(all_signatures)} signatures", flush=True)
                        await client.aclose()
                        return all_signatures

                before = result[-1]['signature']

                if (batch + 1) % 5 == 0:
                    print(f"[+] {len(all_signatures)} signatures so far...", flush=True)

                if len(result) < 1000:
                    break
        except Exception as e:
            print(f"[!] Error: {e}", flush=True)
            break

    print(f"[+] Total: {len(all_signatures)} signatures", flush=True)
    await client.aclose()
    return all_signatures


async def get_transaction(signature, client, rpc_url):
    """Get transaction details"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
        ]
    }

    try:
        response = await client.post(rpc_url, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data.get('result')
    except:
        pass
    return None


async def analyze_recent_activity(days=7):
    """Analyze recent trading activity"""

    print("=" * 70, flush=True)
    print(f"LAST {days} DAYS STRATEGY ANALYSIS", flush=True)
    print("=" * 70, flush=True)
    print(f"Wallet: {WALLET}", flush=True)
    print("=" * 70, flush=True)

    # Get recent signatures
    signatures = await get_recent_signatures(days)

    if not signatures:
        print("\n[!] No recent signatures!", flush=True)
        return

    print(f"\n[*] Analyzing {len(signatures)} transactions...", flush=True)

    client = httpx.AsyncClient(timeout=60.0)
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    # Collect all token trades
    token_trades = defaultdict(lambda: {'buys': [], 'sells': []})

    for i, sig_data in enumerate(signatures):
        signature = sig_data['signature']
        tx = await get_transaction(signature, client, rpc_url)

        if not tx:
            continue

        meta = tx.get('meta', {})
        if meta.get('err'):
            continue

        pre_token_balances = meta.get('preTokenBalances', [])
        post_token_balances = meta.get('postTokenBalances', [])
        pre_balances = meta.get('preBalances', [])
        post_balances = meta.get('postBalances', [])
        account_keys = tx.get('transaction', {}).get('message', {}).get('accountKeys', [])

        # Find wallet index
        wallet_index = None
        for idx, acc in enumerate(account_keys):
            if isinstance(acc, dict):
                if acc.get('pubkey') == WALLET:
                    wallet_index = idx
                    break
            elif acc == WALLET:
                wallet_index = idx
                break

        if wallet_index is None:
            continue

        # Calculate SOL change
        sol_change = 0
        if wallet_index < len(pre_balances) and wallet_index < len(post_balances):
            sol_change = (post_balances[wallet_index] - pre_balances[wallet_index]) / 1e9

        # Find token changes
        token_changes = {}

        for bal in pre_token_balances:
            if bal.get('owner') == WALLET:
                mint = bal.get('mint')
                ui_amount = bal.get('uiTokenAmount', {}).get('uiAmount')
                amount = float(ui_amount) if ui_amount is not None else 0.0
                if mint not in token_changes:
                    token_changes[mint] = {'pre': 0, 'post': 0}
                token_changes[mint]['pre'] = amount

        for bal in post_token_balances:
            if bal.get('owner') == WALLET:
                mint = bal.get('mint')
                ui_amount = bal.get('uiTokenAmount', {}).get('uiAmount')
                amount = float(ui_amount) if ui_amount is not None else 0.0
                if mint not in token_changes:
                    token_changes[mint] = {'pre': 0, 'post': 0}
                token_changes[mint]['post'] = amount

        timestamp = tx.get('blockTime', 0)

        for mint, changes in token_changes.items():
            token_change = changes['post'] - changes['pre']

            if token_change > 0 and sol_change < 0:
                # BUY
                token_trades[mint]['buys'].append({
                    'timestamp': timestamp,
                    'tokens': token_change,
                    'sol': abs(sol_change),
                    'usd': abs(sol_change) * SOL_PRICE
                })
            elif token_change < 0 and sol_change > 0:
                # SELL
                token_trades[mint]['sells'].append({
                    'timestamp': timestamp,
                    'tokens': abs(token_change),
                    'sol': sol_change,
                    'usd': sol_change * SOL_PRICE
                })

        if (i + 1) % 100 == 0:
            print(f"[+] Processed {i + 1}/{len(signatures)} transactions ({len(token_trades)} tokens found)", flush=True)

    await client.aclose()

    print(f"\n[+] Found {len(token_trades)} unique tokens", flush=True)

    # Calculate P&L for each token
    results = []

    for mint, trades in token_trades.items():
        total_buy_sol = sum(b['sol'] for b in trades['buys'])
        total_sell_sol = sum(s['sol'] for s in trades['sells'])

        pnl_sol = total_sell_sol - total_buy_sol
        pnl_usd = pnl_sol * SOL_PRICE

        roi = ((total_sell_sol / total_buy_sol) - 1) * 100 if total_buy_sol > 0 else 0

        first_trade = 0
        last_trade = 0

        all_times = [b['timestamp'] for b in trades['buys']] + [s['timestamp'] for s in trades['sells']]
        if all_times:
            first_trade = min(all_times)
            last_trade = max(all_times)

        results.append({
            'mint': mint,
            'buys': len(trades['buys']),
            'sells': len(trades['sells']),
            'buy_sol': total_buy_sol,
            'sell_sol': total_sell_sol,
            'pnl_sol': pnl_sol,
            'pnl_usd': pnl_usd,
            'roi': roi,
            'first_trade': first_trade,
            'last_trade': last_trade,
            'duration_hours': (last_trade - first_trade) / 3600 if first_trade else 0
        })

    # Results
    print("\n" + "=" * 70, flush=True)
    print("RESULTS", flush=True)
    print("=" * 70, flush=True)

    profitable = [r for r in results if r['pnl_usd'] > 0]
    losing = [r for r in results if r['pnl_usd'] < 0]
    ongoing = [r for r in results if r['buys'] > 0 and r['sells'] == 0]

    total_pnl = sum(r['pnl_usd'] for r in results)
    total_invested = sum(r['buy_sol'] for r in results) * SOL_PRICE

    print(f"\nPerformance (Last {days} Days):", flush=True)
    print(f"  Total Tokens Traded: {len(results)}", flush=True)
    print(f"  Total P&L: ${total_pnl:+,.2f}", flush=True)
    print(f"  Total Invested: ${total_invested:,.2f}", flush=True)
    print(f"  Winners: {len(profitable)} ({len(profitable)/len(results)*100:.1f}%)", flush=True)
    print(f"  Losers: {len(losing)} ({len(losing)/len(results)*100:.1f}%)", flush=True)
    print(f"  Ongoing positions: {len(ongoing)}", flush=True)

    print(f"\n[TOP 10 WINNERS]", flush=True)
    winners = sorted(results, key=lambda x: x['pnl_usd'], reverse=True)[:10]
    for i, r in enumerate(winners, 1):
        dt = datetime.fromtimestamp(r['first_trade']).strftime('%Y-%m-%d %H:%M')
        print(f"  {i}. {r['mint'][:16]}... | ${r['pnl_usd']:+,.2f} | ROI: {r['roi']:+.0f}% | {r['buys']}B/{r['sells']}S | {dt}", flush=True)

    print(f"\n[TOP 5 LOSERS]", flush=True)
    losers = sorted(results, key=lambda x: x['pnl_usd'])[:5]
    for i, r in enumerate(losers, 1):
        dt = datetime.fromtimestamp(r['first_trade']).strftime('%Y-%m-%d %H:%M')
        print(f"  {i}. {r['mint'][:16]}... | ${r['pnl_usd']:+,.2f} | ROI: {r['roi']:+.0f}% | {r['buys']}B/{r['sells']}S | {dt}", flush=True)

    print(f"\n[ONGOING POSITIONS]", flush=True)
    for i, r in enumerate(ongoing[:5], 1):
        dt = datetime.fromtimestamp(r['first_trade']).strftime('%Y-%m-%d %H:%M')
        print(f"  {i}. {r['mint'][:16]}... | Invested: ${r['buy_sol'] * SOL_PRICE:,.2f} | {r['buys']} buys | {dt}", flush=True)

    # Pattern analysis
    print(f"\n[STRATEGY PATTERNS]", flush=True)

    if profitable:
        avg_roi_winners = sum(r['roi'] for r in profitable) / len(profitable)
        avg_duration_winners = sum(r['duration_hours'] for r in profitable) / len(profitable)
        avg_trades_winners = sum(r['buys'] + r['sells'] for r in profitable) / len(profitable)

        print(f"  Winners:", flush=True)
        print(f"    Average ROI: {avg_roi_winners:+.1f}%", flush=True)
        print(f"    Average Duration: {avg_duration_winners:.1f} hours", flush=True)
        print(f"    Average Trades: {avg_trades_winners:.1f}", flush=True)

    # Quick flips (< 1 hour)
    quick_flips = [r for r in results if r['duration_hours'] < 1 and r['sells'] > 0]
    quick_flip_winners = [r for r in quick_flips if r['pnl_usd'] > 0]

    if quick_flips:
        print(f"\n  Quick Flips (<1 hour):", flush=True)
        print(f"    Total: {len(quick_flips)}", flush=True)
        print(f"    Winners: {len(quick_flip_winners)} ({len(quick_flip_winners)/len(quick_flips)*100:.1f}%)", flush=True)
        if quick_flip_winners:
            avg_pnl = sum(r['pnl_usd'] for r in quick_flip_winners) / len(quick_flip_winners)
            print(f"    Average profit: ${avg_pnl:,.2f}", flush=True)

    # Multi-sell strategy (like LIVEBEAR)
    multi_sell = [r for r in results if r['buys'] == 1 and r['sells'] > 10]
    multi_sell_winners = [r for r in multi_sell if r['pnl_usd'] > 0]

    if multi_sell:
        print(f"\n  Multi-Sell Strategy (1 buy, 10+ sells):", flush=True)
        print(f"    Total: {len(multi_sell)}", flush=True)
        print(f"    Winners: {len(multi_sell_winners)} ({len(multi_sell_winners)/len(multi_sell)*100:.1f}%)", flush=True)
        if multi_sell_winners:
            avg_pnl = sum(r['pnl_usd'] for r in multi_sell_winners) / len(multi_sell_winners)
            avg_sells = sum(r['sells'] for r in multi_sell_winners) / len(multi_sell_winners)
            print(f"    Average profit: ${avg_pnl:,.2f}", flush=True)
            print(f"    Average sells: {avg_sells:.0f}", flush=True)

    print("\n" + "=" * 70, flush=True)


async def main():
    await analyze_recent_activity(days=7)


if __name__ == "__main__":
    asyncio.run(main())

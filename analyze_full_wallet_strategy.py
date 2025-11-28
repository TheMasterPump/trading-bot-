"""
ANALYZE FULL WALLET STRATEGY
Analyser tous les tokens pour identifier la strategie complete
"""
import asyncio
import httpx
import json
from datetime import datetime
from collections import defaultdict

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"
WALLET = "BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE"
SOL_PRICE = 200.0

async def get_all_signatures():
    """Get all signatures from wallet"""
    client = httpx.AsyncClient(timeout=120.0)
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    print(f"\n[*] Fetching all signatures...")

    all_signatures = []
    before = None

    for batch in range(200):
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

                all_signatures.extend(result)
                before = result[-1]['signature']

                if (batch + 1) % 10 == 0:
                    print(f"[+] {len(all_signatures)} signatures...")

                if len(result) < 1000:
                    break
        except:
            break

    print(f"[+] Total: {len(all_signatures)} signatures")
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


async def analyze_token_pnl(token_mint, transactions, client, rpc_url):
    """Analyze P&L for a specific token"""
    buys = []
    sells = []

    for sig_data in transactions:
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
        for i, acc in enumerate(account_keys):
            if isinstance(acc, dict):
                if acc.get('pubkey') == WALLET:
                    wallet_index = i
                    break
            elif acc == WALLET:
                wallet_index = i
                break

        if wallet_index is None:
            continue

        # Calculate SOL change
        sol_change = 0
        if wallet_index < len(pre_balances) and wallet_index < len(post_balances):
            sol_change = (post_balances[wallet_index] - pre_balances[wallet_index]) / 1e9

        # Find token balance change
        pre_amount = 0
        post_amount = 0

        for bal in pre_token_balances:
            if bal.get('mint') == token_mint and bal.get('owner') == WALLET:
                pre_amount = float(bal.get('uiTokenAmount', {}).get('uiAmount', 0))

        for bal in post_token_balances:
            if bal.get('mint') == token_mint and bal.get('owner') == WALLET:
                post_amount = float(bal.get('uiTokenAmount', {}).get('uiAmount', 0))

        token_change = post_amount - pre_amount

        timestamp = tx.get('blockTime', 0)

        if token_change > 0 and sol_change < 0:
            # BUY
            buys.append({
                'signature': signature,
                'timestamp': timestamp,
                'tokens': token_change,
                'sol': abs(sol_change),
                'usd': abs(sol_change) * SOL_PRICE
            })
        elif token_change < 0 and sol_change > 0:
            # SELL
            sells.append({
                'signature': signature,
                'timestamp': timestamp,
                'tokens': abs(token_change),
                'sol': sol_change,
                'usd': sol_change * SOL_PRICE
            })

    total_buy_sol = sum(b['sol'] for b in buys)
    total_sell_sol = sum(s['sol'] for s in sells)

    pnl_sol = total_sell_sol - total_buy_sol
    pnl_usd = pnl_sol * SOL_PRICE

    roi = ((total_sell_sol / total_buy_sol) - 1) * 100 if total_buy_sol > 0 else 0

    return {
        'mint': token_mint,
        'buys': len(buys),
        'sells': len(sells),
        'buy_sol': total_buy_sol,
        'sell_sol': total_sell_sol,
        'pnl_sol': pnl_sol,
        'pnl_usd': pnl_usd,
        'roi': roi,
        'first_trade': min([b['timestamp'] for b in buys] + [s['timestamp'] for s in sells]) if buys or sells else 0,
        'last_trade': max([b['timestamp'] for b in buys] + [s['timestamp'] for s in sells]) if buys or sells else 0
    }


async def main():
    print("=" * 70)
    print("FULL WALLET STRATEGY ANALYSIS")
    print("=" * 70)
    print(f"Wallet: {WALLET}")
    print("=" * 70)

    # Get all signatures
    signatures = await get_all_signatures()

    if not signatures:
        print("\n[!] No signatures!")
        return

    print(f"\n[*] Analyzing first 10,000 transactions for tokens...")

    client = httpx.AsyncClient(timeout=60.0)
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

    # First pass: collect all tokens and their transaction counts
    token_transactions = defaultdict(list)

    batch_size = 50
    max_analyze = min(10000, len(signatures))

    for i in range(0, max_analyze, batch_size):
        batch = signatures[i:i + batch_size]
        batch_num = i // batch_size + 1

        for sig_data in batch:
            signature = sig_data['signature']
            tx = await get_transaction(signature, client, rpc_url)

            if not tx:
                continue

            meta = tx.get('meta', {})
            post_balances = meta.get('postTokenBalances', [])

            for bal in post_balances:
                mint = bal.get('mint')
                owner = bal.get('owner')
                if mint and owner == WALLET:
                    token_transactions[mint].append(sig_data)

        if batch_num % 20 == 0:
            print(f"[+] Processed {batch_num * batch_size}/{max_analyze} transactions ({len(token_transactions)} tokens found)")

    print(f"\n[+] Found {len(token_transactions)} unique tokens")

    # Sort tokens by transaction count
    sorted_tokens = sorted(token_transactions.items(), key=lambda x: len(x[1]), reverse=True)

    print(f"\n[*] Analyzing top 50 most traded tokens...")

    results = []

    for i, (token_mint, tx_list) in enumerate(sorted_tokens[:50], 1):
        print(f"\n[{i}/50] Analyzing token {token_mint[:16]}... ({len(tx_list)} transactions)")

        result = await analyze_token_pnl(token_mint, tx_list, client, rpc_url)
        results.append(result)

        print(f"        Buys: {result['buys']}, Sells: {result['sells']}, P&L: ${result['pnl_usd']:+.2f} (ROI: {result['roi']:+.1f}%)")

    await client.aclose()

    # Analysis
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    profitable = [r for r in results if r['pnl_usd'] > 0]
    losing = [r for r in results if r['pnl_usd'] < 0]

    total_pnl = sum(r['pnl_usd'] for r in results)
    total_invested = sum(r['buy_sol'] for r in results) * SOL_PRICE

    print(f"\nTop 50 Tokens Performance:")
    print(f"  Total P&L: ${total_pnl:+,.2f}")
    print(f"  Total Invested: ${total_invested:,.2f}")
    print(f"  Win Rate: {len(profitable)}/{len(results)} ({len(profitable)/len(results)*100:.1f}%)")

    print(f"\n[TOP 10 WINNERS]")
    winners = sorted(results, key=lambda x: x['pnl_usd'], reverse=True)[:10]
    for i, r in enumerate(winners, 1):
        print(f"  {i}. {r['mint'][:16]}... | P&L: ${r['pnl_usd']:+,.2f} | ROI: {r['roi']:+.1f}% | Trades: {r['buys']}B/{r['sells']}S")

    print(f"\n[TOP 10 LOSERS]")
    losers = sorted(results, key=lambda x: x['pnl_usd'])[:10]
    for i, r in enumerate(losers, 1):
        print(f"  {i}. {r['mint'][:16]}... | P&L: ${r['pnl_usd']:+,.2f} | ROI: {r['roi']:+.1f}% | Trades: {r['buys']}B/{r['sells']}S")

    # Pattern analysis
    print(f"\n[PATTERN ANALYSIS]")

    avg_roi_winners = sum(r['roi'] for r in profitable) / len(profitable) if profitable else 0
    avg_roi_losers = sum(r['roi'] for r in losing) / len(losing) if losing else 0

    avg_trades_winners = sum(r['buys'] + r['sells'] for r in profitable) / len(profitable) if profitable else 0
    avg_trades_losers = sum(r['buys'] + r['sells'] for r in losing) / len(losing) if losing else 0

    print(f"  Winners:")
    print(f"    Average ROI: {avg_roi_winners:+.1f}%")
    print(f"    Average Trades: {avg_trades_winners:.1f}")

    print(f"  Losers:")
    print(f"    Average ROI: {avg_roi_losers:+.1f}%")
    print(f"    Average Trades: {avg_trades_losers:.1f}")

    # Strategy insights
    print(f"\n[STRATEGY INSIGHTS]")

    high_volume_traders = [r for r in results if (r['buys'] + r['sells']) > 10]
    high_volume_winners = [r for r in high_volume_traders if r['pnl_usd'] > 0]

    print(f"  High volume trades (>10 transactions): {len(high_volume_traders)}")
    print(f"  High volume winners: {len(high_volume_winners)}/{len(high_volume_traders)} ({len(high_volume_winners)/len(high_volume_traders)*100:.1f}%)")

    quick_flippers = [r for r in results if (r['last_trade'] - r['first_trade']) < 3600]  # < 1 hour
    quick_flip_winners = [r for r in quick_flippers if r['pnl_usd'] > 0]

    print(f"  Quick flips (<1 hour): {len(quick_flippers)}")
    print(f"  Quick flip winners: {len(quick_flip_winners)}/{len(quick_flippers)} ({len(quick_flip_winners)/len(quick_flippers)*100:.1f}%)")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

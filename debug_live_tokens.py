"""
DEBUG - Affiche TOUS les tokens et pourquoi ils sont acceptés/refusés
"""
import asyncio
import json
import websockets
from datetime import datetime

OPTIMAL_WINDOW = {
    'min_mc': 9500,
    'max_mc': 13000,
}
SOL_PRICE_USD = 200

def calculate_score(token_data):
    """Score simplifié"""
    score = 0
    breakdown = {}

    # Transactions (0-40 pts)
    txn = token_data.get('txnCount', 0)
    if txn >= 100: txn_score = 40
    elif txn >= 50: txn_score = 35
    elif txn >= 30: txn_score = 30
    elif txn >= 20: txn_score = 25
    elif txn >= 10: txn_score = 20
    elif txn >= 5: txn_score = 15
    elif txn >= 3: txn_score = 10
    elif txn >= 1: txn_score = 5
    else: txn_score = 0
    score += txn_score
    breakdown['txn'] = txn_score

    # Initial Buy (0-20 pts)
    init = token_data.get('initialBuy', 0)
    if init > 2: init_score = 0
    elif init >= 1: init_score = 20
    elif init >= 0.5: init_score = 15
    elif init >= 0.2: init_score = 10
    else: init_score = 5
    score += init_score
    breakdown['init'] = init_score

    # MC (0-20 pts)
    mc = token_data.get('market_cap_usd', 0)
    if OPTIMAL_WINDOW['min_mc'] <= mc <= OPTIMAL_WINDOW['max_mc']:
        if mc <= 10500: mc_score = 20
        elif mc <= 11500: mc_score = 15
        else: mc_score = 10
    else:
        mc_score = 0
    score += mc_score
    breakdown['mc'] = mc_score

    # Early bonus
    early_bonus = 15
    score += early_bonus
    breakdown['early'] = early_bonus

    # Social (0-10 pts)
    social = 0
    if token_data.get('twitter'): social += 4
    if token_data.get('telegram'): social += 3
    if token_data.get('website'): social += 3
    score += social
    breakdown['social'] = social

    # Bundle check
    holders = token_data.get('holderCount', 0)
    txn_count = token_data.get('txnCount', 0)
    bundle_penalty = 0
    if holders > 10 and txn_count > 0:
        ratio = txn_count / holders
        if ratio < 1.3:
            bundle_penalty = -20
        elif ratio < 1.5:
            bundle_penalty = -10
    score += bundle_penalty
    if bundle_penalty < 0:
        breakdown['bundle_penalty'] = bundle_penalty

    return {
        'total': max(0, min(score, 100)),
        'breakdown': breakdown,
        'should_buy': score >= 40,
        'confidence': 'HIGH' if score >= 60 else 'MEDIUM' if score >= 40 else 'LOW'
    }

async def debug_live():
    """Debug live"""
    print("\n" + "="*80)
    print("DEBUG MODE - Affiche TOUS les tokens et leur analyse")
    print("="*80)
    print(f"Fenêtre optimale: ${OPTIMAL_WINDOW['min_mc']:,} - ${OPTIMAL_WINDOW['max_mc']:,}")
    print("="*80 + "\n")

    tokens_seen = 0
    tokens_in_window = 0
    tokens_passed = 0

    try:
        async with websockets.connect('wss://pumpportal.fun/api/data') as ws:
            await ws.send(json.dumps({'method': 'subscribeNewToken'}))
            print("[CONNECTED] En écoute...\n")

            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(msg)

                    if not isinstance(data, dict):
                        continue

                    tokens_seen += 1

                    symbol = data.get('symbol', '???')
                    mc_sol = data.get('marketCapSol', 0)
                    mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0
                    holders = data.get('holderCount', 0)
                    volume_usd = data.get('usdMarketCap', mc_usd)
                    txn = data.get('txnCount', 0)
                    init_buy = data.get('initialBuy', 0)

                    # Afficher TOUS les tokens
                    print(f"\n[{tokens_seen}] {symbol} @ ${mc_usd:,.0f}")
                    print(f"  Holders: {holders} | Volume: ${volume_usd:,.0f} | Txn: {txn} | Init: {init_buy:.2f} SOL")

                    # Check fenêtre
                    if OPTIMAL_WINDOW['min_mc'] <= mc_usd <= OPTIMAL_WINDOW['max_mc']:
                        tokens_in_window += 1
                        print(f"  ✅ DANS LA FENÊTRE ${OPTIMAL_WINDOW['min_mc']:,}-${OPTIMAL_WINDOW['max_mc']:,}")

                        # Check filtres de base
                        if holders < 9:
                            print(f"  ❌ REJETÉ: Holders ({holders}) < 9")
                            continue

                        if volume_usd < 2000:
                            print(f"  ❌ REJETÉ: Volume (${volume_usd:.0f}) < $2K")
                            continue

                        print(f"  ✅ Passe les filtres de base")

                        # Score
                        token_data = {
                            'market_cap_usd': mc_usd,
                            'txnCount': txn,
                            'initialBuy': init_buy,
                            'holderCount': holders,
                            'twitter': data.get('twitter'),
                            'telegram': data.get('telegram'),
                            'website': data.get('website'),
                        }

                        score = calculate_score(token_data)

                        print(f"  Score: {score['total']}/100 ({score['confidence']})")
                        print(f"  Breakdown: {score['breakdown']}")

                        if score['should_buy']:
                            tokens_passed += 1
                            print(f"  ✅✅✅ ACHÈTERAIT CE TOKEN! (#{tokens_passed})")
                        else:
                            print(f"  ❌ REJETÉ: Score trop bas ({score['total']} < 40)")

                    elif mc_usd < OPTIMAL_WINDOW['min_mc']:
                        print(f"  ⏸️  En dessous de la fenêtre (${mc_usd:,.0f} < ${OPTIMAL_WINDOW['min_mc']:,})")
                    else:
                        print(f"  ⬆️  Au-dessus de la fenêtre (${mc_usd:,.0f} > ${OPTIMAL_WINDOW['max_mc']:,})")

                    # Stats
                    if tokens_seen % 10 == 0:
                        print(f"\n{'='*80}")
                        print(f"STATS: Scanned: {tokens_seen} | In window: {tokens_in_window} | Passed: {tokens_passed}")
                        print(f"{'='*80}\n")

                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue

    except KeyboardInterrupt:
        print(f"\n\n{'='*80}")
        print("RÉSUMÉ FINAL")
        print(f"{'='*80}")
        print(f"Tokens scannés: {tokens_seen}")
        print(f"Dans la fenêtre: {tokens_in_window}")
        print(f"Passeraient le score: {tokens_passed}")
        print(f"Taux de passage: {(tokens_passed/tokens_in_window*100) if tokens_in_window > 0 else 0:.1f}%")
        print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(debug_live())

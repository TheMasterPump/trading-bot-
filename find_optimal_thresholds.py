import json
import statistics

with open('bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

runners = [r for r in data['completed'] if r.get('is_runner', False)]
flops = [r for r in data['completed'] if not r.get('is_runner', False)]

print('=== RECHERCHE DES MEILLEURS SEUILS ===\n')

# Tester différents seuils sur le snapshot 15s
def test_threshold(buy_ratio_threshold, txn_threshold, traders_threshold, big_buys_threshold):
    runners_captured = 0
    flops_captured = 0

    for r in runners:
        snap = r.get('15s')
        if snap and isinstance(snap, dict):
            if (snap.get('buy_ratio', 0) * 100 >= buy_ratio_threshold and
                snap.get('txn', 0) >= txn_threshold and
                snap.get('traders', 0) >= traders_threshold and
                snap.get('big_buys_100', 0) >= big_buys_threshold):
                runners_captured += 1

    for f in flops:
        snap = f.get('15s')
        if snap and isinstance(snap, dict):
            if (snap.get('buy_ratio', 0) * 100 >= buy_ratio_threshold and
                snap.get('txn', 0) >= txn_threshold and
                snap.get('traders', 0) >= traders_threshold and
                snap.get('big_buys_100', 0) >= big_buys_threshold):
                flops_captured += 1

    runner_capture_rate = (runners_captured / len(runners)) * 100 if runners else 0
    precision = (runners_captured / (runners_captured + flops_captured)) * 100 if (runners_captured + flops_captured) > 0 else 0

    return runners_captured, flops_captured, runner_capture_rate, precision

print('Test de differents seuils a 15 secondes:\n')

configs = [
    # (buy_ratio, txn, traders, big_buys, nom)
    (60, 30, 20, 8, "Modere - Large"),
    (55, 25, 15, 6, "Liberal - Tres Large"),
    (65, 35, 25, 10, "Strict - Selectif"),
    (50, 20, 12, 5, "Ultra Liberal"),
    (58, 28, 18, 7, "Optimal Balance"),
]

best_config = None
best_score = 0

for buy_r, txn, traders, big_b, name in configs:
    r_cap, f_cap, r_rate, prec = test_threshold(buy_r, txn, traders, big_b)

    # Score = balance entre capture rate et precision
    score = (r_rate * 0.6) + (prec * 0.4)

    print(f'{name}:')
    print(f'  Buy Ratio >= {buy_r}% | Txn >= {txn} | Traders >= {traders} | BigBuys >= {big_b}')
    print(f'  Runners captures: {r_cap}/{len(runners)} ({r_rate:.1f}%)')
    print(f'  Flops captures: {f_cap}/{len(flops)} ({f_cap/len(flops)*100:.1f}%)')
    print(f'  Precision: {prec:.1f}% (quand signal, c\'est un runner)')
    print(f'  Score global: {score:.1f}')
    print()

    if score > best_score:
        best_score = score
        best_config = (buy_r, txn, traders, big_b, name)

print('='*80)
print(f'MEILLEURE CONFIGURATION: {best_config[4]}')
print(f'  Buy Ratio >= {best_config[0]}%')
print(f'  Transactions >= {best_config[1]}')
print(f'  Traders >= {best_config[2]}')
print(f'  Big Buys >= {best_config[3]}')
print(f'  Score: {best_score:.1f}')
print()

# Analyser à quelle MC les runners atteignent ces seuils
print('='*80)
print('=== A QUELLE MC LES RUNNERS ATTEIGNENT CES SEUILS ? ===\n')

best_buy_r, best_txn, best_traders, best_big_b, _ = best_config

entry_points = []
for r in runners:
    # Chercher le premier snapshot où les conditions sont remplies
    for snap_name in ['10s', '15s', '20s', '30s']:
        snap = r.get(snap_name)
        if snap and isinstance(snap, dict):
            if (snap.get('buy_ratio', 0) * 100 >= best_buy_r and
                snap.get('txn', 0) >= best_txn and
                snap.get('traders', 0) >= best_traders and
                snap.get('big_buys_100', 0) >= best_big_b):
                mc = snap.get('mc', 0)
                if mc > 0:
                    entry_points.append({
                        'symbol': r.get('symbol'),
                        'snapshot': snap_name,
                        'mc': mc,
                        'final_mc': r.get('final_mc', 0),
                        'potential_gain': ((r.get('final_mc', 0) - mc) / mc * 100) if mc > 0 else 0
                    })
                break

if entry_points:
    print(f'Runners detectes: {len(entry_points)}/{len(runners)}\n')

    entry_mcs = [e['mc'] for e in entry_points]
    gains = [e['potential_gain'] for e in entry_points if e['potential_gain'] > 0]

    print(f'MC d\'entree (quand signal detecte):')
    print(f'  Moyenne: ${statistics.mean(entry_mcs):,.0f}')
    print(f'  Mediane: ${statistics.median(entry_mcs):,.0f}')
    print(f'  Min: ${min(entry_mcs):,.0f}')
    print(f'  Max: ${max(entry_mcs):,.0f}')
    print()

    print(f'Gain potentiel si entree au signal:')
    print(f'  Moyenne: +{statistics.mean(gains):.0f}%')
    print(f'  Mediane: +{statistics.median(gains):.0f}%')
    print(f'  Min: +{min(gains):.0f}%')
    print(f'  Max: +{max(gains):.0f}%')
    print()

    # Montrer quelques exemples
    print('Exemples d\'entrees:')
    for e in sorted(entry_points, key=lambda x: x['potential_gain'], reverse=True)[:10]:
        print(f'  {e["symbol"]}: Entree @ ${e["mc"]:,.0f} ({e["snapshot"]}) -> ${e["final_mc"]:,.0f} = +{e["potential_gain"]:.0f}%')

print('\n' + '='*80)
print('=== RECOMMANDATION POUR TRADING BOT ===')
print('='*80)
print(f'\n1. SURVEILLER A 15 SECONDES:')
print(f'   - Buy Ratio >= {best_config[0]}%')
print(f'   - Transactions >= {best_config[1]}')
print(f'   - Traders >= {best_config[2]}')
print(f'   - Big Buys >= {best_config[3]}')
print(f'\n2. ENTREE IMMEDIATE quand conditions remplies')
print(f'   MC moyenne d\'entree: ~${statistics.median(entry_mcs) if entry_points else 0:,.0f}')
print(f'\n3. SORTIE:')
print(f'   - Target: $25K minimum (+150-300%)')
print(f'   - Stop: Buy ratio < 40% OU pas de volume')

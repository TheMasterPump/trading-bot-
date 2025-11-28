import json
import statistics

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

runners = d.get('runners', [])
flops = d.get('flops', [])

# Snapshots dans l'ordre chronologique
SNAPSHOTS = ['10s', '15s', '20s', '30s', '1min', '2min', '3min', '5min', '8min', '10min', '15min']

# Analyser les runners qui ont migré
migrated_runners = [r for r in runners if r.get('migration_detected')]

# Trouver ceux qui ont migré rapidement (≤ 3min)
fast_migrants = []
slow_migrants = []

for runner in migrated_runners:
    # Trouver le dernier snapshot disponible
    last_snapshot = None
    for snap in reversed(SNAPSHOTS):
        if snap in runner and runner[snap] and len(runner[snap]) > 0:
            last_snapshot = snap
            break

    # Classer comme rapide si dernier snapshot <= 3min
    if last_snapshot in ['10s', '15s', '20s', '30s', '1min', '2min', '3min']:
        fast_migrants.append(runner)
    else:
        slow_migrants.append(runner)

print('='*80)
print('ANALYSE DES PATTERNS - MIGRATIONS RAPIDES vs LENTES')
print('='*80)

print(f'\nTokens analyses:')
print(f'  - Migrations RAPIDES (<=3min): {len(fast_migrants)} tokens')
print(f'  - Migrations LENTES (>3min):   {len(slow_migrants)} tokens')

# Analyser les patterns aux snapshots précoces (30s et 1min)
for timepoint in ['30s', '1min']:
    print(f'\n{"="*80}')
    print(f'SNAPSHOT @ {timepoint.upper()}')
    print('='*80)

    # Collecter les métriques pour fast migrants
    fast_metrics = {
        'txn': [],
        'traders': [],
        'buy_ratio': [],
        'mc': [],
        'velocity': [],
        'big_buys': []
    }

    # Collecter les métriques pour slow migrants
    slow_metrics = {
        'txn': [],
        'traders': [],
        'buy_ratio': [],
        'mc': [],
        'velocity': [],
        'big_buys': []
    }

    # Collecter les métriques pour flops (pour comparaison)
    flop_metrics = {
        'txn': [],
        'traders': [],
        'buy_ratio': [],
        'mc': []
    }

    # Fast migrants
    for token in fast_migrants:
        snap = token.get(timepoint, {})
        if snap:
            fast_metrics['txn'].append(snap.get('txn', 0))
            fast_metrics['traders'].append(snap.get('traders', 0))
            fast_metrics['buy_ratio'].append(snap.get('buy_ratio', 0))
            fast_metrics['mc'].append(snap.get('mc', 0))
            fast_metrics['velocity'].append(snap.get('velocity', 0))

    # Slow migrants
    for token in slow_migrants:
        snap = token.get(timepoint, {})
        if snap:
            slow_metrics['txn'].append(snap.get('txn', 0))
            slow_metrics['traders'].append(snap.get('traders', 0))
            slow_metrics['buy_ratio'].append(snap.get('buy_ratio', 0))
            slow_metrics['mc'].append(snap.get('mc', 0))
            slow_metrics['velocity'].append(snap.get('velocity', 0))

    # Flops (échantillon)
    for token in flops[:100]:  # Prendre un échantillon
        snap = token.get(timepoint, {})
        if snap:
            flop_metrics['txn'].append(snap.get('txn', 0))
            flop_metrics['traders'].append(snap.get('traders', 0))
            flop_metrics['buy_ratio'].append(snap.get('buy_ratio', 0))
            flop_metrics['mc'].append(snap.get('mc', 0))

    # Afficher les comparaisons
    print(f'\n[TRANSACTIONS]')
    if fast_metrics['txn']:
        print(f'  Fast migrants: Moyenne={statistics.mean(fast_metrics["txn"]):.1f} | Médiane={statistics.median(fast_metrics["txn"]):.1f}')
    if slow_metrics['txn']:
        print(f'  Slow migrants: Moyenne={statistics.mean(slow_metrics["txn"]):.1f} | Médiane={statistics.median(slow_metrics["txn"]):.1f}')
    if flop_metrics['txn']:
        print(f'  Flops:         Moyenne={statistics.mean(flop_metrics["txn"]):.1f} | Médiane={statistics.median(flop_metrics["txn"]):.1f}')

    print(f'\n[TRADERS UNIQUES]')
    if fast_metrics['traders']:
        print(f'  Fast migrants: Moyenne={statistics.mean(fast_metrics["traders"]):.1f} | Médiane={statistics.median(fast_metrics["traders"]):.1f}')
    if slow_metrics['traders']:
        print(f'  Slow migrants: Moyenne={statistics.mean(slow_metrics["traders"]):.1f} | Médiane={statistics.median(slow_metrics["traders"]):.1f}')
    if flop_metrics['traders']:
        print(f'  Flops:         Moyenne={statistics.mean(flop_metrics["traders"]):.1f} | Médiane={statistics.median(flop_metrics["traders"]):.1f}')

    print(f'\n[BUY RATIO]')
    if fast_metrics['buy_ratio']:
        print(f'  Fast migrants: Moyenne={statistics.mean(fast_metrics["buy_ratio"])*100:.1f}% | Médiane={statistics.median(fast_metrics["buy_ratio"])*100:.1f}%')
    if slow_metrics['buy_ratio']:
        print(f'  Slow migrants: Moyenne={statistics.mean(slow_metrics["buy_ratio"])*100:.1f}% | Médiane={statistics.median(slow_metrics["buy_ratio"])*100:.1f}%')
    if flop_metrics['buy_ratio']:
        print(f'  Flops:         Moyenne={statistics.mean(flop_metrics["buy_ratio"])*100:.1f}% | Médiane={statistics.median(flop_metrics["buy_ratio"])*100:.1f}%')

    print(f'\n[MARKET CAP]')
    if fast_metrics['mc']:
        print(f'  Fast migrants: Moyenne=${statistics.mean(fast_metrics["mc"]):,.0f} | Médiane=${statistics.median(fast_metrics["mc"]):,.0f}')
    if slow_metrics['mc']:
        print(f'  Slow migrants: Moyenne=${statistics.mean(slow_metrics["mc"]):,.0f} | Médiane=${statistics.median(slow_metrics["mc"]):,.0f}')
    if flop_metrics['mc']:
        print(f'  Flops:         Moyenne=${statistics.mean(flop_metrics["mc"]):,.0f} | Médiane=${statistics.median(flop_metrics["mc"]):,.0f}')

    print(f'\n[VELOCITY ($/sec)]')
    if fast_metrics['velocity']:
        print(f'  Fast migrants: Moyenne={statistics.mean(fast_metrics["velocity"]):.0f} | Médiane={statistics.median(fast_metrics["velocity"]):.0f}')
    if slow_metrics['velocity']:
        print(f'  Slow migrants: Moyenne={statistics.mean(slow_metrics["velocity"]):.0f} | Médiane={statistics.median(slow_metrics["velocity"]):.0f}')

# Analyse des whales
print(f'\n{"="*80}')
print('ANALYSE DES WHALES')
print('='*80)

fast_whale_count = [t.get('whale_count', 0) for t in fast_migrants]
slow_whale_count = [t.get('whale_count', 0) for t in slow_migrants]
flop_whale_count = [t.get('whale_count', 0) for t in flops[:100]]

print(f'\n[NOMBRE DE WHALES DETECTEES]')
if fast_whale_count:
    print(f'  Fast migrants: Moyenne={statistics.mean(fast_whale_count):.1f} | Médiane={statistics.median(fast_whale_count):.1f}')
if slow_whale_count:
    print(f'  Slow migrants: Moyenne={statistics.mean(slow_whale_count):.1f} | Médiane={statistics.median(slow_whale_count):.1f}')
if flop_whale_count:
    print(f'  Flops:         Moyenne={statistics.mean(flop_whale_count):.1f} | Médiane={statistics.median(flop_whale_count):.1f}')

print('\n' + '='*80)
print('SIGNAUX CLES POUR DETECTION PRECOCE')
print('='*80)
print('''
Recherchez ces patterns dans les 30s-1min:
1. Volume élevé de transactions (>moyenne flops)
2. Nombre élevé de traders (plus = meilleur)
3. Buy ratio élevé (>60-70%)
4. Vélocité forte (augmentation rapide du MC)
5. Présence de whales

Les tokens qui migrent RAPIDEMENT montrent ces signaux DES LE DEBUT!
''')

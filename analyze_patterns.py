import json
import statistics

with open('bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Séparer runners et flops
runners = [r for r in data['completed'] if r.get('is_runner', False)]
flops = [r for r in data['completed'] if not r.get('is_runner', False)]
migrations = [r for r in runners if r.get('migration_detected', False)]

print(f'=== ANALYSE DES PATTERNS ===')
print(f'Runners: {len(runners)} | Flops: {len(flops)} | Migrations: {len(migrations)}')
print(f'')

# Fonction pour extraire les métriques d'un snapshot
def get_metrics(tokens, snapshot_name):
    metrics = {
        'mc': [],
        'txn': [],
        'buy_ratio': [],
        'traders': [],
        'big_buys_100': [],
        'big_buys_500': [],
        'total_buy_volume': []
    }

    for token in tokens:
        snap = token.get(snapshot_name)
        if snap and isinstance(snap, dict):
            if snap.get('mc'): metrics['mc'].append(snap['mc'])
            if snap.get('txn'): metrics['txn'].append(snap['txn'])
            if snap.get('buy_ratio') is not None: metrics['buy_ratio'].append(snap['buy_ratio'] * 100)
            if snap.get('traders'): metrics['traders'].append(snap['traders'])
            if snap.get('big_buys_100'): metrics['big_buys_100'].append(snap['big_buys_100'])
            if snap.get('big_buys_500'): metrics['big_buys_500'].append(snap['big_buys_500'])
            if snap.get('total_buy_volume'): metrics['total_buy_volume'].append(snap['total_buy_volume'])

    return metrics

# Analyser chaque snapshot
snapshots = ['10s', '15s', '30s', '1min']

for snap_name in snapshots:
    print(f'\n{"="*80}')
    print(f'=== SNAPSHOT {snap_name.upper()} ===')
    print(f'{"="*80}')

    runner_metrics = get_metrics(runners, snap_name)
    flop_metrics = get_metrics(flops, snap_name)

    if len(runner_metrics['buy_ratio']) > 0 and len(flop_metrics['buy_ratio']) > 0:
        print(f'\n[BUY RATIO]:')
        print(f'  Runners: {statistics.mean(runner_metrics["buy_ratio"]):.1f}% (median: {statistics.median(runner_metrics["buy_ratio"]):.1f}%)')
        print(f'  Flops:   {statistics.mean(flop_metrics["buy_ratio"]):.1f}% (median: {statistics.median(flop_metrics["buy_ratio"]):.1f}%)')
        print(f'  >> Difference: +{statistics.mean(runner_metrics["buy_ratio"]) - statistics.mean(flop_metrics["buy_ratio"]):.1f}%')

    if len(runner_metrics['txn']) > 0 and len(flop_metrics['txn']) > 0:
        print(f'\n[TRANSACTIONS]:')
        print(f'  Runners: {statistics.mean(runner_metrics["txn"]):.0f} txn (median: {statistics.median(runner_metrics["txn"]):.0f})')
        print(f'  Flops:   {statistics.mean(flop_metrics["txn"]):.0f} txn (median: {statistics.median(flop_metrics["txn"]):.0f})')
        print(f'  >> Difference: +{statistics.mean(runner_metrics["txn"]) - statistics.mean(flop_metrics["txn"]):.0f} txn')

    if len(runner_metrics['traders']) > 0 and len(flop_metrics['traders']) > 0:
        print(f'\n[TRADERS]:')
        print(f'  Runners: {statistics.mean(runner_metrics["traders"]):.0f} traders (median: {statistics.median(runner_metrics["traders"]):.0f})')
        print(f'  Flops:   {statistics.mean(flop_metrics["traders"]):.0f} traders (median: {statistics.median(flop_metrics["traders"]):.0f})')
        print(f'  >> Difference: +{statistics.mean(runner_metrics["traders"]) - statistics.mean(flop_metrics["traders"]):.0f} traders')

    if len(runner_metrics['big_buys_100']) > 0 and len(flop_metrics['big_buys_100']) > 0:
        print(f'\n[BIG BUYS >$100]:')
        print(f'  Runners: {statistics.mean(runner_metrics["big_buys_100"]):.1f} (median: {statistics.median(runner_metrics["big_buys_100"]):.0f})')
        print(f'  Flops:   {statistics.mean(flop_metrics["big_buys_100"]):.1f} (median: {statistics.median(flop_metrics["big_buys_100"]):.0f})')
        print(f'  >> Difference: +{statistics.mean(runner_metrics["big_buys_100"]) - statistics.mean(flop_metrics["big_buys_100"]):.1f}')

    if len(runner_metrics['total_buy_volume']) > 0 and len(flop_metrics['total_buy_volume']) > 0:
        print(f'\n[VOLUME D\'ACHAT]:')
        print(f'  Runners: ${statistics.mean(runner_metrics["total_buy_volume"]):.0f} (median: ${statistics.median(runner_metrics["total_buy_volume"]):.0f})')
        print(f'  Flops:   ${statistics.mean(flop_metrics["total_buy_volume"]):.0f} (median: ${statistics.median(flop_metrics["total_buy_volume"]):.0f})')
        print(f'  >> Difference: +${statistics.mean(runner_metrics["total_buy_volume"]) - statistics.mean(flop_metrics["total_buy_volume"]):.0f}')

# Analyse des migrations
print(f'\n\n{"="*80}')
print(f'=== ANALYSE SPÉCIALE: MIGRATIONS ($69K) ===')
print(f'{"="*80}')

if len(migrations) > 0:
    print(f'\nTotal migrations: {len(migrations)}')

    # Temps pour migrer
    migration_times = [m.get('pump_time') for m in migrations if m.get('pump_time')]
    if migration_times:
        print(f'\n[TEMPS POUR MIGRATION]:')
        print(f'  Moyenne: {statistics.mean(migration_times):.0f}s ({statistics.mean(migration_times)/60:.1f} min)')
        print(f'  Median:  {statistics.median(migration_times):.0f}s ({statistics.median(migration_times)/60:.1f} min)')
        print(f'  Min:     {min(migration_times):.0f}s')
        print(f'  Max:     {max(migration_times):.0f}s ({max(migration_times)/60:.1f} min)')

    # Métriques à 30s pour migrations
    print(f'\n[METRIQUES A 30 SECONDES (Migrations)]:')
    migration_30s = get_metrics(migrations, '30s')
    if len(migration_30s['buy_ratio']) > 0:
        print(f'  Buy ratio moyen: {statistics.mean(migration_30s["buy_ratio"]):.1f}%')
        print(f'  Transactions: {statistics.mean(migration_30s["txn"]):.0f}')
        print(f'  Traders: {statistics.mean(migration_30s["traders"]):.0f}')
        print(f'  Big buys >$100: {statistics.mean(migration_30s["big_buys_100"]):.0f}')

# Patterns communs
print(f'\n\n{"="*80}')
print(f'=== PATTERNS CLÉS IDENTIFIÉS ===')
print(f'{"="*80}')

# Calculer les seuils optimaux
snap_15s_runners = get_metrics(runners, '15s')
snap_15s_flops = get_metrics(flops, '15s')

if len(snap_15s_runners['buy_ratio']) > 0:
    print(f'\n[SEUILS OPTIMAUX A 15 SECONDES]:')
    buy_ratio_threshold = statistics.median(snap_15s_runners['buy_ratio'])
    txn_threshold = statistics.median(snap_15s_runners['txn'])
    traders_threshold = statistics.median(snap_15s_runners['traders'])

    print(f'  Buy Ratio: >={buy_ratio_threshold:.0f}%')
    print(f'  Transactions: >={txn_threshold:.0f}')
    print(f'  Traders: >={traders_threshold:.0f}')

    # Vérifier combien de runners respectent ces critères
    matching = 0
    for r in runners:
        snap = r.get('15s')
        if snap and isinstance(snap, dict):
            if (snap.get('buy_ratio', 0) * 100 >= buy_ratio_threshold and
                snap.get('txn', 0) >= txn_threshold and
                snap.get('traders', 0) >= traders_threshold):
                matching += 1

    print(f'\n  >> {matching}/{len(runners)} runners ({matching/len(runners)*100:.0f}%) respectent ces criteres')

# Analyse de la progression MC
print(f'\n\n[PROGRESSION MARKET CAP]:')
print(f'\nRunners rapides (<1 min):')
fast_runners = [r for r in runners if r.get('pump_time') and r.get('pump_time') < 60]
if fast_runners:
    print(f'  Total: {len(fast_runners)}')
    for snap_name in ['10s', '15s', '30s']:
        mcs = [r.get(snap_name, {}).get('mc', 0) for r in fast_runners if r.get(snap_name)]
        if mcs:
            print(f'  {snap_name}: ${statistics.median([m for m in mcs if m > 0]):.0f} (median)')

print(f'\nRunners lents (>1 min):')
slow_runners = [r for r in runners if r.get('pump_time') and r.get('pump_time') >= 60]
if slow_runners:
    print(f'  Total: {len(slow_runners)}')
    for snap_name in ['15s', '30s', '1min', '2min']:
        mcs = [r.get(snap_name, {}).get('mc', 0) for r in slow_runners if r.get(snap_name)]
        if mcs:
            print(f'  {snap_name}: ${statistics.median([m for m in mcs if m > 0]):.0f} (median)')

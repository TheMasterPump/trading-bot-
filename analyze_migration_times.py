import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

runners = d.get('runners', [])

# Snapshots dans l'ordre chronologique
SNAPSHOTS = ['10s', '15s', '20s', '30s', '1min', '2min', '3min', '5min', '8min', '10min', '15min']

print('='*80)
print('ANALYSE DES TEMPS DE MIGRATION')
print('='*80)

# Analyser les runners qui ont migré
migrated_runners = [r for r in runners if r.get('migration_detected')]

print(f'\n[RUNNERS AYANT MIGRE]: {len(migrated_runners)}/{len(runners)}\n')

# Trouver le dernier snapshot disponible pour chaque runner
migration_times = {}
for snap in SNAPSHOTS:
    migration_times[snap] = []
migration_times['unknown'] = []

for runner in migrated_runners:
    symbol = runner.get('symbol', 'N/A')

    # Trouver le dernier snapshot disponible
    last_snapshot = None
    for snap in reversed(SNAPSHOTS):
        if snap in runner and runner[snap] and len(runner[snap]) > 0:
            last_snapshot = snap
            break

    if last_snapshot:
        migration_times[last_snapshot].append(runner)
    else:
        migration_times['unknown'].append(runner)

# Afficher les résultats
print('[DISTRIBUTION DES MIGRATIONS PAR TEMPS]')
print('(Le dernier snapshot = moment approximatif de migration)\n')

total = 0
for snap in SNAPSHOTS:
    count = len(migration_times[snap])
    total += count
    if count > 0:
        percentage = (count / len(migrated_runners)) * 100
        print(f'{snap:6} : {count:3} tokens ({percentage:5.1f}%) - Migration vers Raydium')
        # Afficher quelques exemples
        for token in migration_times[snap][:3]:
            sym = token.get('symbol', 'N/A')[:12]
            final_mc = token.get('final_mc', 0)
            print(f'         - {sym:12} | MC: ${final_mc:,.0f}')
        if count > 3:
            print(f'         ... et {count-3} autres')

if migration_times['unknown']:
    print(f'\nUnknown: {len(migration_times["unknown"])} tokens (pas de snapshots)')

print('\n' + '='*80)
print('RESUME')
print('='*80)

# Calculer les stats
ultra_rapide = sum(len(migration_times[s]) for s in ['10s', '15s', '20s', '30s', '1min'])
rapide = sum(len(migration_times[s]) for s in ['2min', '3min'])
moyen = sum(len(migration_times[s]) for s in ['5min', '8min'])
lent = sum(len(migration_times[s]) for s in ['10min', '15min'])

if len(migrated_runners) > 0:
    print(f'\nMigration ULTRA-RAPIDE (<= 1min):  {ultra_rapide:3} tokens ({ultra_rapide/len(migrated_runners)*100:5.1f}%)')
    print(f'Migration RAPIDE (2-3min):         {rapide:3} tokens ({rapide/len(migrated_runners)*100:5.1f}%)')
    print(f'Migration MOYENNE (5-8min):        {moyen:3} tokens ({moyen/len(migrated_runners)*100:5.1f}%)')
    print(f'Migration LENTE (10-15min):        {lent:3} tokens ({lent/len(migrated_runners)*100:5.1f}%)')

print('\n' + '='*80)

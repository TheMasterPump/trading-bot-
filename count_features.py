import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

# Trouver le token specifique
mint = '2QnMa9jcqwY5Sh8A2MfnF6Ua1CwiJtMKPpRDRUmupump'
token = None
for t in d.get('runners', []) + d.get('flops', []):
    if t.get('mint') == mint:
        token = t
        break

if not token:
    print('Token non trouve')
    exit()

# Listes des snapshots temporels
snapshots = ['10s', '15s', '20s', '30s', '1min', '2min', '3min', '5min', '8min', '10min', '15min', '20min']

# Compter les features
print('='*80)
print(f'COMPTAGE DES FEATURES - Token: {token.get("symbol", "N/A")[:20]}')
print('='*80)

# 1. Champs de base (hors snapshots et ml_metrics)
base_keys = [k for k in token.keys() if k not in snapshots and k != 'ml_metrics']
print(f'\n[CHAMPS DE BASE]: {len(base_keys)} features')
for k in base_keys:
    v = token[k]
    if isinstance(v, list):
        print(f'  - {k}: liste de {len(v)} elements')
    elif isinstance(v, dict):
        print(f'  - {k}: dict avec {len(v)} cles')
    else:
        print(f'  - {k}')

# 2. Snapshots temporels
total_snapshot_fields = 0
print(f'\n[SNAPSHOTS TEMPORELS]:')
for snap in snapshots:
    if snap in token and token[snap] is not None:
        num_fields = len(token[snap])
        total_snapshot_fields += num_fields
        print(f'  - {snap}: {num_fields} fields')

print(f'  TOTAL snapshots: {total_snapshot_fields} features')

# 3. ML Metrics
ml_metrics = token.get('ml_metrics', {})
print(f'\n[ML METRICS]: {len(ml_metrics)} features')
if ml_metrics:
    print('  Exemples:')
    for i, k in enumerate(list(ml_metrics.keys())[:5]):
        print(f'    - {k}')
    if len(ml_metrics) > 5:
        print(f'    ... et {len(ml_metrics)-5} autres')

# 4. TOTAL
total = len(base_keys) + total_snapshot_fields + len(ml_metrics)
print(f'\n{"="*80}')
print(f'TOTAL FEATURES POUR CE TOKEN: {total}')
print(f'{"="*80}')
print(f'\nRepartition:')
print(f'  Base: {len(base_keys)} ({len(base_keys)/total*100:.1f}%)')
print(f'  Snapshots: {total_snapshot_fields} ({total_snapshot_fields/total*100:.1f}%)')
print(f'  ML Metrics: {len(ml_metrics)} ({len(ml_metrics)/total*100:.1f}%)')

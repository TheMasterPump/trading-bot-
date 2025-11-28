import json
import pandas as pd

# Charger les donnees
with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

runners = d.get('runners', [])
flops = d.get('flops', [])

print('='*80)
print('DATASET POUR PREDICTION VERY EARLY @ 15 SECONDES')
print('='*80)

dataset = []

# Fonction pour extraire les features @ 15s
def extract_features_15s(token):
    features = {}

    # Snapshots @ 10s et 15s
    snap_10s = token.get('10s', {})
    snap_15s = token.get('15s', {})

    if not snap_15s:
        return None  # Pas de donnees @ 15s

    # Features du snapshot 10s (prefixe 10s_)
    features['10s_txn'] = snap_10s.get('txn', 0) if snap_10s else 0
    features['10s_traders'] = snap_10s.get('traders', 0) if snap_10s else 0
    features['10s_buy_ratio'] = snap_10s.get('buy_ratio', 0) if snap_10s else 0
    features['10s_mc'] = snap_10s.get('mc', 0) if snap_10s else 0
    features['10s_velocity'] = snap_10s.get('velocity', 0) if snap_10s else 0

    # Features du snapshot 15s (prefixe 15s_)
    features['15s_txn'] = snap_15s.get('txn', 0)
    features['15s_traders'] = snap_15s.get('traders', 0)
    features['15s_buy_ratio'] = snap_15s.get('buy_ratio', 0)
    features['15s_mc'] = snap_15s.get('mc', 0)
    features['15s_velocity'] = snap_15s.get('velocity', 0)

    # Features derivees (evolution entre 10s et 15s)
    if snap_10s and snap_10s.get('mc', 0) > 0:
        features['mc_growth_10s_15s'] = (snap_15s.get('mc', 0) - snap_10s.get('mc', 0)) / snap_10s.get('mc', 1)
        features['txn_growth_10s_15s'] = snap_15s.get('txn', 0) - snap_10s.get('txn', 0)
        features['traders_growth_10s_15s'] = snap_15s.get('traders', 0) - snap_10s.get('traders', 0)
    else:
        features['mc_growth_10s_15s'] = 0
        features['txn_growth_10s_15s'] = 0
        features['traders_growth_10s_15s'] = 0

    # Whale count
    features['whale_count'] = token.get('whale_count', 0)

    # LABEL : Est-ce que le token a migre ?
    features['migrated'] = 1 if token.get('migration_detected', False) else 0

    return features

# Traiter les runners
print(f'\nTraitement des RUNNERS...')
runners_processed = 0
for runner in runners:
    features = extract_features_15s(runner)
    if features:
        dataset.append(features)
        runners_processed += 1

print(f'  -> {runners_processed} runners avec donnees @ 15s')

# Traiter les flops
print(f'\nTraitement des FLOPS...')
flops_processed = 0
for flop in flops:
    features = extract_features_15s(flop)
    if features:
        dataset.append(features)
        flops_processed += 1

print(f'  -> {flops_processed} flops avec donnees @ 15s')

# Creer DataFrame
df = pd.DataFrame(dataset)

# Sauvegarder
output_file = 'dataset_15s_prediction.csv'
df.to_csv(output_file, index=False)

print('\n' + '='*80)
print('DATASET CREE - PREDICTION @ 15 SECONDES')
print('='*80)
print(f'\nFichier: {output_file}')
print(f'Total tokens: {len(df)}')
print(f'  - Runners (migrated=1): {df["migrated"].sum()}')
print(f'  - Flops (migrated=0): {len(df) - df["migrated"].sum()}')
print(f'  - Features: {len(df.columns)} colonnes')

print(f'\n[COLONNES DU DATASET]')
for i, col in enumerate(df.columns, 1):
    print(f'  {i}. {col}')

print(f'\n[STATISTIQUES @ 15s - RUNNERS vs FLOPS]')
print('\nRUNNERS (@ 15s):')
print(df[df['migrated']==1][['15s_txn', '15s_traders', '15s_buy_ratio', '15s_mc', '15s_velocity']].describe())

print('\nFLOPS (@ 15s):')
print(df[df['migrated']==0][['15s_txn', '15s_traders', '15s_buy_ratio', '15s_mc', '15s_velocity']].describe())

print('='*80)

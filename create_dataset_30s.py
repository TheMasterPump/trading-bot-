import json
import pandas as pd

# Charger les donnees
with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

runners = d.get('runners', [])
flops = d.get('flops', [])

print('='*80)
print('DATASET POUR PREDICTION EARLY @ 30 SECONDES')
print('='*80)

dataset = []

# Fonction pour extraire les features @ 30s
def extract_features_30s(token):
    features = {}

    # Snapshots jusqu'a 30s
    snap_10s = token.get('10s', {})
    snap_15s = token.get('15s', {})
    snap_20s = token.get('20s', {})
    snap_30s = token.get('30s', {})

    if not snap_30s:
        return None  # Pas de donnees @ 30s

    # Features du snapshot 10s
    features['10s_txn'] = snap_10s.get('txn', 0) if snap_10s else 0
    features['10s_traders'] = snap_10s.get('traders', 0) if snap_10s else 0
    features['10s_buy_ratio'] = snap_10s.get('buy_ratio', 0) if snap_10s else 0
    features['10s_mc'] = snap_10s.get('mc', 0) if snap_10s else 0
    features['10s_velocity'] = snap_10s.get('velocity', 0) if snap_10s else 0

    # Features du snapshot 15s
    features['15s_txn'] = snap_15s.get('txn', 0) if snap_15s else 0
    features['15s_traders'] = snap_15s.get('traders', 0) if snap_15s else 0
    features['15s_buy_ratio'] = snap_15s.get('buy_ratio', 0) if snap_15s else 0
    features['15s_mc'] = snap_15s.get('mc', 0) if snap_15s else 0
    features['15s_velocity'] = snap_15s.get('velocity', 0) if snap_15s else 0

    # Features du snapshot 20s
    features['20s_txn'] = snap_20s.get('txn', 0) if snap_20s else 0
    features['20s_traders'] = snap_20s.get('traders', 0) if snap_20s else 0
    features['20s_buy_ratio'] = snap_20s.get('buy_ratio', 0) if snap_20s else 0
    features['20s_mc'] = snap_20s.get('mc', 0) if snap_20s else 0
    features['20s_velocity'] = snap_20s.get('velocity', 0) if snap_20s else 0

    # Features du snapshot 30s
    features['30s_txn'] = snap_30s.get('txn', 0)
    features['30s_traders'] = snap_30s.get('traders', 0)
    features['30s_buy_ratio'] = snap_30s.get('buy_ratio', 0)
    features['30s_mc'] = snap_30s.get('mc', 0)
    features['30s_velocity'] = snap_30s.get('velocity', 0)

    # Features derivees (evolution)
    # Croissance 10s -> 30s
    if snap_10s and snap_10s.get('mc', 0) > 0:
        features['mc_growth_10s_30s'] = (snap_30s.get('mc', 0) - snap_10s.get('mc', 0)) / snap_10s.get('mc', 1)
        features['txn_growth_10s_30s'] = snap_30s.get('txn', 0) - snap_10s.get('txn', 0)
        features['traders_growth_10s_30s'] = snap_30s.get('traders', 0) - snap_10s.get('traders', 0)
    else:
        features['mc_growth_10s_30s'] = 0
        features['txn_growth_10s_30s'] = 0
        features['traders_growth_10s_30s'] = 0

    # Tendance (est-ce que ca monte ou ca descend?)
    mc_values = [snap_10s.get('mc', 0) if snap_10s else 0,
                 snap_15s.get('mc', 0) if snap_15s else 0,
                 snap_20s.get('mc', 0) if snap_20s else 0,
                 snap_30s.get('mc', 0)]

    # Compter combien de fois le MC augmente
    increasing_count = sum(1 for i in range(len(mc_values)-1) if mc_values[i+1] > mc_values[i])
    features['mc_trend_up_count'] = increasing_count  # 0-3

    # Whale count
    features['whale_count'] = token.get('whale_count', 0)

    # LABEL : Est-ce que le token a migre ?
    features['migrated'] = 1 if token.get('migration_detected', False) else 0

    return features

# Traiter les runners
print(f'\nTraitement des RUNNERS...')
runners_processed = 0
for runner in runners:
    features = extract_features_30s(runner)
    if features:
        dataset.append(features)
        runners_processed += 1

print(f'  -> {runners_processed} runners avec donnees @ 30s')

# Traiter les flops
print(f'\nTraitement des FLOPS...')
flops_processed = 0
for flop in flops:
    features = extract_features_30s(flop)
    if features:
        dataset.append(features)
        flops_processed += 1

print(f'  -> {flops_processed} flops avec donnees @ 30s')

# Creer DataFrame
df = pd.DataFrame(dataset)

# Sauvegarder
output_file = 'dataset_30s_prediction.csv'
df.to_csv(output_file, index=False)

print('\n' + '='*80)
print('DATASET CREE - PREDICTION @ 30 SECONDES')
print('='*80)
print(f'\nFichier: {output_file}')
print(f'Total tokens: {len(df)}')
print(f'  - Runners (migrated=1): {df["migrated"].sum()}')
print(f'  - Flops (migrated=0): {len(df) - df["migrated"].sum()}')
print(f'  - Features: {len(df.columns)} colonnes')

print(f'\n[COLONNES DU DATASET]')
for i, col in enumerate(df.columns, 1):
    print(f'  {i}. {col}')

print(f'\n[STATISTIQUES @ 30s - RUNNERS vs FLOPS]')
print('\nRUNNERS (@ 30s):')
print(df[df['migrated']==1][['30s_txn', '30s_traders', '30s_buy_ratio', '30s_mc', '30s_velocity']].describe())

print('\nFLOPS (@ 30s):')
print(df[df['migrated']==0][['30s_txn', '30s_traders', '30s_buy_ratio', '30s_mc', '30s_velocity']].describe())

print('\n[FEATURES DERIVEES - RUNNERS vs FLOPS]')
print('\nRUNNERS (croissance):')
print(df[df['migrated']==1][['mc_growth_10s_30s', 'txn_growth_10s_30s', 'traders_growth_10s_30s', 'mc_trend_up_count']].describe())

print('\nFLOPS (croissance):')
print(df[df['migrated']==0][['mc_growth_10s_30s', 'txn_growth_10s_30s', 'traders_growth_10s_30s', 'mc_trend_up_count']].describe())

print('='*80)

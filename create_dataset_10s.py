import json
import pandas as pd

# Charger les donnees
with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

runners = d.get('runners', [])
flops = d.get('flops', [])

print('='*80)
print('DATASET POUR PREDICTION ULTRA-EARLY @ 10 SECONDES')
print('='*80)

dataset = []

# Fonction pour extraire les features @ 10s
def extract_features_10s(token):
    features = {}

    # Snapshot @ 10s
    snap_10s = token.get('10s', {})

    if not snap_10s:
        return None  # Pas de donnees @ 10s

    # Verifier que les donnees sont valides (au moins 1 transaction)
    txn = snap_10s.get('txn', 0)
    if txn < 1:
        return None  # Pas assez de donnees

    mc = snap_10s.get('mc', 0)
    if mc <= 0:
        return None  # MC invalide

    # Features du snapshot 10s
    features['txn'] = txn
    features['traders'] = snap_10s.get('traders', 0)
    features['buy_ratio'] = snap_10s.get('buy_ratio', 0)
    features['mc'] = mc
    features['velocity'] = snap_10s.get('velocity', 0)

    # Whale count (depuis le snapshot ou le token principal)
    features['whale_count'] = snap_10s.get('whale_count', token.get('whale_count', 0))

    # LABEL : Est-ce que le token a migre ?
    features['migrated'] = 1 if token.get('migration_detected', False) else 0

    return features

# Traiter les runners
print(f'\nTraitement des RUNNERS...')
runners_processed = 0
for runner in runners:
    features = extract_features_10s(runner)
    if features:
        dataset.append(features)
        runners_processed += 1

print(f'  -> {runners_processed} runners avec donnees @ 10s')

# Traiter les flops
print(f'\nTraitement des FLOPS...')
flops_processed = 0
for flop in flops:
    features = extract_features_10s(flop)
    if features:
        dataset.append(features)
        flops_processed += 1

print(f'  -> {flops_processed} flops avec donnees @ 10s')

# Creer DataFrame
df = pd.DataFrame(dataset)

# Sauvegarder
output_file = 'dataset_10s_prediction.csv'
df.to_csv(output_file, index=False)

print('\n' + '='*80)
print('DATASET CREE - PREDICTION @ 10 SECONDES')
print('='*80)
print(f'\nFichier: {output_file}')
print(f'Total tokens: {len(df)}')
print(f'  - Runners (migrated=1): {df["migrated"].sum()}')
print(f'  - Flops (migrated=0): {len(df) - df["migrated"].sum()}')
print(f'  - Features: {len(df.columns)} colonnes')

print(f'\n[COLONNES DU DATASET]')
for i, col in enumerate(df.columns, 1):
    print(f'  {i}. {col}')

print(f'\n[STATISTIQUES @ 10s - RUNNERS vs FLOPS]')
print('\nRUNNERS:')
print(df[df['migrated']==1][['txn', 'traders', 'buy_ratio', 'mc', 'velocity']].describe())

print('\nFLOPS:')
print(df[df['migrated']==0][['txn', 'traders', 'buy_ratio', 'mc', 'velocity']].describe())

print('='*80)

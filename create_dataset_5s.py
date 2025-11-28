import json
import pandas as pd

# Charger les donnees depuis bot_data.json
print('Chargement de bot_data.json...')
with open('bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('='*80)
print('DATASET POUR PREDICTION ULTRA-PRECOCE @ 5 SECONDES')
print('='*80)

dataset = []
runners_count = 0
flops_count = 0

# Fonction pour extraire les features @ 5s
def extract_features_5s(token):
    features = {}

    # Vérifier si c'est un dict
    if not isinstance(token, dict):
        return None

    # Snapshot @ 5s (stocké directement dans token['5s'])
    snap_5s = token.get('5s', {})

    if not snap_5s or not isinstance(snap_5s, dict):
        return None  # Pas de donnees @ 5s

    # Features du snapshot 5s
    features['txn'] = snap_5s.get('txn', 0)
    features['traders'] = snap_5s.get('traders', 0)
    features['buy_ratio'] = snap_5s.get('buy_ratio', 0)
    features['mc'] = snap_5s.get('mc', 0)
    features['velocity'] = snap_5s.get('velocity', 0)

    # LABEL : Est-ce que le token a migre ?
    features['migrated'] = 1 if token.get('migration_detected', False) else 0

    return features

# Traiter tous les tokens
print(f'\nTraitement des tokens...')

# Si data est une liste
if isinstance(data, list):
    for token in data:
        features = extract_features_5s(token)
        if features:
            dataset.append(features)
            if features['migrated'] == 1:
                runners_count += 1
            else:
                flops_count += 1

# Si data est un dict avec runners/flops
elif isinstance(data, dict):
    # Traiter les runners
    runners = data.get('runners', [])
    for runner in runners:
        features = extract_features_5s(runner)
        if features:
            dataset.append(features)
            runners_count += 1

    # Traiter les flops
    flops = data.get('flops', [])
    for flop in flops:
        features = extract_features_5s(flop)
        if features:
            dataset.append(features)
            flops_count += 1

print(f'  -> {runners_count} runners avec donnees @ 5s')
print(f'  -> {flops_count} flops avec donnees @ 5s')

# Creer DataFrame
df = pd.DataFrame(dataset)

if len(df) == 0:
    print('\n[ERREUR] Aucune donnee trouvee!')
    print('Verifiez que bot_data.json contient des snapshots @ 5s')
    exit(1)

# Sauvegarder
output_file = 'dataset_5s_prediction.csv'
df.to_csv(output_file, index=False)

print('\n' + '='*80)
print('DATASET CREE - PREDICTION @ 5 SECONDES')
print('='*80)
print(f'\nFichier: {output_file}')
print(f'Total tokens: {len(df)}')
print(f'  - Runners (migrated=1): {df["migrated"].sum()}')
print(f'  - Flops (migrated=0): {len(df) - df["migrated"].sum()}')
print(f'  - Features: {len(df.columns)} colonnes')

print(f'\n[COLONNES DU DATASET]')
for i, col in enumerate(df.columns, 1):
    print(f'  {i}. {col}')

print(f'\n[STATISTIQUES @ 5s - RUNNERS vs FLOPS]')
print('\nRUNNERS:')
if df['migrated'].sum() > 0:
    print(df[df['migrated']==1][['txn', 'traders', 'buy_ratio', 'mc']].describe())
else:
    print('Aucun runner trouve')

print('\nFLOPS:')
if (len(df) - df['migrated'].sum()) > 0:
    print(df[df['migrated']==0][['txn', 'traders', 'buy_ratio', 'mc']].describe())
else:
    print('Aucun flop trouve')

print('='*80)

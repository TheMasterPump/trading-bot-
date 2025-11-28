import json
import pandas as pd

# Charger les donnees depuis bot_data.json
print('Chargement de bot_data.json...')
with open('bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('='*80)
print('DATASET POUR PREDICTION TRES PRECOCE @ 7 SECONDES')
print('='*80)

dataset = []
runners_count = 0
flops_count = 0

# Fonction pour extraire les features @ 7s
def extract_features_7s(token):
    features = {}

    # Vérifier si c'est un dict
    if not isinstance(token, dict):
        return None

    # Snapshot @ 7s (stocké directement dans token['7s'])
    snap_7s = token.get('7s', {})

    if not snap_7s or not isinstance(snap_7s, dict):
        return None  # Pas de donnees @ 7s

    # Features du snapshot 7s
    features['txn'] = snap_7s.get('txn', 0)
    features['traders'] = snap_7s.get('traders', 0)
    features['buy_ratio'] = snap_7s.get('buy_ratio', 0)
    features['mc'] = snap_7s.get('mc', 0)
    features['velocity'] = snap_7s.get('velocity', 0)

    # LABEL : Est-ce que le token a migre ?
    features['migrated'] = 1 if token.get('migration_detected', False) else 0

    return features

# Traiter tous les tokens
print(f'\nTraitement des tokens...')

# Si data est une liste
if isinstance(data, list):
    for token in data:
        features = extract_features_7s(token)
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
        features = extract_features_7s(runner)
        if features:
            dataset.append(features)
            runners_count += 1

    # Traiter les flops
    flops = data.get('flops', [])
    for flop in flops:
        features = extract_features_7s(flop)
        if features:
            dataset.append(features)
            flops_count += 1

print(f'  -> {runners_count} runners avec donnees @ 7s')
print(f'  -> {flops_count} flops avec donnees @ 7s')

# Creer DataFrame
df = pd.DataFrame(dataset)

if len(df) == 0:
    print('\n[ERREUR] Aucune donnee trouvee!')
    print('Verifiez que bot_data.json contient des snapshots @ 7s')
    exit(1)

# Sauvegarder
output_file = 'dataset_7s_prediction.csv'
df.to_csv(output_file, index=False)

print('\n' + '='*80)
print('DATASET CREE - PREDICTION @ 7 SECONDES')
print('='*80)
print(f'\nFichier: {output_file}')
print(f'Total tokens: {len(df)}')
print(f'  - Runners (migrated=1): {df["migrated"].sum()}')
print(f'  - Flops (migrated=0): {len(df) - df["migrated"].sum()}')
print(f'  - Features: {len(df.columns)} colonnes')

print(f'\n[COLONNES DU DATASET]')
for i, col in enumerate(df.columns, 1):
    print(f'  {i}. {col}')

print(f'\n[STATISTIQUES @ 7s - RUNNERS vs FLOPS]')
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

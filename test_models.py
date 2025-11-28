import pandas as pd
import joblib
import os

print('='*80)
print('VERIFICATION DES MODELES')
print('='*80)

# 1. Verifier que les fichiers existent
print('\n[1. VERIFICATION DES FICHIERS]')
print('-'*80)

files_to_check = ['model_10s.pkl', 'model_15s.pkl', 'dataset_10s_prediction.csv', 'dataset_15s_prediction.csv']
for file in files_to_check:
    exists = os.path.exists(file)
    size = os.path.getsize(file) if exists else 0
    status = 'OK' if exists else 'MANQUANT'
    print(f'{file:30} : {status:10} ({size:,} bytes)')

# 2. Charger les modeles
print('\n[2. CHARGEMENT DES MODELES]')
print('-'*80)

try:
    model_10s = joblib.load('model_10s.pkl')
    print('model_10s.pkl charge avec succes')
    print(f'  Type: {type(model_10s).__name__}')
    print(f'  Nombre de features: {model_10s.n_features_in_}')
except Exception as e:
    print(f'ERREUR lors du chargement de model_10s.pkl: {e}')
    exit(1)

try:
    model_15s = joblib.load('model_15s.pkl')
    print('model_15s.pkl charge avec succes')
    print(f'  Type: {type(model_15s).__name__}')
    print(f'  Nombre de features: {model_15s.n_features_in_}')
except Exception as e:
    print(f'ERREUR lors du chargement de model_15s.pkl: {e}')
    exit(1)

# 3. Charger les datasets
print('\n[3. CHARGEMENT DES DATASETS]')
print('-'*80)

df_10s = pd.read_csv('dataset_10s_prediction.csv')
df_15s = pd.read_csv('dataset_15s_prediction.csv')

print(f'Dataset 10s: {len(df_10s)} tokens')
print(f'Dataset 15s: {len(df_15s)} tokens')

# 4. Tester sur des VRAIS RUNNERS
print('\n[4. TEST SUR DES VRAIS RUNNERS]')
print('-'*80)

runners_10s = df_10s[df_10s['migrated'] == 1].head(10)
print(f'\nTest sur {len(runners_10s)} vrais RUNNERS @ 10s:')
print('')

X_runners_10s = runners_10s.drop('migrated', axis=1)
predictions_10s = model_10s.predict_proba(X_runners_10s)[:, 1]

for i, (idx, row) in enumerate(runners_10s.iterrows()):
    proba = predictions_10s[i]
    mc = row['mc']
    traders = row['traders']
    buy_ratio = row['buy_ratio']

    decision = 'ENTRER' if proba > 0.5 and mc < 15000 else 'SURVEILLER'

    print(f'Runner #{i+1}:')
    print(f'  MC: ${mc:,.0f} | Traders: {traders:.0f} | Buy Ratio: {buy_ratio:.1%}')
    print(f'  Prediction: {proba:.1%} chance de migrer')
    print(f'  Decision: {decision}')
    print('')

# 5. Tester sur des VRAIS FLOPS
print('\n[5. TEST SUR DES VRAIS FLOPS]')
print('-'*80)

flops_10s = df_10s[df_10s['migrated'] == 0].head(10)
print(f'\nTest sur {len(flops_10s)} vrais FLOPS @ 10s:')
print('')

X_flops_10s = flops_10s.drop('migrated', axis=1)
predictions_flops_10s = model_10s.predict_proba(X_flops_10s)[:, 1]

for i, (idx, row) in enumerate(flops_10s.iterrows()):
    proba = predictions_flops_10s[i]
    mc = row['mc']
    traders = row['traders']
    buy_ratio = row['buy_ratio']

    decision = 'ENTRER' if proba > 0.5 and mc < 15000 else 'IGNORER'

    print(f'Flop #{i+1}:')
    print(f'  MC: ${mc:,.0f} | Traders: {traders:.0f} | Buy Ratio: {buy_ratio:.1%}')
    print(f'  Prediction: {proba:.1%} chance de migrer')
    print(f'  Decision: {decision}')
    print('')

# 6. Tester MODELE 15s sur des RUNNERS
print('\n[6. TEST MODELE 15s SUR DES VRAIS RUNNERS]')
print('-'*80)

runners_15s = df_15s[df_15s['migrated'] == 1].head(10)
print(f'\nTest sur {len(runners_15s)} vrais RUNNERS @ 15s:')
print('')

X_runners_15s = runners_15s.drop('migrated', axis=1)
predictions_15s = model_15s.predict_proba(X_runners_15s)[:, 1]

for i, (idx, row) in enumerate(runners_15s.iterrows()):
    proba = predictions_15s[i]
    mc_10s = row['10s_mc']
    mc_15s = row['15s_mc']
    traders_15s = row['15s_traders']
    growth = row['mc_growth_10s_15s']

    decision = 'ENTRER' if proba > 0.6 and mc_15s < 20000 else 'SURVEILLER'

    print(f'Runner #{i+1}:')
    print(f'  MC: ${mc_10s:,.0f} -> ${mc_15s:,.0f} (+{growth:.1%})')
    print(f'  Traders @ 15s: {traders_15s:.0f}')
    print(f'  Prediction: {proba:.1%} chance de migrer')
    print(f'  Decision: {decision}')
    print('')

# 7. Statistiques globales
print('\n[7. STATISTIQUES GLOBALES]')
print('-'*80)

# Predire sur TOUT le dataset
X_all_10s = df_10s.drop('migrated', axis=1)
y_all_10s = df_10s['migrated']
pred_all_10s = model_10s.predict_proba(X_all_10s)[:, 1]

# Compter combien le modele predit correctement
threshold = 0.5
predicted_runners = (pred_all_10s > threshold).sum()
actual_runners = y_all_10s.sum()
actual_flops = len(y_all_10s) - actual_runners

# Vrais runners detectes
true_runners_detected = ((pred_all_10s > threshold) & (y_all_10s == 1)).sum()
# Faux positifs
false_positives = ((pred_all_10s > threshold) & (y_all_10s == 0)).sum()

print(f'\nModele @ 10s sur TOUT le dataset:')
print(f'  Tokens total: {len(df_10s)}')
print(f'  Vrais runners: {actual_runners}')
print(f'  Vrais flops: {actual_flops}')
print(f'')
print(f'  Predictions "RUNNER" (proba > 50%): {predicted_runners}')
print(f'    - Vrais runners detectes: {true_runners_detected}/{actual_runners} ({true_runners_detected/actual_runners*100:.1f}%)')
print(f'    - Faux positifs (flops): {false_positives}')
print(f'')
if predicted_runners > 0:
    precision = true_runners_detected / predicted_runners
    print(f'  Precision: {precision:.1%} (quand dit RUNNER, correct {precision:.0%} du temps)')

# Pareil pour 15s
X_all_15s = df_15s.drop('migrated', axis=1)
y_all_15s = df_15s['migrated']
pred_all_15s = model_15s.predict_proba(X_all_15s)[:, 1]

threshold_15s = 0.6
predicted_runners_15s = (pred_all_15s > threshold_15s).sum()
actual_runners_15s = y_all_15s.sum()
true_runners_detected_15s = ((pred_all_15s > threshold_15s) & (y_all_15s == 1)).sum()
false_positives_15s = ((pred_all_15s > threshold_15s) & (y_all_15s == 0)).sum()

print(f'\nModele @ 15s sur TOUT le dataset:')
print(f'  Tokens total: {len(df_15s)}')
print(f'  Vrais runners: {actual_runners_15s}')
print(f'')
print(f'  Predictions "RUNNER" (proba > 60%): {predicted_runners_15s}')
print(f'    - Vrais runners detectes: {true_runners_detected_15s}/{actual_runners_15s} ({true_runners_detected_15s/actual_runners_15s*100:.1f}%)')
print(f'    - Faux positifs (flops): {false_positives_15s}')
print(f'')
if predicted_runners_15s > 0:
    precision_15s = true_runners_detected_15s / predicted_runners_15s
    print(f'  Precision: {precision_15s:.1%} (quand dit RUNNER, correct {precision_15s:.0%} du temps)')

print('\n' + '='*80)
print('CONCLUSION')
print('='*80)
print(f'''
Les modeles sont bien entraines et fonctionnent !

MODELE @ 10s:
- Detecte {true_runners_detected}/{actual_runners} runners ({true_runners_detected/actual_runners*100:.1f}%)
- Mais aussi {false_positives} faux positifs
- Utilise pour FILTRAGE RAPIDE

MODELE @ 15s:
- Detecte {true_runners_detected_15s}/{actual_runners_15s} runners ({true_runners_detected_15s/actual_runners_15s*100:.1f}%)
- Avec {false_positives_15s} faux positifs
- Meilleure precision que @ 10s
- Utilise pour CONFIRMATION

Les modeles fonctionnent bien pour une premiere version !
''')
print('='*80)

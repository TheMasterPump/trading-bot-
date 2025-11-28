"""
EXPORT ML DATASET - Créer un CSV formaté pour Machine Learning
Extrait toutes les features depuis bot_data.json et crée un dataset flat
"""
import json
import csv
from datetime import datetime

def flatten_snapshot(snapshot, prefix):
    """Aplatir un snapshot en colonnes préfixées"""
    if not snapshot:
        return {}

    flat = {}
    for key, value in snapshot.items():
        if isinstance(value, (int, float, bool)):
            flat[f'{prefix}_{key}'] = value
        elif isinstance(value, list) and key == 'whale_wallets':
            flat[f'{prefix}_whale_count'] = len(value)

    return flat

def export_to_csv(output_file='ml_dataset.csv'):
    """Exporter toutes les données en CSV pour ML"""
    print('='*80)
    print('EXPORT ML DATASET')
    print('='*80)

    # Charger les données
    try:
        with open('bot_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f'ERREUR: Impossible de charger bot_data.json: {e}')
        return

    # Combiner runners et flops
    all_tokens = data.get('runners', []) + data.get('flops', [])
    print(f'\nTokens trouvés: {len(all_tokens)} ({len(data.get("runners", []))} runners, {len(data.get("flops", []))} flops)')

    if not all_tokens:
        print('ERREUR: Aucun token à exporter!')
        return

    # Préparer les données
    rows = []

    for token in all_tokens:
        row = {
            # === INFORMATIONS DE BASE ===
            'symbol': token.get('symbol', ''),
            'mint': token.get('mint', ''),
            'is_runner': 1 if token.get('is_runner') else 0,  # LABEL PRINCIPAL
            'final_mc': token.get('final_mc', 0),
            'pump_time': token.get('pump_time', 0),
            'migration_detected': 1 if token.get('migration_detected') else 0,

            # === WHALE ACTIVITY ===
            'whale_count': token.get('whale_count', 0),
            'whale_total_volume_usd': token.get('whale_total_volume_usd', 0),
        }

        # === SNAPSHOTS TEMPORELS ===
        snapshot_times = ['10s', '15s', '20s', '30s', '1min', '2min', '3min', '5min', '8min', '10min', '15min', '20min']

        for snap_time in snapshot_times:
            snapshot = token.get(snap_time)
            if snapshot:
                flattened = flatten_snapshot(snapshot, snap_time)
                row.update(flattened)

        # === ML METRICS AVANCÉES ===
        ml_metrics = token.get('ml_metrics', {})
        if ml_metrics:
            for key, value in ml_metrics.items():
                if isinstance(value, (int, float)):
                    row[f'ml_{key}'] = value
                elif value is None:
                    row[f'ml_{key}'] = None

        # === SUPPLY DISTRIBUTION ===
        supply_dist = token.get('supply_distribution', {})
        if supply_dist:
            row['supply_top_3_percent'] = supply_dist.get('top_3_percent', 0)
            row['supply_top_5_percent'] = supply_dist.get('top_5_percent', 0)
            row['supply_top_10_percent'] = supply_dist.get('top_10_percent', 0)
            row['total_holders'] = supply_dist.get('total_holders', 0)

        rows.append(row)

    # Écrire le CSV
    if rows:
        # Obtenir toutes les colonnes possibles
        all_keys = set()
        for row in rows:
            all_keys.update(row.keys())

        # Trier les colonnes pour cohérence
        ordered_keys = sorted(all_keys)

        # Mettre les colonnes importantes en premier
        priority_keys = ['symbol', 'mint', 'is_runner', 'final_mc', 'pump_time', 'migration_detected']
        for key in reversed(priority_keys):
            if key in ordered_keys:
                ordered_keys.remove(key)
                ordered_keys.insert(0, key)

        # Écrire le CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=ordered_keys)
            writer.writeheader()
            writer.writerows(rows)

        print(f'\n[OK] Dataset exporte: {output_file}')
        print(f'[OK] Nombre de lignes: {len(rows)}')
        print(f'[OK] Nombre de features: {len(ordered_keys)}')
        print('\n' + '='*80)
        print('FEATURES PRINCIPALES:')
        print('='*80)

        # Afficher quelques stats
        feature_groups = {
            'Base': [k for k in ordered_keys if not ('_' in k or k.startswith('ml_'))],
            'Snapshots (10s-20min)': [k for k in ordered_keys if any(t in k for t in ['10s', '15s', '20s', '30s', '1min', '2min', '3min', '5min', '8min', '10min', '15min', '20min'])],
            'ML Metrics Avancées': [k for k in ordered_keys if k.startswith('ml_')],
            'Supply Distribution': [k for k in ordered_keys if 'supply' in k or 'holder' in k]
        }

        for group_name, features in feature_groups.items():
            print(f'\n{group_name}: {len(features)} features')
            if len(features) <= 10:
                for f in features:
                    print(f'  - {f}')
            else:
                print(f'  Exemples: {", ".join(features[:5])}...')

        print('\n' + '='*80)
        print('UTILISATION POUR MACHINE LEARNING:')
        print('='*80)
        print('''
1. Charger le CSV avec pandas:
   import pandas as pd
   df = pd.read_csv('ml_dataset.csv')

2. Séparer features et label:
   X = df.drop(['symbol', 'mint', 'is_runner'], axis=1)
   y = df['is_runner']

3. Entraîner un modèle (exemple XGBoost):
   from xgboost import XGBClassifier
   model = XGBClassifier()
   model.fit(X, y)

4. Prédire:
   predictions = model.predict(X_test)
        ''')

        # Créer aussi un fichier de description
        with open('ml_dataset_description.txt', 'w', encoding='utf-8') as f:
            f.write('='*80 + '\n')
            f.write('ML DATASET DESCRIPTION\n')
            f.write('='*80 + '\n\n')
            f.write(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write(f'Total tokens: {len(rows)}\n')
            f.write(f'Runners: {sum(1 for r in rows if r["is_runner"] == 1)}\n')
            f.write(f'Flops: {sum(1 for r in rows if r["is_runner"] == 0)}\n')
            f.write(f'Total features: {len(ordered_keys)}\n\n')

            f.write('FEATURE GROUPS:\n')
            f.write('-'*80 + '\n')
            for group_name, features in feature_groups.items():
                f.write(f'\n{group_name}: {len(features)} features\n')
                for feature in features:
                    f.write(f'  - {feature}\n')

        print('\n[OK] Description sauvegardee: ml_dataset_description.txt')
        print('\nFichiers crees avec succes!')

    else:
        print('ERREUR: Aucune donnée à exporter!')

if __name__ == '__main__':
    export_to_csv()

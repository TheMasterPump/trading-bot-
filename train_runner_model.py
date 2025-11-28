"""
TRAIN RUNNER MODEL - Entraine l'IA a detecter les RUNNERS
Utilise les donnees collectees par pattern_discovery_bot.py

Modeles entraines:
1. CLASSIFIER: Est-ce un runner? (oui/non)
2. REGRESSOR: Jusqu'ou ca peut monter? (target price / multiplier)
3. MIGRATION: Va-t-il migrer? (probabilite)

Objectif: "Ce token a 85% de chance de faire 5x, target $350k"
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("TRAIN RUNNER MODEL - IA de detection des RUNNERS")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)


def load_bot_data(filepath='bot_data.json'):
    """Charge les donnees du bot de collecte"""
    print(f"\n[1/6] CHARGEMENT DES DONNEES")
    print("-"*50)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        completed = data.get('completed', [])
        runners = data.get('runners', [])
        flops = data.get('flops', [])

        print(f"  Tokens completed: {len(completed)}")
        print(f"  Runners: {len(runners)}")
        print(f"  Flops: {len(flops)}")

        # Utiliser completed qui contient tout
        return completed

    except FileNotFoundError:
        print(f"  [ERROR] Fichier {filepath} non trouve!")
        print(f"  Lance d'abord: python pattern_discovery_bot.py")
        return []


def extract_features(tokens):
    """Extrait les features de chaque token pour le ML"""
    print(f"\n[2/6] EXTRACTION DES FEATURES")
    print("-"*50)

    features_list = []

    for token in tokens:
        try:
            features = {}

            # === LABEL ===
            features['is_runner'] = 1 if token.get('is_runner', False) else 0
            features['final_mc'] = token.get('final_mc', 0)
            features['migration_detected'] = 1 if token.get('migration_detected', False) else 0

            # === SNAPSHOTS FEATURES ===
            # 3s snapshot
            snap_3s = token.get('3s', {}) or {}
            features['3s_txn'] = snap_3s.get('txn', 0)
            features['3s_buy_ratio'] = snap_3s.get('buy_ratio', 0)
            features['3s_traders'] = snap_3s.get('traders', 0)
            features['3s_mc'] = snap_3s.get('mc', 0)

            # 5s snapshot
            snap_5s = token.get('5s', {}) or {}
            features['5s_txn'] = snap_5s.get('txn', 0)
            features['5s_buy_ratio'] = snap_5s.get('buy_ratio', 0)
            features['5s_traders'] = snap_5s.get('traders', 0)
            features['5s_mc'] = snap_5s.get('mc', 0)

            # 7s snapshot
            snap_7s = token.get('7s', {}) or {}
            features['7s_txn'] = snap_7s.get('txn', 0)
            features['7s_buy_ratio'] = snap_7s.get('buy_ratio', 0)
            features['7s_traders'] = snap_7s.get('traders', 0)
            features['7s_mc'] = snap_7s.get('mc', 0)

            # 10s snapshot (CRUCIAL pour early detection)
            snap_10s = token.get('10s', {}) or {}
            features['10s_txn'] = snap_10s.get('txn', 0)
            features['10s_buys'] = snap_10s.get('buys', 0)
            features['10s_sells'] = snap_10s.get('sells', 0)
            features['10s_buy_ratio'] = snap_10s.get('buy_ratio', 0)
            features['10s_traders'] = snap_10s.get('traders', 0)
            features['10s_mc'] = snap_10s.get('mc', 0)
            features['10s_big_buys_100'] = snap_10s.get('big_buys_100', 0)
            features['10s_big_buys_500'] = snap_10s.get('big_buys_500', 0)
            features['10s_total_buy_volume'] = snap_10s.get('total_buy_volume', 0)
            features['10s_smart_money'] = snap_10s.get('smart_money_count', 0)
            features['10s_whale_count'] = snap_10s.get('whale_count', 0)

            # 15s snapshot
            snap_15s = token.get('15s', {}) or {}
            features['15s_txn'] = snap_15s.get('txn', 0)
            features['15s_buys'] = snap_15s.get('buys', 0)
            features['15s_sells'] = snap_15s.get('sells', 0)
            features['15s_buy_ratio'] = snap_15s.get('buy_ratio', 0)
            features['15s_traders'] = snap_15s.get('traders', 0)
            features['15s_mc'] = snap_15s.get('mc', 0)
            features['15s_big_buys_100'] = snap_15s.get('big_buys_100', 0)
            features['15s_big_buys_500'] = snap_15s.get('big_buys_500', 0)
            features['15s_total_buy_volume'] = snap_15s.get('total_buy_volume', 0)
            features['15s_smart_money'] = snap_15s.get('smart_money_count', 0)
            features['15s_whale_count'] = snap_15s.get('whale_count', 0)

            # 30s snapshot
            snap_30s = token.get('30s', {}) or {}
            features['30s_txn'] = snap_30s.get('txn', 0)
            features['30s_buy_ratio'] = snap_30s.get('buy_ratio', 0)
            features['30s_traders'] = snap_30s.get('traders', 0)
            features['30s_mc'] = snap_30s.get('mc', 0)
            features['30s_big_buys_100'] = snap_30s.get('big_buys_100', 0)
            features['30s_big_buys_500'] = snap_30s.get('big_buys_500', 0)
            features['30s_whale_count'] = snap_30s.get('whale_count', 0)

            # 1min snapshot
            snap_1min = token.get('1min', {}) or {}
            features['1min_txn'] = snap_1min.get('txn', 0)
            features['1min_buy_ratio'] = snap_1min.get('buy_ratio', 0)
            features['1min_traders'] = snap_1min.get('traders', 0)
            features['1min_mc'] = snap_1min.get('mc', 0)
            features['1min_big_buys_500'] = snap_1min.get('big_buys_500', 0)

            # 5min snapshot
            snap_5min = token.get('5min', {}) or {}
            features['5min_txn'] = snap_5min.get('txn', 0)
            features['5min_buy_ratio'] = snap_5min.get('buy_ratio', 0)
            features['5min_traders'] = snap_5min.get('traders', 0)
            features['5min_mc'] = snap_5min.get('mc', 0)

            # 10min snapshot
            snap_10min = token.get('10min', {}) or {}
            features['10min_txn'] = snap_10min.get('txn', 0)
            features['10min_buy_ratio'] = snap_10min.get('buy_ratio', 0)
            features['10min_mc'] = snap_10min.get('mc', 0)

            # === VELOCITY & MOMENTUM ===
            # MC growth rates
            if features['10s_mc'] > 0:
                features['mc_growth_10s_to_30s'] = (features['30s_mc'] - features['10s_mc']) / features['10s_mc']
                features['mc_growth_10s_to_1min'] = (features['1min_mc'] - features['10s_mc']) / features['10s_mc']
            else:
                features['mc_growth_10s_to_30s'] = 0
                features['mc_growth_10s_to_1min'] = 0

            if features['30s_mc'] > 0:
                features['mc_growth_30s_to_5min'] = (features['5min_mc'] - features['30s_mc']) / features['30s_mc']
            else:
                features['mc_growth_30s_to_5min'] = 0

            # Transaction velocity
            features['txn_velocity_10s'] = features['10s_txn'] / 10 if features['10s_txn'] else 0
            features['txn_velocity_30s'] = features['30s_txn'] / 30 if features['30s_txn'] else 0
            features['txn_velocity_1min'] = features['1min_txn'] / 60 if features['1min_txn'] else 0

            # Trader growth
            if features['10s_traders'] > 0:
                features['trader_growth_10s_to_30s'] = features['30s_traders'] / features['10s_traders']
                features['trader_growth_10s_to_1min'] = features['1min_traders'] / features['10s_traders']
            else:
                features['trader_growth_10s_to_30s'] = 0
                features['trader_growth_10s_to_1min'] = 0

            # === WHALE METRICS ===
            features['whale_count'] = token.get('whale_count', 0)
            features['whale_total_volume'] = token.get('whale_total_volume_usd', 0)

            # Whale wallets
            whale_wallets = token.get('whale_wallets_detected', [])
            features['num_whale_wallets'] = len(whale_wallets) if whale_wallets else 0

            # === ML METRICS (si disponible) ===
            ml_metrics = token.get('ml_metrics', {}) or {}

            features['peak_velocity'] = ml_metrics.get('peak_velocity', 0)
            features['avg_velocity'] = ml_metrics.get('avg_velocity', 0)
            features['acceleration'] = ml_metrics.get('acceleration', 0)
            features['gain_percent_from_start'] = ml_metrics.get('gain_percent_from_start', 0)

            features['time_to_10k'] = ml_metrics.get('time_to_10k', 9999)
            features['time_to_20k'] = ml_metrics.get('time_to_20k', 9999)
            features['time_to_40k'] = ml_metrics.get('time_to_40k', 9999)
            features['time_to_69k'] = ml_metrics.get('time_to_69k', 9999)

            features['ath_mc'] = ml_metrics.get('ath_mc', 0)
            features['ath_time'] = ml_metrics.get('ath_time', 9999)
            features['max_drawdown'] = ml_metrics.get('max_drawdown_percent', 0)
            features['volatility'] = ml_metrics.get('volatility', 0)
            features['num_pumps'] = ml_metrics.get('num_pumps', 0)
            features['num_dumps'] = ml_metrics.get('num_dumps', 0)

            features['whale_entry_before_10k'] = ml_metrics.get('whale_entry_before_10k', 0)
            features['whale_entry_10k_to_20k'] = ml_metrics.get('whale_entry_10k_to_20k', 0)
            features['whale_exit_count'] = ml_metrics.get('whale_exit_count', 0)

            features['avg_hold_time'] = ml_metrics.get('avg_hold_time', 0)
            features['paper_hands_count'] = ml_metrics.get('paper_hands_count', 0)
            features['diamond_hands_count'] = ml_metrics.get('diamond_hands_count', 0)
            features['holder_ratio'] = ml_metrics.get('holder_ratio', 0)

            # === SUPPLY DISTRIBUTION ===
            supply = token.get('supply_distribution', {}) or {}
            features['total_holders'] = supply.get('total_holders', 0)
            features['top_3_percent'] = supply.get('top_3_percent', 0)
            features['top_10_percent'] = supply.get('top_10_percent', 0)

            # === COMPUTED FEATURES ===
            # Early signal score (combine des metriques early)
            features['early_signal_score'] = (
                features['10s_buy_ratio'] * 30 +
                min(features['10s_txn'], 100) * 0.3 +
                features['10s_big_buys_100'] * 5 +
                features['10s_whale_count'] * 10
            )

            # Momentum score
            features['momentum_score'] = (
                features['15s_buy_ratio'] * 20 +
                features['mc_growth_10s_to_30s'] * 50 +
                features['txn_velocity_30s'] * 10
            )

            # Whale confidence
            features['whale_confidence'] = (
                features['num_whale_wallets'] * 20 +
                features['whale_entry_before_10k'] * 15 +
                min(features['whale_total_volume'] / 1000, 50)
            )

            features_list.append(features)

        except Exception as e:
            print(f"  [WARNING] Erreur extraction pour un token: {e}")
            continue

    df = pd.DataFrame(features_list)
    print(f"  Features extraites: {len(df)} tokens, {len(df.columns)} features")

    return df


def prepare_training_data(df):
    """Prepare les donnees pour l'entrainement"""
    print(f"\n[3/6] PREPARATION DES DONNEES")
    print("-"*50)

    # Separer features et labels
    label_cols = ['is_runner', 'final_mc', 'migration_detected']
    feature_cols = [col for col in df.columns if col not in label_cols]

    X = df[feature_cols].copy()
    y_runner = df['is_runner'].copy()
    y_price = df['final_mc'].copy()
    y_migration = df['migration_detected'].copy()

    # Remplacer NaN et inf
    X = X.replace([np.inf, -np.inf], 0)
    X = X.fillna(0)

    # Remplacer les valeurs None/9999 pour time_to_*
    time_cols = [col for col in X.columns if col.startswith('time_to_')]
    for col in time_cols:
        X[col] = X[col].replace(9999, 1800)  # 30 min max
        X[col] = X[col].fillna(1800)

    print(f"  Features: {len(feature_cols)}")
    print(f"  Runners: {y_runner.sum()} ({y_runner.sum()/len(y_runner)*100:.1f}%)")
    print(f"  Migrations: {y_migration.sum()} ({y_migration.sum()/len(y_migration)*100:.1f}%)")
    print(f"  Prix moyen: ${y_price.mean():,.0f}")
    print(f"  Prix max: ${y_price.max():,.0f}")

    return X, y_runner, y_price, y_migration, feature_cols


def train_runner_classifier(X, y, feature_cols):
    """Entraine le modele de classification RUNNER/FLOP"""
    print(f"\n[4/6] ENTRAINEMENT CLASSIFIER (Runner vs Flop)")
    print("-"*50)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train Random Forest
    print("  Training Random Forest...")
    rf_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train_scaled, y_train)

    # Evaluate
    y_pred = rf_model.predict(X_test_scaled)
    y_proba = rf_model.predict_proba(X_test_scaled)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    print(f"\n  === RESULTATS CLASSIFIER ===")
    print(f"  Accuracy:  {accuracy*100:.2f}%")
    print(f"  Precision: {precision*100:.2f}% (quand dit RUNNER, correct X%)")
    print(f"  Recall:    {recall*100:.2f}% (detecte X% des vrais runners)")
    print(f"  F1-Score:  {f1*100:.2f}%")

    # Cross-validation
    cv_scores = cross_val_score(rf_model, X_train_scaled, y_train, cv=5)
    print(f"  CV Score:  {cv_scores.mean()*100:.2f}% (+/- {cv_scores.std()*100:.2f}%)")

    # Feature importance
    print(f"\n  === TOP 15 FEATURES (Classifier) ===")
    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': rf_model.feature_importances_
    }).sort_values('importance', ascending=False)

    for i, row in importances.head(15).iterrows():
        print(f"  {row['feature']:30} {row['importance']*100:.2f}%")

    return rf_model, scaler, importances


def train_price_regressor(X, y, feature_cols):
    """Entraine le modele de regression pour predire le prix final"""
    print(f"\n[5/6] ENTRAINEMENT REGRESSOR (Target Price)")
    print("-"*50)

    # Filtrer les prix aberrants
    mask = (y > 0) & (y < 10000000)  # Entre $0 et $10M
    X_filtered = X[mask]
    y_filtered = y[mask]

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_filtered, y_filtered, test_size=0.2, random_state=42
    )

    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train Random Forest Regressor
    print("  Training Random Forest Regressor...")
    rf_model = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train_scaled, y_train)

    # Evaluate
    y_pred = rf_model.predict(X_test_scaled)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"\n  === RESULTATS REGRESSOR ===")
    print(f"  MAE:  ${mae:,.0f} (erreur moyenne)")
    print(f"  RMSE: ${rmse:,.0f}")
    print(f"  R2:   {r2:.3f}")

    # Calculer erreur en %
    mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
    print(f"  MAPE: {mape:.1f}% (erreur moyenne en %)")

    # Feature importance
    print(f"\n  === TOP 15 FEATURES (Regressor) ===")
    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': rf_model.feature_importances_
    }).sort_values('importance', ascending=False)

    for i, row in importances.head(15).iterrows():
        print(f"  {row['feature']:30} {row['importance']*100:.2f}%")

    return rf_model, scaler


def train_migration_classifier(X, y, feature_cols):
    """Entraine le modele pour predire la migration"""
    print(f"\n[6/6] ENTRAINEMENT MIGRATION CLASSIFIER")
    print("-"*50)

    # Utiliser seulement les features early (avant migration)
    early_features = [col for col in feature_cols if any(x in col for x in ['3s', '5s', '7s', '10s', '15s', '30s', '1min'])]
    early_features += ['early_signal_score', 'momentum_score', 'whale_confidence']
    early_features = [f for f in early_features if f in X.columns]

    X_early = X[early_features]

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_early, y, test_size=0.2, random_state=42, stratify=y
    )

    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train
    print("  Training Gradient Boosting...")
    gb_model = GradientBoostingClassifier(
        n_estimators=150,
        max_depth=8,
        learning_rate=0.1,
        random_state=42
    )
    gb_model.fit(X_train_scaled, y_train)

    # Evaluate
    y_pred = gb_model.predict(X_test_scaled)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)

    print(f"\n  === RESULTATS MIGRATION ===")
    print(f"  Accuracy:  {accuracy*100:.2f}%")
    print(f"  Precision: {precision*100:.2f}%")
    print(f"  Recall:    {recall*100:.2f}%")

    return gb_model, scaler, early_features


def save_models(classifier, clf_scaler, regressor, reg_scaler, migration_model, mig_scaler,
                feature_cols, early_features, clf_importances):
    """Sauvegarde tous les modeles"""
    print(f"\n[SAUVEGARDE DES MODELES]")
    print("-"*50)

    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Sauvegarder les modeles
    joblib.dump(classifier, models_dir / f'runner_classifier_{timestamp}.pkl')
    joblib.dump(clf_scaler, models_dir / f'runner_classifier_scaler_{timestamp}.pkl')
    joblib.dump(regressor, models_dir / f'price_regressor_{timestamp}.pkl')
    joblib.dump(reg_scaler, models_dir / f'price_regressor_scaler_{timestamp}.pkl')
    joblib.dump(migration_model, models_dir / f'migration_classifier_{timestamp}.pkl')
    joblib.dump(mig_scaler, models_dir / f'migration_classifier_scaler_{timestamp}.pkl')

    # Sauvegarder les noms de features
    with open(models_dir / f'runner_feature_names_{timestamp}.json', 'w') as f:
        json.dump(feature_cols, f)

    with open(models_dir / f'migration_feature_names_{timestamp}.json', 'w') as f:
        json.dump(early_features, f)

    # Sauvegarder aussi en "latest"
    joblib.dump(classifier, models_dir / 'runner_classifier_latest.pkl')
    joblib.dump(clf_scaler, models_dir / 'runner_classifier_scaler_latest.pkl')
    joblib.dump(regressor, models_dir / 'price_regressor_latest.pkl')
    joblib.dump(reg_scaler, models_dir / 'price_regressor_scaler_latest.pkl')
    joblib.dump(migration_model, models_dir / 'migration_classifier_latest.pkl')
    joblib.dump(mig_scaler, models_dir / 'migration_classifier_scaler_latest.pkl')

    with open(models_dir / 'runner_feature_names.json', 'w') as f:
        json.dump(feature_cols, f)

    with open(models_dir / 'migration_feature_names.json', 'w') as f:
        json.dump(early_features, f)

    # Sauvegarder les importances
    clf_importances.to_csv(models_dir / 'feature_importances.csv', index=False)

    print(f"  Modeles sauvegardes dans: {models_dir}/")
    print(f"  - runner_classifier_latest.pkl")
    print(f"  - price_regressor_latest.pkl")
    print(f"  - migration_classifier_latest.pkl")
    print(f"  - feature_importances.csv")


def main():
    # 1. Charger les donnees
    tokens = load_bot_data('bot_data.json')

    if len(tokens) < 20:
        print(f"\n[WARNING] Seulement {len(tokens)} tokens!")
        print("Il faut plus de donnees pour un bon entrainement.")
        print("Lance: python pattern_discovery_bot.py")
        print("Et laisse tourner plusieurs heures pour collecter des donnees.")

        if len(tokens) < 5:
            print("\n[STOP] Pas assez de donnees pour entrainer.")
            return

    # 2. Extraire features
    df = extract_features(tokens)

    if len(df) < 10:
        print("\n[STOP] Pas assez de donnees valides.")
        return

    # 3. Preparer les donnees
    X, y_runner, y_price, y_migration, feature_cols = prepare_training_data(df)

    # 4. Entrainer le classifier
    classifier, clf_scaler, clf_importances = train_runner_classifier(X, y_runner, feature_cols)

    # 5. Entrainer le regressor
    regressor, reg_scaler = train_price_regressor(X, y_price, feature_cols)

    # 6. Entrainer le migration classifier
    migration_model, mig_scaler, early_features = train_migration_classifier(X, y_migration, feature_cols)

    # 7. Sauvegarder
    save_models(
        classifier, clf_scaler,
        regressor, reg_scaler,
        migration_model, mig_scaler,
        feature_cols, early_features,
        clf_importances
    )

    # Resume
    print(f"\n{'='*80}")
    print("ENTRAINEMENT TERMINE!")
    print("="*80)
    print(f"""
Les modeles sont prets! Voici ce qu'ils font:

1. RUNNER CLASSIFIER
   - Input: Features a 10s, 15s, 30s, 1min...
   - Output: Probabilite que ce soit un RUNNER (0-100%)

2. PRICE REGRESSOR
   - Input: Memes features
   - Output: Prix final predit ($)

3. MIGRATION CLASSIFIER
   - Input: Features early (10s-1min)
   - Output: Probabilite de migration (0-100%)

UTILISATION:
   from predict_runner import RunnerPredictor
   predictor = RunnerPredictor()
   result = predictor.predict(token_data)

   print(f"Runner: {{result['runner_probability']}}%")
   print(f"Target: ${{result['predicted_price']:,}}")
   print(f"Migration: {{result['migration_probability']}}%")
""")
    print("="*80)


if __name__ == "__main__":
    main()

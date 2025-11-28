"""
HYPERPARAMETER OPTIMIZATION WITH OPTUNA
Optimise automatiquement les hyperparamètres pour maximiser la précision
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score
from imblearn.over_sampling import SMOTE
import joblib
import json
from datetime import datetime
from rich.console import Console
import optuna
from optuna.visualization import plot_optimization_history, plot_param_importances

import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

console = Console()

# Configuration
RANDOM_STATE = 42
TEST_SIZE = 0.2
N_TRIALS = 100  # Nombre d'essais pour l'optimisation
N_FOLDS = 5  # Cross-validation folds

# Paths
dataset_dir = Path(__file__).parent / "rug coin" / "ml_module" / "dataset"
models_dir = Path(__file__).parent / "models"
models_dir.mkdir(exist_ok=True)

console.print("\n[bold cyan]=" * 70)
console.print("[bold cyan]OPTIMISATION DES HYPERPARAMÈTRES AVEC OPTUNA")
console.print("[bold cyan]=" * 70)

# 1. Charger et préparer les données
console.print("\n[bold green][1/4] Préparation des données...")
df = pd.read_csv(dataset_dir / "features_roi.csv")

def simplify_roi_label(original_label):
    if original_label == 0:
        return 0
    elif original_label in [1, 2, 3]:
        return 1
    else:
        return 2

df['roi_simplified'] = df['roi_label'].apply(simplify_roi_label)

exclude_cols = ['token_mint', 'timestamp', 'collected_at', 'label', 'label_reason',
                'roi_label', 'roi_category', 'roi_multiplier', 'roi_simplified']
feature_cols = [col for col in df.columns if col not in exclude_cols]

X = df[feature_cols].fillna(0)
y = df['roi_simplified']

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
)

# Normalisation
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# SMOTE
if (y_train == 2).sum() >= 6:
    smote = SMOTE(random_state=RANDOM_STATE)
    X_train_balanced, y_train_balanced = smote.fit_resample(X_train_scaled, y_train)
    console.print(f"[green]   ✓ Données préparées: {len(X_train_balanced)} samples après SMOTE")
else:
    X_train_balanced = X_train_scaled
    y_train_balanced = y_train
    console.print(f"[green]   ✓ Données préparées: {len(X_train_balanced)} samples")

# 2. Définir les fonctions d'optimisation
console.print("\n[bold green][2/4] Définition des objectifs d'optimisation...")

def objective_xgboost(trial):
    """Objectif pour XGBoost"""
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 500),
        'max_depth': trial.suggest_int('max_depth', 3, 15),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'gamma': trial.suggest_float('gamma', 0, 1.0),
        'reg_alpha': trial.suggest_float('reg_alpha', 0, 2.0),
        'reg_lambda': trial.suggest_float('reg_lambda', 0, 2.0),
        'random_state': RANDOM_STATE,
        'tree_method': 'hist',
        'eval_metric': 'mlogloss',
        'n_jobs': -1
    }

    model = xgb.XGBClassifier(**params)

    # Cross-validation
    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_val_score(model, X_train_balanced, y_train_balanced, cv=cv, scoring='accuracy', n_jobs=-1)

    return scores.mean()

def objective_lightgbm(trial):
    """Objectif pour LightGBM"""
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 500),
        'max_depth': trial.suggest_int('max_depth', 3, 15),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'num_leaves': trial.suggest_int('num_leaves', 15, 127),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'reg_alpha': trial.suggest_float('reg_alpha', 0, 2.0),
        'reg_lambda': trial.suggest_float('reg_lambda', 0, 2.0),
        'random_state': RANDOM_STATE,
        'n_jobs': -1,
        'verbose': -1
    }

    model = lgb.LGBMClassifier(**params)

    # Cross-validation
    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_val_score(model, X_train_balanced, y_train_balanced, cv=cv, scoring='accuracy', n_jobs=-1)

    return scores.mean()

def objective_catboost(trial):
    """Objectif pour CatBoost"""
    params = {
        'iterations': trial.suggest_int('iterations', 100, 500),
        'depth': trial.suggest_int('depth', 3, 12),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 1, 10),
        'random_state': RANDOM_STATE,
        'verbose': False,
        'thread_count': -1
    }

    model = CatBoostClassifier(**params)

    # Cross-validation
    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_val_score(model, X_train_balanced, y_train_balanced, cv=cv, scoring='accuracy', n_jobs=1)

    return scores.mean()

# 3. Optimiser chaque modèle
console.print("\n[bold green][3/4] Optimisation des hyperparamètres...")
best_params = {}

# XGBoost
console.print("\n[bold yellow]Optimisation XGBoost...")
study_xgb = optuna.create_study(direction='maximize', study_name='xgboost')
study_xgb.optimize(objective_xgboost, n_trials=N_TRIALS, show_progress_bar=True)
best_params['xgboost'] = study_xgb.best_params
console.print(f"[green]   ✓ Meilleur score XGBoost: {study_xgb.best_value:.4f}")
console.print(f"[cyan]   Meilleurs paramètres: {study_xgb.best_params}")

# LightGBM
console.print("\n[bold yellow]Optimisation LightGBM...")
study_lgb = optuna.create_study(direction='maximize', study_name='lightgbm')
study_lgb.optimize(objective_lightgbm, n_trials=N_TRIALS, show_progress_bar=True)
best_params['lightgbm'] = study_lgb.best_params
console.print(f"[green]   ✓ Meilleur score LightGBM: {study_lgb.best_value:.4f}")
console.print(f"[cyan]   Meilleurs paramètres: {study_lgb.best_params}")

# CatBoost
console.print("\n[bold yellow]Optimisation CatBoost...")
study_cat = optuna.create_study(direction='maximize', study_name='catboost')
study_cat.optimize(objective_catboost, n_trials=N_TRIALS, show_progress_bar=True)
best_params['catboost'] = study_cat.best_params
console.print(f"[green]   ✓ Meilleur score CatBoost: {study_cat.best_value:.4f}")
console.print(f"[cyan]   Meilleurs paramètres: {study_cat.best_params}")

# 4. Entraîner les modèles finaux avec les meilleurs paramètres
console.print("\n[bold green][4/4] Entraînement des modèles optimisés...")

# XGBoost optimisé
xgb_params = best_params['xgboost'].copy()
xgb_params.update({
    'random_state': RANDOM_STATE,
    'tree_method': 'hist',
    'eval_metric': 'mlogloss',
    'n_jobs': -1
})
xgb_optimized = xgb.XGBClassifier(**xgb_params)
xgb_optimized.fit(X_train_balanced, y_train_balanced)
xgb_pred = xgb_optimized.predict(X_test_scaled)
xgb_acc = accuracy_score(y_test, xgb_pred)
console.print(f"[green]   ✓ XGBoost optimisé - Test Accuracy: {xgb_acc:.4f}")

# LightGBM optimisé
lgb_params = best_params['lightgbm'].copy()
lgb_params.update({
    'random_state': RANDOM_STATE,
    'n_jobs': -1,
    'verbose': -1
})
lgb_optimized = lgb.LGBMClassifier(**lgb_params)
lgb_optimized.fit(X_train_balanced, y_train_balanced)
lgb_pred = lgb_optimized.predict(X_test_scaled)
lgb_acc = accuracy_score(y_test, lgb_pred)
console.print(f"[green]   ✓ LightGBM optimisé - Test Accuracy: {lgb_acc:.4f}")

# CatBoost optimisé
cat_params = best_params['catboost'].copy()
cat_params.update({
    'random_state': RANDOM_STATE,
    'verbose': False,
    'thread_count': -1
})
cat_optimized = CatBoostClassifier(**cat_params)
cat_optimized.fit(X_train_balanced, y_train_balanced)
cat_pred = cat_optimized.predict(X_test_scaled)
cat_acc = accuracy_score(y_test, cat_pred)
console.print(f"[green]   ✓ CatBoost optimisé - Test Accuracy: {cat_acc:.4f}")

# Identifier le meilleur modèle
results = {
    'xgboost': xgb_acc,
    'lightgbm': lgb_acc,
    'catboost': cat_acc
}

best_model_name = max(results.items(), key=lambda x: x[1])[0]
best_model = {
    'xgboost': xgb_optimized,
    'lightgbm': lgb_optimized,
    'catboost': cat_optimized
}[best_model_name]
best_accuracy = results[best_model_name]

console.print("\n[bold green]" + "=" * 70)
console.print(f"[bold green]MEILLEUR MODÈLE OPTIMISÉ: {best_model_name.upper()}")
console.print(f"[bold green]ACCURACY: {best_accuracy:.4f} ({best_accuracy*100:.2f}%)")
console.print("[bold green]" + "=" * 70)

# Sauvegarder les résultats
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Sauvegarder le meilleur modèle
model_file = models_dir / f"roi_predictor_optimized_{best_model_name}.pkl"
joblib.dump(best_model, model_file)
console.print(f"\n[green]✓ Modèle optimisé sauvegardé: {model_file}")

# Sauvegarder en tant que latest
latest_file = models_dir / "roi_predictor_latest.pkl"
joblib.dump(best_model, latest_file)
console.print(f"[green]✓ Modèle latest mis à jour: {latest_file}")

# Sauvegarder les hyperparamètres optimaux
hyperparams_file = models_dir / f"optimized_hyperparams_{timestamp}.json"
with open(hyperparams_file, 'w') as f:
    json.dump(best_params, f, indent=2)
console.print(f"[green]✓ Hyperparamètres sauvegardés: {hyperparams_file}")

# Sauvegarder les métriques
metrics = {
    'timestamp': timestamp,
    'best_model': best_model_name,
    'best_accuracy': best_accuracy,
    'all_accuracies': {k: float(v) for k, v in results.items()},
    'best_params': best_params,
    'optimization_trials': N_TRIALS,
    'cv_folds': N_FOLDS
}

metrics_file = models_dir / f"optimized_metrics_{timestamp}.json"
with open(metrics_file, 'w') as f:
    json.dump(metrics, f, indent=2)
console.print(f"[green]✓ Métriques sauvegardées: {metrics_file}")

console.print("\n[bold green]" + "=" * 70)
console.print("[bold green]OPTIMISATION TERMINÉE!")
console.print("[bold green]" + "=" * 70)
console.print(f"\n[bold cyan]Résultats:")
for name, acc in results.items():
    console.print(f"[cyan]  {name:12} : {acc:.4f} ({acc*100:.2f}%)")
console.print(f"\n[bold green]✓ Le meilleur modèle a été sauvegardé et peut être utilisé dans l'application.")

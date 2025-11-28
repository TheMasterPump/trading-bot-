"""
ADVANCED MODEL TRAINING - XGBoost, LightGBM, CatBoost + Ensemble
Maximise la précision avec les meilleurs modèles de gradient boosting
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from imblearn.over_sampling import SMOTE
import joblib
import json
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# Import advanced gradient boosting models
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

console = Console()

# Configuration
RANDOM_STATE = 42
TEST_SIZE = 0.2
VAL_SIZE = 0.15

# Paths
dataset_dir = Path(__file__).parent / "rug coin" / "ml_module" / "dataset"
models_dir = Path(__file__).parent / "models"
models_dir.mkdir(exist_ok=True)

console.print("\n[bold cyan]=" * 70)
console.print("[bold cyan]ENTRAINEMENT MODELES AVANCES - GRADIENT BOOSTING + ENSEMBLE")
console.print("[bold cyan]=" * 70)

# 1. Charger le dataset
console.print("\n[bold green][1/7] Chargement du dataset ROI...")
df = pd.read_csv(dataset_dir / "features_roi.csv")
console.print(f"[green]   ✓ {len(df)} tokens chargés")

# 2. Simplifier les catégories
console.print("\n[bold green][2/7] Simplification des catégories...")
console.print("\n[yellow]Catégories:")
console.print("[yellow]  0 - RUG   : Token rug pull")
console.print("[yellow]  1 - SAFE  : ROI 1-10x (gain modéré)")
console.print("[yellow]  2 - GEM   : ROI >10x (excellent potentiel)")

def simplify_roi_label(original_label):
    """Simplifie en 3 catégories"""
    if original_label == 0:  # RUG
        return 0
    elif original_label in [1, 2, 3]:  # FLOP, LOW, MEDIUM
        return 1  # SAFE
    else:  # HIGH, MOON
        return 2  # GEM

df['roi_simplified'] = df['roi_label'].apply(simplify_roi_label)

# Distribution
console.print("\n[cyan]Distribution:")
label_counts = df['roi_simplified'].value_counts().sort_index()
label_names = {0: "RUG", 1: "SAFE", 2: "GEM"}
for label_id in sorted(label_counts.index):
    count = label_counts[label_id]
    percentage = (count / len(df)) * 100
    console.print(f"[cyan]  {label_id} - {label_names[label_id]:6} : {count:4} tokens ({percentage:5.1f}%)")

# 3. Préparer les features
console.print("\n[bold green][3/7] Préparation des features...")

# Colonnes à exclure
exclude_cols = ['token_mint', 'timestamp', 'collected_at', 'label', 'label_reason',
                'roi_label', 'roi_category', 'roi_multiplier', 'roi_simplified']

feature_cols = [col for col in df.columns if col not in exclude_cols]
console.print(f"[green]   ✓ {len(feature_cols)} features utilisées")

# Gérer les valeurs manquantes
X = df[feature_cols].fillna(0)
y = df['roi_simplified']

# 4. Split et normalisation
console.print("\n[bold green][4/7] Split train/val/test...")
X_train_val, X_test, y_train_val, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
)

X_train, X_val, y_train, y_val = train_test_split(
    X_train_val, y_train_val, test_size=VAL_SIZE, random_state=RANDOM_STATE, stratify=y_train_val
)

console.print(f"[green]   ✓ Train: {len(X_train)} samples")
console.print(f"[green]   ✓ Val:   {len(X_val)} samples")
console.print(f"[green]   ✓ Test:  {len(X_test)} samples")

# Normalisation (pour certains modèles)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)

# SMOTE pour équilibrer les classes
gem_count = (y_train == 2).sum()
console.print(f"\n[cyan]   GEM tokens dans train set: {gem_count}")

if gem_count >= 6:
    console.print("[green]   ✓ Application de SMOTE pour équilibrer les classes...")
    smote = SMOTE(random_state=RANDOM_STATE)
    X_train_balanced, y_train_balanced = smote.fit_resample(X_train_scaled, y_train)
    console.print(f"[green]   ✓ Train après SMOTE: {len(X_train_balanced)} samples")

    # Pour les modèles qui n'ont pas besoin de scaling
    X_train_raw_balanced, _ = smote.fit_resample(X_train, y_train)
else:
    console.print("[yellow]   ⚠ Pas assez de GEM tokens pour SMOTE")
    X_train_balanced = X_train_scaled
    X_train_raw_balanced = X_train.values
    y_train_balanced = y_train

# Distribution finale
train_dist = pd.Series(y_train_balanced).value_counts().sort_index()
console.print("\n[cyan]Distribution après SMOTE:")
for label_id in sorted(train_dist.index):
    count = train_dist[label_id]
    console.print(f"[cyan]     {label_names[label_id]:6} : {count:4} samples")

# 5. Entraîner les modèles avancés
console.print("\n[bold green][5/7] Entraînement des modèles avancés...")

models = {}
model_scores = {}

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    console=console
) as progress:

    # Random Forest (baseline)
    task = progress.add_task("[cyan]Random Forest...", total=1)
    rf_model = RandomForestClassifier(
        n_estimators=300,
        max_depth=25,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        class_weight='balanced'
    )
    rf_model.fit(X_train_balanced, y_train_balanced)
    val_pred_rf = rf_model.predict(X_val_scaled)
    val_acc_rf = accuracy_score(y_val, val_pred_rf)
    models['random_forest'] = rf_model
    model_scores['random_forest'] = val_acc_rf
    progress.update(task, completed=1)
    console.print(f"[green]   ✓ Random Forest - Val Accuracy: {val_acc_rf:.4f}")

    # XGBoost
    task = progress.add_task("[cyan]XGBoost...", total=1)
    xgb_model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=RANDOM_STATE,
        eval_metric='mlogloss',
        tree_method='hist',
        n_jobs=-1
    )
    xgb_model.fit(
        X_train_balanced, y_train_balanced,
        eval_set=[(X_val_scaled, y_val)],
        verbose=False
    )
    val_pred_xgb = xgb_model.predict(X_val_scaled)
    val_acc_xgb = accuracy_score(y_val, val_pred_xgb)
    models['xgboost'] = xgb_model
    model_scores['xgboost'] = val_acc_xgb
    progress.update(task, completed=1)
    console.print(f"[green]   ✓ XGBoost - Val Accuracy: {val_acc_xgb:.4f}")

    # LightGBM
    task = progress.add_task("[cyan]LightGBM...", total=1)
    lgb_model = lgb.LGBMClassifier(
        n_estimators=300,
        max_depth=8,
        learning_rate=0.05,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbose=-1
    )
    lgb_model.fit(
        X_train_balanced, y_train_balanced,
        eval_set=[(X_val_scaled, y_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)]
    )
    val_pred_lgb = lgb_model.predict(X_val_scaled)
    val_acc_lgb = accuracy_score(y_val, val_pred_lgb)
    models['lightgbm'] = lgb_model
    model_scores['lightgbm'] = val_acc_lgb
    progress.update(task, completed=1)
    console.print(f"[green]   ✓ LightGBM - Val Accuracy: {val_acc_lgb:.4f}")

    # CatBoost
    task = progress.add_task("[cyan]CatBoost...", total=1)
    cat_model = CatBoostClassifier(
        iterations=300,
        depth=8,
        learning_rate=0.05,
        l2_leaf_reg=3,
        random_state=RANDOM_STATE,
        verbose=False,
        thread_count=-1
    )
    cat_model.fit(
        X_train_balanced, y_train_balanced,
        eval_set=(X_val_scaled, y_val),
        early_stopping_rounds=50,
        verbose=False
    )
    val_pred_cat = cat_model.predict(X_val_scaled)
    val_acc_cat = accuracy_score(y_val, val_pred_cat)
    models['catboost'] = cat_model
    model_scores['catboost'] = val_acc_cat
    progress.update(task, completed=1)
    console.print(f"[green]   ✓ CatBoost - Val Accuracy: {val_acc_cat:.4f}")

# 6. Créer un ensemble de modèles (Voting Classifier)
console.print("\n[bold green][6/7] Création de l'ensemble de modèles...")

# Utiliser les 3 meilleurs modèles pour l'ensemble
ensemble_models = [
    ('xgboost', models['xgboost']),
    ('lightgbm', models['lightgbm']),
    ('catboost', models['catboost'])
]

voting_model = VotingClassifier(
    estimators=ensemble_models,
    voting='soft',  # Soft voting (moyenne des probabilités)
    n_jobs=-1
)

console.print("[cyan]   Entraînement de l'ensemble...")
voting_model.fit(X_train_balanced, y_train_balanced)
val_pred_ensemble = voting_model.predict(X_val_scaled)
val_acc_ensemble = accuracy_score(y_val, val_pred_ensemble)
models['ensemble'] = voting_model
model_scores['ensemble'] = val_acc_ensemble
console.print(f"[green]   ✓ Ensemble - Val Accuracy: {val_acc_ensemble:.4f}")

# 7. Évaluation finale sur le test set
console.print("\n[bold green][7/7] Évaluation finale sur le test set...")

results = {}
console.print("\n[bold cyan]" + "=" * 70)
console.print("[bold cyan]RÉSULTATS SUR TEST SET")
console.print("[bold cyan]" + "=" * 70)

for model_name, model in models.items():
    console.print(f"\n[bold yellow]{'=' * 70}")
    console.print(f"[bold yellow]MODÈLE: {model_name.upper()}")
    console.print(f"[bold yellow]{'=' * 70}")

    # Prédictions
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)

    # Métriques
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')

    console.print(f"\n[green]Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    console.print(f"[green]F1-Score: {f1:.4f}")
    console.print("\n[cyan]Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['RUG', 'SAFE', 'GEM']))
    console.print("\n[cyan]Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    results[model_name] = {
        'accuracy': float(accuracy),
        'f1_score': float(f1),
        'val_accuracy': float(model_scores.get(model_name, 0))
    }

# Identifier le meilleur modèle
best_model_name = max(results.items(), key=lambda x: x[1]['accuracy'])[0]
best_model = models[best_model_name]
best_accuracy = results[best_model_name]['accuracy']

console.print("\n[bold green]" + "=" * 70)
console.print(f"[bold green]MEILLEUR MODÈLE: {best_model_name.upper()}")
console.print(f"[bold green]ACCURACY: {best_accuracy:.4f} ({best_accuracy*100:.2f}%)")
console.print("[bold green]" + "=" * 70)

# Sauvegarder les modèles
console.print("\n[bold cyan]" + "=" * 70)
console.print("[bold cyan]SAUVEGARDE DES MODÈLES")
console.print("[bold cyan]" + "=" * 70)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Sauvegarder le meilleur modèle
model_file = models_dir / f"roi_predictor_{best_model_name}_{timestamp}.pkl"
joblib.dump(best_model, model_file)
console.print(f"\n[green]✓ Meilleur modèle sauvegardé: {model_file}")

# Sauvegarder en tant que "latest"
latest_file = models_dir / "roi_predictor_latest.pkl"
joblib.dump(best_model, latest_file)
console.print(f"[green]✓ Modèle latest: {latest_file}")

# Sauvegarder aussi l'ensemble
ensemble_file = models_dir / "roi_predictor_ensemble.pkl"
joblib.dump(models['ensemble'], ensemble_file)
console.print(f"[green]✓ Ensemble sauvegardé: {ensemble_file}")

# Sauvegarder tous les modèles individuels
for name, model in models.items():
    if name != 'ensemble':
        individual_file = models_dir / f"roi_predictor_{name}.pkl"
        joblib.dump(model, individual_file)
        console.print(f"[green]✓ {name} sauvegardé: {individual_file}")

# Sauvegarder le scaler
scaler_file = models_dir / "roi_scaler_latest.pkl"
joblib.dump(scaler, scaler_file)
console.print(f"[green]✓ Scaler sauvegardé: {scaler_file}")

# Sauvegarder les feature names
feature_file = models_dir / "roi_feature_names.json"
with open(feature_file, 'w') as f:
    json.dump(feature_cols, f, indent=2)
console.print(f"[green]✓ Features sauvegardées: {feature_file}")

# Sauvegarder les métriques complètes
metrics = {
    'timestamp': timestamp,
    'best_model': best_model_name,
    'best_accuracy': best_accuracy,
    'n_samples_train': len(X_train_balanced),
    'n_samples_test': len(X_test),
    'n_features': len(feature_cols),
    'categories': label_names,
    'all_results': results,
    'train_params': {
        'test_size': TEST_SIZE,
        'val_size': VAL_SIZE,
        'random_state': RANDOM_STATE,
        'smote_applied': True
    }
}

metrics_file = models_dir / f"roi_metrics_{timestamp}.json"
with open(metrics_file, 'w') as f:
    json.dump(metrics, f, indent=2)
console.print(f"[green]✓ Métriques sauvegardées: {metrics_file}")

# Comparaison finale
console.print("\n[bold cyan]" + "=" * 70)
console.print("[bold cyan]COMPARAISON DES MODÈLES")
console.print("[bold cyan]" + "=" * 70)
console.print("\n[cyan]Modèle              | Test Accuracy | Val Accuracy")
console.print("[cyan]" + "-" * 70)
for name, res in results.items():
    test_acc = res['accuracy'] * 100
    val_acc = res.get('val_accuracy', 0) * 100
    console.print(f"[cyan]{name:19} | {test_acc:12.2f}% | {val_acc:11.2f}%")

console.print("\n[bold green]" + "=" * 70)
console.print("[bold green]ENTRAÎNEMENT TERMINÉ!")
console.print("[bold green]" + "=" * 70)
console.print(f"\n[bold green]✓ Meilleur modèle: {best_model_name.upper()}")
console.print(f"[bold green]✓ Accuracy finale: {best_accuracy:.2%}")
console.print(f"\n[yellow]Prochaine étape: Lancer l'application Flask avec le nouveau modèle")
console.print(f"[yellow]  python app.py")

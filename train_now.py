"""
ENTRAINEMENT RAPIDE - XGBoost + LightGBM + Ensemble
Version optimisée sans CatBoost pour Windows
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from imblearn.over_sampling import SMOTE
import joblib
import json
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import xgboost as xgb
import lightgbm as lgb

console = Console()

# Configuration
RANDOM_STATE = 42
TEST_SIZE = 0.2
VAL_SIZE = 0.15

# Paths
dataset_dir = Path(__file__).parent / "rug coin" / "ml_module" / "dataset"
models_dir = Path(__file__).parent / "models"
models_dir.mkdir(exist_ok=True)

console.print("\n[bold cyan]" + "=" * 70)
console.print("[bold cyan]ENTRAINEMENT MODELES AVANCES - XGBOOST + LIGHTGBM + ENSEMBLE")
console.print("[bold cyan]" + "=" * 70)

# 1. Charger le dataset
console.print("\n[bold green][1/6] Chargement du dataset ROI...")
df = pd.read_csv(dataset_dir / "features_roi.csv")
console.print(f"[green]   OK - {len(df)} tokens charges")

# 2. Simplifier les catégories
console.print("\n[bold green][2/6] Simplification des catégories...")

def simplify_roi_label(original_label):
    if original_label == 0:
        return 0
    elif original_label in [1, 2, 3]:
        return 1
    else:
        return 2

df['roi_simplified'] = df['roi_label'].apply(simplify_roi_label)

label_counts = df['roi_simplified'].value_counts().sort_index()
label_names = {0: "RUG", 1: "SAFE", 2: "GEM"}
console.print("\n[cyan]Distribution:")
for label_id in sorted(label_counts.index):
    count = label_counts[label_id]
    percentage = (count / len(df)) * 100
    console.print(f"[cyan]  {label_id} - {label_names[label_id]:6} : {count:4} tokens ({percentage:5.1f}%)")

# 3. Préparer les features
console.print("\n[bold green][3/6] Préparation des features...")

exclude_cols = ['token_mint', 'timestamp', 'collected_at', 'label', 'label_reason',
                'roi_label', 'roi_category', 'roi_multiplier', 'roi_simplified']

feature_cols = [col for col in df.columns if col not in exclude_cols]
console.print(f"[green]   OK - {len(feature_cols)} features utilisees")

X = df[feature_cols].fillna(0)
y = df['roi_simplified']

# 4. Split et normalisation
console.print("\n[bold green][4/6] Split train/val/test...")
X_train_val, X_test, y_train_val, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
)

X_train, X_val, y_train, y_val = train_test_split(
    X_train_val, y_train_val, test_size=VAL_SIZE, random_state=RANDOM_STATE, stratify=y_train_val
)

console.print(f"[green]   OK -Train: {len(X_train)} samples")
console.print(f"[green]   OK -Val:   {len(X_val)} samples")
console.print(f"[green]   OK -Test:  {len(X_test)} samples")

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)

# SMOTE
gem_count = (y_train == 2).sum()
console.print(f"\n[cyan]   GEM tokens dans train set: {gem_count}")

if gem_count >= 6:
    console.print("[green]   OK -Application de SMOTE...")
    smote = SMOTE(random_state=RANDOM_STATE)
    X_train_balanced, y_train_balanced = smote.fit_resample(X_train_scaled, y_train)
    console.print(f"[green]   OK -Train après SMOTE: {len(X_train_balanced)} samples")
else:
    X_train_balanced = X_train_scaled
    y_train_balanced = y_train

# 5. Entraîner les modèles
console.print("\n[bold green][5/6] Entraînement des modèles...")

models = {}
model_scores = {}

with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), console=console) as progress:

    # Random Forest
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
    console.print(f"[green]   OK -Random Forest - Val Accuracy: {val_acc_rf:.4f} ({val_acc_rf*100:.2f}%)")

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
    xgb_model.fit(X_train_balanced, y_train_balanced, eval_set=[(X_val_scaled, y_val)], verbose=False)
    val_pred_xgb = xgb_model.predict(X_val_scaled)
    val_acc_xgb = accuracy_score(y_val, val_pred_xgb)
    models['xgboost'] = xgb_model
    model_scores['xgboost'] = val_acc_xgb
    progress.update(task, completed=1)
    console.print(f"[green]   OK -XGBoost - Val Accuracy: {val_acc_xgb:.4f} ({val_acc_xgb*100:.2f}%)")

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
    lgb_model.fit(X_train_balanced, y_train_balanced, eval_set=[(X_val_scaled, y_val)], callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)])
    val_pred_lgb = lgb_model.predict(X_val_scaled)
    val_acc_lgb = accuracy_score(y_val, val_pred_lgb)
    models['lightgbm'] = lgb_model
    model_scores['lightgbm'] = val_acc_lgb
    progress.update(task, completed=1)
    console.print(f"[green]   OK -LightGBM - Val Accuracy: {val_acc_lgb:.4f} ({val_acc_lgb*100:.2f}%)")

# Ensemble
console.print("\n[bold yellow]Création de l'ensemble...")
ensemble_models = [
    ('xgboost', models['xgboost']),
    ('lightgbm', models['lightgbm']),
    ('random_forest', models['random_forest'])
]

voting_model = VotingClassifier(estimators=ensemble_models, voting='soft', n_jobs=-1)
voting_model.fit(X_train_balanced, y_train_balanced)
val_pred_ensemble = voting_model.predict(X_val_scaled)
val_acc_ensemble = accuracy_score(y_val, val_pred_ensemble)
models['ensemble'] = voting_model
model_scores['ensemble'] = val_acc_ensemble
console.print(f"[green]   OK -Ensemble - Val Accuracy: {val_acc_ensemble:.4f} ({val_acc_ensemble*100:.2f}%)")

# 6. Évaluation finale
console.print("\n[bold green][6/6] Évaluation finale sur le test set...")

results = {}
for model_name, model in models.items():
    console.print(f"\n[bold yellow]{'=' * 70}")
    console.print(f"[bold yellow]MODÈLE: {model_name.upper()}")
    console.print(f"[bold yellow]{'=' * 70}")

    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')

    console.print(f"\n[green]Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    console.print(f"[green]F1-Score: {f1:.4f}")
    print(classification_report(y_test, y_pred, target_names=['RUG', 'SAFE', 'GEM']))
    print(confusion_matrix(y_test, y_pred))

    results[model_name] = {'accuracy': float(accuracy), 'f1_score': float(f1)}

# Meilleur modèle
best_model_name = max(results.items(), key=lambda x: x[1]['accuracy'])[0]
best_model = models[best_model_name]
best_accuracy = results[best_model_name]['accuracy']

console.print("\n[bold green]" + "=" * 70)
console.print(f"[bold green]MEILLEUR MODÈLE: {best_model_name.upper()}")
console.print(f"[bold green]ACCURACY: {best_accuracy:.4f} ({best_accuracy*100:.2f}%)")
console.print("[bold green]" + "=" * 70)

# Sauvegarder
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

model_file = models_dir / f"roi_predictor_{best_model_name}_{timestamp}.pkl"
joblib.dump(best_model, model_file)
console.print(f"\n[green]OK -Meilleur modèle: {model_file}")

latest_file = models_dir / "roi_predictor_latest.pkl"
joblib.dump(best_model, latest_file)
console.print(f"[green]OK -Latest: {latest_file}")

ensemble_file = models_dir / "roi_predictor_ensemble.pkl"
joblib.dump(models['ensemble'], ensemble_file)
console.print(f"[green]OK -Ensemble: {ensemble_file}")

for name, model in models.items():
    if name != 'ensemble':
        individual_file = models_dir / f"roi_predictor_{name}.pkl"
        joblib.dump(model, individual_file)
        console.print(f"[green]OK -{name}: {individual_file}")

scaler_file = models_dir / "roi_scaler_latest.pkl"
joblib.dump(scaler, scaler_file)
console.print(f"[green]OK -Scaler: {scaler_file}")

feature_file = models_dir / "roi_feature_names.json"
with open(feature_file, 'w') as f:
    json.dump(feature_cols, f, indent=2)
console.print(f"[green]OK -Features: {feature_file}")

metrics = {
    'timestamp': timestamp,
    'best_model': best_model_name,
    'best_accuracy': best_accuracy,
    'n_samples_train': len(X_train_balanced),
    'n_samples_test': len(X_test),
    'n_features': len(feature_cols),
    'categories': label_names,
    'all_results': results
}

metrics_file = models_dir / f"roi_metrics_{timestamp}.json"
with open(metrics_file, 'w') as f:
    json.dump(metrics, f, indent=2)
console.print(f"[green]OK -Métriques: {metrics_file}")

console.print("\n[bold cyan]COMPARAISON:")
console.print("[cyan]Modèle              | Test Accuracy")
console.print("[cyan]" + "-" * 40)
for name, res in results.items():
    test_acc = res['accuracy'] * 100
    console.print(f"[cyan]{name:19} | {test_acc:12.2f}%")

console.print("\n[bold green]" + "=" * 70)
console.print("[bold green]ENTRAINEMENT TERMINÉ!")
console.print(f"[bold green]OK -Meilleur: {best_model_name.upper()} - {best_accuracy:.2%}")
console.print("[bold green]" + "=" * 70)

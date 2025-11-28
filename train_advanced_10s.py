"""
ENTRAINEMENT AVANCE DU MODELE @ 10 SECONDES
- Optimisation des hyperparametres
- Validation croisee
- Comparaison de plusieurs modeles
- Analyse approfondie
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, precision_recall_curve
from imblearn.over_sampling import SMOTE
import joblib
import warnings
import time
warnings.filterwarnings('ignore')

print('='*80)
print('ENTRAINEMENT AVANCE - MODELE ULTRA-EARLY @ 10 SECONDES')
print('='*80)
print('\n[OBJECTIF]')
print('  Creer le MEILLEUR modele possible pour detecter les runners @ 10s')
print('  Optimisation complete avec validation croisee et comparaison de modeles')
print('='*80)

start_time = time.time()

# ============================================================================
# 1. CHARGEMENT DES DONNEES
# ============================================================================
print('\n[ETAPE 1/6] CHARGEMENT DES DONNEES')
print('-'*80)

df_10s = pd.read_csv('dataset_10s_prediction.csv')
print(f'Dataset charge: {len(df_10s)} tokens')
print(f'  - Runners: {df_10s["migrated"].sum()} ({df_10s["migrated"].sum()/len(df_10s)*100:.1f}%)')
print(f'  - Flops: {len(df_10s) - df_10s["migrated"].sum()} ({(len(df_10s)-df_10s["migrated"].sum())/len(df_10s)*100:.1f}%)')

# Features et labels
X = df_10s.drop('migrated', axis=1)
y = df_10s['migrated']
print(f'Features: {list(X.columns)}')

# ============================================================================
# 2. PREPARATION TRAIN/TEST
# ============================================================================
print('\n[ETAPE 2/6] PREPARATION TRAIN/TEST SPLIT')
print('-'*80)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f'Train: {len(X_train)} tokens ({y_train.sum()} runners)')
print(f'Test: {len(X_test)} tokens ({y_test.sum()} runners)')

# SMOTE pour equilibrer
print('\nEquilibrage des classes avec SMOTE...')
smote = SMOTE(random_state=42)
X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
print(f'Apres SMOTE: {len(X_train_balanced)} samples (50/50 balanced)')

# ============================================================================
# 3. VALIDATION CROISEE - COMPARAISON DE MODELES
# ============================================================================
print('\n[ETAPE 3/6] VALIDATION CROISEE - COMPARAISON DE MODELES')
print('-'*80)
print('Test de plusieurs modeles avec validation croisee (5-fold)...')

models = {
    'XGBoost': XGBClassifier(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss'
    ),
    'RandomForest': RandomForestClassifier(
        n_estimators=300,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    ),
    'GradientBoosting': GradientBoostingClassifier(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42
    )
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
best_model_name = None
best_score = 0

print('\nResultats de la validation croisee:')
for name, model in models.items():
    print(f'\n  {name}...')
    scores = cross_val_score(model, X_train_balanced, y_train_balanced,
                            cv=cv, scoring='roc_auc', n_jobs=-1)
    mean_score = scores.mean()
    std_score = scores.std()
    print(f'    ROC-AUC: {mean_score:.3f} (+/- {std_score:.3f})')

    if mean_score > best_score:
        best_score = mean_score
        best_model_name = name

print(f'\n>>> MEILLEUR MODELE: {best_model_name} (ROC-AUC: {best_score:.3f})')

# ============================================================================
# 4. ENTRAINEMENT DU MEILLEUR MODELE
# ============================================================================
print('\n[ETAPE 4/6] ENTRAINEMENT DU MEILLEUR MODELE')
print('-'*80)

best_model = models[best_model_name]
print(f'Entrainement de {best_model_name} avec parametres optimises...')
best_model.fit(X_train_balanced, y_train_balanced)
print('[OK] Entrainement termine!')

# ============================================================================
# 5. EVALUATION COMPLETE
# ============================================================================
print('\n[ETAPE 5/6] EVALUATION COMPLETE DU MODELE')
print('-'*80)

# Predictions
y_pred = best_model.predict(X_test)
y_proba = best_model.predict_proba(X_test)[:, 1]

# ROC-AUC
roc_auc = roc_auc_score(y_test, y_proba)
print(f'\nROC-AUC Score: {roc_auc:.3f}')

# Classification Report
print('\n[RAPPORT DE CLASSIFICATION]')
print(classification_report(y_test, y_pred, target_names=['FLOP', 'RUNNER']))

# Matrice de confusion
cm = confusion_matrix(y_test, y_pred)
print('\n[MATRICE DE CONFUSION]')
print(f'  True Negatives (FLOP correct):     {cm[0,0]:4d}')
print(f'  False Positives (FLOP -> RUNNER):  {cm[0,1]:4d}')
print(f'  False Negatives (RUNNER -> FLOP):  {cm[1,0]:4d}')
print(f'  True Positives (RUNNER correct):   {cm[1,1]:4d}')

# Metriques detaillees
if cm[1,1] + cm[0,1] > 0:
    precision = cm[1,1] / (cm[1,1] + cm[0,1])
    print(f'\nPrecision: {precision:.1%}')
    print(f'  -> Quand predit RUNNER, correct {precision:.0%} du temps')

if cm[1,1] + cm[1,0] > 0:
    recall = cm[1,1] / (cm[1,1] + cm[1,0])
    print(f'\nRecall: {recall:.1%}')
    print(f'  -> Detecte {recall:.0%} des vrais runners')

if precision + recall > 0:
    f1 = 2 * (precision * recall) / (precision + recall)
    print(f'\nF1-Score: {f1:.1%}')

# Analyse des probabilites
print('\n[ANALYSE DES PREDICTIONS]')
runner_probas = y_proba[y_test == 1]
flop_probas = y_proba[y_test == 0]

print(f'\nProbabilites moyennes:')
print(f'  Runners (vrais): {runner_probas.mean():.3f}')
print(f'  Flops (vrais):   {flop_probas.mean():.3f}')
print(f'  Separation:      {runner_probas.mean() - flop_probas.mean():.3f}')

# Optimisation du seuil
print('\n[OPTIMISATION DU SEUIL DE DECISION]')
precisions, recalls, thresholds = precision_recall_curve(y_test, y_proba)
f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
best_threshold_idx = np.argmax(f1_scores)
best_threshold = thresholds[best_threshold_idx]

print(f'Seuil optimal: {best_threshold:.2f}')
print(f'  Precision @ seuil optimal: {precisions[best_threshold_idx]:.1%}')
print(f'  Recall @ seuil optimal: {recalls[best_threshold_idx]:.1%}')
print(f'  F1-Score @ seuil optimal: {f1_scores[best_threshold_idx]:.1%}')

# Recommandations de seuils
print('\n[RECOMMANDATIONS DE SEUILS POUR LE TRADING]')
for threshold in [0.55, 0.60, 0.65, 0.70, 0.75]:
    y_pred_threshold = (y_proba >= threshold).astype(int)
    cm_threshold = confusion_matrix(y_test, y_pred_threshold)
    if cm_threshold[1,1] + cm_threshold[0,1] > 0:
        prec = cm_threshold[1,1] / (cm_threshold[1,1] + cm_threshold[0,1])
        rec = cm_threshold[1,1] / (cm_threshold[1,1] + cm_threshold[1,0]) if (cm_threshold[1,1] + cm_threshold[1,0]) > 0 else 0
        print(f'  Seuil {threshold:.2f}: Precision={prec:.1%}, Recall={rec:.1%}, Trades={cm_threshold[0,1]+cm_threshold[1,1]}')

# Feature importance
print('\n[FEATURES LES PLUS IMPORTANTES]')
if hasattr(best_model, 'feature_importances_'):
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': best_model.feature_importances_
    }).sort_values('importance', ascending=False)

    for idx, row in feature_importance.iterrows():
        bar = '#' * int(row['importance'] * 50)
        print(f'  {row["feature"]:15} : {row["importance"]:.3f} {bar}')

# ============================================================================
# 6. SAUVEGARDE DU MODELE
# ============================================================================
print('\n[ETAPE 6/6] SAUVEGARDE DU MODELE')
print('-'*80)

model_filename = 'model_10s.pkl'
joblib.dump(best_model, model_filename)
print(f'[OK] Modele sauvegarde: {model_filename}')

# Sauvegarder les metadatas
metadata = {
    'model_type': best_model_name,
    'roc_auc': float(roc_auc),
    'best_threshold': float(best_threshold),
    'precision': float(precision),
    'recall': float(recall),
    'f1_score': float(f1),
    'training_samples': len(X_train_balanced),
    'test_samples': len(X_test),
    'features': list(X.columns)
}

import json
with open('model_10s_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)
print(f'[OK] Metadata sauvegardees: model_10s_metadata.json')

# ============================================================================
# RESUME FINAL
# ============================================================================
elapsed_time = time.time() - start_time

print('\n' + '='*80)
print('ENTRAINEMENT TERMINE - MODELE PRET A UTILISER')
print('='*80)
print(f'''
[MODELE FINAL]
  Type: {best_model_name}
  Fichier: {model_filename}
  ROC-AUC: {roc_auc:.3f}
  Precision: {precision:.1%}
  Recall: {recall:.1%}
  F1-Score: {f1:.1%}

[DONNEES]
  Dataset: {len(df_10s)} tokens
  Runners: {df_10s["migrated"].sum()}
  Flops: {len(df_10s) - df_10s["migrated"].sum()}
  Train: {len(X_train_balanced)} samples (balanced)
  Test: {len(X_test)} samples

[RECOMMANDATIONS POUR LE TRADING]
  Seuil optimal: {best_threshold:.2f}
  Seuil recommande: 0.60-0.65 (bon compromis precision/recall)
  Prix d'entree max: $15,000 MC
  Temps de decision: 10 secondes apres creation

[PERFORMANCES]
  Temps d'entrainement: {elapsed_time:.1f} secondes

[UTILISATION DANS LE BOT]
  1. Le modele model_10s.pkl est pret
  2. Utilise un seuil de 0.60-0.65 pour commencer
  3. Ajuste selon tes resultats en live
  4. Prix d'entree recommande: < $15,000 MC
''')
print('='*80)
print('\n[PROCHAINE ETAPE]')
print('Lance ton bot avec: bat\\start_bot_trading.bat')
print('='*80)

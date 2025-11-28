import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from imblearn.over_sampling import SMOTE
import joblib
import warnings
warnings.filterwarnings('ignore')

print('='*80)
print('ENTRAINEMENT DES MODELES POUR ENTREE A 10-15K MC')
print('='*80)

# ============================================================================
# MODELE 1: PREDICTION @ 10 SECONDES
# ============================================================================
print('\n[MODELE 1: PREDICTION @ 10s - ULTRA EARLY]')
print('-'*80)

df_10s = pd.read_csv('dataset_10s_prediction_COMBINED.csv')
print(f'Dataset: {len(df_10s)} tokens ({df_10s["migrated"].sum()} runners)')

# Features et labels
X_10s = df_10s.drop('migrated', axis=1)
y_10s = df_10s['migrated']

# Split train/test
X_train_10s, X_test_10s, y_train_10s, y_test_10s = train_test_split(
    X_10s, y_10s, test_size=0.2, random_state=42, stratify=y_10s
)

# SMOTE pour equilibrer les classes
smote = SMOTE(random_state=42)
X_train_10s_balanced, y_train_10s_balanced = smote.fit_resample(X_train_10s, y_train_10s)
print(f'Apres SMOTE: {len(y_train_10s_balanced)} samples (balanced)')

# Entrainer XGBoost
model_10s = XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric='logloss'
)

print('Entrainement du modele...')
model_10s.fit(X_train_10s_balanced, y_train_10s_balanced)

# Predictions
y_pred_10s = model_10s.predict(X_test_10s)
y_proba_10s = model_10s.predict_proba(X_test_10s)[:, 1]

# Evaluation
print('\n[RESULTATS @ 10s]')
print(classification_report(y_test_10s, y_pred_10s, target_names=['FLOP', 'RUNNER']))
print(f'ROC-AUC Score: {roc_auc_score(y_test_10s, y_proba_10s):.3f}')

# Matrice de confusion
cm = confusion_matrix(y_test_10s, y_pred_10s)
print('\nMatrice de confusion:')
print(f'  True Negatives (FLOP correct):     {cm[0,0]}')
print(f'  False Positives (FLOP -> RUNNER):  {cm[0,1]}')
print(f'  False Negatives (RUNNER -> FLOP):  {cm[1,0]}')
print(f'  True Positives (RUNNER correct):   {cm[1,1]}')

# Calculer precision et recall
if cm[1,1] + cm[0,1] > 0:
    precision = cm[1,1] / (cm[1,1] + cm[0,1])
    print(f'\nPrecision: {precision:.2%} (quand predit RUNNER, correct {precision:.0%} du temps)')
if cm[1,1] + cm[1,0] > 0:
    recall = cm[1,1] / (cm[1,1] + cm[1,0])
    print(f'Recall: {recall:.2%} (detecte {recall:.0%} des vrais runners)')

# Feature importance
feature_importance_10s = pd.DataFrame({
    'feature': X_10s.columns,
    'importance': model_10s.feature_importances_
}).sort_values('importance', ascending=False)

print('\nFeatures importantes (ordre):')
for i, row in feature_importance_10s.iterrows():
    print(f'  {row["feature"]:15} : {row["importance"]:.3f}')

# Sauvegarder le modele
joblib.dump(model_10s, 'model_10s.pkl')
print('\nModele sauvegarde: model_10s.pkl')

# ============================================================================
# MODELE 2: PREDICTION @ 15 SECONDES
# ============================================================================
print('\n' + '='*80)
print('[MODELE 2: PREDICTION @ 15s - VERY EARLY]')
print('-'*80)

df_15s = pd.read_csv('dataset_15s_prediction_COMBINED.csv')
print(f'Dataset: {len(df_15s)} tokens ({df_15s["migrated"].sum()} runners)')

# Features et labels
X_15s = df_15s.drop('migrated', axis=1)
y_15s = df_15s['migrated']

# Split train/test
X_train_15s, X_test_15s, y_train_15s, y_test_15s = train_test_split(
    X_15s, y_15s, test_size=0.2, random_state=42, stratify=y_15s
)

# SMOTE
X_train_15s_balanced, y_train_15s_balanced = smote.fit_resample(X_train_15s, y_train_15s)
print(f'Apres SMOTE: {len(y_train_15s_balanced)} samples (balanced)')

# Entrainer XGBoost
model_15s = XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric='logloss'
)

print('Entrainement du modele...')
model_15s.fit(X_train_15s_balanced, y_train_15s_balanced)

# Predictions
y_pred_15s = model_15s.predict(X_test_15s)
y_proba_15s = model_15s.predict_proba(X_test_15s)[:, 1]

# Evaluation
print('\n[RESULTATS @ 15s]')
print(classification_report(y_test_15s, y_pred_15s, target_names=['FLOP', 'RUNNER']))
print(f'ROC-AUC Score: {roc_auc_score(y_test_15s, y_proba_15s):.3f}')

# Matrice de confusion
cm = confusion_matrix(y_test_15s, y_pred_15s)
print('\nMatrice de confusion:')
print(f'  True Negatives (FLOP correct):     {cm[0,0]}')
print(f'  False Positives (FLOP -> RUNNER):  {cm[0,1]}')
print(f'  False Negatives (RUNNER -> FLOP):  {cm[1,0]}')
print(f'  True Positives (RUNNER correct):   {cm[1,1]}')

# Calculer precision et recall
if cm[1,1] + cm[0,1] > 0:
    precision = cm[1,1] / (cm[1,1] + cm[0,1])
    print(f'\nPrecision: {precision:.2%} (quand predit RUNNER, correct {precision:.0%} du temps)')
if cm[1,1] + cm[1,0] > 0:
    recall = cm[1,1] / (cm[1,1] + cm[1,0])
    print(f'Recall: {recall:.2%} (detecte {recall:.0%} des vrais runners)')

# Feature importance
feature_importance_15s = pd.DataFrame({
    'feature': X_15s.columns,
    'importance': model_15s.feature_importances_
}).sort_values('importance', ascending=False)

print('\nTop 10 features importantes:')
for i, row in feature_importance_15s.head(10).iterrows():
    print(f'  {row["feature"]:25} : {row["importance"]:.3f}')

# Sauvegarder le modele
joblib.dump(model_15s, 'model_15s.pkl')
print('\nModele sauvegarde: model_15s.pkl')

# ============================================================================
# RESUME
# ============================================================================
print('\n' + '='*80)
print('RESUME - SYSTEME DE PREDICTION PRET')
print('='*80)
print(f'''
MODELES ENTRAINES:
1. model_10s.pkl - Prediction @ 10 secondes (7 features)
2. model_15s.pkl - Prediction @ 15 secondes (15 features)

STRATEGIE D'UTILISATION:
-----------------------
@ 10 SECONDES:
  - Charger model_10s.pkl
  - Predire: proba_10s = model.predict_proba(features)[:, 1]
  - SI proba_10s > 0.65 ET MC < $15,000:
      → ENTRER IMMEDIATEMENT (prix d'entree: 10-15K)
  - SINON:
      → SURVEILLER jusqu'a 15 secondes

@ 15 SECONDES:
  - Charger model_15s.pkl
  - Predire: proba_15s = model.predict_proba(features)[:, 1]
  - SI proba_15s > 0.70 ET MC < $20,000:
      → ENTRER MAINTENANT (prix d'entree: 15-20K)
  - SINON:
      → IGNORER le token (trop cher ou pas assez confiant)

OBJECTIF ATTEINT:
- Entree maximale a 10-20K MC
- Detection ultra-rapide (10-15 secondes)
- Double confirmation pour plus de securite

PROCHAINE ETAPE:
- Creer le script de prediction en temps reel
''')
print('='*80)

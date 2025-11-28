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
print('ENTRAINEMENT DES MODELES ULTRA-PRECOCES @ 5s ET 7s')
print('='*80)

# ============================================================================
# MODELE 1: PREDICTION @ 5 SECONDES
# ============================================================================
print('\n[MODELE 1: PREDICTION @ 5s - ULTRA EARLY ENTRY]')
print('-'*80)

try:
    df_5s = pd.read_csv('dataset_5s_prediction.csv')
    print(f'Dataset: {len(df_5s)} tokens ({df_5s["migrated"].sum()} runners)')

    if len(df_5s) < 10:
        print('[ERREUR] Pas assez de donnees pour entrainer le modele @ 5s')
        print('Collecte plus de donnees avec pattern_discovery_bot.py')
        exit(1)

    # Features et labels
    X_5s = df_5s.drop('migrated', axis=1)
    y_5s = df_5s['migrated']

    # Verifier qu'on a des runners ET des flops
    if y_5s.sum() == 0 or y_5s.sum() == len(y_5s):
        print('[ERREUR] Dataset desequilibre - il faut des runners ET des flops')
        print(f'  Runners: {y_5s.sum()}')
        print(f'  Flops: {len(y_5s) - y_5s.sum()}')
        exit(1)

    # Split train/test
    X_train_5s, X_test_5s, y_train_5s, y_test_5s = train_test_split(
        X_5s, y_5s, test_size=0.2, random_state=42, stratify=y_5s
    )

    # SMOTE pour equilibrer les classes
    smote = SMOTE(random_state=42)
    X_train_5s_balanced, y_train_5s_balanced = smote.fit_resample(X_train_5s, y_train_5s)
    print(f'Apres SMOTE: {len(y_train_5s_balanced)} samples (balanced)')

    # Entrainer XGBoost
    model_5s = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss'
    )

    print('Entrainement du modele @ 5s...')
    model_5s.fit(X_train_5s_balanced, y_train_5s_balanced)

    # Predictions
    y_pred_5s = model_5s.predict(X_test_5s)
    y_proba_5s = model_5s.predict_proba(X_test_5s)[:, 1]

    # Evaluation
    print('\n[RESULTATS @ 5s]')
    print(classification_report(y_test_5s, y_pred_5s, target_names=['FLOP', 'RUNNER']))
    print(f'ROC-AUC Score: {roc_auc_score(y_test_5s, y_proba_5s):.3f}')

    # Matrice de confusion
    cm = confusion_matrix(y_test_5s, y_pred_5s)
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
    feature_importance_5s = pd.DataFrame({
        'feature': X_5s.columns,
        'importance': model_5s.feature_importances_
    }).sort_values('importance', ascending=False)

    print('\nFeatures importantes @ 5s:')
    for i, row in feature_importance_5s.iterrows():
        print(f'  {row["feature"]:15} : {row["importance"]:.3f}')

    # Sauvegarder le modele
    joblib.dump(model_5s, 'model_5s.pkl')
    print('\nModele sauvegarde: model_5s.pkl')

    model_5s_trained = True

except FileNotFoundError:
    print('[ERREUR] dataset_5s_prediction.csv non trouve')
    print('Lance d\'abord: python create_dataset_5s.py')
    model_5s_trained = False
except Exception as e:
    print(f'[ERREUR] Impossible d\'entrainer le modele @ 5s: {e}')
    model_5s_trained = False

# ============================================================================
# MODELE 2: PREDICTION @ 7 SECONDES
# ============================================================================
print('\n' + '='*80)
print('[MODELE 2: PREDICTION @ 7s - VERY EARLY ENTRY]')
print('-'*80)

try:
    df_7s = pd.read_csv('dataset_7s_prediction.csv')
    print(f'Dataset: {len(df_7s)} tokens ({df_7s["migrated"].sum()} runners)')

    if len(df_7s) < 10:
        print('[ERREUR] Pas assez de donnees pour entrainer le modele @ 7s')
        print('Collecte plus de donnees avec pattern_discovery_bot.py')
        exit(1)

    # Features et labels
    X_7s = df_7s.drop('migrated', axis=1)
    y_7s = df_7s['migrated']

    # Verifier qu'on a des runners ET des flops
    if y_7s.sum() == 0 or y_7s.sum() == len(y_7s):
        print('[ERREUR] Dataset desequilibre - il faut des runners ET des flops')
        print(f'  Runners: {y_7s.sum()}')
        print(f'  Flops: {len(y_7s) - y_7s.sum()}')
        exit(1)

    # Split train/test
    X_train_7s, X_test_7s, y_train_7s, y_test_7s = train_test_split(
        X_7s, y_7s, test_size=0.2, random_state=42, stratify=y_7s
    )

    # SMOTE
    X_train_7s_balanced, y_train_7s_balanced = smote.fit_resample(X_train_7s, y_train_7s)
    print(f'Apres SMOTE: {len(y_train_7s_balanced)} samples (balanced)')

    # Entrainer XGBoost
    model_7s = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss'
    )

    print('Entrainement du modele @ 7s...')
    model_7s.fit(X_train_7s_balanced, y_train_7s_balanced)

    # Predictions
    y_pred_7s = model_7s.predict(X_test_7s)
    y_proba_7s = model_7s.predict_proba(X_test_7s)[:, 1]

    # Evaluation
    print('\n[RESULTATS @ 7s]')
    print(classification_report(y_test_7s, y_pred_7s, target_names=['FLOP', 'RUNNER']))
    print(f'ROC-AUC Score: {roc_auc_score(y_test_7s, y_proba_7s):.3f}')

    # Matrice de confusion
    cm = confusion_matrix(y_test_7s, y_pred_7s)
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
    feature_importance_7s = pd.DataFrame({
        'feature': X_7s.columns,
        'importance': model_7s.feature_importances_
    }).sort_values('importance', ascending=False)

    print('\nFeatures importantes @ 7s:')
    for i, row in feature_importance_7s.iterrows():
        print(f'  {row["feature"]:15} : {row["importance"]:.3f}')

    # Sauvegarder le modele
    joblib.dump(model_7s, 'model_7s.pkl')
    print('\nModele sauvegarde: model_7s.pkl')

    model_7s_trained = True

except FileNotFoundError:
    print('[ERREUR] dataset_7s_prediction.csv non trouve')
    print('Lance d\'abord: python create_dataset_7s.py')
    model_7s_trained = False
except Exception as e:
    print(f'[ERREUR] Impossible d\'entrainer le modele @ 7s: {e}')
    model_7s_trained = False

# ============================================================================
# RESUME
# ============================================================================
print('\n' + '='*80)
print('RESUME - SYSTEME DE PREDICTION ULTRA-PRECOCE')
print('='*80)

if model_5s_trained and model_7s_trained:
    print(f'''
MODELES ENTRAINES:
1. model_5s.pkl - Prediction @ 5 secondes (entree 6-8K MC)
2. model_7s.pkl - Prediction @ 7 secondes (entree 8-12K MC)

STRATEGIE D'UTILISATION:
-----------------------
@ 5 SECONDES:
  - Charger model_5s.pkl
  - Predire: proba_5s = model.predict_proba(features)[:, 1]
  - SI proba_5s > 0.70 ET MC < $8,000:
      → ENTRER IMMEDIATEMENT (prix d'entree: 6-8K)
  - SINON:
      → SURVEILLER jusqu'a 7 secondes

@ 7 SECONDES:
  - Charger model_7s.pkl
  - Predire: proba_7s = model.predict_proba(features)[:, 1]
  - SI proba_7s > 0.75 ET MC < $12,000:
      → ENTRER MAINTENANT (prix d'entree: 8-12K)
  - SINON:
      → IGNORER le token (fallback sur modeles 10s/15s)

TAKE PROFIT:
  - x2 (200% gain) au lieu de $69K migration
  - Sortie plus rapide, moins de risque

OBJECTIF ATTEINT:
- Entree ULTRA-PRECOCE a 6-12K MC
- Detection en 5-7 secondes
- Take profit a x2 pour gains rapides

PROCHAINE ETAPE:
- Mettre a jour live_trading_bot.py avec ces modeles
- Ajuster take profit a x2 (200%)
''')
else:
    print('\n[ATTENTION] Certains modeles n\'ont pas pu etre entraines')
    if not model_5s_trained:
        print('  - model_5s.pkl: ECHEC')
    if not model_7s_trained:
        print('  - model_7s.pkl: ECHEC')
    print('\nVERIFIE:')
    print('  1. bot_data.json contient des tokens avec snapshots @ 5s et 7s')
    print('  2. Lance: python create_dataset_5s.py')
    print('  3. Lance: python create_dataset_7s.py')
    print('  4. Relance ce script')

print('='*80)

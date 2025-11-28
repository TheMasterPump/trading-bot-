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
print('ENTRAINEMENT MODELE ULTRA-EARLY @ 7 SECONDES')
print('='*80)
print('\n[OBJECTIF]')
print('  Predire les runners a 7 secondes pour entrer TRES TOT')
print('  Prix d\'entree cible: 5-12K MC')
print('='*80)

# ============================================================================
# CHARGEMENT DES DONNEES
# ============================================================================
print('\n[1] CHARGEMENT DU DATASET...')
try:
    df_7s = pd.read_csv('dataset_7s_prediction.csv')
    print(f'  [OK] Dataset charge: {len(df_7s)} tokens')
except FileNotFoundError:
    print('\n[ERREUR] dataset_7s_prediction.csv introuvable!')
    print('Lance d\'abord: python create_dataset_7s.py')
    exit(1)

# Verifier la structure
print(f'\n[STRUCTURE DU DATASET]')
print(f'  Total tokens: {len(df_7s)}')
print(f'  Runners (migrated=1): {df_7s["migrated"].sum()} ({df_7s["migrated"].sum()/len(df_7s)*100:.1f}%)')
print(f'  Flops (migrated=0): {len(df_7s) - df_7s["migrated"].sum()} ({(len(df_7s)-df_7s["migrated"].sum())/len(df_7s)*100:.1f}%)')
print(f'  Features: {list(df_7s.columns)}')

# Verifier qu'on a assez de donnees
if len(df_7s) < 50:
    print('\n[ATTENTION] Dataset trop petit (< 50 tokens)')
    print('Il est recommande d\'avoir au moins 100+ tokens pour un bon entrainement')
    response = input('Continuer quand meme ? (o/n): ')
    if response.lower() != 'o':
        exit(0)

# ============================================================================
# PREPARATION DES DONNEES
# ============================================================================
print('\n[2] PREPARATION DES DONNEES...')

# Features et labels
X_7s = df_7s.drop('migrated', axis=1)
y_7s = df_7s['migrated']

print(f'  Features: {list(X_7s.columns)}')
print(f'  Shape: {X_7s.shape}')

# Split train/test
X_train_7s, X_test_7s, y_train_7s, y_test_7s = train_test_split(
    X_7s, y_7s, test_size=0.2, random_state=42, stratify=y_7s
)

print(f'  Train set: {len(X_train_7s)} tokens')
print(f'  Test set: {len(X_test_7s)} tokens')

# SMOTE pour equilibrer les classes
print('\n[3] EQUILIBRAGE DES CLASSES (SMOTE)...')
smote = SMOTE(random_state=42)
X_train_7s_balanced, y_train_7s_balanced = smote.fit_resample(X_train_7s, y_train_7s)
print(f'  Avant SMOTE: {len(X_train_7s)} samples')
print(f'  Apres SMOTE: {len(X_train_7s_balanced)} samples (balanced)')

# ============================================================================
# ENTRAINEMENT DU MODELE
# ============================================================================
print('\n[4] ENTRAINEMENT DU MODELE XGBoost...')

model_7s = XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    eval_metric='logloss'
)

print('  En cours d\'entrainement...')
model_7s.fit(X_train_7s_balanced, y_train_7s_balanced)
print('  [OK] Entrainement termine!')

# ============================================================================
# EVALUATION DU MODELE
# ============================================================================
print('\n[5] EVALUATION DU MODELE...')

# Predictions
y_pred_7s = model_7s.predict(X_test_7s)
y_proba_7s = model_7s.predict_proba(X_test_7s)[:, 1]

# Rapport de classification
print('\n' + '='*80)
print('[RESULTATS @ 7 SECONDES]')
print('='*80)
print(classification_report(y_test_7s, y_pred_7s, target_names=['FLOP', 'RUNNER']))

# ROC-AUC Score
roc_auc = roc_auc_score(y_test_7s, y_proba_7s)
print(f'ROC-AUC Score: {roc_auc:.3f}')

# Matrice de confusion
cm = confusion_matrix(y_test_7s, y_pred_7s)
print('\n[MATRICE DE CONFUSION]')
print(f'  True Negatives (FLOP correct):     {cm[0,0]}')
print(f'  False Positives (FLOP -> RUNNER):  {cm[0,1]}')
print(f'  False Negatives (RUNNER -> FLOP):  {cm[1,0]}')
print(f'  True Positives (RUNNER correct):   {cm[1,1]}')

# Calculer precision et recall
if cm[1,1] + cm[0,1] > 0:
    precision = cm[1,1] / (cm[1,1] + cm[0,1])
    print(f'\nPrecision: {precision:.2%}')
    print(f'  -> Quand le modele predit RUNNER, il a raison {precision:.0%} du temps')
else:
    precision = 0
    print('\nPrecision: N/A (aucun RUNNER predit)')

if cm[1,1] + cm[1,0] > 0:
    recall = cm[1,1] / (cm[1,1] + cm[1,0])
    print(f'\nRecall: {recall:.2%}')
    print(f'  -> Le modele detecte {recall:.0%} des vrais runners')
else:
    recall = 0
    print('\nRecall: N/A (aucun vrai RUNNER)')

# Feature importance
print('\n[FEATURES LES PLUS IMPORTANTES]')
feature_importance_7s = pd.DataFrame({
    'feature': X_7s.columns,
    'importance': model_7s.feature_importances_
}).sort_values('importance', ascending=False)

for idx, row in feature_importance_7s.iterrows():
    print(f'  {row["feature"]:15} : {row["importance"]:.3f}')

# ============================================================================
# SAUVEGARDER LE MODELE
# ============================================================================
print('\n[6] SAUVEGARDE DU MODELE...')
model_filename = 'model_7s.pkl'
joblib.dump(model_7s, model_filename)
print(f'  [OK] Modele sauvegarde: {model_filename}')

# ============================================================================
# RESUME ET RECOMMANDATIONS
# ============================================================================
print('\n' + '='*80)
print('ENTRAINEMENT TERMINE - MODELE PRET')
print('='*80)
print(f'''
[MODELE CREE]
  Fichier: {model_filename}
  Dataset: {len(df_7s)} tokens ({df_7s["migrated"].sum()} runners)
  ROC-AUC: {roc_auc:.3f}
  Precision: {precision:.1%}
  Recall: {recall:.1%}

[COMMENT UTILISER CE MODELE]
  1. Charger le modele:
     model = joblib.load('model_7s.pkl')

  2. Preparer les features @ 7 secondes:
     features = {{
         'txn': nb_transactions,
         'traders': nb_traders_uniques,
         'buy_ratio': ratio_achats,
         'mc': market_cap,
         'velocity': vitesse_croissance
     }}

  3. Predire:
     proba = model.predict_proba([list(features.values())])[0, 1]

  4. Decision:
     SI proba >= 0.60 ET mc < $12,000:
         -> ACHETER (confiance suffisante, prix early)
     SINON:
         -> SKIP

[RECOMMANDATIONS POUR LE TRADING]
  > Seuil de confiance recommande: 60-65%
  > Prix d'entree max: $12,000 MC
  > Temps de decision: 7 secondes apres creation
  > Stop Loss: -30% du prix d'entree
  > Take Profit: Migration (69K MC)

[PROCHAINES ETAPES]
  1. Mettre a jour live_trading_bot.py pour utiliser model_7s.pkl
  2. Ajuster le seuil de confiance selon tes resultats
  3. Tester en mode simulation avant le live
''')
print('='*80)

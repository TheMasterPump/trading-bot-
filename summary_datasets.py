import pandas as pd

print('='*80)
print('RESUME DES DATASETS CREES POUR ENTRAINEMENT IA')
print('='*80)

# Dataset @ 10s
print('\n[DATASET 1: PREDICTION ULTRA-EARLY @ 10 SECONDES]')
print('-'*80)
df_10s = pd.read_csv('dataset_10s_prediction.csv')
print(f'Fichier: dataset_10s_prediction.csv')
print(f'Total: {len(df_10s)} tokens')
print(f'  - Runners (label=1): {df_10s["migrated"].sum()} tokens')
print(f'  - Flops (label=0):   {len(df_10s) - df_10s["migrated"].sum()} tokens')
print(f'  - Features: {len(df_10s.columns)} colonnes')
print(f'\nFeatures disponibles @ 10s:')
print(f'  - txn, traders, buy_ratio, mc, velocity, whale_count')

# Statistiques cles RUNNERS vs FLOPS @ 10s
runners_10s = df_10s[df_10s['migrated']==1]
flops_10s = df_10s[df_10s['migrated']==0]

print(f'\nComparaison RUNNERS vs FLOPS @ 10s:')
print(f'  Transactions (mediane):')
print(f'    - Runners: {runners_10s["txn"].median():.0f} txn')
print(f'    - Flops:   {flops_10s["txn"].median():.0f} txn')
print(f'    - Ratio:   {runners_10s["txn"].median() / flops_10s["txn"].median():.1f}x')

print(f'  Traders (mediane):')
print(f'    - Runners: {runners_10s["traders"].median():.0f} traders')
print(f'    - Flops:   {flops_10s["traders"].median():.0f} traders')
print(f'    - Ratio:   {runners_10s["traders"].median() / flops_10s["traders"].median():.1f}x')

print(f'  Buy Ratio (mediane):')
print(f'    - Runners: {runners_10s["buy_ratio"].median()*100:.1f}%')
print(f'    - Flops:   {flops_10s["buy_ratio"].median()*100:.1f}%')

print(f'  Market Cap (mediane):')
print(f'    - Runners: ${runners_10s["mc"].median():,.0f}')
print(f'    - Flops:   ${flops_10s["mc"].median():,.0f}')
print(f'    - Ratio:   {runners_10s["mc"].median() / flops_10s["mc"].median():.1f}x')

# Dataset @ 30s
print('\n' + '='*80)
print('[DATASET 2: PREDICTION EARLY @ 30 SECONDES]')
print('-'*80)
df_30s = pd.read_csv('dataset_30s_prediction.csv')
print(f'Fichier: dataset_30s_prediction.csv')
print(f'Total: {len(df_30s)} tokens')
print(f'  - Runners (label=1): {df_30s["migrated"].sum()} tokens')
print(f'  - Flops (label=0):   {len(df_30s) - df_30s["migrated"].sum()} tokens')
print(f'  - Features: {len(df_30s.columns)} colonnes')
print(f'\nFeatures disponibles @ 30s:')
print(f'  - Snapshots: 10s, 15s, 20s, 30s (tous les metriques)')
print(f'  - Features derivees: croissance MC, txn, traders')
print(f'  - Tendance: mc_trend_up_count')

# Statistiques cles RUNNERS vs FLOPS @ 30s
runners_30s = df_30s[df_30s['migrated']==1]
flops_30s = df_30s[df_30s['migrated']==0]

print(f'\nComparaison RUNNERS vs FLOPS @ 30s:')
print(f'  Transactions @ 30s (mediane):')
print(f'    - Runners: {runners_30s["30s_txn"].median():.0f} txn')
print(f'    - Flops:   {flops_30s["30s_txn"].median():.0f} txn')
print(f'    - Ratio:   {runners_30s["30s_txn"].median() / flops_30s["30s_txn"].median():.1f}x')

print(f'  Traders @ 30s (mediane):')
print(f'    - Runners: {runners_30s["30s_traders"].median():.0f} traders')
print(f'    - Flops:   {flops_30s["30s_traders"].median():.0f} traders')
print(f'    - Ratio:   {runners_30s["30s_traders"].median() / flops_30s["30s_traders"].median():.1f}x')

print(f'  Croissance MC 10s->30s (mediane):')
print(f'    - Runners: +{runners_30s["mc_growth_10s_30s"].median()*100:.1f}%')
print(f'    - Flops:   +{flops_30s["mc_growth_10s_30s"].median()*100:.1f}%')

print(f'  Tendance MC (mediane):')
print(f'    - Runners: {runners_30s["mc_trend_up_count"].median():.1f}/3 hausse')
print(f'    - Flops:   {flops_30s["mc_trend_up_count"].median():.1f}/3 hausse')

print('\n' + '='*80)
print('RECOMMANDATIONS POUR ENTRAINEMENT IA')
print('='*80)
print(f'''
1. DATASET @ 10s (ULTRA-EARLY)
   - Utilise pour: Prediction IMMEDIATE (entrer des 11-12 secondes)
   - Avantage: Meilleur prix d'entree
   - Inconvenient: Peu de donnees, predictions moins precises
   - Desequilibre: {len(flops_10s)}/{len(runners_10s)} = {len(flops_10s)/len(runners_10s):.0f}:1
   - Solution: Utiliser SMOTE ou class_weight='balanced'

2. DATASET @ 30s (EARLY)
   - Utilise pour: Prediction avec CONFIRMATION (entrer vers 30-35 secondes)
   - Avantage: Plus de donnees = predictions plus fiables
   - Inconvenient: Prix d'entree plus eleve
   - Desequilibre: {len(flops_30s)}/{len(runners_30s)} = {len(flops_30s)/len(runners_30s):.0f}:1
   - Solution: Utiliser SMOTE ou class_weight='balanced'

3. STRATEGIE RECOMMANDEE
   - Entrainer 2 modeles:
     * Modele A @ 10s: Pour detection rapide (sensibilite elevee)
     * Modele B @ 30s: Pour confirmation (precision elevee)

   - Pipeline de decision:
     1. @ 10s: Modele A dit "potentiel runner" → SURVEILLER
     2. @ 30s: Modele B confirme → ENTRER
     3. Si Modele A+B confirment tous les deux → FORTE CONFIANCE

4. BALANCE PRECISION vs RAPIDITE
   - Si tu veux entrer TOT (10-15s): Utilise dataset @ 10s
   - Si tu veux etre SUR (30s+): Utilise dataset @ 30s
   - Si tu veux BEST OF BOTH: Combine les deux modeles!

FICHIERS PRETS POUR L'IA:
- dataset_10s_prediction.csv ({len(df_10s)} tokens, 7 features)
- dataset_30s_prediction.csv ({len(df_30s)} tokens, 26 features)
''')

print('='*80)

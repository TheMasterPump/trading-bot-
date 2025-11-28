"""
Analyser les MIGRATIONS dans le dataset d'entraînement
"""
import pandas as pd
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Charger le dataset 15s (utilisé pour l'entraînement)
try:
    df = pd.read_csv('dataset_15s_prediction_COMBINED.csv')
    print(f'Dataset chargé: {len(df)} lignes')
except:
    try:
        df = pd.read_csv('dataset_15s_prediction.csv')
        print(f'Dataset chargé: {len(df)} lignes')
    except:
        print('Erreur: Impossible de charger le dataset')
        exit(1)

print('='*80)
print('ANALYSE DES MIGRATIONS DANS LE DATASET D\'ENTRAÎNEMENT')
print('='*80)

# Afficher les colonnes
print(f'\nColonnes disponibles:')
print(df.columns.tolist())

# Chercher la colonne migration/label
if 'migrated' in df.columns:
    migrations = df[df['migrated'] == 1]
    print(f'\n🚀 MIGRATIONS TROUVÉES: {len(migrations)} / {len(df)} ({len(migrations)/len(df)*100:.1f}%)')
elif 'label' in df.columns:
    migrations = df[df['label'] == 1]
    print(f'\n🚀 MIGRATIONS (label=1): {len(migrations)} / {len(df)} ({len(migrations)/len(df)*100:.1f}%)')
else:
    print('\n⚠️ Pas de colonne migration trouvée. Colonnes:')
    print(df.columns.tolist())
    
    # Chercher manuellement
    if '15s_mc' in df.columns:
        # Considérer migration si MC >= 60K
        migrations = df[df['15s_mc'] >= 60000]
        print(f'\n🚀 MIGRATIONS (MC >= 60K): {len(migrations)} / {len(df)}')
    else:
        print('Impossible de détecter les migrations')
        exit(1)

if len(migrations) == 0:
    print('❌ Aucune migration trouvée!')
    exit(0)

# Stats des migrations
print(f'\n{'='*80}')
print('STATS DES MIGRATIONS')
print('='*80)

# Colonnes d'intérêt
cols_to_analyze = ['10s_txn', '10s_traders', '10s_buy_ratio', '10s_mc', '10s_whale_count',
                   '15s_txn', '15s_traders', '15s_buy_ratio', '15s_mc', '15s_whale_count']

stats = {}
for col in cols_to_analyze:
    if col in migrations.columns:
        stats[col] = {
            'mean': migrations[col].mean(),
            'min': migrations[col].min(),
            'max': migrations[col].max(),
            'median': migrations[col].median()
        }

# Afficher @ 10s (équivalent à 8s)
print(f'\n📊 @ 10s (équivalent 8s):')
if '10s_txn' in stats:
    print(f'   TXN: {stats["10s_txn"]["mean"]:.0f} (range {stats["10s_txn"]["min"]:.0f}-{stats["10s_txn"]["max"]:.0f})')
if '10s_traders' in stats:
    print(f'   Traders: {stats["10s_traders"]["mean"]:.0f} (range {stats["10s_traders"]["min"]:.0f}-{stats["10s_traders"]["max"]:.0f})')
if '10s_buy_ratio' in stats:
    print(f'   Buy ratio: {stats["10s_buy_ratio"]["mean"]*100:.0f}% (range {stats["10s_buy_ratio"]["min"]*100:.0f}%-{stats["10s_buy_ratio"]["max"]*100:.0f}%)')
if '10s_mc' in stats:
    print(f'   MC: ${stats["10s_mc"]["mean"]:,.0f} (range ${stats["10s_mc"]["min"]:,.0f}-${stats["10s_mc"]["max"]:,.0f})')
if '10s_whale_count' in stats:
    print(f'   Whales: {stats["10s_whale_count"]["mean"]:.2f} (range {stats["10s_whale_count"]["min"]:.0f}-{stats["10s_whale_count"]["max"]:.0f})')

# Afficher @ 15s
print(f'\n📊 @ 15s:')
if '15s_txn' in stats:
    print(f'   TXN: {stats["15s_txn"]["mean"]:.0f} (range {stats["15s_txn"]["min"]:.0f}-{stats["15s_txn"]["max"]:.0f})')
if '15s_traders' in stats:
    print(f'   Traders: {stats["15s_traders"]["mean"]:.0f} (range {stats["15s_traders"]["min"]:.0f}-{stats["15s_traders"]["max"]:.0f})')
if '15s_buy_ratio' in stats:
    print(f'   Buy ratio: {stats["15s_buy_ratio"]["mean"]*100:.0f}% (range {stats["15s_buy_ratio"]["min"]*100:.0f}%-{stats["15s_buy_ratio"]["max"]*100:.0f}%)')
if '15s_mc' in stats:
    print(f'   MC: ${stats["15s_mc"]["mean"]:,.0f} (range ${stats["15s_mc"]["min"]:,.0f}-${stats["15s_mc"]["max"]:,.0f})')
if '15s_whale_count' in stats:
    print(f'   Whales: {stats["15s_whale_count"]["mean"]:.2f} (range {stats["15s_whale_count"]["min"]:.0f}-{stats["15s_whale_count"]["max"]:.0f})')

# Distribution des baleines
if '10s_whale_count' in migrations.columns:
    print(f'\n🐋 DISTRIBUTION BALEINES @ 10s:')
    whale_dist = migrations['10s_whale_count'].value_counts().sort_index()
    for whales, count in whale_dist.items():
        pct = count / len(migrations) * 100
        print(f'   {int(whales)} baleines: {count} ({pct:.1f}%)')

print(f'\n{'='*80}')

import pandas as pd
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

df = pd.read_csv('dataset_15s_prediction_COMBINED.csv')
migrations = df[df['migrated'] == 1]

print('='*80)
print(f'DISTRIBUTION BALEINES - {len(migrations)} MIGRATIONS')
print('='*80)

if 'whale_count' in migrations.columns:
    whale_dist = migrations['whale_count'].value_counts().sort_index()
    
    print(f'\n🐋 BALEINES:')
    print(f'   Moyenne: {migrations["whale_count"].mean():.2f}')
    print(f'   Range: {migrations["whale_count"].min():.0f}-{migrations["whale_count"].max():.0f}')
    
    print(f'\n📊 DISTRIBUTION:')
    for whales, count in whale_dist.items():
        pct = count / len(migrations) * 100
        print(f'   {int(whales)} baleines: {count:3d} ({pct:5.1f}%)')
    
    # Catégories
    whale_0 = len(migrations[migrations['whale_count'] == 0])
    whale_1 = len(migrations[migrations['whale_count'] == 1])
    whale_2plus = len(migrations[migrations['whale_count'] >= 2])
    
    print(f'\n🎯 RÉSUMÉ:')
    print(f'   0 baleines: {whale_0}/{len(migrations)} ({whale_0/len(migrations)*100:.1f}%)')
    print(f'   1 baleine:  {whale_1}/{len(migrations)} ({whale_1/len(migrations)*100:.1f}%)')
    print(f'   2+ baleines: {whale_2plus}/{len(migrations)} ({whale_2plus/len(migrations)*100:.1f}%)')

print(f'\n{'='*80}')

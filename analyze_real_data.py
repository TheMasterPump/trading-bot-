"""
Analyse les VRAIES données du bot dans le bon dossier
"""
import json

# Charger les VRAIES données
real_file = r'C:\Users\user\Desktop\prediction AI\trading_history.json'

with open(real_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data.get('trades', [])

print('='*80)
print('ANALYSE DES VRAIES DONNEES - 296 TRADES')
print('='*80)

print(f'\nTotal trades: {len(trades)}')

wins = [t for t in trades if t.get('is_win', False)]
losses = [t for t in trades if not t.get('is_win', False)]

print(f'Wins: {len(wins)} ({len(wins)/len(trades)*100:.1f}%)')
print(f'Losses: {len(losses)} ({len(losses)/len(trades)*100:.1f}%)')

# MIGRATIONS
migrations = [t for t in trades if t.get('exit_mc', 0) >= 69000]
near_migrations = [t for t in trades if 50000 <= t.get('exit_mc', 0) < 69000]
reached_2x = [t for t in trades if
              (t.get('profit_ratio', 0) >= 2.0) or
              ('2x' in t.get('exit_reason', ''))]

print(f'\n{"="*80}')
print('MIGRATIONS')
print('='*80)
print(f'\nTokens qui ont MIGRE (>= 69K): {len(migrations)} ({len(migrations)/len(trades)*100:.1f}%)')
print(f'Tokens PROCHES (50-69K): {len(near_migrations)} ({len(near_migrations)/len(trades)*100:.1f}%)')
print(f'Tokens qui ont atteint 2x: {len(reached_2x)} ({len(reached_2x)/len(trades)*100:.1f}%)')

if migrations:
    print(f'\n{"="*80}')
    print('DETAILS DES MIGRATIONS')
    print('='*80)
    for t in sorted(migrations, key=lambda x: x.get('exit_mc', 0), reverse=True)[:10]:
        print(f"\n{t['symbol']}")
        print(f"  Entry MC: ${t['entry_mc']:,.0f}")
        print(f"  Exit MC: ${t['exit_mc']:,.0f}")
        print(f"  Profit: {t.get('profit_percent', 0):+.1f}%")
        print(f"  Exit reason: {t.get('exit_reason', 'N/A')}")
        print(f"  Win: {'YES' if t.get('is_win') else 'NO'}")

# Parmi les WINS, combien ont migré ?
if wins:
    wins_migrated = [t for t in wins if t.get('exit_mc', 0) >= 69000]
    print(f'\n{"="*80}')
    print('WINS QUI ONT MIGRE')
    print('='*80)
    print(f'\nSur {len(wins)} winners:')
    print(f'  - Ont migré (>=69K): {len(wins_migrated)} ({len(wins_migrated)/len(wins)*100:.1f}%)')
    print(f'  - N\'ont PAS migré: {len(wins)-len(wins_migrated)} ({(len(wins)-len(wins_migrated))/len(wins)*100:.1f}%)')

    if wins_migrated:
        print(f'\nWINS avec MIGRATION:')
        for t in wins_migrated:
            print(f"  - {t['symbol']}: ${t['entry_mc']:,.0f} -> ${t['exit_mc']:,.0f} ({t.get('profit_percent', 0):+.1f}%)")

# Distribution MC sortie
print(f'\n{"="*80}')
print('DISTRIBUTION MC DE SORTIE')
print('='*80)

ranges = [
    (0, 5000, '< 5K'),
    (5000, 10000, '5-10K'),
    (10000, 20000, '10-20K'),
    (20000, 30000, '20-30K'),
    (30000, 50000, '30-50K'),
    (50000, 69000, '50-69K'),
    (69000, 100000, '69-100K (MIGRE)'),
    (100000, 1000000, '>100K (MIGRE++)'),
]

print(f'\n{"MC Range":<20} {"Count":<10} {"Percent":<10}')
print('-'*40)

for min_mc, max_mc, label in ranges:
    count = len([t for t in trades if min_mc <= t.get('exit_mc', 0) < max_mc])
    pct = count / len(trades) * 100 if trades else 0
    print(f'{label:<20} {count:<10} {pct:<9.1f}%')

# MC max
if trades:
    max_exit_mc = max(t.get('exit_mc', 0) for t in trades)
    max_token = [t for t in trades if t.get('exit_mc', 0) == max_exit_mc][0]
    print(f'\nMC maximum atteint: ${max_exit_mc:,.0f}')
    print(f'Token: {max_token.get("symbol", "Unknown")}')

print('\n' + '='*80)
print('CONCLUSION')
print('='*80)

migration_rate = len(migrations) / len(trades) * 100 if trades else 0
print(f'\nTaux de migration: {migration_rate:.1f}%')

if wins:
    win_migration_rate = len(wins_migrated) / len(wins) * 100 if wins else 0
    print(f'Taux de migration parmi les WINS: {win_migration_rate:.1f}%')

    if win_migration_rate < 25:
        print('\n[!] Moins de 25% des winners migrent')
        print('    -> La strategie "garder 40% pour migration" n\'est peut-etre pas optimale')
        print('    -> Recommandation: Vendre 80-100% a 2-3x au lieu d\'attendre 69K')
    else:
        print('\n[OK] Plus de 25% des winners migrent')
        print('    -> La strategie "garder 40% pour migration" a du sens')

print('\n' + '='*80)

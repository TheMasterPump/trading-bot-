"""
Vérifier TOUTES les migrations possibles
"""
import json
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data['trades']

print('='*80)
print('RECHERCHE DE TOUTES LES MIGRATIONS')
print('='*80)

# Chercher différents critères
exit_53k = [t for t in trades if t.get('exit_mc', 0) >= 53000]
profit_2x = [t for t in trades if t.get('profit_ratio', 0) >= 2.0]
exit_reason_migration = [t for t in trades if 'MIGRATION' in str(t.get('exit_reason', '')).upper()]
profit_150plus = [t for t in trades if t.get('profit_percent', 0) >= 150]

print(f'\n📊 CRITÈRES:')
print(f'   Exit MC >= $53,000: {len(exit_53k)} trades')
print(f'   Profit ratio >= 2.0x: {len(profit_2x)} trades')
print(f'   Exit reason MIGRATION: {len(exit_reason_migration)} trades')
print(f'   Profit >= 150%: {len(profit_150plus)} trades')

# Combiner tous
all_potential = set()
for t in exit_53k + profit_2x + exit_reason_migration + profit_150plus:
    all_potential.add(t['symbol'])

print(f'\n🚀 TOTAL MIGRATIONS POTENTIELLES: {len(all_potential)} tokens uniques')

# Afficher tous
print(f'\n{'='*80}')
print('LISTE COMPLÈTE')
print('='*80)

combined = exit_53k + profit_2x + exit_reason_migration + profit_150plus
seen = set()
count = 0

for t in sorted(combined, key=lambda x: x.get('profit_percent', 0), reverse=True):
    if t['symbol'] in seen:
        continue
    seen.add(t['symbol'])
    count += 1
    
    print(f'\n{count}. {t.get("symbol")}: +{t.get("profit_percent", 0):.1f}%')
    print(f'   Entry MC: ${t.get("entry_mc", 0):,.0f}')
    print(f'   Exit MC: ${t.get("exit_mc", 0):,.0f}')
    print(f'   Profit ratio: {t.get("profit_ratio", 0):.2f}x')
    print(f'   Exit reason: {t.get("exit_reason", "N/A")}')

print(f'\n{'='*80}')
print(f'TOTAL: {count} migrations/gros winners')
print('='*80)

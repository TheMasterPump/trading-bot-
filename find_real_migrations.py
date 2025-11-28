"""
Trouver TOUTES les vraies migrations (pas juste MC >= 53K)
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
print('RECHERCHE DE TOUTES LES VRAIES MIGRATIONS')
print('='*80)

# Chercher tous les indices de migration
migrations = []

for t in trades:
    exit_reason = str(t.get('exit_reason', '')).upper()
    entry_reason = str(t.get('entry_reason', t.get('reason', ''))).upper()
    profit = t.get('profit_percent', 0)
    exit_mc = t.get('exit_mc', 0)
    
    # Migration indicators
    is_migration = False
    
    # 1. Exit reason contient MIGRATION
    if 'MIGRATION' in exit_reason:
        is_migration = True
    
    # 2. Exit reason = TAKE PROFIT FINAL
    if 'TAKE PROFIT FINAL' in exit_reason:
        is_migration = True
    
    # 3. Exit MC très élevé (30K+, 40K+, 50K+, etc.)
    if exit_mc >= 30000 and profit > 100:
        is_migration = True
    
    # 4. Profit ratio >= 3x
    if t.get('profit_ratio', 0) >= 3.0:
        is_migration = True
    
    if is_migration:
        migrations.append(t)

# Enlever duplicates
seen = {}
for m in migrations:
    key = m['symbol']
    if key not in seen or m.get('profit_percent', 0) > seen[key].get('profit_percent', 0):
        seen[key] = m

migrations = list(seen.values())

print(f'\n🚀 MIGRATIONS TROUVÉES: {len(migrations)} trades')

# Afficher toutes
print(f'\n{'='*80}')
print('LISTE COMPLÈTE DES MIGRATIONS')
print('='*80)

for i, m in enumerate(sorted(migrations, key=lambda x: x.get('profit_percent', 0), reverse=True), 1):
    print(f'\n{i}. {m.get("symbol")}: +{m.get("profit_percent", 0):.1f}%')
    print(f'   Entry MC: ${m.get("entry_mc", 0):,.0f}')
    print(f'   Exit MC: ${m.get("exit_mc", 0):,.0f}')
    print(f'   Profit ratio: {m.get("profit_ratio", 0):.2f}x')
    print(f'   Exit reason: {m.get("exit_reason", "N/A")}')
    
    # Features
    f = m.get('features', {})
    if f:
        print(f'   Buy ratio: {f.get("buy_ratio", 0)*100:.0f}%, TXN: {f.get("txn", 0)}, Traders: {f.get("traders", 0)}, Whales: {f.get("whale_count", 0)}')

print(f'\n{'='*80}')

# Stats
if migrations:
    mcs = [m.get('entry_mc', 0) for m in migrations]
    buy_ratios = [m.get('features', {}).get('buy_ratio', 0) for m in migrations if m.get('features', {}).get('buy_ratio', 0) > 0]
    txns = [m.get('features', {}).get('txn', 0) for m in migrations if m.get('features', {}).get('txn', 0) > 0]
    traders = [m.get('features', {}).get('traders', 0) for m in migrations if m.get('features', {}).get('traders', 0) > 0]
    whales = [m.get('features', {}).get('whale_count', 0) for m in migrations]
    
    print('STATS GLOBALES')
    print('='*80)
    print(f'\nMC entrée: ${sum(mcs)/len(mcs):,.0f} (range ${min(mcs):,.0f}-${max(mcs):,.0f})')
    if buy_ratios:
        print(f'Buy ratio: {sum(buy_ratios)/len(buy_ratios)*100:.0f}% (range {min(buy_ratios)*100:.0f}%-{max(buy_ratios)*100:.0f}%)')
    if txns:
        print(f'TXN: {sum(txns)/len(txns):.0f} (range {min(txns)}-{max(txns)})')
    if traders:
        print(f'Traders: {sum(traders)/len(traders):.0f} (range {min(traders)}-{max(traders)})')
    print(f'Whales: {sum(whales)/len(whales):.2f} (range {min(whales)}-{max(whales)})')

print(f'\n{'='*80}')

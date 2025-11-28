"""
Chercher TOUS les tokens qui ont atteint 60K, 70K, 80K+ MC
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
print('RECHERCHE TOKENS PAR EXIT MC ÉLEVÉ')
print('='*80)

# Différents seuils
above_60k = [t for t in trades if t.get('exit_mc', 0) >= 60000]
above_70k = [t for t in trades if t.get('exit_mc', 0) >= 70000]
above_80k = [t for t in trades if t.get('exit_mc', 0) >= 80000]
above_50k = [t for t in trades if t.get('exit_mc', 0) >= 50000]

print(f'\n📊 PAR SEUIL:')
print(f'   Exit MC >= $50,000: {len(above_50k)} trades')
print(f'   Exit MC >= $60,000: {len(above_60k)} trades')
print(f'   Exit MC >= $70,000: {len(above_70k)} trades')
print(f'   Exit MC >= $80,000: {len(above_80k)} trades')

# Trouver le max exit_mc
all_exit_mcs = [t.get('exit_mc', 0) for t in trades]
max_exit = max(all_exit_mcs) if all_exit_mcs else 0

print(f'\n📈 MAX EXIT MC DANS L\'HISTORIQUE: ${max_exit:,.0f}')

# Afficher TOP 20 par exit_mc
print(f'\n{'='*80}')
print('TOP 20 PAR EXIT MC')
print('='*80)

top_20 = sorted(trades, key=lambda x: x.get('exit_mc', 0), reverse=True)[:20]

for i, t in enumerate(top_20, 1):
    f = t.get('features', {})
    
    print(f'\n{i}. {t.get("symbol")}: Exit MC ${t.get("exit_mc", 0):,.0f}')
    print(f'   Entry MC: ${t.get("entry_mc", 0):,.0f} → Profit: +{t.get("profit_percent", 0):.1f}%')
    print(f'   Exit: {t.get("exit_reason", "N/A")}')
    if f:
        print(f'   Features: Buy {f.get("buy_ratio", 0)*100:.0f}%, {f.get("txn", 0)}txn, {f.get("traders", 0)}traders, {f.get("whale_count", 0)}whales')

# Stats des migrations 60K+
if above_60k:
    print(f'\n{'='*80}')
    print(f'STATS DES {len(above_60k)} MIGRATIONS >= 60K')
    print('='*80)
    
    mcs = [m.get('entry_mc', 0) for m in above_60k]
    buy_ratios = [m.get('features', {}).get('buy_ratio', 0) for m in above_60k if m.get('features', {}).get('buy_ratio', 0) > 0]
    txns = [m.get('features', {}).get('txn', 0) for m in above_60k if m.get('features', {}).get('txn', 0) > 0]
    traders = [m.get('features', {}).get('traders', 0) for m in above_60k if m.get('features', {}).get('traders', 0) > 0]
    whales = [m.get('features', {}).get('whale_count', 0) for m in above_60k]
    
    print(f'\nMC entrée: ${sum(mcs)/len(mcs):,.0f} (range ${min(mcs):,.0f}-${max(mcs):,.0f})')
    if buy_ratios:
        print(f'Buy ratio: {sum(buy_ratios)/len(buy_ratios)*100:.0f}% (range {min(buy_ratios)*100:.0f}%-{max(buy_ratios)*100:.0f}%)')
    if txns:
        print(f'TXN: {sum(txns)/len(txns):.0f} (range {min(txns)}-{max(txns)})')
    if traders:
        print(f'Traders: {sum(traders)/len(traders):.0f} (range {min(traders)}-{max(traders)})')
    print(f'Whales: {sum(whales)/len(whales):.2f} (range {min(whales)}-{max(whales)})')

print(f'\n{'='*80}')

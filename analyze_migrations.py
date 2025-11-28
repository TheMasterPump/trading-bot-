"""
Analyse des VRAIES MIGRATIONS (exit_mc >= 53K)
Avec stats @ 8s et @ 15s
"""
import json
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Charger l'historique
with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data['trades']

print('='*80)
print('ANALYSE DES VRAIES MIGRATIONS (MC >= $53,000)')
print('='*80)

# Filtrer seulement les migrations
migrations = [t for t in trades if t.get('exit_mc', 0) >= 53000]

print(f'\n🚀 MIGRATIONS TROUVÉES: {len(migrations)} trades')

if len(migrations) == 0:
    print('\n❌ AUCUNE MIGRATION TROUVÉE!')
    print('\nRecherche des tokens qui sont allés le plus haut...')
    
    # Prendre les top 10 exit_mc
    top_exits = sorted(trades, key=lambda x: x.get('exit_mc', 0), reverse=True)[:10]
    
    print(f'\n📊 TOP 10 EXIT MC:')
    for i, t in enumerate(top_exits, 1):
        print(f'{i}. {t.get("symbol")}: Exit MC ${t.get("exit_mc", 0):,.0f}, Profit {t.get("profit_percent", 0):.1f}%')
    
    exit(0)

print(f'\n{'='*80}')
print(f'CARACTÉRISTIQUES DES {len(migrations)} MIGRATIONS')
print('='*80)

# MC entrée
mc_entries = [t.get('entry_mc', 0) for t in migrations]
avg_mc_entry = sum(mc_entries) / len(mc_entries)

print(f'\n📍 MC ENTRÉE: ${avg_mc_entry:,.0f} en moyenne')

# Stats au moment de l'achat (entry_features)
print(f'\n{'='*80}')
print('STATS AU MOMENT DE L\'ACHAT (ENTRY)')
print('='*80)

# Buy ratio
buy_ratios = [t.get('features', {}).get('buy_ratio', 0) for t in migrations if t.get('features', {}).get('buy_ratio', 0) > 0]
if buy_ratios:
    avg_buy = sum(buy_ratios) / len(buy_ratios)
    min_buy = min(buy_ratios)
    max_buy = max(buy_ratios)
    print(f'\n📈 BUY RATIO:')
    print(f'   Moyenne: {avg_buy*100:.1f}%')
    print(f'   Min: {min_buy*100:.0f}%')
    print(f'   Max: {max_buy*100:.0f}%')
    
    above_75 = len([b for b in buy_ratios if b >= 0.75])
    above_80 = len([b for b in buy_ratios if b >= 0.80])
    print(f'   >= 75%: {above_75}/{len(buy_ratios)} ({above_75/len(buy_ratios)*100:.0f}%)')
    print(f'   >= 80%: {above_80}/{len(buy_ratios)} ({above_80/len(buy_ratios)*100:.0f}%)')

# Txn
txns = [t.get('features', {}).get('txn', 0) for t in migrations if t.get('features', {}).get('txn', 0) > 0]
if txns:
    avg_txn = sum(txns) / len(txns)
    min_txn = min(txns)
    max_txn = max(txns)
    print(f'\n💱 TRANSACTIONS:')
    print(f'   Moyenne: {avg_txn:.0f}')
    print(f'   Min: {min_txn}')
    print(f'   Max: {max_txn}')

# Traders
traders_list = [t.get('features', {}).get('traders', 0) for t in migrations if t.get('features', {}).get('traders', 0) > 0]
if traders_list:
    avg_traders = sum(traders_list) / len(traders_list)
    min_traders = min(traders_list)
    max_traders = max(traders_list)
    print(f'\n👥 TRADERS:')
    print(f'   Moyenne: {avg_traders:.0f}')
    print(f'   Min: {min_traders}')
    print(f'   Max: {max_traders}')

# Baleines
whales = [t.get('features', {}).get('whale_count', 0) for t in migrations]
avg_whales = sum(whales) / len(whales)

print(f'\n🐋 BALEINES:')
print(f'   Moyenne: {avg_whales:.2f}')

whale_0 = len([w for w in whales if w == 0])
whale_1 = len([w for w in whales if w == 1])
whale_2 = len([w for w in whales if w == 2])
whale_3plus = len([w for w in whales if w >= 3])

print(f'   0 baleines: {whale_0} ({whale_0/len(whales)*100:.0f}%)')
print(f'   1 baleine: {whale_1} ({whale_1/len(whales)*100:.0f}%)')
print(f'   2 baleines: {whale_2} ({whale_2/len(whales)*100:.0f}%)')
print(f'   3+ baleines: {whale_3plus} ({whale_3plus/len(whales)*100:.0f}%)')

# Temps d'achat (8s ou 15s)
entry_times = [t.get('entry_time', 'Unknown') for t in migrations]
at_8s = len([e for e in entry_times if '8s' in str(e)])
at_15s = len([e for e in entry_times if '15s' in str(e)])

print(f'\n⏱️ TIMING D\'ACHAT:')
print(f'   @ 8s: {at_8s} ({at_8s/len(migrations)*100:.0f}%)')
print(f'   @ 15s: {at_15s} ({at_15s/len(migrations)*100:.0f}%)')

# Liste détaillée
print(f'\n{'='*80}')
print(f'LISTE DÉTAILLÉE DES {len(migrations)} MIGRATIONS')
print('='*80)

for i, t in enumerate(sorted(migrations, key=lambda x: x.get('profit_percent', 0), reverse=True), 1):
    f = t.get('features', {})
    
    print(f'\n{i}. {t.get("symbol")}: +{t.get("profit_percent", 0):.1f}%')
    print(f'   Entry MC: ${t.get("entry_mc", 0):,.0f}')
    print(f'   Exit MC: ${t.get("exit_mc", 0):,.0f}')
    print(f'   Timing: {t.get("entry_time", "?")}')
    print(f'   Buy ratio: {f.get("buy_ratio", 0)*100:.0f}%')
    print(f'   Txn: {f.get("txn", 0)}, Traders: {f.get("traders", 0)}')
    print(f'   Baleines: {f.get("whale_count", 0)}')
    print(f'   Raison: {t.get("entry_reason", t.get("reason", "N/A"))}')

# Profil type
print(f'\n{'='*80}')
print('🎯 PROFIL TYPE DE LA MIGRATION')
print('='*80)

print(f'\n✅ CARACTÉRISTIQUES IDÉALES:')
print(f'   MC entrée: ${avg_mc_entry:,.0f}')
if buy_ratios:
    print(f'   Buy ratio: {avg_buy*100:.0f}%+')
if txns:
    print(f'   Transactions: {avg_txn:.0f}')
if traders_list:
    print(f'   Traders: {avg_traders:.0f}')
print(f'   Baleines: {avg_whales:.1f}')
print(f'   Timing: {at_8s}x @ 8s, {at_15s}x @ 15s')

if whale_0 > len(whales) * 0.5:
    print(f'\n   ⚠️ {whale_0/len(whales)*100:.0f}% des migrations avaient 0 baleines!')

print(f'\n{'='*80}')

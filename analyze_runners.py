"""
Analyse des RUNNERS (tokens qui ont migré ou fait 2x+)
Pour identifier leurs caractéristiques communes
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
print('ANALYSE DES RUNNERS (MIGRATIONS & BIG WINNERS)')
print('='*80)

# Définir ce qu'est un "runner"
runners = []
big_winners = []
small_winners = []

for t in trades:
    if not t.get('is_win', False):
        continue

    exit_mc = t.get('exit_mc', 0)
    profit_ratio = t.get('profit_ratio', 0)
    profit_percent = t.get('profit_percent', 0)

    # Migration ou 2x
    if exit_mc >= 53000 or profit_ratio >= 2.0:
        runners.append(t)
    elif profit_percent >= 100:
        big_winners.append(t)
    else:
        small_winners.append(t)

print(f'\n📊 CLASSIFICATION:')
print(f'   🚀 RUNNERS (migrations/2x+): {len(runners)} trades')
print(f'   💰 BIG WINNERS (100%+): {len(big_winners)} trades')
print(f'   ✅ SMALL WINNERS (< 100%): {len(small_winners)} trades')

if len(runners) == 0:
    print('\n⚠️ AUCUN RUNNER - Analyse BIG WINNERS...')
    runners = big_winners

if len(runners) == 0:
    print('\n❌ AUCUN BIG WINNER')
    exit(0)

print(f'\n{'='*80}')
print(f'CARACTÉRISTIQUES DES {len(runners)} RUNNERS')
print('='*80)

# MC
mc_entries = [t.get('entry_mc', 0) for t in runners]
avg_mc = sum(mc_entries) / len(mc_entries)

print(f'\n📍 MC ENTRÉE: ${avg_mc:,.0f} en moyenne')

# Buy ratio
buy_ratios = [t.get('features', {}).get('buy_ratio', 0) for t in runners if t.get('features', {}).get('buy_ratio', 0) > 0]
if buy_ratios:
    avg_buy_ratio = sum(buy_ratios) / len(buy_ratios)
    print(f'📈 BUY RATIO: {avg_buy_ratio*100:.1f}% en moyenne')
    
    above_75 = len([br for br in buy_ratios if br >= 0.75])
    print(f'   {above_75}/{len(buy_ratios)} runners avaient >= 75% ({above_75/len(buy_ratios)*100:.0f}%)')

# Txn
txns = [t.get('features', {}).get('txn', 0) for t in runners if t.get('features', {}).get('txn', 0) > 0]
if txns:
    avg_txn = sum(txns) / len(txns)
    print(f'💱 TRANSACTIONS: {avg_txn:.0f} en moyenne')

# Traders
traders_list = [t.get('features', {}).get('traders', 0) for t in runners if t.get('features', {}).get('traders', 0) > 0]
if traders_list:
    avg_traders = sum(traders_list) / len(traders_list)
    print(f'👥 TRADERS: {avg_traders:.0f} en moyenne')

# Baleines
whales = [t.get('features', {}).get('whale_count', 0) for t in runners]
avg_whales = sum(whales) / len(whales)
print(f'🐋 BALEINES: {avg_whales:.2f} en moyenne')

whale_0 = len([w for w in whales if w == 0])
whale_1 = len([w for w in whales if w == 1])
whale_2plus = len([w for w in whales if w >= 2])

print(f'   0 baleines: {whale_0} ({whale_0/len(whales)*100:.0f}%)')
print(f'   1 baleine: {whale_1} ({whale_1/len(whales)*100:.0f}%)')
print(f'   2+ baleines: {whale_2plus} ({whale_2plus/len(whales)*100:.0f}%)')

# Liste
print(f'\n{'='*80}')
print(f'LISTE DES RUNNERS')
print('='*80)

for i, t in enumerate(sorted(runners, key=lambda x: x.get('profit_percent', 0), reverse=True)[:10], 1):
    f = t.get('features', {})
    print(f'\n{i}. {t.get("symbol")}: +{t.get("profit_percent", 0):.1f}%')
    print(f'   MC ${t.get("entry_mc", 0):,.0f}, Buy {f.get("buy_ratio", 0)*100:.0f}%, {f.get("txn", 0)}txn, {f.get("traders", 0)}traders, {f.get("whale_count", 0)} whales')

print(f'\n{'='*80}')

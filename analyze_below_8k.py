"""
Analyse détaillée des trades EN DESSOUS de 8K
Pour déterminer si 7.4K-8K est meilleur que < 7.4K
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
print('ANALYSE DETAILLEE DES TRADES < 8K MC')
print('='*80)

# Filtrer seulement les trades < 8K
trades_below_8k = [t for t in trades if t.get('entry_mc', 0) < 8000]

print(f'\nTotal trades < 8K: {len(trades_below_8k)} trades')

# Créer des tranches plus précises
ranges = {
    '< 5K': (0, 5000),
    '5K-6K': (5000, 6000),
    '6K-7K': (6000, 7000),
    '7K-7.4K': (7000, 7400),
    '7.4K-8K': (7400, 8000),
}

results = {}

for range_name, (min_mc, max_mc) in ranges.items():
    wins = []
    losses = []

    for t in trades_below_8k:
        entry_mc = t.get('entry_mc', 0)
        if min_mc <= entry_mc < max_mc:
            if t.get('is_win', False):
                wins.append(t)
            else:
                losses.append(t)

    total = len(wins) + len(losses)
    wr = (len(wins) / total * 100) if total > 0 else 0

    results[range_name] = {
        'wins': wins,
        'losses': losses,
        'total': total,
        'wr': wr
    }

# Afficher les résultats
print(f'\n{'='*80}')
print('WIN RATE PAR TRANCHE DE MC (< 8K)')
print('='*80)

for range_name in ['< 5K', '5K-6K', '6K-7K', '7K-7.4K', '7.4K-8K']:
    data = results[range_name]

    if data['total'] == 0:
        continue

    emoji = '✅' if data['wr'] >= 20 else '⚠️' if data['wr'] >= 15 else '❌'

    print(f'\n{emoji} {range_name:10}: {len(data["wins"])}W / {len(data["losses"])}L ({data["wr"]:.1f}% WR) - {data["total"]} trades')

    if len(data['wins']) > 0:
        avg_profit = sum(t.get('profit_percent', 0) for t in data['wins']) / len(data['wins'])
        print(f'   Winners: Profit moyen +{avg_profit:.1f}%')

        # Top 3 winners
        top_3 = sorted(data['wins'], key=lambda x: x.get('profit_percent', 0), reverse=True)[:3]
        for i, t in enumerate(top_3, 1):
            print(f'     {i}. {t.get("symbol")}: +{t.get("profit_percent", 0):.1f}% @ ${t.get("entry_mc", 0):,.0f}')

    if len(data['losses']) > 0:
        avg_loss = sum(t.get('profit_percent', 0) for t in data['losses']) / len(data['losses'])
        print(f'   Losers: Perte moyenne {avg_loss:.1f}%')

# Comparaison 7.4K-8K vs < 7.4K
print(f'\n{'='*80}')
print('COMPARAISON: 7.4K-8K vs < 7.4K')
print('='*80)

# Zone 7.4K-8K
zone_7400_8000 = results['7.4K-8K']
print(f'\n📊 ZONE 7.4K-8K:')
print(f'   Total: {zone_7400_8000["total"]} trades')
print(f'   Win Rate: {zone_7400_8000["wr"]:.1f}%')

# Zone < 7.4K (combiner toutes les tranches)
wins_below_7400 = []
losses_below_7400 = []
for range_name in ['< 5K', '5K-6K', '6K-7K', '7K-7.4K']:
    wins_below_7400.extend(results[range_name]['wins'])
    losses_below_7400.extend(results[range_name]['losses'])

total_below_7400 = len(wins_below_7400) + len(losses_below_7400)
wr_below_7400 = (len(wins_below_7400) / total_below_7400 * 100) if total_below_7400 > 0 else 0

print(f'\n📊 ZONE < 7.4K:')
print(f'   Total: {total_below_7400} trades')
print(f'   Win Rate: {wr_below_7400:.1f}%')

print(f'\n{'='*80}')
print('🎯 RECOMMANDATION')
print('='*80)

if zone_7400_8000['wr'] > wr_below_7400 + 5:
    print(f'\n✅ ZONE 7.4K-8K EST MEILLEURE!')
    print(f'   7.4K-8K: {zone_7400_8000["wr"]:.1f}% WR')
    print(f'   < 7.4K: {wr_below_7400:.1f}% WR')
    print(f'   Différence: +{zone_7400_8000["wr"] - wr_below_7400:.1f}%')
    print(f'\n→ RECOMMANDATION: Mettre le minimum à $7,400')
elif wr_below_7400 > zone_7400_8000['wr'] + 5:
    print(f'\n⚠️ ZONE < 7.4K EST MEILLEURE!')
    print(f'   < 7.4K: {wr_below_7400:.1f}% WR')
    print(f'   7.4K-8K: {zone_7400_8000["wr"]:.1f}% WR')
    print(f'\n→ RECOMMANDATION: Baisser le minimum en dessous de 7.4K')
else:
    print(f'\n🟡 PAS DE GRANDE DIFFÉRENCE')
    print(f'   7.4K-8K: {zone_7400_8000["wr"]:.1f}% WR')
    print(f'   < 7.4K: {wr_below_7400:.1f}% WR')
    print(f'\n→ RECOMMANDATION: Garder 8K minimum (zone optimale testée)')

print(f'\n{'='*80}')

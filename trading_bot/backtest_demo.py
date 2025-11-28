import json
import sys
sys.path.append('..')

# Charger les données historiques
with open('../bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

from config import ENTRY_FILTERS, TARGETS, SELL_PERCENTAGES

print('='*80)
print('DEMONSTRATION: DANS QUOI LE BOT AURAIT RENTRE')
print('='*80)
print(f'\nFiltres d\'entree utilises (a 15 secondes):')
print(f'  - Buy Ratio >= {ENTRY_FILTERS["buy_ratio_min"]}%')
print(f'  - Transactions >= {ENTRY_FILTERS["transactions_min"]}')
print(f'  - Traders >= {ENTRY_FILTERS["traders_min"]}')
print(f'  - Big Buys >= {ENTRY_FILTERS["big_buys_min"]}')
print(f'\nTargets de sortie:')
print(f'  - Target 1: ${TARGETS["target_1"]:,} (vendre {SELL_PERCENTAGES["target_1"]}%)')
print(f'  - Target 2: ${TARGETS["target_2"]:,} (vendre {SELL_PERCENTAGES["target_2"]}%)')
print(f'  - Target 3: ${TARGETS["target_3"]:,} (vendre {SELL_PERCENTAGES["target_3"]}%)')
print('\n' + '='*80)

# Analyser chaque token pour voir si le bot aurait rentré
entries = []

for token in data['completed']:
    snap_15s = token.get('15s')

    if not snap_15s or not isinstance(snap_15s, dict):
        continue

    # Vérifier les conditions d'entrée
    buy_ratio_pct = snap_15s.get('buy_ratio', 0) * 100
    txn = snap_15s.get('txn', 0)
    traders = snap_15s.get('traders', 0)
    big_buys = snap_15s.get('big_buys_100', 0)
    entry_mc = snap_15s.get('mc', 0)

    # Est-ce que le bot aurait rentré?
    would_enter = (
        buy_ratio_pct >= ENTRY_FILTERS['buy_ratio_min'] and
        txn >= ENTRY_FILTERS['transactions_min'] and
        traders >= ENTRY_FILTERS['traders_min'] and
        big_buys >= ENTRY_FILTERS['big_buys_min'] and
        entry_mc > 0
    )

    if would_enter:
        # Calculer le résultat
        final_mc = token.get('final_mc', entry_mc)
        is_runner = token.get('is_runner', False)
        is_migration = token.get('migration_detected', False)

        # Calculer les targets atteints
        targets_hit = []
        if final_mc >= TARGETS['target_1']:
            targets_hit.append('T1 ($25K)')
        if final_mc >= TARGETS['target_2']:
            targets_hit.append('T2 ($50K)')
        if final_mc >= TARGETS['target_3']:
            targets_hit.append('T3 ($69K)')

        gain_pct = ((final_mc - entry_mc) / entry_mc * 100) if entry_mc > 0 else 0

        entries.append({
            'symbol': token.get('symbol', '???'),
            'entry_mc': entry_mc,
            'final_mc': final_mc,
            'buy_ratio': buy_ratio_pct,
            'txn': txn,
            'traders': traders,
            'big_buys': big_buys,
            'gain_pct': gain_pct,
            'is_runner': is_runner,
            'is_migration': is_migration,
            'targets_hit': targets_hit
        })

# Trier par gain
entries.sort(key=lambda x: x['gain_pct'], reverse=True)

print(f'\n\nRESULTATS DU BACKTEST')
print('='*80)
print(f'\nTotal tokens analyses: {len(data["completed"])}')
print(f'Entrees qui auraient ete prises: {len(entries)}')

winners = [e for e in entries if e['gain_pct'] > 0]
losers = [e for e in entries if e['gain_pct'] <= 0]
runners_caught = [e for e in entries if e['is_runner']]
migrations_caught = [e for e in entries if e['is_migration']]

print(f'  - Gagnants: {len(winners)} ({len(winners)/len(entries)*100:.1f}%)')
print(f'  - Perdants: {len(losers)} ({len(losers)/len(entries)*100:.1f}%)')
print(f'  - Runners captes: {len(runners_caught)}')
print(f'  - Migrations captees: {len(migrations_caught)}')

if winners:
    avg_gain = sum(e['gain_pct'] for e in winners) / len(winners)
    print(f'\nGain moyen des gagnants: +{avg_gain:.1f}%')

if losers:
    avg_loss = sum(e['gain_pct'] for e in losers) / len(losers)
    print(f'Perte moyenne des perdants: {avg_loss:.1f}%')

# Afficher les meilleures entrées
print(f'\n\n{"="*80}')
print('TOP 10 MEILLEURES ENTREES')
print('='*80)

for i, entry in enumerate(entries[:10], 1):
    status = 'MIGRATION' if entry['is_migration'] else ('RUNNER' if entry['is_runner'] else 'FLOP')
    targets_str = ' + '.join(entry['targets_hit']) if entry['targets_hit'] else 'Aucun target'

    print(f'\n{i}. {entry["symbol"]} [{status}]')
    print(f'   Entree: ${entry["entry_mc"]:,.0f} -> Sortie: ${entry["final_mc"]:,.0f}')
    print(f'   Gain: {entry["gain_pct"]:+.1f}%')
    print(f'   Targets atteints: {targets_str}')
    print(f'   Metriques a 15s: BR={entry["buy_ratio"]:.0f}% | Txn={entry["txn"]} | Traders={entry["traders"]} | BigBuys={entry["big_buys"]}')

# Afficher les pires entrées
print(f'\n\n{"="*80}')
print('PIRES ENTREES (pour comprendre les pertes)')
print('='*80)

for i, entry in enumerate(entries[-5:], 1):
    print(f'\n{i}. {entry["symbol"]}')
    print(f'   Entree: ${entry["entry_mc"]:,.0f} -> Sortie: ${entry["final_mc"]:,.0f}')
    print(f'   Perte: {entry["gain_pct"]:.1f}%')
    print(f'   Metriques a 15s: BR={entry["buy_ratio"]:.0f}% | Txn={entry["txn"]} | Traders={entry["traders"]} | BigBuys={entry["big_buys"]}')

# Statistiques par target
print(f'\n\n{"="*80}')
print('ANALYSE PAR TARGET')
print('='*80)

target_1_hits = len([e for e in entries if 'T1 ($25K)' in e['targets_hit']])
target_2_hits = len([e for e in entries if 'T2 ($50K)' in e['targets_hit']])
target_3_hits = len([e for e in entries if 'T3 ($69K)' in e['targets_hit']])

print(f'\nTarget 1 ($25K): {target_1_hits}/{len(entries)} positions ({target_1_hits/len(entries)*100:.1f}%)')
print(f'Target 2 ($50K): {target_2_hits}/{len(entries)} positions ({target_2_hits/len(entries)*100:.1f}%)')
print(f'Target 3 ($69K): {target_3_hits}/{len(entries)} positions ({target_3_hits/len(entries)*100:.1f}%)')

print(f'\n\n{"="*80}')
print('CONCLUSION')
print('='*80)
print(f'\nLe bot aurait pris {len(entries)} positions.')
print(f'Sur ces {len(entries)} positions:')
print(f'  - {len(winners)} auraient ete gagnantes (+{sum(e["gain_pct"] for e in winners):.0f}% total)')
print(f'  - {len(losers)} auraient ete perdantes ({sum(e["gain_pct"] for e in losers):.0f}% total)')
print(f'  - {target_1_hits} auraient atteint le Target 1 ($25K) = +150-200%')
print(f'  - {target_2_hits} auraient atteint le Target 2 ($50K) = +300-400%')
print(f'  - {target_3_hits} auraient atteint le Target 3 ($69K) = +500-600%')
print(f'\nCe sont des resultats passes, pas une garantie future!')
print('='*80)

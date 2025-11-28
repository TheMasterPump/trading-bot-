"""
Trouve le SWEET SPOT optimal pour l'entrée
Analyse fine par tranches de MC
"""
import json

with open('trading_history.json', 'r') as f:
    data = json.load(f)

trades = data['trades']

print('='*80)
print('ANALYSE FINE PAR TRANCHES DE MC - TROUVER LE SWEET SPOT')
print('='*80)

# Définir des tranches plus fines
ranges = [
    (0, 7000, '<7K'),
    (7000, 8000, '7-8K'),
    (8000, 9000, '8-9K'),
    (9000, 10000, '9-10K'),
    (10000, 11000, '10-11K'),
    (11000, 12000, '11-12K'),
    (12000, 13000, '12-13K'),
    (13000, 14000, '13-14K'),
    (14000, 15000, '14-15K'),
    (15000, 20000, '15-20K'),
    (20000, 100000, '>20K'),
]

print('\n{:<15} {:>8} {:>8} {:>10} {:>12} {:>15}'.format(
    'MC RANGE', 'TOTAL', 'WINS', 'WIN RATE', 'AVG PROFIT', 'REACH 2X'
))
print('-'*80)

best_wr = 0
best_range = None

for min_mc, max_mc, label in ranges:
    range_trades = [t for t in trades if min_mc <= t['entry_mc'] < max_mc]

    if not range_trades:
        continue

    wins = [t for t in range_trades if t['is_win']]
    win_rate = len(wins) / len(range_trades) * 100 if range_trades else 0

    # Compter combien ont atteint 2x (profit_ratio >= 2.0 OU partial_sold)
    reached_2x = [t for t in range_trades if
                  (t.get('profit_ratio', 0) >= 2.0) or
                  ('2x' in t.get('exit_reason', ''))]
    pct_reach_2x = len(reached_2x) / len(range_trades) * 100 if range_trades else 0

    # Profit moyen
    avg_profit = sum(t['profit_ratio'] for t in range_trades) / len(range_trades)

    # Marquer le meilleur win rate
    marker = ' *BEST*' if win_rate > best_wr else ''
    if win_rate > best_wr:
        best_wr = win_rate
        best_range = label

    print('{:<15} {:>8} {:>8} {:>9.1f}% {:>11.2f}x {:>13.1f}%{}'.format(
        label,
        len(range_trades),
        len(wins),
        win_rate,
        avg_profit,
        pct_reach_2x,
        marker
    ))

print('\n' + '='*80)
print(f'MEILLEUR WIN RATE: {best_range} avec {best_wr:.1f}%')
print('='*80)

# Analyser les trades qui ont atteint 2x
print('\n' + '='*80)
print('ANALYSE DES TRADES QUI ATTEIGNENT 2X')
print('='*80)

all_2x_trades = [t for t in trades if
                 (t.get('profit_ratio', 0) >= 2.0) or
                 ('2x' in t.get('exit_reason', ''))]

print(f'\nTotal trades qui atteignent 2x: {len(all_2x_trades)} ({len(all_2x_trades)/len(trades)*100:.1f}%)')

# Parmi ceux qui atteignent 2x, combien win vs lose ?
wins_after_2x = [t for t in all_2x_trades if t['is_win']]
losses_after_2x = [t for t in all_2x_trades if not t['is_win']]

print(f'  - Finissent en WIN: {len(wins_after_2x)} ({len(wins_after_2x)/len(all_2x_trades)*100:.1f}%)')
print(f'  - Finissent en LOSS: {len(losses_after_2x)} ({len(losses_after_2x)/len(all_2x_trades)*100:.1f}%)')

if losses_after_2x:
    print(f'\n*** WARNING: {len(losses_after_2x)} trades ont atteint 2x puis PERDU!')
    print('     Strategie partial profit devrait les sauver...')
    avg_loss_after_2x = sum(t['profit_percent'] for t in losses_after_2x) / len(losses_after_2x)
    print(f'     Perte moyenne: {avg_loss_after_2x:.1f}%')

# MC moyen pour ceux qui atteignent 2x
if all_2x_trades:
    avg_mc_2x = sum(t['entry_mc'] for t in all_2x_trades) / len(all_2x_trades)
    print(f'\nMC moyen entrée pour atteindre 2x: ${avg_mc_2x:,.0f}')

# Analyser les features des trades qui atteignent 2x
print('\n' + '='*80)
print('FEATURES DES TRADES QUI ATTEIGNENT 2X')
print('='*80)

if all_2x_trades:
    avg_buy_ratio = sum(t['features'].get('buy_ratio', 0) for t in all_2x_trades) / len(all_2x_trades)
    avg_whale = sum(t['features'].get('whale_count', 0) for t in all_2x_trades) / len(all_2x_trades)
    avg_elite = sum(t['features'].get('elite_wallet_count', 0) for t in all_2x_trades) / len(all_2x_trades)
    avg_txn = sum(t['features'].get('txn', 0) for t in all_2x_trades) / len(all_2x_trades)

    print(f'Buy ratio moyen: {avg_buy_ratio*100:.1f}%')
    print(f'Whale count moyen: {avg_whale:.2f}')
    print(f'Elite wallet count moyen: {avg_elite:.2f}')
    print(f'Txn count moyen: {avg_txn:.1f}')

    # Comparer avec tous les trades
    all_avg_buy_ratio = sum(t['features'].get('buy_ratio', 0) for t in trades) / len(trades)
    all_avg_whale = sum(t['features'].get('whale_count', 0) for t in trades) / len(trades)

    print('\nCOMPARAISON vs TOUS LES TRADES:')
    print(f'Buy ratio: {avg_buy_ratio*100:.1f}% vs {all_avg_buy_ratio*100:.1f}% (diff: {(avg_buy_ratio-all_avg_buy_ratio)*100:+.1f}%)')
    print(f'Whale count: {avg_whale:.2f} vs {all_avg_whale:.2f} (diff: {avg_whale-all_avg_whale:+.2f})')

# RECOMMANDATIONS
print('\n' + '='*80)
print('RECOMMANDATIONS POUR LE SWEET SPOT')
print('='*80)

# Trouver la range avec le meilleur ratio (win_rate * pct_reach_2x)
best_score = 0
best_combo = None

print('\nSCORE COMPOSITE (Win Rate × % atteignent 2x):')
print('-'*80)

for min_mc, max_mc, label in ranges:
    range_trades = [t for t in trades if min_mc <= t['entry_mc'] < max_mc]

    if not range_trades or len(range_trades) < 5:  # Skip si < 5 trades
        continue

    wins = [t for t in range_trades if t['is_win']]
    win_rate = len(wins) / len(range_trades) * 100

    reached_2x = [t for t in range_trades if
                  (t.get('profit_ratio', 0) >= 2.0) or
                  ('2x' in t.get('exit_reason', ''))]
    pct_reach_2x = len(reached_2x) / len(range_trades) * 100

    # Score composite
    score = (win_rate / 100) * (pct_reach_2x / 100) * 10000

    marker = ' *TARGET*' if score > best_score else ''
    if score > best_score:
        best_score = score
        best_combo = (label, win_rate, pct_reach_2x)

    print(f'{label:<15} Score: {score:>6.1f} (WR:{win_rate:>5.1f}% x 2x:{pct_reach_2x:>5.1f}%){marker}')

if best_combo:
    print('\n' + '='*80)
    print(f'*** SWEET SPOT OPTIMAL: {best_combo[0]}')
    print(f'   Win Rate: {best_combo[1]:.1f}%')
    print(f'   Atteignent 2x: {best_combo[2]:.1f}%')
    print(f'   Score: {best_score:.1f}')
    print('='*80)

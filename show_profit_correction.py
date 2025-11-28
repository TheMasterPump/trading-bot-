"""
Montre la correction du calcul de profit pour le trade "Bug"
"""
import sys, codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import json

# Charger l'historique
with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data.get('trades', [])

print('='*80)
print('CORRECTION DU CALCUL DE PROFIT')
print('='*80)

print('\nLe trade "Bug" a fait x2 (50% vendu), puis le reste a baissé.')
print('Avec l\'ancien calcul, ça comptait comme une PERTE.')
print('Avec le nouveau calcul, c\'est un GAIN!\n')

# Trouver le trade Bug
bug_trade = None
for t in trades:
    if 'Bug' in t['symbol'] or 'déjà vendu @ 2x' in t.get('exit_reason', ''):
        bug_trade = t
        break

if bug_trade:
    entry_mc = bug_trade['entry_mc']
    exit_mc = bug_trade['exit_mc']

    print(f'TRADE: {bug_trade["symbol"]}')
    print(f'Entry MC: ${entry_mc:,.0f}')
    print(f'Exit MC: ${exit_mc:,.0f}')
    print(f'Exit Reason: {bug_trade["exit_reason"]}')

    print(f'\n{"="*80}')
    print('ANCIEN CALCUL (FAUX):')
    print(f'{"="*80}')
    old_profit_ratio = exit_mc / entry_mc
    old_profit_percent = (old_profit_ratio - 1) * 100
    print(f'Profit ratio: {old_profit_ratio:.2f}x')
    print(f'Profit percent: {old_profit_percent:+.1f}%')
    print(f'Résultat: ❌ PERTE de {abs(old_profit_percent):.1f}%')

    print(f'\n{"="*80}')
    print('NOUVEAU CALCUL (CORRECT):')
    print(f'{"="*80}')
    print('50% vendus à x2 = 100% de la mise récupérée')
    print('50% restants sont GRATUITS')
    print(f'50% restants valent maintenant: {exit_mc/entry_mc:.2f}x')

    new_profit_ratio = 1.0 + 0.5 * (exit_mc / entry_mc)
    new_profit_percent = (new_profit_ratio - 1) * 100

    print(f'\nProfit REEL:')
    print(f'  100% récupéré (partial @ 2x)')
    print(f'  + 50% × {exit_mc/entry_mc:.2f}x')
    print(f'  = {new_profit_ratio:.2f}x')
    print(f'  = {new_profit_percent:+.1f}%')
    print(f'Résultat: ✅ GAIN de {new_profit_percent:.1f}%')

    print(f'\n{"="*80}')
    print('DIFFERENCE:')
    print(f'{"="*80}')
    print(f'Ancien: {old_profit_percent:+.1f}% (FAUX)')
    print(f'Nouveau: {new_profit_percent:+.1f}% (CORRECT)')
    print(f'Différence: {new_profit_percent - old_profit_percent:+.1f}% points!')

    print(f'\n💡 C\'EST POUR ÇA que la stratégie PARTIAL PROFIT est GENIALE!')
    print(f'   Même quand le token redescend, on est EN GAIN!')

else:
    print('Trade avec partial profit pas trouvé dans l\'historique.')

print(f'\n{"="*80}')
print('STATS CORRIGEES:')
print(f'{"="*80}')

wins_old = 0
wins_new = 0

for t in trades:
    entry_mc = t['entry_mc']
    exit_mc = t['exit_mc']
    partial_sold = 'déjà vendu @ 2x' in t.get('exit_reason', '')

    # Ancien calcul
    old_profit_percent = (exit_mc / entry_mc - 1) * 100
    if old_profit_percent > 0:
        wins_old += 1

    # Nouveau calcul
    if partial_sold:
        new_profit_percent = (1.0 + 0.5 * (exit_mc / entry_mc) - 1) * 100
    else:
        new_profit_percent = old_profit_percent

    if new_profit_percent > 0:
        wins_new += 1

total = len(trades)
wr_old = (wins_old / total * 100) if total > 0 else 0
wr_new = (wins_new / total * 100) if total > 0 else 0

print(f'Total trades: {total}')
print(f'\nAVEC ANCIEN CALCUL (FAUX):')
print(f'  Wins: {wins_old}/{total} ({wr_old:.1f}%)')
print(f'  Losses: {total - wins_old}/{total}')

print(f'\nAVEC NOUVEAU CALCUL (CORRECT):')
print(f'  Wins: {wins_new}/{total} ({wr_new:.1f}%)')
print(f'  Losses: {total - wins_new}/{total}')

print(f'\n✅ Win rate amélioré de {wr_new - wr_old:+.1f}% points!')
print('='*80)

"""
Vérifier si paramètres optimisés gardent TOUS les winners
"""
import json
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Charger l'historique
with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data['trades'][-98:]

# Récupérer les winners AUTO-BUY
autobuy_wins = []
for t in trades:
    if not t.get('is_win', False):
        continue
    reason = t.get('entry_reason', t.get('reason', 'Unknown'))
    if 'AUTO-BUY' in reason:
        autobuy_wins.append(t)

print('='*80)
print('VÉRIFICATION: Paramètres OPTIMISÉS pour garder tous les winners')
print('='*80)

# PARAMÈTRES OPTIMISÉS
opt_min_txn = 22
opt_min_traders = 17
opt_min_buy_ratio = 0.72
opt_max_whales = 3

print(f'\nPARAMÈTRES OPTIMISÉS:')
print(f'  MIN_TXN: {opt_min_txn}')
print(f'  MIN_TRADERS: {opt_min_traders}')
print(f'  MIN_BUY_RATIO: {opt_min_buy_ratio*100:.0f}%')
print(f'  MAX_WHALES: {opt_max_whales}')

print(f'\n{"="*80}')
print(f'TEST SUR LES 16 WINNERS AUTO-BUY')
print('='*80)

kept = []
lost = []

for t in autobuy_wins:
    f = t.get('features', {})
    txn = f.get('txn', 0)
    traders = f.get('traders', 0)
    buy_ratio = f.get('buy_ratio', 0)
    whales = f.get('whale_count', 0)

    # Check avec paramètres optimisés
    passes = True
    reasons = []

    if txn < opt_min_txn:
        passes = False
        reasons.append(f'TXN {txn} < {opt_min_txn}')

    if traders < opt_min_traders:
        passes = False
        reasons.append(f'Traders {traders} < {opt_min_traders}')

    if buy_ratio < opt_min_buy_ratio:
        passes = False
        reasons.append(f'Buy ratio {buy_ratio*100:.0f}% < {opt_min_buy_ratio*100:.0f}%')

    if whales > opt_max_whales:
        passes = False
        reasons.append(f'Whales {whales} > {opt_max_whales}')

    if passes:
        kept.append(t)
    else:
        lost.append((t, reasons))

print(f'\nRÉSULTAT:')
print(f'  Gardés: {len(kept)}/{len(autobuy_wins)} winners ({len(kept)/len(autobuy_wins)*100:.0f}%)')
print(f'  Perdus: {len(lost)}/{len(autobuy_wins)} winners ({len(lost)/len(autobuy_wins)*100:.0f}%)')

if len(lost) == 0:
    print(f'\nPARFAIT! TOUS LES WINNERS SONT GARDÉS!')

    total_profit = sum(t.get('profit_percent', 0) for t in kept)
    avg_profit = total_profit / len(kept) if kept else 0

    print(f'\nTOUS LES 16 WINNERS AUTO-BUY:')
    print(f'   Profit total: +{total_profit:.1f}%')
    print(f'   Profit moyen: +{avg_profit:.1f}%')

    # Afficher tous les winners
    print(f'\n{"="*80}')
    print('LISTE COMPLÈTE DES WINNERS GARDÉS:')
    print('='*80)

    sorted_wins = sorted(kept, key=lambda x: x.get('profit_percent', 0), reverse=True)
    for i, t in enumerate(sorted_wins, 1):
        f = t.get('features', {})
        print(f'{i}. {t.get("symbol")}: +{t.get("profit_percent", 0):.1f}% ({f.get("txn", 0)}txn, {f.get("traders", 0)}tr, {f.get("buy_ratio", 0)*100:.0f}%buy, {f.get("whale_count", 0)}whales)')

else:
    print(f'\nWINNERS PERDUS:')
    for t, reasons in lost:
        f = t.get('features', {})
        print(f'\n{t.get("symbol")}: +{t.get("profit_percent", 0):.1f}%')
        print(f'   Features: {f.get("txn", 0)}txn, {f.get("traders", 0)}traders, {f.get("buy_ratio", 0)*100:.0f}%buy, {f.get("whale_count", 0)}whales')
        print(f'   Raisons: {" | ".join(reasons)}')

print(f'\n{"="*80}')
print('CONCLUSION')
print('='*80)

if len(lost) == 0:
    print(f'\nCes paramètres sont PARFAITS pour AUTO-BUY!')
    print(f'   -> Tous les 16 winners historiques sont capturés')
    print(f'   -> Aucun bon token perdu')
    print(f'\nRECOMMANDATION: Appliquer ces paramètres!')
else:
    print(f'\nIl y a encore {len(lost)} winner(s) perdu(s)')
    print(f'   -> Ajuster encore les paramètres')

print(f'\n{"="*80}')

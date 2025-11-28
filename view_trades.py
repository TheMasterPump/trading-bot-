"""
Script pour voir l'historique des trades de façon lisible
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
print(f'HISTORIQUE DES TRADES: {len(trades)} trades')
print('='*80)

# Stats générales
wins = [t for t in trades if t.get('is_win', False)]
losses = [t for t in trades if not t.get('is_win', False)]
wr = len(wins) / len(trades) * 100 if trades else 0

print(f'\nSTATS GLOBALES:')
print(f'  Wins: {len(wins)} ({wr:.1f}%)')
print(f'  Losses: {len(losses)}')
print(f'  Total: {len(trades)} trades')

if wins:
    avg_win = sum(t.get('profit_percent', 0) for t in wins) / len(wins)
    print(f'  Profit moyen (wins): +{avg_win:.1f}%')

if losses:
    avg_loss = sum(t.get('profit_percent', 0) for t in losses) / len(losses)
    print(f'  Perte moyenne (losses): {avg_loss:.1f}%')

# Demander combien de trades afficher
print(f'\n{"="*80}')
choice = input('\nCombien de trades voulez-vous voir? (ex: 10, 20, all): ').strip().lower()

if choice == 'all':
    trades_to_show = trades
else:
    try:
        n = int(choice)
        trades_to_show = trades[-n:]  # Les N derniers
    except:
        trades_to_show = trades[-10:]  # Par défaut: 10 derniers

print(f'\n{"="*80}')
print(f'AFFICHAGE DES {len(trades_to_show)} DERNIERS TRADES')
print('='*80)

for i, trade in enumerate(trades_to_show, 1):
    symbol = trade.get('symbol', 'N/A')
    profit = trade.get('profit_percent', 0)
    is_win = trade.get('is_win', False)
    entry_mc = trade.get('entry_mc', 0)
    exit_mc = trade.get('exit_mc', 0)
    entry_reason = trade.get('entry_reason', trade.get('reason', 'N/A'))
    exit_reason = trade.get('exit_reason', 'N/A')
    features = trade.get('features', {})

    result = 'WIN' if is_win else 'LOSS'

    print(f'\n{i}. [{result}] {symbol}: {profit:+.1f}%')
    print(f'   Entry: ${entry_mc:,.0f} -> Exit: ${exit_mc:,.0f}')
    print(f'   Entry reason: {entry_reason}')
    print(f'   Exit reason: {exit_reason}')

    if features:
        whales = features.get('whale_count', 0)
        buy_ratio = features.get('buy_ratio', 0)
        txn = features.get('txn', 0)
        traders = features.get('traders', 0)
        print(f'   Features: {whales} whales, {buy_ratio*100:.0f}% buy, {txn} txn, {traders} traders')

print(f'\n{"="*80}')

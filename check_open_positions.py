"""
Vérifie les positions ouvertes du bot
"""
import sys
import codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

import json

# Charger l'historique
with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

closed_trades = data.get('trades', [])

print('='*80)
print('ANALYSE DES POSITIONS')
print('='*80)

print(f'\n📊 POSITIONS FERMEES (dans historique): {len(closed_trades)}')

if closed_trades:
    wins = len([t for t in closed_trades if t['is_win']])
    losses = len(closed_trades) - wins
    print(f'  Wins: {wins}')
    print(f'  Losses: {losses}')

    for i, trade in enumerate(closed_trades, 1):
        result = "✅ WIN" if trade['is_win'] else "❌ LOSS"
        print(f'\n  Trade #{i}: {trade["symbol"]} - {result}')
        print(f'    Entry: ${trade["entry_mc"]:.0f} @ {trade["entry_time"]}')
        print(f'    Exit: ${trade["exit_mc"]:.0f}')
        print(f'    Profit: {trade["profit_ratio"]:.2f}x ({trade["profit_percent"]:+.1f}%)')
        print(f'    Raison: {trade["exit_reason"]}')

print(f'\n{"="*80}')
print('⚠️ PROBLEME POTENTIEL:')
print('='*80)
print("""
Si le bot a fait plus de trades que ça, c'est que:

1. Les positions sont OUVERTES mais pas encore FERMEES
   → Elles ne sont pas enregistrées tant qu'elles ne sont pas vendues

2. Le bot n'appelle pas check_position() assez souvent
   → Les stop loss / take profit ne sont pas vérifiés

3. Les positions restent ouvertes indéfiniment
   → Il faut vérifier si handle_trade() appelle bien check_position()

SOLUTION:
Le bot doit appeler check_position() à CHAQUE nouveau trade reçu
pour vérifier si les positions ouvertes ont atteint TP ou SL.
""")
print('='*80)

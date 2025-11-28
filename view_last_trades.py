import json

with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data['trades'][-5:]

print('='*70)
print('DERNIERS 5 TRADES')
print('='*70)

for i, t in enumerate(trades):
    print(f'\n{i+1}. {t.get("symbol", "?")} ({t.get("mint", "?")[:8]}...)')
    print(f'   Entree: ${t.get("entry_mc", 0):,.0f}')
    print(f'   Sortie: ${t.get("exit_mc", 0):,.0f}')
    print(f'   Profit: {t.get("profit_ratio", 1):.2f}x ({t.get("profit_percent", 0):+.1f}%)')
    print(f'   Raison entree: {t.get("reason", "?")}')
    print(f'   Date: {t.get("exit_time", "?")}')

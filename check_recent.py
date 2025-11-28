import json

with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data.get('trades', [])
recent = trades[-20:]
wins = [t for t in recent if t.get('is_win')]

print(f'=== 20 DERNIERS TRADES ===')
print(f'Wins: {len(wins)}/{len(recent)} ({len(wins)/len(recent)*100:.1f}%)')

print(f'\nDerniers 10 trades:')
for t in trades[-10:]:
    status = 'WIN' if t.get('is_win') else 'LOSS'
    print(f'  {t.get("symbol", "?")}: {t.get("profit_percent", 0):+.1f}% ({status}) - {t.get("exit_reason", "?")}')

import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'=== STATISTIQUES DASHBOARD ===')
print(f'Total completed: {len(data.get("completed", []))}')
print(f'Total runners: {len(data.get("runners", []))}')
print(f'Total flops: {len(data.get("flops", []))}')

print(f'\n=== DERNIERS 10 TOKENS COMPLETES ===')
recent = data.get('completed', [])[-10:]
for t in recent:
    symbol = t.get('symbol', '???')
    mc = t.get('final_mc', 0)
    status = 'RUNNER' if t.get('is_runner') else 'FLOP'
    print(f'{symbol:15} ${mc:>10,.0f} - {status}')

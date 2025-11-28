import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Tous les tokens qui ont atteint >= $15K
all_runners = [r for r in data['completed'] if r.get('final_mc', 0) >= 15000]

# Runners marqués comme runners
marked_runners = data.get('runners', [])

print(f'=== ANALYSE DES RUNNERS ===')
print(f'Total tokens analysés: {len(data["completed"])}')
print(f'')
print(f'Tokens qui ont atteint >=$15K: {len(all_runners)}')
print(f'Tokens marqués comme runners: {len(marked_runners)}')
print(f'')

if len(all_runners) > len(marked_runners):
    print(f'[PROBLEME] On a manqué {len(all_runners) - len(marked_runners)} runners!')
    print(f'')

print(f'=== DERNIERS RUNNERS (>=$15K) ===')
for r in all_runners[-10:]:
    symbol = r.get('symbol', '???')
    mc = r.get('final_mc', 0)
    early = r.get('early_runner', False)
    is_runner = r.get('is_runner', False)
    pump_time = r.get('pump_time', '?')
    print(f'{symbol}: ${mc:,.0f} | Early: {early} | Marked as runner: {is_runner} | Pump time: {pump_time}')

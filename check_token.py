import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

last = d['completed'][-1]
print('Dernier token complete:')
print(f'  Symbol: {last["symbol"]}')
print(f'  Final MC: ${last["final_mc"]:,.0f}')
print(f'  Type: {"RUNNER" if last["is_runner"] else "FLOP"}')
print(f'  Snapshots presents:')
snapshots = ['10s', '15s', '20s', '30s', '1min', '2min', '3min', '5min', '8min', '10min']
for s in snapshots:
    print(f'    {s}: {"OUI" if last.get(s) else "NON"}')

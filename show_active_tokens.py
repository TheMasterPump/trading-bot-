import json

with open('bot_data.json', 'r') as f:
    d = json.load(f)

active = d.get('tokens', [])
print('='*80)
print('TOKENS EN COURS D\'ANALYSE - TEMPS REEL')
print('='*80)
print(f'\nTotal actifs: {len(active)} tokens\n')

if active:
    print(f'{"#":<4} {"SYMBOL":<15} {"AGE":<8} {"MC ACTUEL":<12} {"TRADES":<8}')
    print('-'*80)
    for i, t in enumerate(active[:20], 1):
        symbol = t.get('symbol', 'N/A')[:15]
        age = t.get('age_seconds', 0)
        mc = t.get('mc_current', 0)
        trades = t.get('trade_count', 0)
        print(f'{i:<4} {symbol:<15} {age:<8}s ${mc:<11,.0f} {trades:<8}')

print(f'\n{"="*80}')
print('DATASET COMPLET')
print('='*80)
print(f'Runners completés: {len(d.get("runners", []))}')
print(f'Flops completés:   {len(d.get("flops", []))}')
print(f'Total completés:   {len(d.get("runners", [])) + len(d.get("flops", []))}')
print(f'En cours:          {len(active)}')

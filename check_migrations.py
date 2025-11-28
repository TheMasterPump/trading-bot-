import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print('VERIFICATION DES MIGRATIONS:')
print('=' * 80)

for i, runner in enumerate(d['runners'], 1):
    symbol = runner.get('symbol', 'N/A')
    mint = runner.get('mint', 'N/A')
    final_mc = runner.get('final_mc', 0)
    migration = runner.get('migration_detected', False)
    migration_price = runner.get('migration_price', 0)
    
    print(f'\n{i}. {symbol}')
    print(f'   Contract: {mint}')
    print(f'   Final MC: ${final_mc:,.0f}')
    print(f'   Migration PumpSwap: {"OUI" if migration else "NON"}')
    if migration:
        print(f'   Migration Price: ${migration_price:,.0f}')
    print(f'   Status: {"MIGRE VERS PUMPSWAP" if final_mc >= 69000 else "RESTE SUR PUMPFUN"}')

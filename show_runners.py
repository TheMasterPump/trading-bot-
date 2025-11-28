import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print('=' * 80)
print('LES 5 RUNNERS ENREGISTRES')
print('=' * 80)

for i, runner in enumerate(d['runners'], 1):
    symbol = runner.get('symbol', 'N/A')
    mint = runner.get('mint', 'N/A')
    final_mc = runner.get('final_mc', 0)
    pump_time = runner.get('pump_time', 0)
    migration = runner.get('migration_detected', False)
    
    print(f'\n{i}. {symbol}')
    print(f'   Contract: {mint}')
    print(f'   Final MC: ${final_mc:,.0f}')
    print(f'   Pump Time: {pump_time:.0f}s ({pump_time/60:.1f} min)')
    print(f'   Migration: {"OUI - PUMPSWAP" if migration else "NON"}')
    print(f'   PumpFun: https://pump.fun/{mint}')

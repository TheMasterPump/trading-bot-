import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

runners = d.get('runners', [])
flops = d.get('flops', [])

print('='*80)
print('VERIFICATION: Champs disponibles et migration Raydium')
print('='*80)

if runners:
    print('\n[CHAMPS DISPONIBLES DANS UN RUNNER]')
    first_runner = runners[0]
    all_fields = list(first_runner.keys())
    print(f'Total de champs: {len(all_fields)}')
    print('\nChamps:')
    for field in sorted(all_fields):
        print(f'  - {field}')

    print('\n[VERIFICATION MIGRATION RAYDIUM]')
    print(f'Analysant {len(runners)} runners...\n')

    migrated_count = 0
    for i, r in enumerate(runners[:10], 1):
        symbol = r.get('symbol', 'N/A')
        final_mc = r.get('final_mc', 0)
        is_runner = r.get('is_runner', False)

        print(f'{i}. {symbol}')
        print(f'   Final MC: ${final_mc:,.0f}')
        print(f'   is_runner: {is_runner}')

else:
    print('Aucun runner trouvé!')

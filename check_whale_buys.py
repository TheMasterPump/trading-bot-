import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print('=' * 80)
print('WHALES ACTIVITY SUR LES RUNNERS')
print('=' * 80)

for i, runner in enumerate(d['runners'], 1):
    symbol = runner.get('symbol', 'N/A')
    mint = runner.get('mint', 'N/A')
    final_mc = runner.get('final_mc', 0)

    # Whale info
    whale_count = runner.get('whale_count', 0)
    whale_wallets = runner.get('whale_wallets_detected', [])
    whale_volume = runner.get('whale_total_volume_usd', 0)

    print(f'\n{i}. {symbol} - Final MC: ${final_mc:,.0f}')
    print(f'   Contract: {mint}')

    if whale_count > 0:
        print(f'   [OUI] {whale_count} WHALE(S) ONT ACHETE!')
        print(f'   Volume Total Whale: ${whale_volume:,.0f}')
        if whale_wallets:
            print(f'   Wallets:')
            for wallet in whale_wallets[:5]:  # Montrer max 5 wallets
                print(f'      - {wallet}')
        else:
            print(f'   (Adresses wallet non enregistrees)')
    else:
        print(f'   [NON] Aucune whale detectee')

print('\n' + '=' * 80)
print('RESUME')
print('=' * 80)
runners_with_whales = sum(1 for r in d['runners'] if r.get('whale_count', 0) > 0)
print(f'Runners avec whales: {runners_with_whales}/{len(d["runners"])}')
print(f'Taux: {runners_with_whales/len(d["runners"])*100:.1f}%' if len(d['runners']) > 0 else 'N/A')

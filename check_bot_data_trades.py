"""
Chercher les trades dans bot_data.json
"""
import json
import sys

print('Chargement de bot_data.json (92MB - patientez)...')

try:
    with open('bot_data.json', 'r', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)

    print('Fichier charge avec succes!\n')
    print('='*80)
    print('STRUCTURE DE BOT_DATA.JSON')
    print('='*80)

    # Explorer la structure
    for key in data.keys():
        if isinstance(data[key], dict):
            print(f'\n{key}: {len(data[key])} items')
            if len(data[key]) > 0:
                # Montrer un exemple
                first_key = list(data[key].keys())[0]
                print(f'  Exemple: {first_key}')
        elif isinstance(data[key], list):
            print(f'\n{key}: {len(data[key])} items (liste)')
        else:
            print(f'\n{key}: {data[key]}')

    # Chercher des trades
    print('\n' + '='*80)
    print('RECHERCHE DE TRADES')
    print('='*80)

    # Vérifier completed_tokens
    if 'completed_tokens' in data:
        completed = data['completed_tokens']
        print(f'\nCompleted tokens: {len(completed)}')

        # Compter les trades totaux
        total_trades = 0
        for mint, token_data in completed.items():
            if isinstance(token_data, dict):
                # Vérifier s'il y a des infos de trade
                if 'profit_percent' in token_data or 'exit_mc' in token_data:
                    total_trades += 1

        print(f'Tokens avec donnees de trade: {total_trades}')

        # Montrer quelques exemples
        print('\nExemples de completed tokens:')
        for i, (mint, token_data) in enumerate(list(completed.items())[:3]):
            if isinstance(token_data, dict):
                symbol = token_data.get('symbol', 'Unknown')
                print(f'\n  {i+1}. {symbol}')
                for key in ['entry_mc', 'exit_mc', 'profit_percent', 'is_winner']:
                    if key in token_data:
                        print(f'     {key}: {token_data[key]}')

    # Vérifier active_tokens
    if 'active_tokens' in data:
        active = data['active_tokens']
        print(f'\nActive tokens: {len(active)}')

    # Chercher d'autres endroits où il pourrait y avoir des trades
    if 'trades' in data:
        print(f'\nTrades (liste directe): {len(data["trades"])}')

except Exception as e:
    print(f'Erreur: {e}')
    import traceback
    traceback.print_exc()

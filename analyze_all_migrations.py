"""
Analyse TOUS les tokens pour trouver ceux qui ont migré
"""
import json

print('='*80)
print('ANALYSE COMPLETE DES MIGRATIONS')
print('='*80)

# Charger bot_data.json avec encodage UTF-8
try:
    with open('bot_data.json', 'r', encoding='utf-8', errors='ignore') as f:
        bot_data = json.load(f)

    print(f'\nBot data charge avec succes')

    # Explorer la structure
    if 'completed_tokens' in bot_data:
        completed = bot_data['completed_tokens']
        print(f'Completed tokens: {len(completed)}')

        # Compter les migrations
        migrations = 0
        near_migrations = 0
        max_mc = 0
        migration_tokens = []

        for mint, token_data in completed.items():
            # Chercher le MC max
            if 'trades' in token_data:
                for trade in token_data['trades']:
                    mc = trade.get('mc', 0)
                    if mc > max_mc:
                        max_mc = mc

                    if mc >= 69000:
                        migrations += 1
                        symbol = token_data.get('symbol', 'Unknown')
                        if symbol not in [t[0] for t in migration_tokens]:
                            migration_tokens.append((symbol, mc, mint))
                        break
                    elif mc >= 50000:
                        near_migrations += 1

        print(f'\n{"="*80}')
        print('RESULTATS')
        print('='*80)
        print(f'\nTokens qui ont MIGRE (>= 69K): {migrations}')
        print(f'Tokens PROCHES migration (50-69K): {near_migrations}')
        print(f'MC maximum atteint: ${max_mc:,.0f}')

        if migration_tokens:
            print(f'\n{"="*80}')
            print('TOKENS QUI ONT MIGRE')
            print('='*80)
            for symbol, mc, mint in sorted(migration_tokens, key=lambda x: x[1], reverse=True)[:10]:
                print(f'\n{symbol}')
                print(f'  MC max: ${mc:,.0f}')
                print(f'  Mint: {mint[:20]}...')

    # Vérifier les active tokens aussi
    if 'active_tokens' in bot_data:
        active = bot_data['active_tokens']
        print(f'\n\nActive tokens: {len(active)}')

    # Vérifier tokens
    if 'tokens' in bot_data:
        all_tokens = bot_data['tokens']
        print(f'All tokens tracked: {len(all_tokens)}')

except Exception as e:
    print(f'\nErreur: {e}')
    print('\nEssayons avec trading_history.json a la place...')

    # Fallback sur learning engine
    try:
        import sys
        sys.path.insert(0, '.')
        from learning_engine import learning_engine

        print(f'\n{"="*80}')
        print('LEARNING ENGINE - TOUS LES TRADES')
        print('='*80)

        all_trades = learning_engine.trades
        print(f'\nTotal trades dans learning engine: {len(all_trades)}')

        migrations = [t for t in all_trades if t.get('exit_mc', 0) >= 69000]
        near = [t for t in all_trades if 50000 <= t.get('exit_mc', 0) < 69000]

        print(f'Migrations (>= 69K): {len(migrations)}')
        print(f'Proches (50-69K): {len(near)}')

        if migrations:
            print(f'\n{"="*80}')
            print('TOKENS QUI ONT MIGRE')
            print('='*80)
            for t in migrations[:10]:
                print(f"\n{t['symbol']}")
                print(f"  Entry MC: ${t['entry_mc']:,.0f}")
                print(f"  Exit MC: ${t['exit_mc']:,.0f}")
                print(f"  Profit: {t.get('profit_percent', 0):+.1f}%")

        # MC max
        if all_trades:
            max_mc = max(t.get('exit_mc', 0) for t in all_trades)
            print(f'\nMC maximum atteint: ${max_mc:,.0f}')

    except Exception as e2:
        print(f'Erreur learning engine: {e2}')

print('\n' + '='*80)

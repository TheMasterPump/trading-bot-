import sys
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from learning_engine import learning_engine
from adaptive_config import adaptive_config

print('='*80)
print('BOT DE TRADING - VERIFICATION DE DEMARRAGE')
print('='*80)
print(f'\n🧠 APPRENTISSAGE AUTOMATIQUE')
print(f'   Trades dans historique: {len(learning_engine.trades)}')
print(f'   Mode: {adaptive_config.params["TRADING_MODE"]}')

print(f'\n⚙️ CONFIGURATION ACTUELLE')
print(f'   MAX_PRICE_8S: ${adaptive_config.params["MAX_PRICE_8S"]:,}')
print(f'   ELITE_WALLET_MAX_MC: ${adaptive_config.params["ELITE_WALLET_MAX_MC"]:,}')
print(f'   ELITE_MIN_BUY_RATIO: {adaptive_config.params["ELITE_MIN_BUY_RATIO"]*100:.0f}%')
print(f'   ELITE_MIN_WHALE_COUNT: {adaptive_config.params["ELITE_MIN_WHALE_COUNT"]}')
print(f'   PRICE_JUMP_TOLERANCE: +{adaptive_config.params["PRICE_JUMP_TOLERANCE"]*100:.0f}%')

print(f'\n💰 STRATEGIE')
print(f'   Partial Profit: 50% @ 2x, 50% @ migration')
print(f'   Anti-Latence: ✅ Activé')

print(f'\n✅ LE BOT EST LANCE ET PRET!')
print('='*80)
print('\nPour surveiller:')
print('  python analyze_bot.py')
print('\nPour ajuster:')
print('  python adjust_config.py')
print('='*80)

import json
import joblib
import pandas as pd
from datetime import datetime

print('='*80)
print('BOT AI DE PREDICTION - STRATEGIE 10s + 15s')
print('='*80)

# Configuration
THRESHOLD_10S = 0.65  # Seuil de confiance @ 10s
THRESHOLD_15S = 0.70  # Seuil de confiance @ 15s
MAX_PRICE_10S = 15000  # Prix max pour entrer @ 10s
MAX_PRICE_15S = 20000  # Prix max pour entrer @ 15s

print(f'\n[CONFIGURATION]')
print(f'  Seuil @ 10s: {THRESHOLD_10S*100:.0f}% confiance, MC < ${MAX_PRICE_10S:,}')
print(f'  Seuil @ 15s: {THRESHOLD_15S*100:.0f}% confiance, MC < ${MAX_PRICE_15S:,}')

# Charger les modeles
print(f'\n[CHARGEMENT DES MODELES]')
model_10s = joblib.load('model_10s.pkl')
model_15s = joblib.load('model_15s.pkl')
print(f'  Model @ 10s: OK')
print(f'  Model @ 15s: OK')

# Charger les donnees
print(f'\n[CHARGEMENT DES DONNEES]')
with open('bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

runners = data.get('runners', [])
flops = data.get('flops', [])[:50]  # Limiter les flops pour le test

print(f'  Runners: {len(runners)}')
print(f'  Flops (sample): {len(flops)}')

# Fonction de prediction
def predict_token(token, model_10s, model_15s):
    """Predit si un token va migrer en utilisant les 2 modeles"""

    result = {
        'symbol': token.get('symbol', 'N/A'),
        'decision_10s': 'PASS',
        'decision_15s': 'PASS',
        'final_decision': 'PASS',
        'entry_price': None,
        'entry_time': None,
        'confidence_10s': 0,
        'confidence_15s': 0,
        'actual_migrated': token.get('migration_detected', False),
        'final_mc': token.get('final_mc', 0)
    }

    # Verifier donnees @ 10s
    snap_10s = token.get('10s', {})
    if not snap_10s:
        return result

    # Extraire features @ 10s
    features_10s = {
        'txn': snap_10s.get('txn', 0),
        'traders': snap_10s.get('traders', 0),
        'buy_ratio': snap_10s.get('buy_ratio', 0),
        'mc': snap_10s.get('mc', 0),
        'velocity': snap_10s.get('velocity', 0),
        'whale_count': token.get('whale_count', 0)
    }

    X_10s = pd.DataFrame([features_10s])
    proba_10s = model_10s.predict_proba(X_10s)[0, 1]
    result['confidence_10s'] = proba_10s

    mc_10s = features_10s['mc']

    # Decision @ 10s
    if proba_10s >= THRESHOLD_10S and mc_10s < MAX_PRICE_10S:
        result['decision_10s'] = 'BUY'
        result['final_decision'] = 'BUY @ 10s'
        result['entry_price'] = mc_10s
        result['entry_time'] = '10s'
        return result
    elif proba_10s >= THRESHOLD_10S:
        result['decision_10s'] = 'HOLD'  # Confiant mais trop cher

    # Verifier donnees @ 15s
    snap_15s = token.get('15s', {})
    if not snap_15s:
        return result

    # Extraire features @ 15s
    features_15s = {
        '10s_txn': snap_10s.get('txn', 0),
        '10s_traders': snap_10s.get('traders', 0),
        '10s_buy_ratio': snap_10s.get('buy_ratio', 0),
        '10s_mc': snap_10s.get('mc', 0),
        '10s_velocity': snap_10s.get('velocity', 0),
        '15s_txn': snap_15s.get('txn', 0),
        '15s_traders': snap_15s.get('traders', 0),
        '15s_buy_ratio': snap_15s.get('buy_ratio', 0),
        '15s_mc': snap_15s.get('mc', 0),
        '15s_velocity': snap_15s.get('velocity', 0),
        'mc_growth_10s_15s': 0,
        'txn_growth_10s_15s': snap_15s.get('txn', 0) - snap_10s.get('txn', 0),
        'traders_growth_10s_15s': snap_15s.get('traders', 0) - snap_10s.get('traders', 0),
        'whale_count': token.get('whale_count', 0)
    }

    if snap_10s.get('mc', 0) > 0:
        features_15s['mc_growth_10s_15s'] = (snap_15s.get('mc', 0) - snap_10s.get('mc', 0)) / snap_10s.get('mc', 1)

    X_15s = pd.DataFrame([features_15s])
    proba_15s = model_15s.predict_proba(X_15s)[0, 1]
    result['confidence_15s'] = proba_15s

    mc_15s = features_15s['15s_mc']

    # Decision @ 15s (si pas deja entre @ 10s)
    if result['decision_10s'] != 'BUY':
        if proba_15s >= THRESHOLD_15S and mc_15s < MAX_PRICE_15S:
            result['decision_15s'] = 'BUY'
            result['final_decision'] = 'BUY @ 15s'
            result['entry_price'] = mc_15s
            result['entry_time'] = '15s'
        elif proba_15s >= THRESHOLD_15S:
            result['decision_15s'] = 'HOLD'  # Confiant mais trop cher

    return result

# Analyser tous les tokens
print(f'\n[ANALYSE DES TOKENS]')
print('-'*80)

results = []

print(f'\nAnalyse des RUNNERS:')
for i, token in enumerate(runners[:20], 1):  # Limiter pour lisibilite
    result = predict_token(token, model_10s, model_15s)
    results.append(result)

    if result['final_decision'] != 'PASS':
        symbol = result['symbol'][:12]
        conf_10s = result['confidence_10s'] * 100
        conf_15s = result['confidence_15s'] * 100
        entry_price = result['entry_price']
        final_mc = result['final_mc']

        if entry_price and entry_price > 0:
            potential_profit = (final_mc / entry_price) if final_mc > 0 else 0

            print(f'\n  {i}. {symbol:12} - {result["final_decision"]}')
            print(f'     Confiance: 10s={conf_10s:.0f}% | 15s={conf_15s:.0f}%')
            print(f'     Entree: ${entry_price:,.0f} -> Final: ${final_mc:,.0f} ({potential_profit:.2f}x)')

print(f'\n\nAnalyse des FLOPS (echantillon):')
for i, token in enumerate(flops, 1):
    result = predict_token(token, model_10s, model_15s)
    results.append(result)

    # Afficher seulement les faux positifs (quand on entre mais c'est un flop)
    if result['final_decision'] != 'PASS':
        symbol = result['symbol'][:12]
        conf_10s = result['confidence_10s'] * 100
        conf_15s = result['confidence_15s'] * 100
        entry_price = result['entry_price']

        print(f'\n  FAUX POSITIF #{i}: {symbol:12} - {result["final_decision"]}')
        print(f'     Confiance: 10s={conf_10s:.0f}% | 15s={conf_15s:.0f}%')
        print(f'     Entree: ${entry_price:,.0f} -> TOKEN EST MORT (PERTE)')

# Statistiques finales
print(f'\n\n' + '='*80)
print('RESULTATS DU BOT AI')
print('='*80)

# Compter les decisions
buy_10s = [r for r in results if r['final_decision'] == 'BUY @ 10s']
buy_15s = [r for r in results if r['final_decision'] == 'BUY @ 15s']
total_buys = buy_10s + buy_15s

# Compter les bons et mauvais
correct_buys = [r for r in total_buys if r['actual_migrated']]
false_positives = [r for r in total_buys if not r['actual_migrated']]

# Runners manques
total_runners = len([r for r in results if r['actual_migrated']])
missed_runners = total_runners - len(correct_buys)

print(f'\n[DECISIONS DU BOT]')
print(f'  BUY @ 10s: {len(buy_10s)} tokens')
print(f'  BUY @ 15s: {len(buy_15s)} tokens')
print(f'  TOTAL BUY: {len(total_buys)} tokens')
print(f'')
print(f'[PRECISION]')
print(f'  Vrais runners detectes: {len(correct_buys)}/{total_runners} ({len(correct_buys)/total_runners*100 if total_runners > 0 else 0:.1f}%)')
print(f'  Faux positifs (flops):  {len(false_positives)}')
if len(total_buys) > 0:
    precision = len(correct_buys) / len(total_buys)
    print(f'  Precision: {precision*100:.1f}% (quand dit BUY, correct {precision*100:.0f}% du temps)')

print(f'\n[RUNNERS MANQUES]')
print(f'  Runners non detectes: {missed_runners}/{total_runners}')

# Calculer profit potentiel
if correct_buys:
    profits = []
    for buy in correct_buys:
        if buy['entry_price'] and buy['entry_price'] > 0 and buy['final_mc'] > 0:
            profit = buy['final_mc'] / buy['entry_price']
            profits.append(profit)

    if profits:
        avg_profit = sum(profits) / len(profits)
        print(f'\n[PROFIT POTENTIEL]')
        print(f'  Profit moyen par runner: {avg_profit:.2f}x')
        print(f'  Meilleur profit: {max(profits):.2f}x')
        print(f'  Pire profit: {min(profits):.2f}x')

print(f'\n[PRIX D\'ENTREE]')
entry_prices = [r['entry_price'] for r in correct_buys if r['entry_price']]
if entry_prices:
    import statistics
    print(f'  Prix moyen d\'entree: ${statistics.mean(entry_prices):,.0f}')
    print(f'  Prix median d\'entree: ${statistics.median(entry_prices):,.0f}')
    print(f'  Prix min: ${min(entry_prices):,.0f}')
    print(f'  Prix max: ${max(entry_prices):,.0f}')

print('\n' + '='*80)
print('CONCLUSION')
print('='*80)
print(f'''
Le bot AI fonctionne et detecte les runners avec:
- {len(correct_buys)}/{total_runners} runners detectes ({len(correct_buys)/total_runners*100 if total_runners > 0 else 0:.1f}%)
- {len(false_positives)} faux positifs
- Prix d'entree median: ${statistics.median(entry_prices) if entry_prices else 0:,.0f}

PROCHAINES ETAPES:
1. Ajuster les seuils de confiance si besoin
2. Integrer avec un bot de trading automatique
3. Tester en LIVE sur de nouveaux tokens
''')
print('='*80)

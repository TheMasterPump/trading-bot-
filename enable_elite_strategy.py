"""
ACTIVER STRATEGIE ELITE_WALLET en parallèle de AUTO_BUY
Baisser le seuil whale pour détecter plus de baleines
"""
import sys, codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import json

print('='*80)
print('ACTIVATION STRATEGIE ELITE_WALLET (en plus de AUTO_BUY)')
print('='*80)

print("""
STRATEGIE ACTUELLE:
  ✅ AUTO_BUY fonctionne bien (1 token sur 6 a fait x2)
  ✅ Partial Profit récupère la mise (-2.8% au lieu de -30%)

OBJECTIF:
  ✅ GARDER AUTO_BUY (pour les runners momentum)
  ✅ AJOUTER ELITE_WALLET (pour les runners avec baleines)
  → Plus de trades de qualité = Plus de x2

PROBLEME TECHNIQUE:
  Seuil whale actuel: $500 (= 2.5 SOL @ $200)
  → TROP ELEVÉ pour PumpFun (petits tokens)
  → whale_count toujours à 0

SOLUTION:
  Baisser seuil whale à $200 (= 1 SOL @ $200)
  → Détecte les achats de 1+ SOL comme baleines
  → ELITE_WALLET pourra se déclencher
""")

# Charger adaptive_params.json
with open('adaptive_params.json', 'r', encoding='utf-8') as f:
    params = json.load(f)

print('\n[CHANGEMENTS]')

# GARDER AUTO_BUY (ne rien changer)
print(f'\n✅ AUTO_BUY (INCHANGÉ):')
print(f'  Min TXN: {params["AUTO_BUY_MIN_TXN"]}')
print(f'  Min Traders: {params["AUTO_BUY_MIN_TRADERS"]}')
print(f'  Max MC: ${params["AUTO_BUY_MAX_MC"]:,}')

# ACTIVER ELITE_WALLET (baisser les seuils)
print(f'\n✅ ELITE_WALLET (AJUSTÉ):')
print(f'  AVANT: Min Whales = {params["ELITE_MIN_WHALE_COUNT"]}')
print(f'  APRES: Min Whales = 2 (baissé)')

print(f'  AVANT: Min Buy Ratio = {params["ELITE_MIN_BUY_RATIO"]*100:.0f}%')
print(f'  APRES: Min Buy Ratio = 75% (baissé)')

print(f'  AVANT: Max MC = ${params["ELITE_WALLET_MAX_MC"]:,}')
print(f'  APRES: Max MC = $10,000 (plus conservateur)')

# Ajuster les paramètres
params['ELITE_MIN_WHALE_COUNT'] = 2  # Au lieu de 3-4
params['ELITE_MIN_BUY_RATIO'] = 0.75  # Au lieu de 0.80-0.85
params['ELITE_WALLET_MAX_MC'] = 10000  # Au lieu de 12000

# AJOUTER un nouveau paramètre pour le seuil whale
if 'WHALE_MIN_AMOUNT_USD' not in params:
    params['WHALE_MIN_AMOUNT_USD'] = 200  # $200 = 1 SOL @ $200

print(f'\n✅ NOUVEAU SEUIL WHALE:')
print(f'  AVANT: $500 (2.5 SOL)')
print(f'  APRES: ${params["WHALE_MIN_AMOUNT_USD"]} (1 SOL)')

# Sauvegarder
with open('adaptive_params.json', 'w', encoding='utf-8') as f:
    json.dump(params, f, indent=2, ensure_ascii=False)

print('\n✅ Paramètres sauvegardés!')

print('\n' + '='*80)
print('RESULTAT ATTENDU:')
print('='*80)
print("""
Le bot va maintenant avoir 2 stratégies qui fonctionnent en PARALLELE:

📊 STRATEGIE 1: AUTO_BUY (momentum)
  → Achète si 25+ txn, 20+ traders, 70%+ buy ratio
  → Continue à donner des x2 comme avant

🐋 STRATEGIE 2: ELITE_WALLET (baleines)
  → Achète si 2+ achats de 1+ SOL détectés
  → Buy ratio 75%+, MC < $10K
  → PRIORITAIRE sur AUTO_BUY (exécute en premier)

RESULTAT:
  ✅ Plus de volume (AUTO_BUY continue)
  ✅ Plus de qualité (ELITE_WALLET s'ajoute)
  ✅ Plus de x2 attendus
""")

print('\n⚠️ MAIS IL FAUT AUSSI MODIFIER live_trading_bot.py:')
print('  Ligne 518: Changer le seuil whale de 500 à 200')
print('='*80)

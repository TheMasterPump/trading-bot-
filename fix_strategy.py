"""
FIX: Désactiver AUTO_BUY et forcer ELITE_WALLET + IA uniquement
Le problème: AUTO_BUY est trop permissif et entre sans whales
"""
import sys, codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import json

print('='*80)
print('FIX: DESACTIVER STRATEGIE AUTO_BUY')
print('='*80)

print("""
PROBLEME IDENTIFIE:
  Les 6 trades ont utilisé AUTO_BUY au lieu de ELITE_WALLET
  AUTO_BUY ne requiert PAS de whales
  → Entrées faibles qui perdent -30%

SOLUTION:
  1. DESACTIVER AUTO_BUY (mettre seuils impossibles)
  2. FORCER uniquement ELITE_WALLET + IA
  3. Baisser seuil whale de $500 à $300 (plus facile à détecter)
  4. Exiger minimum 2 whales au lieu de 3

CHANGEMENTS:
""")

# Charger adaptive_params.json
with open('adaptive_params.json', 'r', encoding='utf-8') as f:
    params = json.load(f)

print('\n[AVANT]')
print(f'  AUTO_BUY_MIN_TXN: {params["AUTO_BUY_MIN_TXN"]}')
print(f'  AUTO_BUY_MIN_TRADERS: {params["AUTO_BUY_MIN_TRADERS"]}')
print(f'  AUTO_BUY_MAX_MC: ${params["AUTO_BUY_MAX_MC"]:,}')
print(f'  ELITE_MIN_WHALE_COUNT: {params["ELITE_MIN_WHALE_COUNT"]}')

# DESACTIVER AUTO_BUY (seuils impossibles)
params['AUTO_BUY_MIN_TXN'] = 999  # Impossible
params['AUTO_BUY_MIN_TRADERS'] = 999  # Impossible
params['AUTO_BUY_MAX_MC'] = 1  # Impossible

# AJUSTER ELITE_WALLET (plus accessible)
params['ELITE_MIN_WHALE_COUNT'] = 2  # Au lieu de 3
params['ELITE_MIN_BUY_RATIO'] = 0.75  # Au lieu de 0.80
params['ELITE_WALLET_MAX_MC'] = 10000  # Max $10K (au lieu de $12K)

# AJUSTER IA (plus stricte)
params['AI_MIN_TXN'] = 30  # Au lieu de 20
params['AI_MIN_TRADERS'] = 25  # Au lieu de 20
params['AI_MIN_BUY_RATIO'] = 0.75  # Au lieu de 0.70
params['THRESHOLD_8S'] = 0.70  # Au lieu de 0.60

print('\n[APRES]')
print(f'  AUTO_BUY_MIN_TXN: {params["AUTO_BUY_MIN_TXN"]} (DESACTIVE)')
print(f'  AUTO_BUY_MIN_TRADERS: {params["AUTO_BUY_MIN_TRADERS"]} (DESACTIVE)')
print(f'  AUTO_BUY_MAX_MC: ${params["AUTO_BUY_MAX_MC"]:,} (DESACTIVE)')
print(f'  ELITE_MIN_WHALE_COUNT: {params["ELITE_MIN_WHALE_COUNT"]} (baissé à 2)')
print(f'  ELITE_MIN_BUY_RATIO: {params["ELITE_MIN_BUY_RATIO"]*100:.0f}%')
print(f'  ELITE_WALLET_MAX_MC: ${params["ELITE_WALLET_MAX_MC"]:,}')
print(f'  AI_MIN_TXN: {params["AI_MIN_TXN"]}')
print(f'  AI_MIN_TRADERS: {params["AI_MIN_TRADERS"]}')
print(f'  THRESHOLD_8S: {params["THRESHOLD_8S"]*100:.0f}%')

# Sauvegarder
with open('adaptive_params.json', 'w', encoding='utf-8') as f:
    json.dump(params, f, indent=2, ensure_ascii=False)

print('\n✅ Paramètres sauvegardés dans adaptive_params.json')

print('\n' + '='*80)
print('PROCHAINE ETAPE:')
print('='*80)
print("""
1. REDEMARRER le bot avec ces nouveaux paramètres
2. Le bot va maintenant:
   ✅ IGNORER les trades sans whales (AUTO_BUY désactivé)
   ✅ N'ACHETER que si 2+ whales détectés
   ✅ N'ACHETER que si IA >= 70% confiance

3. MAIS IL Y A ENCORE UN PROBLEME:
   Les whales sont détectés avec seuil $500 USD
   → Si aucun trade ne dépasse $500, whale_count reste à 0

   VERIFICATION NECESSAIRE:
   → Est-ce que l'API PumpFun retourne 'amount_usd' dans les trades?
   → Ou faut-il calculer amount_usd à partir de sol_amount * sol_price?

   Si amount_usd n'existe pas, il faut:
   1. Calculer amount_usd manuellement
   2. OU baisser le seuil whale à $200-$300
   3. OU utiliser sol_amount > 2 SOL comme critère
""")

print('='*80)
print('VEUX-TU:')
print('  A) Relancer le bot avec ces paramètres (AUTO_BUY désactivé)')
print('  B) D\'abord vérifier si amount_usd existe dans les trades')
print('  C) Baisser le seuil whale à $300 au lieu de $500')
print('='*80)

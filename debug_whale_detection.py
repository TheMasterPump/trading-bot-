"""
DEBUG: Vérifie ce que l'API retourne pour les montants d'achat
Pour comprendre pourquoi whale_count = 0
"""
import sys, codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

print('='*80)
print('DEBUG: DETECTION DES BALEINES')
print('='*80)

print("""
PROBLEME:
  Tous les trades enregistrés ont whale_count = 0
  Même avec seuil à $200 (1 SOL)

POSSIBILITES:
  1. Les tokens PumpFun n'ont vraiment pas de baleines (achats < 1 SOL)
  2. L'API ne retourne pas 'solAmount' correctement
  3. Le calcul amount_usd ne fonctionne pas

VERIFICATION:
  Il faut ajouter un LOG dans live_trading_bot.py pour afficher:
  - Les montants réels des achats (solAmount)
  - Le calcul amount_usd
  - Les whales détectées

MODIFICATION A FAIRE:
  Dans live_trading_bot.py, ligne ~518, après le calcul de whale_count,
  ajouter un print pour afficher:

  print(f'[DEBUG WHALE] Token {symbol}:')
  print(f'  Total buys: {len(buys)}')
  print(f'  Buy amounts (SOL): {[b.get("amount_sol", 0) for b in buys[-5:]]}')
  print(f'  Buy amounts (USD): {[b.get("amount_usd", 0) for b in buys[-5:]]}')
  print(f'  Whales detected (>=$400): {whale_count}')

  Ça permettra de voir:
  - Si solAmount existe dans l'API
  - Les montants réels des achats
  - Pourquoi whale_count = 0
""")

print('\n' + '='*80)
print('RECOMMANDATION:')
print('='*80)
print("""
OPTION 1: Garder seuil à $400-$600 (2-3 SOL)
  → Si vraies baleines seulement
  → Mais risque de whale_count toujours à 0 si petits achats
  → Stratégie ELITE_WALLET jamais déclenchée

OPTION 2: Baisser à $200-$300 (1-1.5 SOL) temporairement
  → Pour tester si la détection fonctionne
  → Voir si whale_count > 0
  → Ajuster ensuite selon résultats

OPTION 3: Ajouter DEBUG d'abord
  → Afficher les montants réels dans la console
  → Comprendre ce que l'API retourne
  → Ajuster le seuil intelligemment

JE RECOMMANDE OPTION 3: Ajouter les logs DEBUG d'abord!
""")

print('='*80)
print('Veux-tu que j\'ajoute ces logs de debug dans le bot ?')
print('(Ça affichera les montants réels des achats pour chaque token)')
print('='*80)

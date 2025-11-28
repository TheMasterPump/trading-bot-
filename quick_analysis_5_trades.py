"""
ANALYSE RAPIDE DES 5 PREMIERS TRADES
Identifie les problèmes critiques
"""
import sys, codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import json
import statistics

# Charger l'historique
with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data.get('trades', [])

print('='*80)
print('ANALYSE RAPIDE - 5 PREMIERS TRADES')
print('='*80)

print(f'\n📊 RESULTATS:')
print(f'  Total: {len(trades)} trades')
wins = [t for t in trades if t['is_win']]
losses = [t for t in trades if not t['is_win']]
print(f'  Wins: {len(wins)} (0%)')
print(f'  Losses: {len(losses)} (100%)')

print(f'\n🔍 ANALYSE DETAILLEE:')
print('='*80)

# Analyser chaque caractéristique
entry_mcs = [t['entry_mc'] for t in trades]
buy_ratios = [t['features']['buy_ratio'] for t in trades]
whale_counts = [t['features']['whale_count'] for t in trades]
elite_counts = [t['features']['elite_wallet_count'] for t in trades]
traders = [t['features']['traders'] for t in trades]
velocities = [t['features']['velocity'] for t in trades]

print(f'\n1. MARKET CAP D\'ENTREE:')
print(f'   Min: ${min(entry_mcs):,.0f}')
print(f'   Max: ${max(entry_mcs):,.0f}')
print(f'   Moyenne: ${statistics.mean(entry_mcs):,.0f}')
print(f'   → Toutes les entrées entre $9K-$11K')

print(f'\n2. BUY RATIO:')
print(f'   Min: {min(buy_ratios)*100:.1f}%')
print(f'   Max: {max(buy_ratios)*100:.1f}%')
print(f'   Moyenne: {statistics.mean(buy_ratios)*100:.1f}%')
print(f'   → Buy ratio semble BON (70-82%)')

print(f'\n3. ⚠️⚠️⚠️ WHALE COUNT (PROBLEME CRITIQUE):')
print(f'   Min: {min(whale_counts)}')
print(f'   Max: {max(whale_counts)}')
print(f'   Moyenne: {statistics.mean(whale_counts):.1f}')
print(f'   → TOUS LES TRADES ONT 0 WHALES !!!')

print(f'\n4. ELITE WALLET COUNT:')
print(f'   Min: {min(elite_counts)}')
print(f'   Max: {max(elite_counts)}')
print(f'   Moyenne: {statistics.mean(elite_counts):.1f}')
print(f'   → Aussi 0 partout')

print(f'\n5. TRADERS COUNT:')
print(f'   Min: {min(traders)}')
print(f'   Max: {max(traders)}')
print(f'   Moyenne: {statistics.mean(traders):.1f}')
print(f'   → Entre 21-34 traders par token')

print(f'\n6. VELOCITY:')
print(f'   Min: {min(velocities):.0f}')
print(f'   Max: {max(velocities):.0f}')
print(f'   Moyenne: {statistics.mean(velocities):.0f}')

# Analyser les sorties
exit_reasons = {}
for t in trades:
    reason = t['exit_reason']
    exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

print(f'\n7. RAISONS DE SORTIE:')
for reason, count in exit_reasons.items():
    print(f'   {reason}: {count}x')

print(f'\n8. PERTES MOYENNES:')
avg_loss = statistics.mean([t['profit_percent'] for t in trades])
print(f'   Perte moyenne: {avg_loss:.1f}%')
print(f'   → Toutes autour de -30% (stop loss)')

print('\n' + '='*80)
print('🚨 PROBLEME CRITIQUE IDENTIFIE:')
print('='*80)
print("""
Le bot entre dans des trades avec 0 WHALES !!!

NORMALEMENT, le bot devrait EXIGER:
  - 3+ whales pour stratégie ELITE_WALLET
  - Elite wallets détectés

MAIS LES 5 TRADES ONT:
  - whale_count = 0
  - elite_wallet_count = 0

CAUSES POSSIBLES:
1. La détection des whales ne fonctionne pas
   → Le seuil de whale est trop élevé
   → Aucune transaction ne dépasse le minimum

2. Le bot entre avec une AUTRE stratégie
   → Peut-être stratégie "MOMENTUM" ou "FAST_PROFIT"
   → Qui n'exige pas de whales

3. Les données de trades ne contiennent pas les montants
   → Impossible de détecter les gros achats

VERIFICATION IMMEDIATE NECESSAIRE:
""")

print('\n' + '='*80)
print('VERIFICATION:')
print('='*80)
print('\nVoyons le contenu d\'un trade pour comprendre...\n')

# Afficher la première trade complète
print('EXEMPLE - Premier trade (OTC):')
print(json.dumps(trades[0], indent=2, ensure_ascii=False))

print('\n' + '='*80)
print('RECOMMANDATIONS:')
print('='*80)
print("""
1. VERIFIER la détection des whales dans live_trading_bot.py
   → Regarder calculate_features()
   → Vérifier le seuil WHALE_MIN_AMOUNT

2. VERIFIER quelle stratégie est vraiment utilisée
   → Tous disent "PARTIAL_PROFIT" mais quelle était la RAISON d'entrée?
   → Est-ce vraiment ELITE_WALLET ou autre chose?

3. SI c'est bien ELITE_WALLET avec 0 whales:
   → Le code a un BUG critique
   → Il devrait REJETER ces trades

4. SOLUTION IMMEDIATE:
   → Baisser le seuil WHALE_MIN_AMOUNT
   → OU désactiver temporairement stratégie ELITE_WALLET
   → OU utiliser une autre stratégie qui fonctionne
""")

print('='*80)

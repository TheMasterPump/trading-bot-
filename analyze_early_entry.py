import json
import statistics

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

runners = d.get('runners', [])
migrated_runners = [r for r in runners if r.get('migration_detected')]

# Fast migrants
SNAPSHOTS = ['10s', '15s', '20s', '30s', '1min', '2min', '3min']
fast_migrants = []
for runner in migrated_runners:
    last_snapshot = None
    for snap in reversed(SNAPSHOTS):
        if snap in runner and runner[snap] and len(runner[snap]) > 0:
            last_snapshot = snap
            break
    if last_snapshot in SNAPSHOTS:
        fast_migrants.append(runner)

print('='*80)
print('ANALYSE: QUAND LES TOKENS ATTEIGNENT 10K et 15K MC')
print('='*80)

# Analyser à quel moment ils atteignent ces seuils
reached_10k_at = []
reached_15k_at = []

for token in fast_migrants:
    symbol = token.get('symbol', 'N/A')

    # Parcourir les snapshots pour trouver quand MC dépasse 10K et 15K
    moment_10k = None
    moment_15k = None

    for snap in SNAPSHOTS:
        snap_data = token.get(snap, {})
        if snap_data:
            mc = snap_data.get('mc', 0)

            # Premier moment où MC >= 10K
            if mc >= 10000 and moment_10k is None:
                moment_10k = snap
                reached_10k_at.append(snap)

            # Premier moment où MC >= 15K
            if mc >= 15000 and moment_15k is None:
                moment_15k = snap
                reached_15k_at.append(snap)

print(f'\n[QUAND LES FAST MIGRANTS ATTEIGNENT 10K MC]')
if reached_10k_at:
    from collections import Counter
    counts_10k = Counter(reached_10k_at)
    for snap in ['10s', '15s', '20s', '30s']:
        count = counts_10k.get(snap, 0)
        if count > 0:
            pct = (count / len(reached_10k_at)) * 100
            print(f'  {snap:6}: {count:3} tokens ({pct:5.1f}%)')

print(f'\n[QUAND LES FAST MIGRANTS ATTEIGNENT 15K MC]')
if reached_15k_at:
    from collections import Counter
    counts_15k = Counter(reached_15k_at)
    for snap in ['10s', '15s', '20s', '30s']:
        count = counts_15k.get(snap, 0)
        if count > 0:
            pct = (count / len(reached_15k_at)) * 100
            print(f'  {snap:6}: {count:3} tokens ({pct:5.1f}%)')

print('\n' + '='*80)
print('REPONSE: COMMENT ENTRER A 10-15K MC')
print('='*80)

print(f'''
[PROBLEME]
La plupart des tokens atteignent 10K-15K MC AVANT les 10 secondes!
Ton bot enregistre le premier snapshot a 10s, donc c'est trop tard.

[SOLUTIONS POUR ENTRER A 10-15K MC]

1. MODIFIER LE BOT pour capturer des snapshots plus precoces:
   - Ajouter snapshot @ 5 secondes
   - Ajouter snapshot @ 3 secondes
   - Detecter le token DES SA CREATION (0-2 secondes)

2. ENTRER IMMEDIATEMENT a la creation du token:
   - Surveiller les nouveaux tokens sur PumpFun WebSocket
   - Entrer SANS ATTENDRE les signaux (tres risque!)
   - Entrer systematiquement sur TOUS les tokens

3. UTILISER DES SIGNAUX "PRE-LAUNCH":
   - Detecter les tokens AVANT qu'ils soient lances
   - Analyser le createur (wallet historique)
   - Verifier si le createur a lance des runners avant

4. STRATEGIE HYBRIDE (RECOMMANDEE):
   - Entrer petit montant @ creation (5-10s si MC < 15K)
   - Attendre signaux @ 10s
   - Si signaux OK: DOUBLER la position
   - Si signaux NOK: SORTIR immediatement

[RISQUES D'ENTRER SI TOT]
- Pas de donnees pour confirmer
- Beaucoup de faux positifs (99% des tokens sont des flops)
- Besoin de capital important (entrer sur beaucoup de tokens)
- Necessite un bot 100% automatique

[RECOMMANDATION]
Pour entrer a 10-15K MC, tu DOIS:
1. Modifier le bot pour capturer snapshots a 3s et 5s
2. Creer un bot de trading automatique
3. Accepter un taux d'echec eleve (90%+)
4. Faire du "spray and pray" (entrer sur beaucoup, garder les winners)

Veux-tu que je modifie le bot pour ajouter des snapshots plus precoces?
''')

print('='*80)

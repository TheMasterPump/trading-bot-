"""
Analyse la qualite des donnees collectees @ 10s
Filtre les tokens pour ne garder que ceux avec des donnees completes
"""
import json
import pandas as pd

print('='*80)
print('ANALYSE DE LA QUALITE DES DONNEES @ 10 SECONDES')
print('='*80)

# Charger bot_data.json
with open('bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

runners = data.get('runners', [])
flops = data.get('flops', [])

print(f'\nDonnees brutes:')
print(f'  Runners: {len(runners)}')
print(f'  Flops: {len(flops)}')
print(f'  Total: {len(runners) + len(flops)}')

# Fonction pour verifier si les donnees @ 10s sont completes
def has_complete_10s_data(token):
    """Verifie qu'un token a des donnees completes @ 10s"""
    snap_10s = token.get('10s', {})

    if not snap_10s:
        return False, "Pas de snapshot @ 10s"

    # Verifier que toutes les features essentielles sont presentes
    # Note: velocity n'est pas toujours presente, c'est OK
    required_fields = ['txn', 'traders', 'buy_ratio', 'mc']
    for field in required_fields:
        if field not in snap_10s:
            return False, f"Champ manquant: {field}"

        value = snap_10s.get(field)
        if value is None:
            return False, f"Valeur None: {field}"

    # Verifier que les valeurs sont coherentes
    txn = snap_10s.get('txn', 0)
    traders = snap_10s.get('traders', 0)
    mc = snap_10s.get('mc', 0)

    # Doit avoir au moins quelques transactions pour etre valide
    if txn < 1:
        return False, "Pas de transactions"

    # MC doit etre > 0
    if mc <= 0:
        return False, "MC invalide"

    # Traders ne peut pas etre > transactions
    if traders > txn:
        return False, "traders > txn (incoherent)"

    return True, "OK"

# Analyser les runners
print('\n' + '-'*80)
print('ANALYSE DES RUNNERS')
print('-'*80)

valid_runners = []
invalid_runners = []

for runner in runners:
    is_valid, reason = has_complete_10s_data(runner)
    if is_valid:
        valid_runners.append(runner)
    else:
        invalid_runners.append((runner, reason))

print(f'\nRunners valides: {len(valid_runners)}/{len(runners)}')
print(f'Runners invalides: {len(invalid_runners)}/{len(runners)}')

if invalid_runners:
    print(f'\nRaisons des rejets (premiers 10):')
    reasons_count = {}
    for _, reason in invalid_runners[:10]:
        reasons_count[reason] = reasons_count.get(reason, 0) + 1
    for reason, count in sorted(reasons_count.items(), key=lambda x: x[1], reverse=True):
        print(f'  - {reason}: {count}')

# Analyser les flops
print('\n' + '-'*80)
print('ANALYSE DES FLOPS')
print('-'*80)

valid_flops = []
invalid_flops = []

for flop in flops:
    is_valid, reason = has_complete_10s_data(flop)
    if is_valid:
        valid_flops.append(flop)
    else:
        invalid_flops.append((flop, reason))

print(f'\nFlops valides: {len(valid_flops)}/{len(flops)}')
print(f'Flops invalides: {len(invalid_flops)}/{len(flops)}')

if invalid_flops:
    print(f'\nRaisons des rejets (top 5):')
    reasons_count = {}
    for _, reason in invalid_flops:
        reasons_count[reason] = reasons_count.get(reason, 0) + 1
    for reason, count in sorted(reasons_count.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f'  - {reason}: {count}')

# Statistiques finales
print('\n' + '='*80)
print('RESUME')
print('='*80)
print(f'\nDonnees valides @ 10s:')
print(f'  Runners: {len(valid_runners)} ({len(valid_runners)/len(runners)*100:.1f}%)')
print(f'  Flops: {len(valid_flops)} ({len(valid_flops)/len(flops)*100:.1f}%)')
print(f'  Total: {len(valid_runners) + len(valid_flops)}')

print(f'\nDonnees rejetees:')
print(f'  Runners: {len(invalid_runners)} ({len(invalid_runners)/len(runners)*100:.1f}%)')
print(f'  Flops: {len(invalid_flops)} ({len(invalid_flops)/len(flops)*100:.1f}%)')
print(f'  Total: {len(invalid_runners) + len(invalid_flops)}')

# Afficher des statistiques sur les donnees valides
if valid_runners:
    print(f'\n[STATISTIQUES RUNNERS VALIDES]')
    runner_txns = [r['10s']['txn'] for r in valid_runners]
    runner_mcs = [r['10s']['mc'] for r in valid_runners]
    print(f'  Transactions @ 10s: min={min(runner_txns)}, max={max(runner_txns)}, moy={sum(runner_txns)/len(runner_txns):.1f}')
    print(f'  Market Cap @ 10s: min=${min(runner_mcs):,.0f}, max=${max(runner_mcs):,.0f}, moy=${sum(runner_mcs)/len(runner_mcs):,.0f}')

if valid_flops:
    print(f'\n[STATISTIQUES FLOPS VALIDES]')
    flop_txns = [f['10s']['txn'] for f in valid_flops]
    flop_mcs = [f['10s']['mc'] for f in valid_flops]
    print(f'  Transactions @ 10s: min={min(flop_txns)}, max={max(flop_txns)}, moy={sum(flop_txns)/len(flop_txns):.1f}')
    print(f'  Market Cap @ 10s: min=${min(flop_mcs):,.0f}, max=${max(flop_mcs):,.0f}, moy=${sum(flop_mcs)/len(flop_mcs):,.0f}')

print('\n' + '='*80)
print('RECOMMANDATION')
print('='*80)

if len(valid_runners) >= 50 and len(valid_flops) >= 100:
    print('\n[OK] Assez de donnees valides pour entrainer un bon modele!')
    print(f'Dataset final: {len(valid_runners)} runners + {len(valid_flops)} flops = {len(valid_runners) + len(valid_flops)} tokens')
else:
    print('\n[ATTENTION] Pas assez de donnees valides!')
    if len(valid_runners) < 50:
        print(f'  - Seulement {len(valid_runners)} runners valides (recommande: 50+)')
    if len(valid_flops) < 100:
        print(f'  - Seulement {len(valid_flops)} flops valides (recommande: 100+)')
    print('\nIl faut collecter plus de donnees avant d\'entrainer.')

print('='*80)

import json
import statistics

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

runners = d.get('runners', [])
migrated_runners = [r for r in runners if r.get('migration_detected')]

# Fast migrants
SNAPSHOTS = ['10s', '15s', '20s', '30s', '1min', '2min', '3min', '5min', '8min', '10min', '15min']
fast_migrants = []
for runner in migrated_runners:
    last_snapshot = None
    for snap in reversed(SNAPSHOTS):
        if snap in runner and runner[snap] and len(runner[snap]) > 0:
            last_snapshot = snap
            break
    if last_snapshot in ['10s', '15s', '20s', '30s', '1min', '2min', '3min']:
        fast_migrants.append(runner)

print('='*80)
print('EVOLUTION DU PRIX: 10s vs 15s (Fast Migrants)')
print('='*80)

mc_10s = []
mc_15s = []
gains = []

for token in fast_migrants:
    snap_10s = token.get('10s', {})
    snap_15s = token.get('15s', {})

    if snap_10s and snap_15s:
        mc_10 = snap_10s.get('mc', 0)
        mc_15 = snap_15s.get('mc', 0)

        if mc_10 > 0 and mc_15 > 0:
            mc_10s.append(mc_10)
            mc_15s.append(mc_15)
            gain_pct = ((mc_15 - mc_10) / mc_10) * 100
            gains.append(gain_pct)

print(f'\n[MARKET CAP]')
print(f'  @ 10s: Moyenne=${statistics.mean(mc_10s):,.0f} | Mediane=${statistics.median(mc_10s):,.0f}')
print(f'  @ 15s: Moyenne=${statistics.mean(mc_15s):,.0f} | Mediane=${statistics.median(mc_15s):,.0f}')

print(f'\n[AUGMENTATION ENTRE 10s et 15s]')
print(f'  Gain moyen: +{statistics.mean(gains):.1f}%')
print(f'  Gain median: +{statistics.median(gains):.1f}%')

# Calculer combien tu perds en attendant 15s au lieu de 11s
print(f'\n[IMPACT PRIX SI TU ENTRES A 11s vs 15s]')
mc_median_10s = statistics.median(mc_10s)
mc_median_15s = statistics.median(mc_15s)
diff = mc_median_15s - mc_median_10s

# Estimation lineaire du prix a 11s (1/5 du chemin entre 10s et 15s)
mc_estimated_11s = mc_median_10s + (diff * 0.2)  # 1 sec sur 5 = 20%

print(f'  Prix median @ 10s: ${mc_median_10s:,.0f}')
print(f'  Prix estime @ 11s: ${mc_estimated_11s:,.0f} (+{((mc_estimated_11s-mc_median_10s)/mc_median_10s)*100:.1f}%)')
print(f'  Prix median @ 15s: ${mc_median_15s:,.0f} (+{((mc_median_15s-mc_median_10s)/mc_median_10s)*100:.1f}%)')

print(f'\n[PROFIT POTENTIEL (jusqu a migration $69K)]')
profit_11s = (69000 / mc_estimated_11s)
profit_15s = (69000 / mc_median_15s)
diff_profit = profit_11s - profit_15s

print(f'  Entree @ 11s: {profit_11s:.2f}x')
print(f'  Entree @ 15s: {profit_15s:.2f}x')
print(f'  Difference:   +{diff_profit:.2f}x ({(diff_profit/profit_15s)*100:.1f}% de profit en plus!)')

print('\n' + '='*80)
print('REPONSE: OUI, ENTRE A 11s!')
print('='*80)
print(f'''
Si les signaux a 10s sont TOUS confirmes:
- Transactions >= 22
- Traders >= 19
- Buy Ratio >= 75%
- MC >= $18K

=> TU PEUX ENTRER DES 11 SECONDES!

Avantage: +{(diff_profit/profit_15s)*100:.1f}% de profit supplementaire
Plus tu entres tot, meilleur est ton prix d'entree.

MAIS ATTENTION:
- Il faut que TOUS les signaux soient vraiment confirmes a 10s
- La transaction prendra 1-2 secondes a s'executer (tu entreras vers 12-13s)
- Si tu as un doute, attends 15s pour plus de securite
''')

print('='*80)

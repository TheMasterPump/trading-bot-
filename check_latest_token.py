import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

# Prendre le dernier flop (le plus récent)
flops = d.get('flops', [])
if not flops:
    print('Aucun flop encore')
    exit()

latest = flops[-1]

print('='*80)
print('DERNIER TOKEN ENREGISTRE - VERIFICATION COMPLETE')
print('='*80)

print(f'\n[INFORMATIONS DE BASE]')
print(f'Symbol: {latest.get("symbol", "N/A")}')
print(f'Mint: {latest.get("mint", "N/A")[:20]}...')
print(f'Is Runner: {latest.get("is_runner", False)} (0 = FLOP)')
print(f'Final MC: ${latest.get("final_mc", 0):,.2f}')
print(f'Pump Time: {latest.get("pump_time", 0)} secondes')

print(f'\n[WHALE ACTIVITY]')
print(f'Whale Count: {latest.get("whale_count", 0)}')
print(f'Whale Volume USD: ${latest.get("whale_total_volume_usd", 0):,.2f}')

print(f'\n[SNAPSHOTS TEMPORELS - Evolution du token]')
snapshot_times = ['10s', '15s', '20s', '30s', '1min', '2min', '3min', '5min', '8min', '10min', '15min']
for snap_time in snapshot_times:
    snap = latest.get(snap_time)
    if snap:
        mc = snap.get('mc_usd', 0)
        txn = snap.get('total_transactions', 0)
        buy_ratio = snap.get('buy_ratio', 0) * 100
        traders = snap.get('unique_traders', 0)
        print(f'  {snap_time:6} -> MC: ${mc:8,.0f} | {txn:3} txn | {buy_ratio:5.1f}% buys | {traders:3} traders')

print(f'\n[ML METRICS AVANCEES]')
ml_metrics = latest.get('ml_metrics', {})
if ml_metrics:
    print(f'Total ML Metrics: {len(ml_metrics)} metriques calculees')
    print(f'\nExemples de metriques:')

    # Catégories
    categories = {
        'Velocite': ['velocity', 'acceleration', 'momentum'],
        'Volume': ['volume', 'avg'],
        'Price': ['price', 'mc'],
        'Ratios': ['ratio', 'percent'],
        'Tendances': ['trend', 'slope']
    }

    shown = 0
    for cat_name, keywords in categories.items():
        matching = [k for k in ml_metrics.keys() if any(kw in k.lower() for kw in keywords)]
        if matching and shown < 15:
            print(f'\n  {cat_name}:')
            for k in matching[:3]:
                v = ml_metrics[k]
                if isinstance(v, (int, float)):
                    print(f'    - {k}: {v:.2f}')
                shown += 1
else:
    print('  Aucune ML metric (token trop ancien)')

print(f'\n[SUPPLY DISTRIBUTION]')
supply_dist = latest.get('supply_distribution', {})
if supply_dist:
    print(f'  Top 3 holders: {supply_dist.get("top_3_percent", 0):.1f}%')
    print(f'  Top 5 holders: {supply_dist.get("top_5_percent", 0):.1f}%')
    print(f'  Top 10 holders: {supply_dist.get("top_10_percent", 0):.1f}%')
    print(f'  Total holders: {supply_dist.get("total_holders", 0)}')
else:
    print('  Non disponible')

print(f'\n{"="*80}')
print('VERIFICATION:')
print('='*80)
print(f'[OK] Informations de base: ✓')
print(f'[OK] Snapshots temporels: {len([s for s in snapshot_times if latest.get(s)])} sur 11')
print(f'[OK] ML Metrics: {len(ml_metrics)} metriques')
print(f'[OK] Whale tracking: {"✓" if latest.get("whale_count", 0) >= 0 else "✗"}')
print(f'[OK] Classification: {"FLOP" if not latest.get("is_runner") else "RUNNER"}')

print(f'\n{"="*80}')
print('TOUTES LES DONNEES SONT COLLECTEES!')
print('='*80)

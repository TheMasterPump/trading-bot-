"""
Compare TXN et TRADERS entre RUNNERS vs FLOPS
"""
import json
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data['trades']

print('='*80)
print('COMPARAISON TXN & TRADERS: RUNNERS vs FLOPS')
print('='*80)

# Séparer
migrations = [t for t in trades if t.get('exit_mc', 0) >= 53000]
losses = [t for t in trades if not t.get('is_win', False)]

print(f'\n📊 DATASET:')
print(f'   Migrations: {len(migrations)} trades')
print(f'   Losses: {len(losses)} trades')

# TXN - MIGRATIONS
txn_migrations = [t.get('features', {}).get('txn', 0) for t in migrations if t.get('features', {}).get('txn', 0) > 0]
if txn_migrations:
    avg_txn_m = sum(txn_migrations) / len(txn_migrations)
    min_txn_m = min(txn_migrations)
    max_txn_m = max(txn_migrations)
    
print(f'\n{'='*80}')
print(f'💱 TRANSACTIONS (TXN)')
print('='*80)

print(f'\n🚀 MIGRATIONS:')
print(f'   Moyenne: {avg_txn_m:.0f}')
print(f'   Range: {min_txn_m}-{max_txn_m}')

# TXN - LOSSES
txn_losses = [t.get('features', {}).get('txn', 0) for t in losses if t.get('features', {}).get('txn', 0) > 0]
if txn_losses:
    avg_txn_l = sum(txn_losses) / len(txn_losses)
    min_txn_l = min(txn_losses)
    max_txn_l = max(txn_losses)
    
print(f'\n❌ LOSSES:')
print(f'   Moyenne: {avg_txn_l:.0f}')
print(f'   Range: {min_txn_l}-{max_txn_l}')

print(f'\n📊 DIFFÉRENCE:')
diff_txn = avg_txn_m - avg_txn_l
pct_diff_txn = (diff_txn / avg_txn_l * 100) if avg_txn_l > 0 else 0
if diff_txn > 0:
    print(f'   Migrations ont {diff_txn:.0f} txn de PLUS ({pct_diff_txn:+.1f}%)')
else:
    print(f'   Migrations ont {abs(diff_txn):.0f} txn de MOINS ({pct_diff_txn:.1f}%)')

# TRADERS - MIGRATIONS
traders_migrations = [t.get('features', {}).get('traders', 0) for t in migrations if t.get('features', {}).get('traders', 0) > 0]
if traders_migrations:
    avg_traders_m = sum(traders_migrations) / len(traders_migrations)
    min_traders_m = min(traders_migrations)
    max_traders_m = max(traders_migrations)

print(f'\n{'='*80}')
print(f'👥 TRADERS UNIQUES')
print('='*80)

print(f'\n🚀 MIGRATIONS:')
print(f'   Moyenne: {avg_traders_m:.0f}')
print(f'   Range: {min_traders_m}-{max_traders_m}')

# TRADERS - LOSSES
traders_losses = [t.get('features', {}).get('traders', 0) for t in losses if t.get('features', {}).get('traders', 0) > 0]
if traders_losses:
    avg_traders_l = sum(traders_losses) / len(traders_losses)
    min_traders_l = min(traders_losses)
    max_traders_l = max(traders_losses)

print(f'\n❌ LOSSES:')
print(f'   Moyenne: {avg_traders_l:.0f}')
print(f'   Range: {min_traders_l}-{max_traders_l}')

print(f'\n📊 DIFFÉRENCE:')
diff_traders = avg_traders_m - avg_traders_l
pct_diff_traders = (diff_traders / avg_traders_l * 100) if avg_traders_l > 0 else 0
if diff_traders > 0:
    print(f'   Migrations ont {diff_traders:.0f} traders de PLUS ({pct_diff_traders:+.1f}%)')
else:
    print(f'   Migrations ont {abs(diff_traders):.0f} traders de MOINS ({pct_diff_traders:.1f}%)')

# Répartition TXN
print(f'\n{'='*80}')
print(f'RÉPARTITION TXN')
print('='*80)

ranges_txn = {
    '< 25': (0, 25),
    '25-35': (25, 35),
    '35-45': (35, 45),
    '> 45': (45, 999)
}

print(f'\n🚀 MIGRATIONS:')
for range_name, (min_t, max_t) in ranges_txn.items():
    count = len([t for t in txn_migrations if min_t <= t < max_t])
    pct = (count / len(txn_migrations) * 100) if txn_migrations else 0
    print(f'   {range_name}: {count}/{len(txn_migrations)} ({pct:.0f}%)')

print(f'\n❌ LOSSES:')
for range_name, (min_t, max_t) in ranges_txn.items():
    count = len([t for t in txn_losses if min_t <= t < max_t])
    pct = (count / len(txn_losses) * 100) if txn_losses else 0
    print(f'   {range_name}: {count}/{len(txn_losses)} ({pct:.0f}%)')

# Répartition TRADERS
print(f'\n{'='*80}')
print(f'RÉPARTITION TRADERS')
print('='*80)

ranges_traders = {
    '< 20': (0, 20),
    '20-25': (20, 25),
    '25-30': (25, 30),
    '> 30': (30, 999)
}

print(f'\n🚀 MIGRATIONS:')
for range_name, (min_t, max_t) in ranges_traders.items():
    count = len([t for t in traders_migrations if min_t <= t < max_t])
    pct = (count / len(traders_migrations) * 100) if traders_migrations else 0
    print(f'   {range_name}: {count}/{len(traders_migrations)} ({pct:.0f}%)')

print(f'\n❌ LOSSES:')
for range_name, (min_t, max_t) in ranges_traders.items():
    count = len([t for t in traders_losses if min_t <= t < max_t])
    pct = (count / len(traders_losses) * 100) if traders_losses else 0
    print(f'   {range_name}: {count}/{len(traders_losses)} ({pct:.0f}%)')

# RECOMMANDATIONS
print(f'\n{'='*80}')
print('🎯 RECOMMANDATIONS')
print('='*80)

print(f'\n💱 TXN:')
print(f'   Migrations: {avg_txn_m:.0f} en moyenne')
print(f'   Losses: {avg_txn_l:.0f} en moyenne')
if abs(diff_txn) < 5:
    print(f'   → PAS DE GRANDE DIFFÉRENCE')
elif diff_txn > 0:
    print(f'   → Migrations ont MOINS de txn (volume plus modéré)')
    print(f'   → RECOMMANDATION: Baisser AUTO_BUY_MAX_TXN')
else:
    print(f'   → Migrations ont PLUS de txn (plus de volume)')
    print(f'   → RECOMMANDATION: Augmenter AUTO_BUY_MIN_TXN')

print(f'\n👥 TRADERS:')
print(f'   Migrations: {avg_traders_m:.0f} en moyenne')
print(f'   Losses: {avg_traders_l:.0f} en moyenne')
if abs(diff_traders) < 3:
    print(f'   → PAS DE GRANDE DIFFÉRENCE')
elif diff_traders > 0:
    print(f'   → Migrations ont MOINS de traders')
    print(f'   → RECOMMANDATION: Baisser AUTO_BUY_MAX_TRADERS')
else:
    print(f'   → Migrations ont PLUS de traders')
    print(f'   → RECOMMANDATION: Augmenter AUTO_BUY_MIN_TRADERS')

print(f'\n{'='*80}')

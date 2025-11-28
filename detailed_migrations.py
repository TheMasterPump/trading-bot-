"""
Analyse ULTRA DÉTAILLÉE de chaque migration
Tous les paramètres pour optimiser le bot
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
print('ANALYSE ULTRA DÉTAILLÉE - CHAQUE MIGRATION')
print('='*80)

# Filtrer migrations
migrations = [t for t in trades if t.get('exit_mc', 0) >= 53000]

print(f'\n🚀 {len(migrations)} MIGRATIONS TROUVÉES\n')

if len(migrations) == 0:
    print('❌ AUCUNE MIGRATION!')
    exit(0)

# Analyser chaque migration en détail
for i, m in enumerate(sorted(migrations, key=lambda x: x.get('profit_percent', 0), reverse=True), 1):
    features = m.get('features', {})
    
    print('='*80)
    print(f'MIGRATION #{i}: {m.get("symbol")} - +{m.get("profit_percent", 0):.1f}%')
    print('='*80)
    
    print(f'\n📍 PRIX & MC:')
    print(f'   Entry MC: ${m.get("entry_mc", 0):,.0f}')
    print(f'   Exit MC: ${m.get("exit_mc", 0):,.0f}')
    print(f'   Ratio: {m.get("profit_ratio", 0):.2f}x')
    
    print(f'\n⏱️ TIMING:')
    print(f'   Acheté @ {m.get("entry_time", "?")}')
    print(f'   Durée: {m.get("timeout_minutes", 0):.0f} min')
    
    print(f'\n💱 TRANSACTIONS:')
    print(f'   Total TXN: {features.get("txn", 0)}')
    print(f'   Buys: {features.get("buys", 0)}')
    print(f'   Sells: {features.get("sells", 0)}')
    
    print(f'\n👥 TRADERS:')
    print(f'   Traders uniques: {features.get("traders", 0)}')
    print(f'   Ratio TXN/Trader: {features.get("txn", 0) / features.get("traders", 1):.2f}')
    
    print(f'\n📈 BUY PRESSURE:')
    buy_ratio = features.get("buy_ratio", 0)
    print(f'   Buy ratio: {buy_ratio*100:.1f}%')
    print(f'   Buys: {features.get("buys", 0)} vs Sells: {features.get("sells", 0)}')
    
    print(f'\n🐋 BALEINES:')
    whale_count = features.get("whale_count", 0)
    print(f'   Whale count: {whale_count}')
    
    print(f'\n🚀 MOMENTUM:')
    print(f'   Velocity: {features.get("velocity", 0):.2f}')
    
    print(f'\n👑 ELITE WALLETS:')
    elite_count = features.get("elite_wallet_count", 0)
    print(f'   Elite count: {elite_count}')
    if features.get("elite_wallets"):
        print(f'   Wallets: {", ".join(features.get("elite_wallets", [])[:3])}')
    
    print(f'\n📊 RAISON D\'ACHAT:')
    print(f'   Entry reason: {m.get("entry_reason", m.get("reason", "N/A"))}')
    print(f'   Confidence: {m.get("confidence", 0)*100:.0f}%')
    print(f'   Strategy: {m.get("strategy", "N/A")}')
    
    print(f'\n🚪 RAISON DE SORTIE:')
    print(f'   Exit reason: {m.get("exit_reason", "N/A")}')
    print(f'   Partial sold: {m.get("partial_sold", False)}')
    
    print()

# SYNTHÈSE - RANGES MIN/MAX
print('='*80)
print('📊 SYNTHÈSE - RANGES MIN/MAX DE TOUTES LES MIGRATIONS')
print('='*80)

# Extraire toutes les valeurs
all_features = [m.get('features', {}) for m in migrations]

txns = [f.get('txn', 0) for f in all_features if f.get('txn', 0) > 0]
traders = [f.get('traders', 0) for f in all_features if f.get('traders', 0) > 0]
buy_ratios = [f.get('buy_ratio', 0) for f in all_features if f.get('buy_ratio', 0) > 0]
whales = [f.get('whale_count', 0) for f in all_features]
velocities = [f.get('velocity', 0) for f in all_features if f.get('velocity', 0) > 0]
entry_mcs = [m.get('entry_mc', 0) for m in migrations]

print(f'\n📍 MC ENTRÉE:')
print(f'   Min: ${min(entry_mcs):,.0f}')
print(f'   Max: ${max(entry_mcs):,.0f}')
print(f'   Moyenne: ${sum(entry_mcs)/len(entry_mcs):,.0f}')

print(f'\n💱 TRANSACTIONS:')
print(f'   Min: {min(txns)}')
print(f'   Max: {max(txns)}')
print(f'   Moyenne: {sum(txns)/len(txns):.0f}')

print(f'\n👥 TRADERS:')
print(f'   Min: {min(traders)}')
print(f'   Max: {max(traders)}')
print(f'   Moyenne: {sum(traders)/len(traders):.0f}')

print(f'\n📈 BUY RATIO:')
print(f'   Min: {min(buy_ratios)*100:.0f}%')
print(f'   Max: {max(buy_ratios)*100:.0f}%')
print(f'   Moyenne: {sum(buy_ratios)/len(buy_ratios)*100:.0f}%')

print(f'\n🐋 BALEINES:')
print(f'   Min: {min(whales)}')
print(f'   Max: {max(whales)}')
print(f'   Moyenne: {sum(whales)/len(whales):.2f}')

if velocities:
    print(f'\n🚀 VELOCITY:')
    print(f'   Min: {min(velocities):.0f}')
    print(f'   Max: {max(velocities):.0f}')
    print(f'   Moyenne: {sum(velocities)/len(velocities):.0f}')

# Ratio TXN/Trader
ratios = [txns[i] / traders[i] if traders[i] > 0 else 0 for i in range(len(txns))]
print(f'\n📊 RATIO TXN/TRADER:')
print(f'   Min: {min(ratios):.2f}')
print(f'   Max: {max(ratios):.2f}')
print(f'   Moyenne: {sum(ratios)/len(ratios):.2f}')

# RECOMMANDATIONS FINALES
print(f'\n{'='*80}')
print('🎯 PARAMÈTRES OPTIMAUX POUR MIGRATIONS')
print('='*80)

print(f'\n✅ FILTRES À APPLIQUER:')
print(f'\n   MC:')
print(f'      MIN: ${min(entry_mcs):,.0f} (ou 8K pour sécurité)')
print(f'      MAX: ${max(entry_mcs):,.0f} (ou 18K pour capturer tous)')

print(f'\n   TRANSACTIONS:')
print(f'      MIN: {min(txns)} txn')
print(f'      MAX: {max(txns)} txn (éviter > 40 = bots)')

print(f'\n   TRADERS:')
print(f'      MIN: {min(traders)} traders')
print(f'      MAX: {max(traders)} traders (éviter > 30)')

print(f'\n   BUY RATIO:')
print(f'      MIN: {min(buy_ratios)*100:.0f}% (CRITIQUE!)')

print(f'\n   BALEINES:')
print(f'      MAX: {max(whales)} baleines (100% migrations = 0 baleines!)')

print(f'\n   RATIO TXN/TRADER:')
print(f'      MAX: {max(ratios):.1f} (éviter wash trading)')

print(f'\n{'='*80}')

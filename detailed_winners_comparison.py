"""
Analyse ultra-détaillée: Tous les winners IA vs AUTO-BUY
Avec TOUTES les caractéristiques de chaque trade
"""
import json
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Charger l'historique
with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data['trades'][-98:]  # Les 98 derniers

print('='*80)
print('ANALYSE ULTRA-DÉTAILLÉE: TOUS LES WINNERS (98 derniers trades)')
print('='*80)

# Séparer IA vs AUTO-BUY
ia_wins = []
autobuy_wins = []

for t in trades:
    if not t.get('is_win', False):
        continue

    reason = t.get('entry_reason', t.get('reason', 'Unknown'))
    if 'IA' in reason or 'AI' in reason:
        ia_wins.append(t)
    elif 'AUTO-BUY' in reason:
        autobuy_wins.append(t)

print(f'\nTotal winners: {len(ia_wins) + len(autobuy_wins)}')
print(f'  IA: {len(ia_wins)} winners')
print(f'  AUTO-BUY: {len(autobuy_wins)} winners')

# ============================================================================
# TOUS LES WINNERS IA
# ============================================================================
print(f'\n{"="*80}')
print(f'TOUS LES {len(ia_wins)} WINNERS IA (détails complets)')
print('='*80)

if ia_wins:
    for i, t in enumerate(ia_wins, 1):
        f = t.get('features', {})
        reason = t.get('entry_reason', 'N/A')
        confidence = 'N/A'
        if 'IA:' in reason:
            parts = reason.split('IA:')[1].strip()
            confidence = parts.split('%')[0] + '%'

        print(f'\n{i}. {t.get("symbol")}: +{t.get("profit_percent", 0):.1f}%')
        print(f'   Entry MC: ${t.get("entry_mc", 0):,.0f}')
        print(f'   Exit MC: ${t.get("exit_mc", 0):,.0f}')
        print(f'   IA Confidence: {confidence}')
        print(f'   TXN: {f.get("txn", 0)}')
        print(f'   Traders: {f.get("traders", 0)}')
        print(f'   Buy Ratio: {f.get("buy_ratio", 0)*100:.0f}%')
        print(f'   Whales: {f.get("whale_count", 0)}')
        print(f'   Exit reason: {t.get("exit_reason", "N/A")}')
else:
    print('\nAucun winner IA')

# ============================================================================
# TOUS LES WINNERS AUTO-BUY
# ============================================================================
print(f'\n{"="*80}')
print(f'TOUS LES {len(autobuy_wins)} WINNERS AUTO-BUY (détails complets)')
print('='*80)

if autobuy_wins:
    for i, t in enumerate(autobuy_wins, 1):
        f = t.get('features', {})

        print(f'\n{i}. {t.get("symbol")}: +{t.get("profit_percent", 0):.1f}%')
        print(f'   Entry MC: ${t.get("entry_mc", 0):,.0f}')
        print(f'   Exit MC: ${t.get("exit_mc", 0):,.0f}')
        print(f'   Entry reason: {t.get("entry_reason", "N/A")}')
        print(f'   TXN: {f.get("txn", 0)}')
        print(f'   Traders: {f.get("traders", 0)}')
        print(f'   Buy Ratio: {f.get("buy_ratio", 0)*100:.0f}%')
        print(f'   Whales: {f.get("whale_count", 0)}')
        print(f'   Exit reason: {t.get("exit_reason", "N/A")}')
else:
    print('\nAucun winner AUTO-BUY')

# ============================================================================
# STATISTIQUES COMPARATIVES
# ============================================================================
print(f'\n{"="*80}')
print('STATISTIQUES COMPARATIVES - WINNERS SEULEMENT')
print('='*80)

def analyze_winners(trades_list, label):
    if not trades_list:
        print(f'\n{label}: Aucun trade')
        return

    mcs = [t.get('entry_mc', 0) for t in trades_list]
    txns = [t.get('features', {}).get('txn', 0) for t in trades_list if t.get('features', {}).get('txn', 0) > 0]
    traders = [t.get('features', {}).get('traders', 0) for t in trades_list if t.get('features', {}).get('traders', 0) > 0]
    buy_ratios = [t.get('features', {}).get('buy_ratio', 0) for t in trades_list if t.get('features', {}).get('buy_ratio', 0) > 0]
    whales = [t.get('features', {}).get('whale_count', 0) for t in trades_list]
    profits = [t.get('profit_percent', 0) for t in trades_list]
    exit_mcs = [t.get('exit_mc', 0) for t in trades_list]

    print(f'\n{label}:')
    print(f'   Nombre: {len(trades_list)} winners')
    print(f'   Profit moyen: +{sum(profits)/len(profits):.1f}%')
    print(f'   Profit MIN: +{min(profits):.1f}%')
    print(f'   Profit MAX: +{max(profits):.1f}%')
    print(f'')
    print(f'   MC entrée moyen: ${sum(mcs)/len(mcs):,.0f}')
    print(f'   MC entrée MIN: ${min(mcs):,.0f}')
    print(f'   MC entrée MAX: ${max(mcs):,.0f}')
    print(f'')
    print(f'   MC sortie moyen: ${sum(exit_mcs)/len(exit_mcs):,.0f}')
    print(f'   MC sortie MAX: ${max(exit_mcs):,.0f}')
    print(f'')
    print(f'   TXN moyen: {sum(txns)/len(txns):.0f}' if txns else '   TXN: N/A')
    print(f'   TXN MIN: {min(txns)}' if txns else '')
    print(f'   TXN MAX: {max(txns)}' if txns else '')
    print(f'')
    print(f'   Traders moyen: {sum(traders)/len(traders):.0f}' if traders else '   Traders: N/A')
    print(f'   Traders MIN: {min(traders)}' if traders else '')
    print(f'   Traders MAX: {max(traders)}' if traders else '')
    print(f'')
    print(f'   Buy ratio moyen: {sum(buy_ratios)/len(buy_ratios)*100:.0f}%' if buy_ratios else '   Buy ratio: N/A')
    print(f'   Buy ratio MIN: {min(buy_ratios)*100:.0f}%' if buy_ratios else '')
    print(f'   Buy ratio MAX: {max(buy_ratios)*100:.0f}%' if buy_ratios else '')
    print(f'')
    print(f'   Whales moyen: {sum(whales)/len(whales):.2f}')
    print(f'   Whales MIN: {min(whales)}')
    print(f'   Whales MAX: {max(whales)}')
    print(f'')
    # Distribution des baleines
    whale_dist = {}
    for w in whales:
        whale_dist[w] = whale_dist.get(w, 0) + 1
    print(f'   Distribution baleines:')
    for w in sorted(whale_dist.keys()):
        count = whale_dist[w]
        pct = count / len(whales) * 100
        print(f'     {w} baleine(s): {count} trades ({pct:.0f}%)')

analyze_winners(ia_wins, 'IA WINNERS')
analyze_winners(autobuy_wins, 'AUTO-BUY WINNERS')

# ============================================================================
# PROFIL IDÉAL
# ============================================================================
print(f'\n{"="*80}')
print('PROFIL IDÉAL POUR GAGNER')
print('='*80)

print(f'\nIA WINNERS - Profil idéal:')
if ia_wins:
    ia_txns = [t.get('features', {}).get('txn', 0) for t in ia_wins if t.get('features', {}).get('txn', 0) > 0]
    ia_traders = [t.get('features', {}).get('traders', 0) for t in ia_wins if t.get('features', {}).get('traders', 0) > 0]
    ia_buy_ratios = [t.get('features', {}).get('buy_ratio', 0) for t in ia_wins if t.get('features', {}).get('buy_ratio', 0) > 0]
    ia_whales = [t.get('features', {}).get('whale_count', 0) for t in ia_wins]
    ia_mcs = [t.get('entry_mc', 0) for t in ia_wins]

    print(f'   MC: ${min(ia_mcs):,.0f} - ${max(ia_mcs):,.0f} (moyen ${sum(ia_mcs)/len(ia_mcs):,.0f})')
    print(f'   TXN: {min(ia_txns)} - {max(ia_txns)} (moyen {sum(ia_txns)/len(ia_txns):.0f})' if ia_txns else '   TXN: N/A')
    print(f'   Traders: {min(ia_traders)} - {max(ia_traders)} (moyen {sum(ia_traders)/len(ia_traders):.0f})' if ia_traders else '   Traders: N/A')
    print(f'   Buy Ratio: {min(ia_buy_ratios)*100:.0f}% - {max(ia_buy_ratios)*100:.0f}% (moyen {sum(ia_buy_ratios)/len(ia_buy_ratios)*100:.0f}%)' if ia_buy_ratios else '   Buy ratio: N/A')
    print(f'   Whales: {min(ia_whales)} - {max(ia_whales)} (moyen {sum(ia_whales)/len(ia_whales):.2f})')

print(f'\nAUTO-BUY WINNERS - Profil idéal:')
if autobuy_wins:
    ab_txns = [t.get('features', {}).get('txn', 0) for t in autobuy_wins if t.get('features', {}).get('txn', 0) > 0]
    ab_traders = [t.get('features', {}).get('traders', 0) for t in autobuy_wins if t.get('features', {}).get('traders', 0) > 0]
    ab_buy_ratios = [t.get('features', {}).get('buy_ratio', 0) for t in autobuy_wins if t.get('features', {}).get('buy_ratio', 0) > 0]
    ab_whales = [t.get('features', {}).get('whale_count', 0) for t in autobuy_wins]
    ab_mcs = [t.get('entry_mc', 0) for t in autobuy_wins]

    print(f'   MC: ${min(ab_mcs):,.0f} - ${max(ab_mcs):,.0f} (moyen ${sum(ab_mcs)/len(ab_mcs):,.0f})')
    print(f'   TXN: {min(ab_txns)} - {max(ab_txns)} (moyen {sum(ab_txns)/len(ab_txns):.0f})' if ab_txns else '   TXN: N/A')
    print(f'   Traders: {min(ab_traders)} - {max(ab_traders)} (moyen {sum(ab_traders)/len(ab_traders):.0f})' if ab_traders else '   Traders: N/A')
    print(f'   Buy Ratio: {min(ab_buy_ratios)*100:.0f}% - {max(ab_buy_ratios)*100:.0f}% (moyen {sum(ab_buy_ratios)/len(ab_buy_ratios)*100:.0f}%)' if ab_buy_ratios else '   Buy ratio: N/A')
    print(f'   Whales: {min(ab_whales)} - {max(ab_whales)} (moyen {sum(ab_whales)/len(ab_whales):.2f})')

print(f'\n{"="*80}')

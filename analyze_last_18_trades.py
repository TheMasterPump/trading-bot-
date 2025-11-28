"""
Analyse des 18 derniers trades pour identifier pourquoi 14 pertes
"""
import json
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Charger l'historique
with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Prendre les 18 derniers
trades = data['trades'][-18:]

print('='*80)
print('ANALYSE DES 18 DERNIERS TRADES')
print('='*80)

winners = [t for t in trades if t.get('is_win', False)]
losers = [t for t in trades if not t.get('is_win', False)]

print(f'\n📊 RÉSULTAT: {len(winners)} WINS / {len(losers)} LOSSES = {len(winners)/len(trades)*100:.1f}% WR')

# Analyser les 14 pertes
print(f'\n{'='*80}')
print(f'ANALYSE DES {len(losers)} PERTES')
print('='*80)

# MC d'entrée des pertes
mc_losses = [t.get('entry_mc', 0) for t in losers]
avg_mc_loss = sum(mc_losses) / len(mc_losses) if mc_losses else 0

print(f'\n💔 MC MOYEN DES PERTES: ${avg_mc_loss:,.0f}')

# Combien sont < 8K?
below_8k = len([mc for mc in mc_losses if mc < 8000])
in_zone_8k_12k = len([mc for mc in mc_losses if 8000 <= mc <= 12000])
above_12k = len([mc for mc in mc_losses if mc > 12000])

print(f'\n📍 RÉPARTITION PAR ZONE:')
print(f'   < 8K: {below_8k} trades ({below_8k/len(losers)*100:.0f}%)')
print(f'   8K-12K (zone optimale): {in_zone_8k_12k} trades ({in_zone_8k_12k/len(losers)*100:.0f}%)')
print(f'   > 12K: {above_12k} trades ({above_12k/len(losers)*100:.0f}%)')

# Baleines
whales_in_losses = [t.get('features', {}).get('whale_count', 0) for t in losers]
avg_whales_loss = sum(whales_in_losses) / len(whales_in_losses) if whales_in_losses else 0

print(f'\n🐋 BALEINES MOYENNES: {avg_whales_loss:.2f}')
print(f'   0 baleines: {len([w for w in whales_in_losses if w == 0])} trades')
print(f'   1 baleine: {len([w for w in whales_in_losses if w == 1])} trades')
print(f'   2+ baleines: {len([w for w in whales_in_losses if w >= 2])} trades')

# Buy ratio
buy_ratios = [t.get('features', {}).get('buy_ratio', 0) for t in losers]
avg_buy_ratio_loss = sum(buy_ratios) / len(buy_ratios) if buy_ratios else 0

print(f'\n📈 BUY RATIO MOYEN: {avg_buy_ratio_loss*100:.1f}%')

# Raisons d'entrée
entry_reasons = {}
for t in losers:
    reason = t.get('entry_reason', t.get('reason', 'Unknown'))
    # Simplifier
    if 'AUTO-BUY' in reason:
        key = 'AUTO-BUY'
    elif 'IA' in reason or '%' in reason:
        key = 'IA'
    elif 'ELITE' in reason:
        key = 'ELITE WALLET'
    elif 'BALEINE' in reason or 'whale' in reason:
        key = 'BALEINES'
    else:
        key = 'AUTRE'

    entry_reasons[key] = entry_reasons.get(key, 0) + 1

print(f'\n🎯 RAISONS D\'ENTRÉE (PERTES):')
for reason, count in sorted(entry_reasons.items(), key=lambda x: x[1], reverse=True):
    print(f'   {reason}: {count} trades ({count/len(losers)*100:.0f}%)')

# Raisons de sortie
exit_reasons = {}
for t in losers:
    reason = t.get('exit_reason', 'Unknown')
    exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

print(f'\n🚪 RAISONS DE SORTIE (PERTES):')
for reason, count in sorted(exit_reasons.items(), key=lambda x: x[1], reverse=True):
    print(f'   {reason}: {count} trades ({count/len(losers)*100:.0f}%)')

# Analyser les 4 winners
print(f'\n{'='*80}')
print(f'ANALYSE DES {len(winners)} WINNERS')
print('='*80)

mc_wins = [t.get('entry_mc', 0) for t in winners]
avg_mc_win = sum(mc_wins) / len(mc_wins) if mc_wins else 0

print(f'\n💰 MC MOYEN DES WINNERS: ${avg_mc_win:,.0f}')

# Combien sont dans la zone optimale?
below_8k_w = len([mc for mc in mc_wins if mc < 8000])
in_zone_8k_12k_w = len([mc for mc in mc_wins if 8000 <= mc <= 12000])
above_12k_w = len([mc for mc in mc_wins if mc > 12000])

print(f'\n📍 RÉPARTITION PAR ZONE:')
print(f'   < 8K: {below_8k_w} trades')
print(f'   8K-12K (zone optimale): {in_zone_8k_12k_w} trades')
print(f'   > 12K: {above_12k_w} trades')

# Baleines
whales_in_wins = [t.get('features', {}).get('whale_count', 0) for t in winners]
avg_whales_win = sum(whales_in_wins) / len(whales_in_wins) if whales_in_wins else 0

print(f'\n🐋 BALEINES MOYENNES: {avg_whales_win:.2f}')

# Buy ratio
buy_ratios_w = [t.get('features', {}).get('buy_ratio', 0) for t in winners]
avg_buy_ratio_win = sum(buy_ratios_w) / len(buy_ratios_w) if buy_ratios_w else 0

print(f'\n📈 BUY RATIO MOYEN: {avg_buy_ratio_win*100:.1f}%')

# Afficher les 4 winners
print(f'\n🏆 LES 4 WINNERS:')
for i, t in enumerate(winners, 1):
    print(f'\n{i}. {t.get("symbol")}: +{t.get("profit_percent", 0):.1f}%')
    print(f'   MC entrée: ${t.get("entry_mc", 0):,.0f}')
    print(f'   Raison: {t.get("entry_reason", t.get("reason", "N/A"))}')
    features = t.get('features', {})
    print(f'   Features: {features.get("whale_count", 0)} whales, {features.get("buy_ratio", 0)*100:.0f}% buy, {features.get("txn", 0)} txn')

# Afficher les pires 5 pertes
print(f'\n{'='*80}')
print(f'TOP 5 PIRES PERTES')
print('='*80)

worst_5 = sorted(losers, key=lambda x: x.get('profit_percent', 0))[:5]
for i, t in enumerate(worst_5, 1):
    print(f'\n{i}. {t.get("symbol")}: {t.get("profit_percent", 0):.1f}%')
    print(f'   MC entrée: ${t.get("entry_mc", 0):,.0f}')
    print(f'   Raison entrée: {t.get("entry_reason", t.get("reason", "N/A"))}')
    print(f'   Raison sortie: {t.get("exit_reason", "N/A")}')
    features = t.get('features', {})
    print(f'   Features: {features.get("whale_count", 0)} whales, {features.get("buy_ratio", 0)*100:.0f}% buy, {features.get("txn", 0)} txn')

# RECOMMANDATIONS
print(f'\n{'='*80}')
print('🎯 RECOMMANDATIONS')
print('='*80)

print(f'\n1. MC D\'ENTRÉE:')
if avg_mc_loss < avg_mc_win:
    print(f'   ✅ Winners entrent plus tard (${avg_mc_win:,.0f} vs ${avg_mc_loss:,.0f})')
else:
    print(f'   ⚠️ Losers entrent plus tard (${avg_mc_loss:,.0f} vs ${avg_mc_win:,.0f})')
    if below_8k > len(losers) * 0.3:
        print(f'   → {below_8k} pertes sont < 8K (zone perdante)')
        print(f'   → SOLUTION: Ajouter filtre MC >= 8K (DÉJÀ FAIT!)')

print(f'\n2. BALEINES:')
if avg_whales_loss > avg_whales_win:
    print(f'   ⚠️ Losers ont plus de baleines ({avg_whales_loss:.2f} vs {avg_whales_win:.2f})')
    print(f'   → SOLUTION: Rejeter si whale_count > 1 (DÉJÀ FAIT!)')
else:
    print(f'   ✅ Winners ont plus de baleines ({avg_whales_win:.2f} vs {avg_whales_loss:.2f})')

print(f'\n3. BUY RATIO:')
if avg_buy_ratio_win > avg_buy_ratio_loss * 1.1:
    print(f'   ⚠️ Winners ont meilleur buy ratio ({avg_buy_ratio_win*100:.0f}% vs {avg_buy_ratio_loss*100:.0f}%)')
    print(f'   → SOLUTION: Augmenter minimum buy ratio à {avg_buy_ratio_win*100:.0f}%')
else:
    print(f'   ✅ Buy ratio similaire')

print(f'\n{'='*80}')

"""
Analyse complète des 240 trades pour identifier les problèmes
"""
import json

# Charger l'historique
with open('trading_history.json', 'r') as f:
    data = json.load(f)

trades = data['trades']
wins = [t for t in trades if t['is_win']]
losses = [t for t in trades if not t['is_win']]

print('='*80)
print('ANALYSE COMPLETE DES TRADES')
print('='*80)
print(f'\nTotal trades: {len(trades)}')
print(f'Wins: {len(wins)} ({len(wins)/len(trades)*100:.1f}%)')
print(f'Losses: {len(losses)} ({len(losses)/len(trades)*100:.1f}%)')

# Analyser les winners
print('\n' + '='*80)
print('ANALYSE DES WINNERS (36 trades)')
print('='*80)
if wins:
    print(f'\nProfit moyen: {sum(t["profit_percent"] for t in wins)/len(wins):.1f}%')
    print(f'Profit médian: {sorted(t["profit_percent"] for t in wins)[len(wins)//2]:.1f}%')

    # MC d'entrée des winners
    entry_mcs = [t['entry_mc'] for t in wins]
    print(f'\nMC entrée moyen: ${sum(entry_mcs)/len(entry_mcs):,.0f}')
    print(f'MC entrée médian: ${sorted(entry_mcs)[len(entry_mcs)//2]:,.0f}')

    # Buy ratio des winners
    buy_ratios = [t['features'].get('buy_ratio', 0) for t in wins]
    print(f'\nBuy ratio moyen: {sum(buy_ratios)/len(buy_ratios)*100:.1f}%')
    print(f'Buy ratio médian: {sorted(buy_ratios)[len(buy_ratios)//2]*100:.1f}%')

    # Whale count des winners
    whale_counts = [t['features'].get('whale_count', 0) for t in wins]
    print(f'\nWhale count moyen: {sum(whale_counts)/len(whale_counts):.2f}')
    winners_with_whales = [t for t in wins if t['features'].get('whale_count', 0) > 0]
    print(f'Winners avec whales: {len(winners_with_whales)} ({len(winners_with_whales)/len(wins)*100:.1f}%)')

    # Elite wallets
    winners_with_elite = [t for t in wins if t['features'].get('elite_wallet_count', 0) > 0]
    print(f'Winners avec elite wallets: {len(winners_with_elite)} ({len(winners_with_elite)/len(wins)*100:.1f}%)')

    # Raisons de sortie
    print('\nRaisons de sortie:')
    timeout_wins = [t for t in wins if 'TIMEOUT' in t.get('exit_reason', '')]
    tp_wins = [t for t in wins if 'TAKE PROFIT' in t.get('exit_reason', '')]
    print(f'  - Timeout (30min): {len(timeout_wins)} ({len(timeout_wins)/len(wins)*100:.1f}%)')
    print(f'  - Take Profit: {len(tp_wins)} ({len(tp_wins)/len(wins)*100:.1f}%)')

# Analyser les losers
print('\n' + '='*80)
print('ANALYSE DES LOSERS (204 trades)')
print('='*80)
if losses:
    print(f'\nPerte moyenne: {sum(t["profit_percent"] for t in losses)/len(losses):.1f}%')
    print(f'Perte médiane: {sorted(t["profit_percent"] for t in losses)[len(losses)//2]:.1f}%')

    # MC d'entrée des losers
    entry_mcs = [t['entry_mc'] for t in losses]
    print(f'\nMC entrée moyen: ${sum(entry_mcs)/len(entry_mcs):,.0f}')
    print(f'MC entrée médian: ${sorted(entry_mcs)[len(entry_mcs)//2]:,.0f}')

    # Buy ratio des losers
    buy_ratios = [t['features'].get('buy_ratio', 0) for t in losses]
    print(f'\nBuy ratio moyen: {sum(buy_ratios)/len(buy_ratios)*100:.1f}%')
    print(f'Buy ratio médian: {sorted(buy_ratios)[len(buy_ratios)//2]*100:.1f}%')

    # Whale count des losers
    whale_counts = [t['features'].get('whale_count', 0) for t in losses]
    print(f'\nWhale count moyen: {sum(whale_counts)/len(whale_counts):.2f}')
    losers_with_whales = [t for t in losses if t['features'].get('whale_count', 0) > 0]
    print(f'Losers avec whales: {len(losers_with_whales)} ({len(losers_with_whales)/len(losses)*100:.1f}%)')

    # Elite wallets
    losers_with_elite = [t for t in losses if t['features'].get('elite_wallet_count', 0) > 0]
    print(f'Losers avec elite wallets: {len(losers_with_elite)} ({len(losers_with_elite)/len(losses)*100:.1f}%)')

    # Raisons de sortie
    print('\nRaisons de sortie:')
    sl_losses = [t for t in losses if 'STOP LOSS' in t.get('exit_reason', '') and '2x' not in t.get('exit_reason', '')]
    sl_after_2x = [t for t in losses if 'STOP LOSS' in t.get('exit_reason', '') and '2x' in t.get('exit_reason', '')]
    timeout_losses = [t for t in losses if 'TIMEOUT' in t.get('exit_reason', '')]
    print(f'  - Stop Loss direct: {len(sl_losses)} ({len(sl_losses)/len(losses)*100:.1f}%)')
    print(f'  - Stop Loss après 2x: {len(sl_after_2x)} ({len(sl_after_2x)/len(losses)*100:.1f}%)')
    print(f'  - Timeout (30min): {len(timeout_losses)} ({len(timeout_losses)/len(losses)*100:.1f}%)')

    # Analyser les pertes après 2x
    if sl_after_2x:
        print(f'\n  >>> {len(sl_after_2x)} trades ont atteint 2x puis sont redescendus!')
        print(f'      Perte moyenne: {sum(t["profit_percent"] for t in sl_after_2x)/len(sl_after_2x):.1f}%')

# Comparaison Winners vs Losers
print('\n' + '='*80)
print('COMPARAISON WINNERS vs LOSERS')
print('='*80)
if wins and losses:
    print(f'\nMC entrée:')
    print(f'  Winners: ${sum(t["entry_mc"] for t in wins)/len(wins):,.0f}')
    print(f'  Losers:  ${sum(t["entry_mc"] for t in losses)/len(losses):,.0f}')

    print(f'\nBuy ratio:')
    print(f'  Winners: {sum(t["features"].get("buy_ratio", 0) for t in wins)/len(wins)*100:.1f}%')
    print(f'  Losers:  {sum(t["features"].get("buy_ratio", 0) for t in losses)/len(losses)*100:.1f}%')

    print(f'\nWhale count:')
    print(f'  Winners: {sum(t["features"].get("whale_count", 0) for t in wins)/len(wins):.2f}')
    print(f'  Losers:  {sum(t["features"].get("whale_count", 0) for t in losses)/len(losses):.2f}')

    print(f'\nTxn count:')
    print(f'  Winners: {sum(t["features"].get("txn", 0) for t in wins)/len(wins):.1f}')
    print(f'  Losers:  {sum(t["features"].get("txn", 0) for t in losses)/len(losses):.1f}')

# PROBLEMES IDENTIFIES
print('\n' + '='*80)
print('PROBLEMES IDENTIFIES')
print('='*80)

problems = []

# Problème 1: Trop de stop loss directs
if losses:
    sl_direct_pct = len(sl_losses) / len(losses) * 100
    if sl_direct_pct > 70:
        problems.append(f'1. {sl_direct_pct:.0f}% des losses sont des stop loss directs (-30%)')
        problems.append(f'   => Les tokens chutent avant d\'atteindre 2x')
        problems.append(f'   => Les critères d\'entrée sont trop permissifs')

# Problème 2: Win rate trop bas
if len(wins) / len(trades) < 0.20:
    problems.append(f'2. Win rate de {len(wins)/len(trades)*100:.1f}% est trop bas')
    problems.append(f'   => Besoin de filtres plus stricts')

# Problème 3: Trades qui atteignent 2x puis redescendent
if losses and sl_after_2x:
    pct_2x_then_loss = len(sl_after_2x) / len(losses) * 100
    if pct_2x_then_loss > 5:
        problems.append(f'3. {len(sl_after_2x)} trades ont atteint 2x puis sont redescendus ({pct_2x_then_loss:.1f}%)')
        problems.append(f'   => La stratégie partial profit fonctionne partiellement')

# Problème 4: Différence whale count
if wins and losses:
    avg_whale_winners = sum(t["features"].get("whale_count", 0) for t in wins)/len(wins)
    avg_whale_losers = sum(t["features"].get("whale_count", 0) for t in losses)/len(losses)
    if avg_whale_winners > avg_whale_losers * 1.5:
        problems.append(f'4. Winners ont plus de whales ({avg_whale_winners:.2f}) que losers ({avg_whale_losers:.2f})')
        problems.append(f'   => Renforcer les filtres sur whale_count')

if problems:
    for p in problems:
        print(p)
else:
    print('Aucun problème majeur identifié')

# RECOMMANDATIONS
print('\n' + '='*80)
print('RECOMMANDATIONS')
print('='*80)
print('\n1. AUGMENTER LES FILTRES D\'ENTREE:')
print('   - Exiger whale_count >= 1 (au moins 1 baleine)')
print('   - Augmenter buy_ratio minimum à 85%')
print('   - Réduire MC max à $10K au lieu de $15K')

print('\n2. OPTIMISER LE STOP LOSS:')
print('   - Tester un stop loss à -25% au lieu de -30%')
print('   - OU utiliser un trailing stop loss')

print('\n3. STRATEGIE PARTIAL PROFIT:')
if sl_after_2x and len(sl_after_2x) > 10:
    print(f'   - {len(sl_after_2x)} trades ont atteint 2x: la stratégie fonctionne!')
    print('   - MAIS ils redescendent ensuite')
    print('   - Vendre 75% à 2x au lieu de 50%?')
    print('   - OU vendre tout à 3x au lieu d\'attendre 69K?')

print('\n4. FOCUS SUR LES PATTERNS GAGNANTS:')
if wins:
    avg_whale_winners = sum(t["features"].get("whale_count", 0) for t in wins)/len(wins)
    if avg_whale_winners >= 1:
        print(f'   - Winners ont en moyenne {avg_whale_winners:.1f} whales')
        print('   - Exiger whale_count >= 2 pour auto-buy')

print('\n' + '='*80)

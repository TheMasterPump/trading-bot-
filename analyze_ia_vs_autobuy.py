"""
Analyse ultra-détaillée: IA vs AUTO-BUY sur les 100 derniers trades
"""
import json
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Charger l'historique
with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data['trades'][-100:]  # Les 100 derniers

print('='*80)
print('ANALYSE ULTRA-DÉTAILLÉE: IA vs AUTO-BUY (100 derniers trades)')
print('='*80)

# Séparer IA vs AUTO-BUY
ia_trades = []
autobuy_trades = []

for t in trades:
    reason = t.get('entry_reason', t.get('reason', 'Unknown'))
    if 'IA' in reason or 'AI' in reason:
        ia_trades.append(t)
    elif 'AUTO-BUY' in reason:
        autobuy_trades.append(t)

# Stats globales
ia_wins = [t for t in ia_trades if t.get('is_win', False)]
ia_losses = [t for t in ia_trades if not t.get('is_win', False)]
ia_wr = len(ia_wins) / len(ia_trades) * 100 if ia_trades else 0

autobuy_wins = [t for t in autobuy_trades if t.get('is_win', False)]
autobuy_losses = [t for t in autobuy_trades if not t.get('is_win', False)]
autobuy_wr = len(autobuy_wins) / len(autobuy_trades) * 100 if autobuy_trades else 0

print(f'\nSTATS GLOBALES:')
print(f'\nIA: {len(ia_wins)}W/{len(ia_losses)}L ({ia_wr:.1f}% WR) - {len(ia_trades)} trades')
if ia_wins:
    avg_profit_ia = sum(t.get('profit_percent', 0) for t in ia_wins) / len(ia_wins)
    print(f'   Profit moyen: +{avg_profit_ia:.1f}%')
if ia_losses:
    avg_loss_ia = sum(t.get('profit_percent', 0) for t in ia_losses) / len(ia_losses)
    print(f'   Perte moyenne: {avg_loss_ia:.1f}%')

print(f'\nAUTO-BUY: {len(autobuy_wins)}W/{len(autobuy_losses)}L ({autobuy_wr:.1f}% WR) - {len(autobuy_trades)} trades')
if autobuy_wins:
    avg_profit_ab = sum(t.get('profit_percent', 0) for t in autobuy_wins) / len(autobuy_wins)
    print(f'   Profit moyen: +{avg_profit_ab:.1f}%')
if autobuy_losses:
    avg_loss_ab = sum(t.get('profit_percent', 0) for t in autobuy_losses) / len(autobuy_losses)
    print(f'   Perte moyenne: {avg_loss_ab:.1f}%')

# Migrations
ia_migrations = [t for t in ia_trades if t.get('exit_mc', 0) >= 53000]
ab_migrations = [t for t in autobuy_trades if t.get('exit_mc', 0) >= 53000]

print(f'\nMIGRATIONS:')
print(f'   IA: {len(ia_migrations)} migrations ({len(ia_migrations)/len(ia_trades)*100:.1f}% des trades IA)' if ia_trades else '   IA: 0')
print(f'   AUTO-BUY: {len(ab_migrations)} migrations ({len(ab_migrations)/len(autobuy_trades)*100:.1f}% des trades AUTO-BUY)' if autobuy_trades else '   AUTO-BUY: 0')

print(f'\n{"="*80}')
print('COMPARAISON DES CARACTÉRISTIQUES')
print('='*80)

# Comparer MC, TXN, Traders, Buy Ratio, Whales
def analyze_features(trades_list, label):
    if not trades_list:
        print(f'\n{label}: Aucun trade')
        return

    mcs = [t.get('entry_mc', 0) for t in trades_list]
    txns = [t.get('features', {}).get('txn', 0) for t in trades_list if t.get('features', {}).get('txn', 0) > 0]
    traders = [t.get('features', {}).get('traders', 0) for t in trades_list if t.get('features', {}).get('traders', 0) > 0]
    buy_ratios = [t.get('features', {}).get('buy_ratio', 0) for t in trades_list if t.get('features', {}).get('buy_ratio', 0) > 0]
    whales = [t.get('features', {}).get('whale_count', 0) for t in trades_list]

    print(f'\n{label}:')
    print(f'   MC moyen: ${sum(mcs)/len(mcs):,.0f}' if mcs else '   MC: N/A')
    print(f'   TXN moyen: {sum(txns)/len(txns):.0f} (range {min(txns)}-{max(txns)})' if txns else '   TXN: N/A')
    print(f'   Traders moyen: {sum(traders)/len(traders):.0f} (range {min(traders)}-{max(traders)})' if traders else '   Traders: N/A')
    print(f'   Buy ratio moyen: {sum(buy_ratios)/len(buy_ratios)*100:.0f}%' if buy_ratios else '   Buy ratio: N/A')
    print(f'   Whales moyen: {sum(whales)/len(whales):.2f}' if whales else '   Whales: N/A')

print(f'\nWINNERS:')
analyze_features(ia_wins, '  IA WINS')
analyze_features(autobuy_wins, '  AUTO-BUY WINS')

print(f'\nLOSERS:')
analyze_features(ia_losses, '  IA LOSSES')
analyze_features(autobuy_losses, '  AUTO-BUY LOSSES')

print(f'\n{"="*80}')
print('TOP 10 IA WINS')
print('='*80)

if ia_wins:
    top_ia = sorted(ia_wins, key=lambda x: x.get('profit_percent', 0), reverse=True)[:10]
    for i, t in enumerate(top_ia, 1):
        f = t.get('features', {})
        reason = t.get('entry_reason', 'N/A')
        confidence = 'N/A'
        if 'IA:' in reason:
            confidence = reason.split('IA:')[1].strip().split('%')[0] + '%'

        print(f'\n{i}. {t.get("symbol")}: +{t.get("profit_percent", 0):.1f}%')
        print(f'   Entry MC: ${t.get("entry_mc", 0):,.0f} -> Exit: ${t.get("exit_mc", 0):,.0f}')
        print(f'   IA Confidence: {confidence}')
        print(f'   Features: {f.get("whale_count", 0)}whales, {f.get("buy_ratio", 0)*100:.0f}%buy, {f.get("txn", 0)}txn, {f.get("traders", 0)}traders')
else:
    print('\nAucun win IA')

print(f'\n{"="*80}')
print('TOP 10 AUTO-BUY WINS')
print('='*80)

if autobuy_wins:
    top_ab = sorted(autobuy_wins, key=lambda x: x.get('profit_percent', 0), reverse=True)[:10]
    for i, t in enumerate(top_ab, 1):
        f = t.get('features', {})

        print(f'\n{i}. {t.get("symbol")}: +{t.get("profit_percent", 0):.1f}%')
        print(f'   Entry MC: ${t.get("entry_mc", 0):,.0f} -> Exit: ${t.get("exit_mc", 0):,.0f}')
        print(f'   Raison: {t.get("entry_reason", "N/A")}')
        print(f'   Features: {f.get("whale_count", 0)}whales, {f.get("buy_ratio", 0)*100:.0f}%buy, {f.get("txn", 0)}txn, {f.get("traders", 0)}traders')
else:
    print('\nAucun win AUTO-BUY')

print(f'\n{"="*80}')
print('TOUTES LES MIGRATIONS (IA + AUTO-BUY)')
print('='*80)

all_migrations = [t for t in trades if t.get('exit_mc', 0) >= 53000]

if all_migrations:
    for i, t in enumerate(all_migrations, 1):
        f = t.get('features', {})
        reason = t.get('entry_reason', 'N/A')
        is_ia = 'IA' in reason

        print(f'\n{i}. {t.get("symbol")}: +{t.get("profit_percent", 0):.1f}% (Exit: ${t.get("exit_mc", 0):,.0f})')
        print(f'   Type: {"IA" if is_ia else "AUTO-BUY"}')
        print(f'   Entry MC: ${t.get("entry_mc", 0):,.0f}')
        print(f'   Raison: {reason}')
        print(f'   Features: {f.get("whale_count", 0)}whales, {f.get("buy_ratio", 0)*100:.0f}%buy, {f.get("txn", 0)}txn, {f.get("traders", 0)}traders')
else:
    print('\nAucune migration dans les 100 derniers trades')

print(f'\n{"="*80}')
print('RECOMMANDATIONS')
print('='*80)

print(f'\n1. WIN RATE:')
if ia_trades and autobuy_trades:
    if ia_wr > autobuy_wr * 1.2:
        print(f'   IA est {ia_wr/autobuy_wr:.1f}x meilleur que AUTO-BUY')
        print(f'   -> RECOMMANDATION: Forcer plus de trades IA!')
        print(f'   -> Actuellement: {len(ia_trades)} IA vs {len(autobuy_trades)} AUTO-BUY')
    else:
        print(f'   Performance similaire')

print(f'\n2. MIGRATIONS:')
ia_mig_rate = len(ia_migrations)/len(ia_trades)*100 if ia_trades else 0
ab_mig_rate = len(ab_migrations)/len(autobuy_trades)*100 if autobuy_trades else 0
print(f'   IA: {ia_mig_rate:.1f}% taux de migration')
print(f'   AUTO-BUY: {ab_mig_rate:.1f}% taux de migration')
if ia_mig_rate > ab_mig_rate:
    print(f'   IA trouve plus de migrations!')

print(f'\n{"="*80}')

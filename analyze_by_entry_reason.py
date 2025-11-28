"""
Analyse détaillée des trades par RAISON D'ENTRÉE (AUTO-BUY, IA, etc.)
"""
import json
import sys
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Charger l'historique
with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

trades = data['trades']

print('='*80)
print('ANALYSE PAR RAISON D ENTREE (AUTO-BUY vs IA)')
print('='*80)
print(f'\nTotal trades: {len(trades)}')

# Classifier par raison d'entrée
by_entry_reason = {}

for t in trades:
    # Récupérer la raison d'entrée (nouveau champ)
    entry_reason = t.get('entry_reason', 'Unknown')
    
    # Si pas de entry_reason, essayer de deviner depuis les features
    if entry_reason in ['Unknown', 'N/A', 'STOP LOSS', 'TIMEOUT', 'TIMEOUT (30min)']:
        # C'est l'ancien format, reconstruire
        features = t.get('features', {})
        confidence = t.get('confidence', 0)
        
        if confidence == 1.0:
            if features.get('consecutive_whales', False):
                entry_reason = '2 BALEINES CONSECUTIVES'
            elif features.get('elite_wallet_count', 0) > 0:
                entry_reason = 'ELITE WALLET'
            elif (features.get('txn', 0) >= 35 and 
                  features.get('traders', 0) >= 25 and 
                  features.get('buy_ratio', 0) >= 0.75):
                entry_reason = 'AUTO-BUY'
            else:
                entry_reason = 'PATTERN FORT'
        else:
            entry_reason = 'IA'
    
    # Simplifier les raisons
    if 'AUTO-BUY' in entry_reason or 'PATTERN' in entry_reason:
        key = 'AUTO-BUY'
    elif 'IA' in entry_reason or 'WHALE BOOST' in entry_reason:
        key = 'IA'
    elif 'ELITE' in entry_reason:
        key = 'ELITE WALLET'
    elif 'BALEINE' in entry_reason:
        key = 'BALEINES CONSECUTIVES'
    else:
        key = 'AUTRE'
    
    if key not in by_entry_reason:
        by_entry_reason[key] = {'wins': [], 'losses': []}
    
    if t.get('profit_percent', 0) > 0:
        by_entry_reason[key]['wins'].append(t)
    else:
        by_entry_reason[key]['losses'].append(t)

# Afficher les stats par raison d'entrée
print(f'\n{'='*80}')
print('STATISTIQUES PAR SOURCE D ENTREE')
print('='*80)

for reason, data in sorted(by_entry_reason.items(), key=lambda x: len(x[1]['wins']) + len(x[1]['losses']), reverse=True):
    wins = data['wins']
    losses = data['losses']
    total = len(wins) + len(losses)
    wr = len(wins) / total * 100 if total > 0 else 0
    
    emoji = '✅' if wr >= 20 else '⚠️' if wr >= 15 else '❌'
    
    print(f'\n{emoji} {reason}: {total} trades')
    print(f'   Win Rate: {wr:.1f}% ({len(wins)}W / {len(losses)}L)')
    
    if wins:
        avg_profit = sum(t.get('profit_percent', 0) for t in wins) / len(wins)
        avg_mc_entry = sum(t.get('entry_mc', 0) for t in wins) / len(wins)
        avg_duration = sum(t.get('timeout_minutes', 0) for t in wins) / len(wins)
        print(f'   Winners - Profit moyen: +{avg_profit:.1f}%, MC: ${avg_mc_entry:,.0f}, Durée: {avg_duration:.1f}min')
    
    if losses:
        avg_loss = sum(t.get('profit_percent', 0) for t in losses) / len(losses)
        avg_mc_entry = sum(t.get('entry_mc', 0) for t in losses) / len(losses)
        avg_duration = sum(t.get('timeout_minutes', 0) for t in losses) / len(losses)
        print(f'   Losers - Perte moyenne: {avg_loss:.1f}%, MC: ${avg_mc_entry:,.0f}, Durée: {avg_duration:.1f}min')

# Top 5 par raison d'entrée
print(f'\n{'='*80}')
print('TOP 5 WINNERS PAR SOURCE')
print('='*80)

for reason, data in by_entry_reason.items():
    wins = data['wins']
    if not wins:
        continue
    
    top_5 = sorted(wins, key=lambda x: x.get('profit_percent', 0), reverse=True)[:5]
    
    print(f'\n{reason}:')
    for i, t in enumerate(top_5, 1):
        print(f'  {i}. {t.get("symbol")}: +{t.get("profit_percent", 0):.1f}% @ ${t.get("entry_mc", 0):,.0f}')

# Analyse des features par source
print(f'\n{'='*80}')
print('FEATURES MOYENNES PAR SOURCE')
print('='*80)

for reason, data in by_entry_reason.items():
    all_trades = data['wins'] + data['losses']
    
    if not all_trades:
        continue
    
    avg_whales = sum(t.get('features', {}).get('whale_count', 0) for t in all_trades) / len(all_trades)
    avg_buy_ratio = sum(t.get('features', {}).get('buy_ratio', 0) for t in all_trades) / len(all_trades)
    avg_txn = sum(t.get('features', {}).get('txn', 0) for t in all_trades) / len(all_trades)
    avg_traders = sum(t.get('features', {}).get('traders', 0) for t in all_trades) / len(all_trades)
    
    print(f'\n{reason}:')
    print(f'  Baleines: {avg_whales:.2f}')
    print(f'  Buy ratio: {avg_buy_ratio*100:.1f}%')
    print(f'  Transactions: {avg_txn:.1f}')
    print(f'  Traders: {avg_traders:.1f}')

print(f'\n{'='*80}')

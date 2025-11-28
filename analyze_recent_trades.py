"""
Script pour analyser les derniers trades et identifier les patterns des winners vs losers
"""
import json
import pandas as pd
from datetime import datetime
import sys
import codecs

# Fix encoding pour Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Charger l'historique
with open('trading_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Le fichier peut être un dict ou une liste
if isinstance(data, dict):
    # Si c'est un dict, récupérer les trades (peut-être sous 'trades' ou autre clé)
    if 'trades' in data:
        trades = data['trades']
    else:
        # Essayer de convertir le dict en liste
        trades = list(data.values()) if data else []
else:
    trades = data

print(f"Total trades dans l'historique: {len(trades)}")

if len(trades) == 0:
    print("Aucun trade trouvé dans l'historique!")
    exit(0)

# Analyser tous les trades disponibles (ou max 100)
recent_trades = trades[-100:] if len(trades) > 100 else trades

print(f"\n{'='*80}")
print(f"ANALYSE DES {len(recent_trades)} DERNIERS TRADES")
print(f"{'='*80}")

# Séparer winners et losers
winners = [t for t in recent_trades if t.get('profit_percent', 0) > 0]
losers = [t for t in recent_trades if t.get('profit_percent', 0) <= 0]

print(f"\n📊 STATISTIQUES GLOBALES")
print(f"  Winners: {len(winners)} ({len(winners)/len(recent_trades)*100:.1f}%)")
print(f"  Losers: {len(losers)} ({len(losers)/len(recent_trades)*100:.1f}%)")

# Calculer moyennes pour winners
if winners:
    print(f"\n💰 WINNERS (n={len(winners)})")
    avg_profit = sum(t.get('profit_percent', 0) for t in winners) / len(winners)
    avg_entry_mc_w = sum(t.get('entry_mc', 0) for t in winners) / len(winners)
    avg_exit_mc_w = sum(t.get('exit_mc', 0) for t in winners) / len(winners)

    # Features moyennes
    avg_txn_w = sum(t.get('entry_features', {}).get('txn', 0) for t in winners) / len(winners)
    avg_traders_w = sum(t.get('entry_features', {}).get('traders', 0) for t in winners) / len(winners)
    avg_buy_ratio_w = sum(t.get('entry_features', {}).get('buy_ratio', 0) for t in winners) / len(winners)
    avg_whale_w = sum(t.get('entry_features', {}).get('whale_count', 0) for t in winners) / len(winners)
    avg_elite_w = sum(t.get('entry_features', {}).get('elite_wallet_count', 0) for t in winners) / len(winners)

    print(f"  Profit moyen: +{avg_profit:.1f}%")
    print(f"  MC entrée: ${avg_entry_mc_w:,.0f}")
    print(f"  MC sortie: ${avg_exit_mc_w:,.0f}")
    print(f"  Transactions: {avg_txn_w:.1f}")
    print(f"  Traders: {avg_traders_w:.1f}")
    print(f"  Buy ratio: {avg_buy_ratio_w*100:.1f}%")
    print(f"  Baleines: {avg_whale_w:.1f}")
    print(f"  Elite wallets: {avg_elite_w:.1f}")

    # Raisons d'entrée
    reasons_w = {}
    for t in winners:
        reason = t.get('reason', 'Unknown')
        reasons_w[reason] = reasons_w.get(reason, 0) + 1

    print(f"\n  Raisons d'entrée (Winners):")
    for reason, count in sorted(reasons_w.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {reason}: {count} trades ({count/len(winners)*100:.1f}%)")

# Calculer moyennes pour losers
if losers:
    print(f"\n📉 LOSERS (n={len(losers)})")
    avg_loss = sum(t.get('profit_percent', 0) for t in losers) / len(losers)
    avg_entry_mc_l = sum(t.get('entry_mc', 0) for t in losers) / len(losers)
    avg_exit_mc_l = sum(t.get('exit_mc', 0) for t in losers) / len(losers)

    # Features moyennes
    avg_txn_l = sum(t.get('entry_features', {}).get('txn', 0) for t in losers) / len(losers)
    avg_traders_l = sum(t.get('entry_features', {}).get('traders', 0) for t in losers) / len(losers)
    avg_buy_ratio_l = sum(t.get('entry_features', {}).get('buy_ratio', 0) for t in losers) / len(losers)
    avg_whale_l = sum(t.get('entry_features', {}).get('whale_count', 0) for t in losers) / len(losers)
    avg_elite_l = sum(t.get('entry_features', {}).get('elite_wallet_count', 0) for t in losers) / len(losers)

    print(f"  Perte moyenne: {avg_loss:.1f}%")
    print(f"  MC entrée: ${avg_entry_mc_l:,.0f}")
    print(f"  MC sortie: ${avg_exit_mc_l:,.0f}")
    print(f"  Transactions: {avg_txn_l:.1f}")
    print(f"  Traders: {avg_traders_l:.1f}")
    print(f"  Buy ratio: {avg_buy_ratio_l*100:.1f}%")
    print(f"  Baleines: {avg_whale_l:.1f}")
    print(f"  Elite wallets: {avg_elite_l:.1f}")

    # Raisons d'entrée
    reasons_l = {}
    for t in losers:
        reason = t.get('reason', 'Unknown')
        reasons_l[reason] = reasons_l.get(reason, 0) + 1

    print(f"\n  Raisons d'entrée (Losers):")
    for reason, count in sorted(reasons_l.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {reason}: {count} trades ({count/len(losers)*100:.1f}%)")

# Comparaison directe
if winners and losers:
    print(f"\n{'='*80}")
    print(f"COMPARAISON WINNERS VS LOSERS")
    print(f"{'='*80}")

    print(f"\n📊 DIFFÉRENCES CLÉS:")
    if avg_entry_mc_l > 0:
        print(f"  MC entrée: ${avg_entry_mc_w:,.0f} (W) vs ${avg_entry_mc_l:,.0f} (L) = {(avg_entry_mc_w-avg_entry_mc_l)/avg_entry_mc_l*100:+.1f}%")
    else:
        print(f"  MC entrée: ${avg_entry_mc_w:,.0f} (W) vs ${avg_entry_mc_l:,.0f} (L)")

    if avg_txn_l > 0:
        print(f"  Transactions: {avg_txn_w:.1f} (W) vs {avg_txn_l:.1f} (L) = {(avg_txn_w-avg_txn_l)/avg_txn_l*100:+.1f}%")
    else:
        print(f"  Transactions: {avg_txn_w:.1f} (W) vs {avg_txn_l:.1f} (L) - Données manquantes")

    if avg_traders_l > 0:
        print(f"  Traders: {avg_traders_w:.1f} (W) vs {avg_traders_l:.1f} (L) = {(avg_traders_w-avg_traders_l)/avg_traders_l*100:+.1f}%")
    else:
        print(f"  Traders: {avg_traders_w:.1f} (W) vs {avg_traders_l:.1f} (L) - Données manquantes")

    if avg_buy_ratio_l > 0:
        print(f"  Buy ratio: {avg_buy_ratio_w*100:.1f}% (W) vs {avg_buy_ratio_l*100:.1f}% (L) = {(avg_buy_ratio_w-avg_buy_ratio_l)/avg_buy_ratio_l*100:+.1f}%")
    else:
        print(f"  Buy ratio: {avg_buy_ratio_w*100:.1f}% (W) vs {avg_buy_ratio_l*100:.1f}% (L) - Données manquantes")

    print(f"  Baleines: {avg_whale_w:.1f} (W) vs {avg_whale_l:.1f} (L)")
    print(f"  Elite wallets: {avg_elite_w:.1f} (W) vs {avg_elite_l:.1f} (L)")

# Afficher les meilleurs et pires trades
print(f"\n{'='*80}")
print(f"TOP 5 MEILLEURS TRADES")
print(f"{'='*80}")
sorted_trades = sorted(recent_trades, key=lambda x: x.get('profit_percent', 0), reverse=True)[:5]
for i, trade in enumerate(sorted_trades, 1):
    print(f"\n{i}. {trade.get('symbol', 'N/A')} - Profit: {trade.get('profit_percent', 0):.1f}%")
    print(f"   Raison: {trade.get('reason', 'N/A')}")
    print(f"   MC: ${trade.get('entry_mc', 0):,.0f} -> ${trade.get('exit_mc', 0):,.0f}")
    features = trade.get('entry_features', {})
    print(f"   Features: {features.get('txn', 0)} txn, {features.get('traders', 0)} traders, {features.get('buy_ratio', 0)*100:.0f}% buy, {features.get('whale_count', 0)} whales")

print(f"\n{'='*80}")
print(f"TOP 5 PIRES TRADES")
print(f"{'='*80}")
sorted_trades = sorted(recent_trades, key=lambda x: x.get('profit_percent', 0))[:5]
for i, trade in enumerate(sorted_trades, 1):
    print(f"\n{i}. {trade.get('symbol', 'N/A')} - Perte: {trade.get('profit_percent', 0):.1f}%")
    print(f"   Raison: {trade.get('reason', 'N/A')}")
    print(f"   MC: ${trade.get('entry_mc', 0):,.0f} -> ${trade.get('exit_mc', 0):,.0f}")
    features = trade.get('entry_features', {})
    print(f"   Features: {features.get('txn', 0)} txn, {features.get('traders', 0)} traders, {features.get('buy_ratio', 0)*100:.0f}% buy, {features.get('whale_count', 0)} whales")

# Recommandations
print(f"\n{'='*80}")
print(f"🎯 RECOMMANDATIONS D'AMÉLIORATION")
print(f"{'='*80}")

if winners and losers:
    print("\nBasé sur l'analyse:")

    # 1. MC d'entrée
    if avg_entry_mc_w < avg_entry_mc_l:
        print(f"\n1. ✅ PRIORITÉ HAUTE: Entrer PLUS TÔT")
        print(f"   Winners entrent à ${avg_entry_mc_w:,.0f} vs Losers à ${avg_entry_mc_l:,.0f}")
        print(f"   → Réduire le sweet spot max ou augmenter la vitesse de détection")

    # 2. Baleines
    if avg_whale_w > avg_whale_l * 1.2:
        print(f"\n2. ✅ PRIORITÉ HAUTE: Exiger PLUS de BALEINES")
        print(f"   Winners ont {avg_whale_w:.1f} baleines vs Losers {avg_whale_l:.1f}")
        print(f"   → Augmenter AI_MIN_WHALE_COUNT ou exiger minimum 2 baleines")

    # 3. Buy ratio
    if avg_buy_ratio_w > avg_buy_ratio_l * 1.1:
        print(f"\n3. ✅ PRIORITÉ MOYENNE: Augmenter buy ratio minimum")
        print(f"   Winners ont {avg_buy_ratio_w*100:.1f}% vs Losers {avg_buy_ratio_l*100:.1f}%")
        print(f"   → Augmenter AI_STRICT_BUY_RATIO de {avg_buy_ratio_l*100:.0f}% à {avg_buy_ratio_w*100:.0f}%")

    # 4. Traders
    if avg_traders_w > avg_traders_l * 1.2:
        print(f"\n4. ✅ PRIORITÉ MOYENNE: Exiger plus de traders uniques")
        print(f"   Winners ont {avg_traders_w:.1f} traders vs Losers {avg_traders_l:.1f}")
        print(f"   → Ajouter un filtre AI_MIN_TRADERS minimum")

print(f"\n{'='*80}")

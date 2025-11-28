"""
ANALYSE PROFONDE DES RUNNERS
Collecte toutes les données possibles pour trouver la formule mathématique
"""
import json
import requests
import time
from collections import defaultdict
from datetime import datetime

SOL_PRICE = 200

def get_token_trades(mint):
    """Récupérer tous les trades d'un token"""
    try:
        url = f"https://frontend-api.pump.fun/trades/all/{mint}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def analyze_wallet_age(wallet, all_trades):
    """Vérifier si un wallet est fresh (première transaction = ce token)"""
    # Si c'est la seule transaction du wallet dans nos données = probablement fresh
    wallet_txs = [t for t in all_trades if t.get('user') == wallet]
    return len(wallet_txs) == 1  # Fresh si 1 seule tx

def detect_bundles(trades_at_time):
    """Détecter les bundles (achats groupés au même timestamp)"""
    bundles = []
    timestamp_groups = defaultdict(list)

    for trade in trades_at_time:
        ts = trade.get('timestamp', 0)
        if trade.get('is_buy'):
            timestamp_groups[ts].append(trade)

    # Bundle = 3+ achats au même timestamp
    for ts, trades in timestamp_groups.items():
        if len(trades) >= 3:
            bundles.append({
                'timestamp': ts,
                'size': len(trades),
                'total_sol': sum(t.get('sol_amount', 0) for t in trades)
            })

    return bundles

def calculate_holders_distribution(trades):
    """Calculer la distribution des holders"""
    holdings = defaultdict(float)  # {wallet: balance}

    for trade in sorted(trades, key=lambda x: x.get('timestamp', 0)):
        wallet = trade.get('user')
        amount = trade.get('token_amount', 0)

        if trade.get('is_buy'):
            holdings[wallet] += amount
        else:
            holdings[wallet] -= amount

    # Retirer les wallets avec balance nulle
    active_holders = {w: bal for w, bal in holdings.items() if bal > 0}

    if not active_holders:
        return {
            'total_holders': 0,
            'top_10_percent': 0,
            'gini': 0
        }

    # Top 10 holders
    sorted_holders = sorted(active_holders.values(), reverse=True)
    total_supply = sum(sorted_holders)
    top_10 = sorted_holders[:10]
    top_10_percent = (sum(top_10) / total_supply * 100) if total_supply > 0 else 0

    return {
        'total_holders': len(active_holders),
        'top_10_percent': top_10_percent,
        'largest_holder_percent': (sorted_holders[0] / total_supply * 100) if sorted_holders else 0
    }

def analyze_snapshot_detailed(trades, start_time, duration_seconds):
    """Analyse détaillée à un moment donné"""
    end_time = start_time + duration_seconds
    snapshot_trades = [t for t in trades if start_time <= t.get('timestamp', 0) < end_time]

    if not snapshot_trades:
        return None

    buys = [t for t in snapshot_trades if t.get('is_buy')]
    sells = [t for t in snapshot_trades if not t.get('is_buy')]

    # Unique wallets
    unique_buyers = set(t.get('user') for t in buys if t.get('user'))
    unique_sellers = set(t.get('user') for t in sells if t.get('user'))
    unique_traders = unique_buyers | unique_sellers

    # Fresh wallets (approximation)
    fresh_wallets = sum(1 for t in snapshot_trades if analyze_wallet_age(t.get('user'), trades))

    # Bundles
    bundles = detect_bundles(snapshot_trades)

    # Volume
    buy_volume_sol = sum(t.get('sol_amount', 0) for t in buys)
    sell_volume_sol = sum(t.get('sol_amount', 0) for t in sells)
    total_volume_sol = buy_volume_sol + sell_volume_sol

    # Average sizes
    avg_buy_size = (buy_volume_sol / len(buys)) if buys else 0
    avg_sell_size = (sell_volume_sol / len(sells)) if sells else 0

    # Repeat buyers (wallets qui achètent 2+ fois)
    buyer_counts = defaultdict(int)
    for b in buys:
        buyer_counts[b.get('user')] += 1
    repeat_buyers = sum(1 for count in buyer_counts.values() if count >= 2)

    # Market cap à la fin de la période
    final_mc = snapshot_trades[-1].get('market_cap_sol', 0) * SOL_PRICE if snapshot_trades else 0

    # Holders distribution
    holders = calculate_holders_distribution(snapshot_trades)

    return {
        'txn': len(snapshot_trades),
        'buys': len(buys),
        'sells': len(sells),
        'buy_ratio': len(buys) / len(snapshot_trades) if snapshot_trades else 0,

        # Traders
        'unique_traders': len(unique_traders),
        'unique_buyers': len(unique_buyers),
        'unique_sellers': len(unique_sellers),

        # Fresh wallets
        'fresh_wallets': fresh_wallets,
        'fresh_wallet_percent': (fresh_wallets / len(unique_traders) * 100) if unique_traders else 0,

        # Bundles
        'bundles_count': len(bundles),
        'bundles_total_size': sum(b['size'] for b in bundles),

        # Volume
        'volume_sol': total_volume_sol,
        'volume_usd': total_volume_sol * SOL_PRICE,
        'buy_volume_sol': buy_volume_sol,
        'sell_volume_sol': sell_volume_sol,

        # Average sizes
        'avg_buy_size_sol': avg_buy_size,
        'avg_sell_size_sol': avg_sell_size,
        'buy_sell_size_ratio': (avg_buy_size / avg_sell_size) if avg_sell_size > 0 else 0,

        # Repeat behavior
        'repeat_buyers': repeat_buyers,
        'repeat_buyer_percent': (repeat_buyers / len(unique_buyers) * 100) if unique_buyers else 0,

        # Market cap
        'mc_usd': final_mc,

        # Holders
        'holders': holders['total_holders'],
        'top_10_holder_percent': holders['top_10_percent'],
        'largest_holder_percent': holders['largest_holder_percent']
    }

def analyze_runner_complete(runner_data):
    """Analyse complète d'un RUNNER avec toutes les données"""
    mint = runner_data.get('mint')
    symbol = runner_data.get('symbol', 'Unknown')

    print(f"\n{'='*80}")
    print(f"Analyse profonde: {symbol}")
    print(f"Mint: {mint}")
    print(f"{'='*80}")

    # Récupérer tous les trades
    trades = get_token_trades(mint)

    if not trades or len(trades) < 10:
        print(f"  [X] Pas assez de trades: {len(trades) if trades else 0}")
        return None

    print(f"  [OK] {len(trades)} trades recuperes")

    # Trier par timestamp
    sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', 0))
    start_time = sorted_trades[0].get('timestamp', 0)

    # Analyser à différents intervalles
    snapshots = {}
    intervals = [
        ('10s', 10),
        ('15s', 15),
        ('20s', 20),
        ('30s', 30),
        ('40s', 40),
        ('1min', 60),
        ('2min', 120),
        ('5min', 300)
    ]

    for label, duration in intervals:
        snapshot = analyze_snapshot_detailed(sorted_trades, start_time, duration)
        if snapshot:
            snapshots[label] = snapshot
            print(f"  [+] {label}: {snapshot['txn']} txn, {snapshot['buy_ratio']*100:.1f}% buys, {snapshot['fresh_wallet_percent']:.1f}% fresh")

    # Market cap final
    final_mc = sorted_trades[-1].get('market_cap_sol', 0) * SOL_PRICE

    return {
        'symbol': symbol,
        'mint': mint,
        'total_trades': len(sorted_trades),
        'final_mc_usd': final_mc,
        'snapshots': snapshots,
        'analyzed_at': datetime.now().isoformat()
    }

def main():
    print("\n" + "="*80)
    print("ANALYSE PROFONDE DES RUNNERS")
    print("="*80)

    # Charger les données du bot
    try:
        with open('bot_data.json', 'r') as f:
            bot_data = json.load(f)
    except:
        print("\n❌ Impossible de charger bot_data.json")
        return

    # Récupérer tous les runners
    completed = bot_data.get('completed', [])
    runners = [t for t in completed if t.get('is_runner', False)]

    print(f"\n{len(runners)} RUNNERS trouvés dans bot_data.json")

    if not runners:
        print("\n[!] Aucun runner a analyser. Laisse le bot tourner pour collecter des donnees.")
        return

    # Analyser chaque runner
    detailed_runners = []

    for i, runner in enumerate(runners, 1):
        print(f"\n[{i}/{len(runners)}]", end=" ")

        result = analyze_runner_complete(runner)

        if result:
            detailed_runners.append(result)

        # Rate limiting
        time.sleep(0.5)

    # Sauvegarder les résultats
    output_file = 'runners_detailed_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(detailed_runners, f, indent=2)

    print(f"\n{'='*80}")
    print(f"ANALYSE TERMINÉE!")
    print(f"{'='*80}")
    print(f"\n{len(detailed_runners)} runners analysés en détail")
    print(f"Résultats sauvegardés: {output_file}")

    # Afficher un résumé
    if detailed_runners:
        print(f"\n{'='*80}")
        print("RÉSUMÉ DES PATTERNS DÉCOUVERTS:")
        print(f"{'='*80}")

        # Moyennes à 15s
        snapshots_15s = [r['snapshots']['15s'] for r in detailed_runners if '15s' in r.get('snapshots', {})]

        if snapshots_15s:
            avg_fresh_15s = sum(s['fresh_wallet_percent'] for s in snapshots_15s) / len(snapshots_15s)
            avg_bundles_15s = sum(s['bundles_count'] for s in snapshots_15s) / len(snapshots_15s)
            avg_repeat_15s = sum(s['repeat_buyer_percent'] for s in snapshots_15s) / len(snapshots_15s)
            avg_top10_15s = sum(s['top_10_holder_percent'] for s in snapshots_15s) / len(snapshots_15s)

            print(f"\nPattern RUNNERS @ 15s (moyenne):")
            print(f"  Fresh wallets: {avg_fresh_15s:.1f}%")
            print(f"  Bundles: {avg_bundles_15s:.1f}")
            print(f"  Repeat buyers: {avg_repeat_15s:.1f}%")
            print(f"  Top 10 holders: {avg_top10_15s:.1f}% du supply")

if __name__ == "__main__":
    main()

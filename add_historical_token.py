"""
Script pour ajouter un token historique aux donnees d'entrainement
Recupere les transactions depuis la creation et reconstitue les snapshots
"""
import requests
import json
import time
from datetime import datetime

MINT = "8fHv8DNtXyfEwiCyRyxcu9ukwGADmP7CHHCYj9kGpump"
SOL_PRICE_USD = 200

def get_token_trades():
    """Recuperer les trades depuis PumpPortal API"""
    try:
        url = f"https://pumpportal.fun/api/trades/{MINT}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            trades = response.json()
            return trades
        else:
            print(f"[ERROR] API returned status {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] Failed to fetch trades: {e}")
        return None

def calculate_snapshot(trades, max_age_seconds, creation_time):
    """Calculer les metriques pour une periode"""
    # Filtrer les trades dans la periode
    trades_in_period = [
        t for t in trades
        if (t['timestamp'] - creation_time) <= max_age_seconds
    ]

    if not trades_in_period:
        return {
            'txn': 0,
            'buys': 0,
            'sells': 0,
            'buy_ratio': 0,
            'traders': 0
        }

    buys = [t for t in trades_in_period if t['is_buy']]
    sells = [t for t in trades_in_period if not t['is_buy']]
    unique_traders = len(set(t['user'] for t in trades_in_period))

    return {
        'txn': len(trades_in_period),
        'buys': len(buys),
        'sells': len(sells),
        'buy_ratio': len(buys) / len(trades_in_period) if trades_in_period else 0,
        'traders': unique_traders
    }

def get_mc_at_time(trades, target_time):
    """Obtenir la market cap a un moment donne"""
    relevant_trades = [t for t in trades if t['timestamp'] <= target_time]
    if relevant_trades:
        # Prendre le dernier trade avant ce temps
        last_trade = sorted(relevant_trades, key=lambda x: x['timestamp'])[-1]
        return last_trade.get('market_cap_sol', 0) * SOL_PRICE_USD
    return 0

def main():
    print(f"[INFO] Recuperation des trades pour {MINT}...")

    trades = get_token_trades()

    if not trades or len(trades) == 0:
        print("[ERROR] Aucun trade trouve")
        return

    # Trier par timestamp
    trades = sorted(trades, key=lambda x: x['timestamp'])
    creation_time = trades[0]['timestamp']

    print(f"[INFO] {len(trades)} trades recuperes")
    print(f"[INFO] Token cree a: {datetime.fromtimestamp(creation_time)}")

    # Calculer les snapshots
    snapshot_15s = calculate_snapshot(trades, 15, creation_time)
    snapshot_20s = calculate_snapshot(trades, 20, creation_time)
    snapshot_30s = calculate_snapshot(trades, 30, creation_time)
    snapshot_1min = calculate_snapshot(trades, 60, creation_time)

    # Market caps aux differents moments
    mc_15s = get_mc_at_time(trades, creation_time + 15)
    mc_20s = get_mc_at_time(trades, creation_time + 20)
    mc_30s = get_mc_at_time(trades, creation_time + 30)
    mc_1min = get_mc_at_time(trades, creation_time + 60)
    mc_final = trades[-1].get('market_cap_sol', 0) * SOL_PRICE_USD

    snapshot_15s['mc'] = mc_15s
    snapshot_20s['mc'] = mc_20s
    snapshot_30s['mc'] = mc_30s
    snapshot_1min['mc'] = mc_1min

    # Afficher les resultats
    print(f"\n{'='*60}")
    print(f"[ANALYSE] Token: {trades[0].get('symbol', '???')}")
    print(f"{'='*60}")
    print(f"15s:  ${mc_15s:,.0f} | {snapshot_15s['txn']} txn | {snapshot_15s['buy_ratio']*100:.1f}% buys | {snapshot_15s['traders']} traders")
    print(f"20s:  ${mc_20s:,.0f} | {snapshot_20s['txn']} txn | {snapshot_20s['buy_ratio']*100:.1f}% buys | {snapshot_20s['traders']} traders")
    print(f"30s:  ${mc_30s:,.0f} | {snapshot_30s['txn']} txn | {snapshot_30s['buy_ratio']*100:.1f}% buys | {snapshot_30s['traders']} traders")
    print(f"1min: ${mc_1min:,.0f} | {snapshot_1min['txn']} txn | {snapshot_1min['buy_ratio']*100:.1f}% buys | {snapshot_1min['traders']} traders")
    print(f"Final: ${mc_final:,.0f}")
    print(f"{'='*60}")

    # Creer l'entree pour bot_data.json
    is_runner = mc_final >= 15000

    token_data = {
        'symbol': trades[0].get('symbol', '???'),
        'mint': MINT,
        '15s': snapshot_15s,
        '20s': snapshot_20s,
        '30s': snapshot_30s,
        '1min': snapshot_1min,
        'final_mc': mc_final,
        'is_runner': is_runner,
        'source': 'historical'  # Marquer comme donnee historique
    }

    # Charger bot_data.json
    try:
        with open('bot_data.json', 'r') as f:
            data = json.load(f)
    except:
        data = {
            'tokens': [],
            'completed': [],
            'runners': [],
            'flops': [],
            'alerts': [],
            'stats': {'total_tokens': 0, 'total_runners': 0, 'total_flops': 0, 'win_rate': 0}
        }

    # Ajouter le token
    data['completed'].append(token_data)

    # Recalculer les stats
    runners = [a for a in data['completed'] if a.get('is_runner', False)]
    flops = [a for a in data['completed'] if not a.get('is_runner', False)]

    data['runners'] = runners
    data['flops'] = flops
    data['stats'] = {
        'total_tokens': len(data['completed']),
        'total_runners': len(runners),
        'total_flops': len(flops),
        'win_rate': (len(runners) / len(data['completed']) * 100) if data['completed'] else 0
    }

    # Sauvegarder
    with open('bot_data.json', 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n[SUCCESS] Token ajoute aux donnees!")
    print(f"[INFO] Status: {'RUNNER' if is_runner else 'FLOP'}")
    print(f"[INFO] Total tokens: {data['stats']['total_tokens']}")
    print(f"[INFO] Total runners: {data['stats']['total_runners']}")
    print(f"[INFO] Win rate: {data['stats']['win_rate']:.2f}%")

if __name__ == "__main__":
    main()

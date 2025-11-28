"""
Ajouter manuellement un token au fichier de donnees
Usage: python add_manual_token.py <mint_address>
"""
import sys
import json
import requests
import time

SOL_PRICE = 200

def get_token_trades(mint):
    """Recuperer tous les trades d'un token"""
    try:
        url = f"https://frontend-api.pump.fun/trades/all/{mint}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def get_token_info(mint):
    """Recuperer les infos du token"""
    try:
        url = f"https://frontend-api.pump.fun/coins/{mint}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def analyze_token_snapshots(trades):
    """Analyser le token a differents intervalles"""
    if not trades or len(trades) < 10:
        return None

    # Trier par timestamp
    sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', 0))
    start_time = sorted_trades[0].get('timestamp', 0)

    snapshots = {}
    intervals = [('15s', 15), ('30s', 30), ('1min', 60), ('5min', 300)]

    for label, duration in intervals:
        end_time = start_time + duration
        period_trades = [t for t in sorted_trades if t.get('timestamp', 0) <= end_time]

        if period_trades:
            buys = sum(1 for t in period_trades if t.get('is_buy'))
            sells = len(period_trades) - buys

            traders = set(t.get('user') for t in period_trades if t.get('user'))

            final_mc = period_trades[-1].get('market_cap_sol', 0) * SOL_PRICE

            snapshots[label] = {
                'txn': len(period_trades),
                'buys': buys,
                'sells': sells,
                'buy_ratio': buys / len(period_trades) if period_trades else 0,
                'traders': len(traders),
                'mc': final_mc
            }

    # Market cap final
    final_mc = sorted_trades[-1].get('market_cap_sol', 0) * SOL_PRICE

    return {
        'snapshots': snapshots,
        'final_mc': final_mc,
        'total_trades': len(sorted_trades)
    }

def add_token_to_data(mint):
    """Ajouter un token aux donnees"""
    print(f"\n{'='*80}")
    print(f"AJOUT MANUEL D'UN TOKEN")
    print(f"{'='*80}")
    print(f"\nMint: {mint}")

    # Recuperer les infos
    print("\n[1/3] Recuperation des infos du token...")
    token_info = get_token_info(mint)

    if not token_info:
        print("  [ERREUR] Impossible de recuperer les infos du token")
        return False

    symbol = token_info.get('symbol', 'Unknown')
    print(f"  [OK] Symbol: {symbol}")

    # Recuperer les trades
    print("\n[2/3] Recuperation des trades...")
    trades = get_token_trades(mint)

    if not trades or len(trades) < 10:
        print(f"  [ERREUR] Pas assez de trades: {len(trades) if trades else 0}")
        return False

    print(f"  [OK] {len(trades)} trades recuperes")

    # Analyser
    print("\n[3/3] Analyse des snapshots...")
    analysis = analyze_token_snapshots(trades)

    if not analysis:
        print("  [ERREUR] Echec de l'analyse")
        return False

    final_mc = analysis['final_mc']
    is_runner = final_mc >= 15000

    print(f"  [OK] Market cap final: ${final_mc:,.0f}")
    print(f"  [OK] Status: {'RUNNER' if is_runner else 'FLOP'}")

    # Preparer les donnees
    token_data = {
        'symbol': symbol,
        'mint': mint,
        'final_mc': final_mc,
        'total_trades': analysis['total_trades'],
        'is_runner': is_runner,
        '15s': analysis['snapshots'].get('15s', {}),
        '30s': analysis['snapshots'].get('30s', {}),
        '1min': analysis['snapshots'].get('1min', {}),
        '5min': analysis['snapshots'].get('5min', {})
    }

    # Charger bot_data.json
    try:
        with open('bot_data.json', 'r') as f:
            bot_data = json.load(f)
    except:
        bot_data = {
            'tokens': [],
            'completed': [],
            'runners': [],
            'flops': [],
            'alerts': [],
            'stats': {
                'total_tokens': 0,
                'total_runners': 0,
                'total_flops': 0,
                'win_rate': 0
            }
        }

    # Verifier si le token existe deja
    existing = [t for t in bot_data.get('completed', []) if t.get('mint') == mint]
    if existing:
        print(f"\n  [!] Ce token existe deja dans bot_data.json")
        return False

    # Ajouter aux donnees
    bot_data['completed'].append(token_data)

    # Mettre a jour les stats
    runners = [t for t in bot_data['completed'] if t.get('is_runner')]
    flops = [t for t in bot_data['completed'] if not t.get('is_runner')]

    bot_data['runners'] = runners[-20:]
    bot_data['flops'] = flops[-20:]
    bot_data['stats'] = {
        'total_tokens': len(bot_data['completed']),
        'total_runners': len(runners),
        'total_flops': len(flops),
        'win_rate': (len(runners) / len(bot_data['completed']) * 100) if bot_data['completed'] else 0
    }

    # Sauvegarder
    with open('bot_data.json', 'w') as f:
        json.dump(bot_data, f, indent=2)

    print(f"\n{'='*80}")
    print(f"TOKEN AJOUTE AVEC SUCCES!")
    print(f"{'='*80}")
    print(f"\nStats mises a jour:")
    print(f"  Total tokens: {bot_data['stats']['total_tokens']}")
    print(f"  Runners: {bot_data['stats']['total_runners']}")
    print(f"  Flops: {bot_data['stats']['total_flops']}")
    print(f"  Win rate: {bot_data['stats']['win_rate']:.1f}%")

    # Afficher le snapshot 15s
    s15 = token_data.get('15s', {})
    if s15:
        print(f"\nSnapshot 15s:")
        print(f"  {s15.get('txn', 0)} txn | {s15.get('buy_ratio', 0)*100:.1f}% buys | {s15.get('traders', 0)} traders")

    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("\nUsage: python add_manual_token.py <mint_address>")
        print("\nExemple:")
        print("  python add_manual_token.py D5TqcssMbVADExMyvpL7HXHuLSzvVNufCiCAvQG6pump")
        sys.exit(1)

    mint = sys.argv[1]

    success = add_token_to_data(mint)

    if not success:
        sys.exit(1)

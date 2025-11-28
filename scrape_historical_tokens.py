"""
Scraper pour analyser 1000+ tokens historiques de Pump.fun
Trouver les patterns des tokens qui migrent ($50K+) vs ceux qui flop
"""
import requests
import json
import time
from datetime import datetime

def get_token_history(mint):
    """Récupérer l'historique d'un token"""
    try:
        # API Pump.fun pour les données historiques
        url = f"https://frontend-api.pump.fun/trades/all/{mint}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            trades = response.json()
            return trades
        return None
    except Exception as e:
        return None

def analyze_token_metrics(trades):
    """Analyser les métriques d'un token depuis ses trades"""
    if not trades:
        return None

    # Trier par timestamp
    sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', 0))

    # Calculer les snapshots à 15s, 30s, 1min, 5min
    first_ts = sorted_trades[0].get('timestamp', 0)

    snapshots = {
        '15s': {'end': first_ts + 15},
        '30s': {'end': first_ts + 30},
        '1min': {'end': first_ts + 60},
        '5min': {'end': first_ts + 300}
    }

    for period, info in snapshots.items():
        period_trades = [t for t in sorted_trades if t.get('timestamp', 0) <= info['end']]

        if period_trades:
            buys = sum(1 for t in period_trades if t.get('is_buy'))
            sells = len(period_trades) - buys

            snapshots[period]['txn'] = len(period_trades)
            snapshots[period]['buys'] = buys
            snapshots[period]['sells'] = sells
            snapshots[period]['buy_ratio'] = buys / len(period_trades) if period_trades else 0

            # Traders uniques
            traders = set(t.get('user') for t in period_trades if t.get('user'))
            snapshots[period]['traders'] = len(traders)

            # Market cap final de cette période
            if period_trades:
                last_trade = period_trades[-1]
                snapshots[period]['mc'] = last_trade.get('market_cap_sol', 0)

    # Market cap final (dernier trade)
    final_mc = sorted_trades[-1].get('market_cap_sol', 0) if sorted_trades else 0

    return {
        'snapshots': snapshots,
        'final_mc': final_mc,
        'total_trades': len(sorted_trades)
    }

def scrape_recent_tokens(limit=1000):
    """Scraper les tokens récents depuis l'API Pump.fun"""
    print(f"\n{'='*80}")
    print(f"SCRAPING {limit} TOKENS HISTORIQUES...")
    print(f"{'='*80}\n")

    tokens_data = []

    # API pour récupérer les tokens récents
    try:
        url = "https://frontend-api.pump.fun/coins"
        params = {
            'limit': limit,
            'offset': 0,
            'sort': 'created_timestamp',
            'order': 'DESC'
        }

        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            coins = response.json()

            print(f"Trouvé {len(coins)} tokens à analyser...")

            for i, coin in enumerate(coins[:limit], 1):
                mint = coin.get('mint')
                symbol = coin.get('symbol', 'Unknown')

                if i % 10 == 0:
                    print(f"  [{i}/{limit}] Analysé: {symbol}...")

                # Récupérer les trades
                trades = get_token_history(mint)

                if trades and len(trades) > 10:  # Au moins 10 trades
                    metrics = analyze_token_metrics(trades)

                    if metrics:
                        token_data = {
                            'symbol': symbol,
                            'mint': mint,
                            'final_mc': metrics['final_mc'],
                            'total_trades': metrics['total_trades'],
                            '15s': metrics['snapshots'].get('15s', {}),
                            '30s': metrics['snapshots'].get('30s', {}),
                            '1min': metrics['snapshots'].get('1min', {}),
                            '5min': metrics['snapshots'].get('5min', {})
                        }

                        tokens_data.append(token_data)

                # Rate limiting
                time.sleep(0.1)

            # Sauvegarder
            output_file = 'historical_tokens_analysis.json'
            with open(output_file, 'w') as f:
                json.dump(tokens_data, f, indent=2)

            print(f"\n{'='*80}")
            print(f"SCRAPING TERMINÉ!")
            print(f"{'='*80}")
            print(f"\nTokens analysés: {len(tokens_data)}")
            print(f"Sauvegardé dans: {output_file}")

            # Analyse rapide
            analyze_quick_stats(tokens_data)

    except Exception as e:
        print(f"\nERREUR: {e}")

def analyze_quick_stats(tokens_data):
    """Analyse rapide des données collectées"""
    print(f"\n{'='*80}")
    print("ANALYSE RAPIDE:")
    print(f"{'='*80}")

    # Convertir SOL market cap en USD (environ $200/SOL)
    SOL_PRICE = 200

    tokens_50k = [t for t in tokens_data if t['final_mc'] * SOL_PRICE >= 50000]
    tokens_45k = [t for t in tokens_data if t['final_mc'] * SOL_PRICE >= 45000]
    tokens_15k = [t for t in tokens_data if t['final_mc'] * SOL_PRICE >= 15000]

    print(f"\nTokens $50K+ (Migration): {len(tokens_50k)} ({len(tokens_50k)/len(tokens_data)*100:.1f}%)")
    print(f"Tokens $45K+:             {len(tokens_45k)} ({len(tokens_45k)/len(tokens_data)*100:.1f}%)")
    print(f"Tokens $15K+ (Runners):   {len(tokens_15k)} ({len(tokens_15k)/len(tokens_data)*100:.1f}%)")

    if tokens_50k:
        print(f"\n{'='*80}")
        print(f"TOP TOKENS QUI ONT MIGRÉ ($50K+):")
        print(f"{'='*80}")
        for t in sorted(tokens_50k, key=lambda x: x['final_mc'], reverse=True)[:10]:
            s15 = t.get('15s', {})
            print(f"\n{t['symbol']} | ${t['final_mc']*SOL_PRICE:,.0f}")
            print(f"  15s: {s15.get('txn',0):3}txn | {s15.get('buy_ratio',0)*100:5.1f}% buys | {s15.get('traders',0)} traders")

if __name__ == "__main__":
    scrape_recent_tokens(1000)

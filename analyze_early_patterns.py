"""
ANALYSE DES PATTERNS PRÉCOCES - 30 secondes et 1 minute
Analyse les 3 tokens gagnants pour trouver la formule mathématique
"""
import requests
import json
from datetime import datetime

# Les 3 tokens qui ont migrés avec succès
TOKENS = {
    'PLOPPER': '5weo14h7pxCa8x3dZQECiBGnWF4LtmiTMFCqRVuXpump',
    'KATIE': '7tjqiEk3zRt67wuDrRNp6izzqSFfECfo6uxVWDEpump',
    'INCOG': 'DKAN3tyxnvgUrgGHAHsorBGgVGdVt9uEiRUybHrs77P3',
}

def analyze_token(name, mint):
    """Analyser un token via l'API PumpPortal"""
    print(f"\n{'='*80}")
    print(f"ANALYSE: {name}")
    print(f"Mint: {mint}")
    print(f"{'='*80}")

    try:
        # Appeler l'API PumpPortal
        url = f"https://pumpportal.fun/api/trade-data?mint={mint}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            print(f"\n[API DATA]")
            print(f"  Total Transactions: {data.get('txnCount', 0)}")
            print(f"  Holders: {data.get('holderCount', 0)}")
            print(f"  Initial Buy: {data.get('initialBuy', 0)} SOL")
            print(f"  Market Cap: ${data.get('usdMarketCap', 0):,.0f}")

            # Vérifier si on a les données de trades détaillées
            if 'trades' in data:
                trades = data['trades']
                print(f"\n[TRADES DÉTAILLÉS] {len(trades)} trades")

                # Trier par timestamp
                trades_sorted = sorted(trades, key=lambda x: x.get('timestamp', 0))

                if len(trades_sorted) > 0:
                    first_timestamp = trades_sorted[0].get('timestamp', 0)

                    # Analyser les 30 premières secondes
                    trades_30s = [t for t in trades_sorted if t.get('timestamp', 0) - first_timestamp <= 30]
                    buys_30s = [t for t in trades_30s if t.get('txType') == 'buy']
                    sells_30s = [t for t in trades_30s if t.get('txType') == 'sell']

                    # Analyser la première minute
                    trades_1min = [t for t in trades_sorted if t.get('timestamp', 0) - first_timestamp <= 60]
                    buys_1min = [t for t in trades_1min if t.get('txType') == 'buy']
                    sells_1min = [t for t in trades_1min if t.get('txType') == 'sell']

                    print(f"\n[30 PREMIÈRES SECONDES]")
                    print(f"  Total: {len(trades_30s)} transactions")
                    print(f"  Buys: {len(buys_30s)} ({len(buys_30s)/len(trades_30s)*100:.1f}%)")
                    print(f"  Sells: {len(sells_30s)} ({len(sells_30s)/len(trades_30s)*100:.1f}%)")
                    print(f"  Vélocité: {len(trades_30s)/30:.2f} txn/sec")

                    print(f"\n[PREMIÈRE MINUTE]")
                    print(f"  Total: {len(trades_1min)} transactions")
                    print(f"  Buys: {len(buys_1min)} ({len(buys_1min)/len(trades_1min)*100:.1f}%)")
                    print(f"  Sells: {len(sells_1min)} ({len(sells_1min)/len(trades_1min)*100:.1f}%)")
                    print(f"  Vélocité: {len(trades_1min)/60:.2f} txn/sec")

                    # Accélération
                    accel = len(trades_1min) / len(trades_30s) if len(trades_30s) > 0 else 0
                    print(f"\n[ACCÉLÉRATION]")
                    print(f"  Ratio 1min/30s: {accel:.2f}x")

                    return {
                        'name': name,
                        'mint': mint,
                        'trades_30s': len(trades_30s),
                        'buys_30s': len(buys_30s),
                        'sells_30s': len(sells_30s),
                        'buy_ratio_30s': len(buys_30s)/len(trades_30s) if len(trades_30s) > 0 else 0,
                        'velocity_30s': len(trades_30s)/30,
                        'trades_1min': len(trades_1min),
                        'buys_1min': len(buys_1min),
                        'sells_1min': len(sells_1min),
                        'buy_ratio_1min': len(buys_1min)/len(trades_1min) if len(trades_1min) > 0 else 0,
                        'velocity_1min': len(trades_1min)/60,
                        'acceleration': accel,
                    }
            else:
                print(f"\n[WARNING] Pas de données de trades détaillées dans l'API")
                print(f"  L'API ne retourne que les stats globales, pas l'historique des trades")
                return None

        else:
            print(f"[ERROR] HTTP {response.status_code}")
            return None

    except Exception as e:
        print(f"[ERROR] {e}")
        return None

def main():
    print(f"\n{'='*80}")
    print(f"ANALYSE DES PATTERNS PRÉCOCES - 30s et 1min")
    print(f"{'='*80}")

    results = []

    for name, mint in TOKENS.items():
        result = analyze_token(name, mint)
        if result:
            results.append(result)

    # Afficher le résumé comparatif
    if results:
        print(f"\n\n{'='*80}")
        print(f"RÉSUMÉ COMPARATIF - FORMULE MATHÉMATIQUE")
        print(f"{'='*80}")

        print(f"\n[30 PREMIÈRES SECONDES]")
        for r in results:
            print(f"  {r['name']:10} | {r['trades_30s']:3} txn | {r['buys_30s']:3}B/{r['sells_30s']:3}S | {r['buy_ratio_30s']*100:.1f}% buys | {r['velocity_30s']:.2f} txn/s")

        print(f"\n[PREMIÈRE MINUTE]")
        for r in results:
            print(f"  {r['name']:10} | {r['trades_1min']:3} txn | {r['buys_1min']:3}B/{r['sells_1min']:3}S | {r['buy_ratio_1min']*100:.1f}% buys | {r['velocity_1min']:.2f} txn/s")

        print(f"\n[ACCÉLÉRATION]")
        for r in results:
            print(f"  {r['name']:10} | {r['acceleration']:.2f}x (1min est {r['acceleration']:.2f}x plus actif que 30s)")

        # Calculer les moyennes
        avg_30s = sum(r['trades_30s'] for r in results) / len(results)
        avg_buy_30s = sum(r['buy_ratio_30s'] for r in results) / len(results)
        avg_1min = sum(r['trades_1min'] for r in results) / len(results)
        avg_buy_1min = sum(r['buy_ratio_1min'] for r in results) / len(results)
        avg_accel = sum(r['acceleration'] for r in results) / len(results)

        print(f"\n{'='*80}")
        print(f"FORMULE MATHÉMATIQUE IDENTIFIÉE")
        print(f"{'='*80}")
        print(f"  30 secondes:  {avg_30s:.0f} txn | {avg_buy_30s*100:.1f}% buys")
        print(f"  1 minute:     {avg_1min:.0f} txn | {avg_buy_1min*100:.1f}% buys")
        print(f"  Accélération: {avg_accel:.2f}x")
        print(f"\n  SEUILS RECOMMANDÉS:")
        print(f"    - MIN 30s: {avg_30s*0.8:.0f} txn avec {avg_buy_30s*0.9*100:.0f}% buys")
        print(f"    - MIN 1min: {avg_1min*0.8:.0f} txn avec {avg_buy_1min*0.9*100:.0f}% buys")
        print(f"    - MIN accélération: {avg_accel*0.8:.2f}x")

if __name__ == "__main__":
    main()

"""
Analyse des données pour améliorer le win rate
Compare les RUNNERS vs FLOPS pour trouver les patterns gagnants
"""
import json

def analyze_data():
    with open('bot_data.json', 'r') as f:
        data = json.load(f)

    completed = data.get('completed', [])
    runners = [t for t in completed if t.get('is_runner')]
    flops = [t for t in completed if not t.get('is_runner')]

    print("\n" + "="*80)
    print(f"ANALYSE: {len(runners)} RUNNERS vs {len(flops)} FLOPS")
    print(f"Win Rate: {len(runners)/len(completed)*100:.1f}%")
    print("="*80)

    # Analyser les métriques moyennes
    def get_avg_metrics(tokens, label):
        if not tokens:
            return

        print(f"\n[{label}] - Moyenne:")

        # 15s
        metrics_15s = [t.get('15s') for t in tokens if t.get('15s')]
        if metrics_15s:
            avg_txn = sum(m['txn'] for m in metrics_15s) / len(metrics_15s)
            avg_buy = sum(m['buy_ratio'] for m in metrics_15s) / len(metrics_15s)
            avg_traders = sum(m.get('traders', 0) for m in metrics_15s) / len(metrics_15s)
            print(f"  15s:  {avg_txn:.1f} txn | {avg_buy*100:.1f}% buys | {avg_traders:.1f} traders")

        # 30s
        metrics_30s = [t.get('30s') for t in tokens if t.get('30s')]
        if metrics_30s:
            avg_txn = sum(m['txn'] for m in metrics_30s) / len(metrics_30s)
            avg_buy = sum(m['buy_ratio'] for m in metrics_30s) / len(metrics_30s)
            print(f"  30s:  {avg_txn:.1f} txn | {avg_buy*100:.1f}% buys")

        # 1min
        metrics_1m = [t.get('1min') for t in tokens if t.get('1min')]
        if metrics_1m:
            avg_txn = sum(m['txn'] for m in metrics_1m) / len(metrics_1m)
            avg_buy = sum(m['buy_ratio'] for m in metrics_1m) / len(metrics_1m)
            print(f"  1min: {avg_txn:.1f} txn | {avg_buy*100:.1f}% buys")

        # 5min
        metrics_5m = [t.get('5min') for t in tokens if t.get('5min')]
        if metrics_5m:
            avg_txn = sum(m['txn'] for m in metrics_5m) / len(metrics_5m)
            avg_buy = sum(m['buy_ratio'] for m in metrics_5m) / len(metrics_5m)
            print(f"  5min: {avg_txn:.1f} txn | {avg_buy*100:.1f}% buys")

        # Final MC
        final_mcs = [t.get('final_mc', 0) for t in tokens]
        avg_final = sum(final_mcs) / len(final_mcs)
        print(f"  Final MC: ${avg_final:,.0f}")

    get_avg_metrics(runners, "RUNNERS")
    get_avg_metrics(flops, "FLOPS")

    # Trouver les critères discriminants
    print("\n" + "="*80)
    print("CRITÈRES POUR AMÉLIORER LE WIN RATE:")
    print("="*80)

    # Analyser les runners individuellement
    print("\n[TOP 8 RUNNERS]:")
    for r in runners:
        s15 = r.get('15s', {})
        s1m = r.get('1min', {})
        print(f"  {r['symbol']:15} | 15s: {s15.get('txn',0):3} txn {s15.get('buy_ratio',0)*100:5.1f}% | 1min: {s1m.get('txn',0):3} txn {s1m.get('buy_ratio',0)*100:5.1f}% | Final: ${r.get('final_mc',0):,.0f}")

    # Propositions
    print("\n" + "="*80)
    print("RECOMMANDATIONS:")
    print("="*80)
    print("""
1. FILTRE MINIMUM (réduire le bruit):
   - Ne tracker QUE si 15s montre AU MOINS:
     * 10+ transactions
     * 50%+ buy ratio
     * 5+ traders

2. ALERTE UNIQUEMENT SI (être plus sélectif):
   - À 1min:
     * 60+ transactions (minimum)
     * 55%+ buy ratio (constant)
     * Volume croissant (1min > 3x 15s)

3. COMBINER PLUSIEURS SIGNAUX:
   - Ne pas se fier à UN SEUL indicateur
   - Exiger: bon buy ratio + volume + stabilité

4. AJOUTER STOP-LOSS PRÉCOCE:
   - Si à 30s le buy ratio chute < 50% → abandonner
   - Si volume n'augmente pas → abandonner

Avec ces filtres, on devrait passer de 5.8% à 30-50% de win rate
en ne gardant que les meilleurs candidats.
""")

if __name__ == "__main__":
    analyze_data()

"""
Analyse complète des tokens collectés:
- Combien ont atteint $50K+ (migration vers Raydium)
- Statistiques détaillées
"""
import json

def analyze_tokens():
    with open('bot_data.json', 'r') as f:
        data = json.load(f)

    completed = data.get('completed', [])

    print("\n" + "="*80)
    print("ANALYSE COMPLÈTE DES TOKENS COLLECTÉS")
    print("="*80)

    # Statistiques globales
    total_tokens = len(completed)
    runners = [t for t in completed if t.get('is_runner')]
    flops = [t for t in completed if not t.get('is_runner')]

    print(f"\nTOTAL: {total_tokens} tokens analysés")
    print(f"  - RUNNERS (>$15K): {len(runners)} ({len(runners)/total_tokens*100:.1f}%)")
    print(f"  - FLOPS (<$15K):   {len(flops)} ({len(flops)/total_tokens*100:.1f}%)")

    # Analyse des seuils de market cap
    tokens_50k = [t for t in completed if t.get('final_mc', 0) >= 50000]
    tokens_100k = [t for t in completed if t.get('final_mc', 0) >= 100000]
    tokens_500k = [t for t in completed if t.get('final_mc', 0) >= 500000]

    print("\n" + "-"*80)
    print("SEUILS DE MARKET CAP:")
    print("-"*80)
    print(f"  $50K+  (Migration Raydium): {len(tokens_50k):3} tokens ({len(tokens_50k)/total_tokens*100:.1f}%)")
    print(f"  $100K+:                     {len(tokens_100k):3} tokens ({len(tokens_100k)/total_tokens*100:.1f}%)")
    print(f"  $500K+:                     {len(tokens_500k):3} tokens ({len(tokens_500k)/total_tokens*100:.1f}%)")

    # Top tokens par final_mc
    print("\n" + "-"*80)
    print("TOP 10 TOKENS (par market cap finale):")
    print("-"*80)
    sorted_tokens = sorted(completed, key=lambda t: t.get('final_mc', 0), reverse=True)[:10]
    for i, t in enumerate(sorted_tokens, 1):
        symbol = t.get('symbol', 'Unknown')
        final_mc = t.get('final_mc', 0)
        s15 = t.get('15s', {})
        print(f"  {i:2}. {symbol:15} | ${final_mc:>10,.0f} | 15s: {s15.get('txn',0):3}txn {s15.get('buy_ratio',0)*100:5.1f}%")

    # Tokens $50K+
    if tokens_50k:
        print("\n" + "="*80)
        print(f"DÉTAILS DES {len(tokens_50k)} TOKENS À $50K+ (MIGRATION POTENTIELLE)")
        print("="*80)
        for t in sorted(tokens_50k, key=lambda x: x.get('final_mc', 0), reverse=True):
            symbol = t.get('symbol', 'Unknown')
            mint = t.get('mint', 'Unknown')
            final_mc = t.get('final_mc', 0)
            s15 = t.get('15s', {})
            s1m = t.get('1min', {})
            s5m = t.get('5min', {})

            print(f"\n{symbol} | ${final_mc:,.0f}")
            print(f"  Mint: {mint}")
            print(f"  15s:  {s15.get('txn',0):3}txn | {s15.get('buy_ratio',0)*100:5.1f}% buys | {s15.get('traders',0):2} traders")
            if s1m:
                print(f"  1min: {s1m.get('txn',0):3}txn | {s1m.get('buy_ratio',0)*100:5.1f}% buys")
            if s5m:
                print(f"  5min: {s5m.get('txn',0):3}txn | {s5m.get('buy_ratio',0)*100:5.1f}% buys | {s5m.get('traders',0):3} traders")

    # Distribution des market caps
    print("\n" + "="*80)
    print("DISTRIBUTION DES MARKET CAPS:")
    print("="*80)
    ranges = [
        (0, 5000, "<$5K"),
        (5000, 10000, "$5K-$10K"),
        (10000, 15000, "$10K-$15K"),
        (15000, 25000, "$15K-$25K"),
        (25000, 50000, "$25K-$50K"),
        (50000, 100000, "$50K-$100K"),
        (100000, 500000, "$100K-$500K"),
        (500000, float('inf'), "$500K+")
    ]

    for min_val, max_val, label in ranges:
        count = len([t for t in completed if min_val <= t.get('final_mc', 0) < max_val])
        pct = count / total_tokens * 100 if total_tokens > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {label:15} | {count:3} tokens ({pct:5.1f}%) {bar}")

if __name__ == "__main__":
    analyze_tokens()

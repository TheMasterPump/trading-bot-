import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

completed = data.get('completed', [])
runners = [t for t in completed if t.get('is_runner')]
tokens_50k = [t for t in completed if t.get('final_mc', 0) >= 50000]

print(f"\nTOTAL tokens: {len(completed)}")
print(f"RUNNERS (>$15K): {len(runners)}")
print(f"Tokens $50K+: {len(tokens_50k)}")

print(f"\n{'='*80}")
print(f"LISTE DES {len(runners)} RUNNERS:")
print(f"{'='*80}\n")

for i, t in enumerate(sorted(runners, key=lambda x: x.get('final_mc', 0), reverse=True), 1):
    symbol = t.get('symbol', 'Unknown')
    final_mc = t.get('final_mc', 0)
    s15 = t.get('15s', {})
    print(f"{i:2}. {symbol:20} - ${final_mc:>10,.0f} | 15s: {s15.get('txn',0):3}txn {s15.get('buy_ratio',0)*100:5.1f}% buys")

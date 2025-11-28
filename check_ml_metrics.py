import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

all_tokens = d.get('runners', []) + d.get('flops', [])
print('=== VERIFICATION DES ML METRICS ===\n')
print(f'Total tokens: {len(all_tokens)}')

with_ml = [t for t in all_tokens if 'ml_metrics' in t and t.get('ml_metrics')]
print(f'Tokens avec ML metrics: {len(with_ml)}\n')

if with_ml:
    recent = with_ml[-1]
    print(f'Dernier token avec ML metrics:')
    print(f'  Symbol: {recent.get("symbol", "N/A")}')
    print(f'  Mint: {recent.get("mint", "N/A")[:12]}...')
    print(f'  Final MC: ${recent.get("final_mc", 0):,.0f}')
    print(f'  Is Runner: {recent.get("is_runner", False)}')
    print(f'\n  ML Metrics: {len(recent.get("ml_metrics", {}))} metriques calculees')

    ml = recent.get("ml_metrics", {})
    print(f'\n  Exemples de metriques:')
    for i, (key, value) in enumerate(list(ml.items())[:10]):
        print(f'    - {key}: {value}')
else:
    print('Aucun token avec ML metrics encore.')
    print('Le bot doit attendre 15 minutes avant de sauvegarder un token avec ml_metrics.')

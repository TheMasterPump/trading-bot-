import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Chercher dans les tokens actifs
tokens = data.get('tokens', [])

print(f'=== TOKENS ACTIFS (en cours d\'analyse) ===')
print(f'Total: {len(tokens)}')
print('')

# Chercher Michael
michael_active = [t for t in tokens if 'Michael' in t.get('symbol', '')]
if michael_active:
    for t in michael_active:
        print(f'{t.get("symbol")}: {t.get("mint")[:8]}... | MC actuelle: ${t.get("current_mc", 0):,.0f}')
        print(f'  Age: {t.get("age", 0):.1f}s | Early runner saved: {t.get("early_runner_saved", False)}')
else:
    print('Michael pas dans les tokens actifs')

print('')
print('=== TOP 10 TOKENS ACTIFS PAR MC ===')
sorted_tokens = sorted(tokens, key=lambda x: x.get('current_mc', 0), reverse=True)[:10]
for t in sorted_tokens:
    symbol = t.get('symbol', '???')
    mc = t.get('current_mc', 0)
    age = t.get('age', 0)
    early_saved = t.get('early_runner_saved', False)
    print(f'{symbol}: ${mc:,.0f} | Age: {age:.1f}s | Early saved: {early_saved}')

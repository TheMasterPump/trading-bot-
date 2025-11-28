import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Chercher le MAYHEM spécifique
mayhem = [r for r in data['completed'] if '3CyycxhN' in r.get('mint', '')]

if mayhem:
    print('MAYHEM 3CyycxhN TROUVE !')
    for r in mayhem:
        print(f"  Symbol: {r.get('symbol')}")
        print(f"  Mint: {r.get('mint')}")
        print(f"  Final MC: ${r.get('final_mc', 0):,.0f}")
        print(f"  Migration: {r.get('migration_detected', False)}")
else:
    print('MAYHEM 3CyycxhN PAS ENCORE ENREGISTRE')
    print('(Le bot a crash avant de sauvegarder)')

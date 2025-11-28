import json

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

runners = d.get('runners', [])
flops = d.get('flops', [])
total = len(runners) + len(flops)

print('=' * 80)
print('DATASET ACTUEL - RUNNERS & FLOPS')
print('=' * 80)

print(f'\n[STATISTIQUES]:')
print(f'   RUNNERS (succes): {len(runners)} tokens')
print(f'   FLOPS (echecs):   {len(flops)} tokens')
print(f'   TOTAL:            {total} tokens')

if len(flops) > 0:
    ratio = len(runners) / len(flops)
    print(f'   Ratio R/F:        {ratio:.1f}')

print(f'\n[OK] LES DEUX CATEGORIES SONT ENREGISTREES!')

print(f'\n[RUNNERS] (Final MC >= $40K):')
for i, r in enumerate(runners[:5], 1):
    symbol = r.get('symbol', 'N/A')
    final_mc = r.get('final_mc', 0)
    print(f'   {i}. {symbol:15} -> ${final_mc:,.0f}')
if len(runners) > 5:
    print(f'   ... et {len(runners) - 5} autres')

print(f'\n[FLOPS] (Final MC < $40K):')
for i, f in enumerate(flops[:5], 1):
    symbol = f.get('symbol', 'N/A')
    final_mc = f.get('final_mc', 0)
    print(f'   {i}. {symbol:15} -> ${final_mc:,.0f}')
if len(flops) > 5:
    print(f'   ... et {len(flops) - 5} autres')

print('\n' + '=' * 80)
print('POURQUOI LES DEUX SONT ESSENTIELS POUR L\'IA:')
print('=' * 80)
print('''
1. RUNNERS (label=1): L'IA apprend les patterns de SUCCES
   - Quelle velocite mene au succes?
   - Quand les whales entrent-elles?
   - Quel ratio buy/sell est bon?

2. FLOPS (label=0): L'IA apprend les patterns d'ECHEC
   - Quels signaux indiquent un echec?
   - Comment reconnaitre un dump?
   - Quand sortir?

Sans les DEUX categories, l'IA ne peut pas faire la difference!
C'est comme apprendre a reconnaitre un chat sans avoir vu de chien.

[OBJECTIF]: Collecter 100-200 tokens (50% runners, 50% flops)
            pour un dataset balance et performant.
''')

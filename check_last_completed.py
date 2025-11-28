import json
import time

with open('bot_data.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

runners = d.get('runners', [])
flops = d.get('flops', [])
all_completed = runners + flops

if not all_completed:
    print('Aucun token complete encore')
    exit()

# Dernier token complete (le plus recent)
last = all_completed[-1]

now = time.time()
created = last.get('created_at', now)
age_seconds = int(now - created)
age_minutes = age_seconds // 60
age_hours = age_minutes // 60

print('='*80)
print('DERNIER TOKEN COMPLETE')
print('='*80)

print(f'\n[INFORMATIONS]')
print(f'Symbol: {last.get("symbol", "N/A")}')
print(f'Mint: {last.get("mint", "N/A")[:40]}...')
print(f'Classification: {"RUNNER" if last.get("is_runner") else "FLOP"}')
print(f'Final MC: ${last.get("final_mc", 0):,.2f}')

print(f'\n[TIMING]')
if age_hours > 0:
    print(f'Complete il y a: {age_hours}h {age_minutes % 60}min')
else:
    print(f'Complete il y a: {age_minutes} minutes')
print(f'(soit {age_seconds} secondes)')

print(f'\n[ANALYSE]')
if age_minutes > 30:
    print('ATTENTION: Ca fait plus de 30 minutes!')
    print('Le bot detecte peut-etre des tokens mais ne les complete plus.')
    print('Raisons possibles:')
    print('  - Tous les tokens recents sont trop jeunes (< 15 min)')
    print('  - Le bot a un probleme pour finaliser les tokens')
elif age_minutes > 15:
    print('Normal - Les tokens detectes recemment sont encore en cours')
    print('Ils seront completes dans quelques minutes')
else:
    print('PARFAIT - Le bot complete regulierement des tokens!')

print('\n' + '='*80)

import os
import time

file_path = 'bot_data.json'
file_mtime = os.path.getmtime(file_path)
now = time.time()
age_seconds = int(now - file_mtime)
age_minutes = age_seconds // 60

print('='*80)
print('DERNIERE MODIFICATION DE bot_data.json')
print('='*80)

if age_minutes > 0:
    print(f'\nFichier modifie il y a: {age_minutes} minutes')
else:
    print(f'\nFichier modifie il y a: {age_seconds} secondes')

print(f'\nExplication:')
print(f'  - Le bot sauvegarde toutes les 30 secondes')
if age_seconds < 60:
    print(f'  - PARFAIT: Le bot est actif et sauvegarde!')
elif age_minutes < 5:
    print(f'  - Normal: Le bot tourne bien')
else:
    print(f'  - ATTENTION: Le bot ne sauvegarde plus depuis {age_minutes} min!')
    print(f'  - Il y a peut-etre un probleme')

print('\n' + '='*80)

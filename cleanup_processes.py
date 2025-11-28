"""
Script pour nettoyer tous les processus Python inutiles
Garde SEULEMENT le pattern_discovery_bot.py le plus récent
"""
import subprocess
import time

print("="*80)
print("NETTOYAGE DES PROCESSUS PYTHON")
print("="*80)

# Liste tous les processus Python
result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                       capture_output=True, text=True)

lines = result.stdout.strip().split('\n')[1:]  # Skip header
pids = []

for line in lines:
    if 'python.exe' in line:
        parts = line.split(',')
        if len(parts) >= 2:
            pid = parts[1].strip('"')
            pids.append(pid)

print(f"\nProcessus Python trouvés: {len(pids)}")

# Identifier le processus pattern_discovery_bot actuel
# On va garder le dernier lancé (PID le plus élevé généralement)
print("\nIdentification du pattern_discovery_bot actuel...")

# Tuer tous les processus SAUF le pattern_discovery_bot le plus récent
# Pour être sûr, on va d'abord demander à l'utilisateur

print(f"\n⚠️  Je vais tuer {len(pids)} processus Python")
print("Ensuite je relancerai UN SEUL pattern_discovery_bot.py")
print("\nAppuyez sur Entrée pour continuer...")
input()

# Tuer tous les processus Python
killed = 0
for pid in pids:
    try:
        subprocess.run(['taskkill', '/F', '/PID', pid],
                      capture_output=True, check=False)
        killed += 1
        print(f"  [X] Tué PID {pid}")
        time.sleep(0.05)
    except:
        pass

print(f"\n✓ {killed} processus arrêtés!")
print("\nMaintenant relance le bot avec:")
print("  python -u pattern_discovery_bot.py")

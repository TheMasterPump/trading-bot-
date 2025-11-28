"""
TEST SYSTEM - Vérifie que tout est prêt pour le lancement
"""
import sys
import os
from pathlib import Path

print("="*80)
print("TEST DU SYSTÈME - PREDICTION AI + TRADING BOT")
print("="*80)

errors = []
warnings = []
success = []

# Test 1: Vérifier les modules Python
print("\n[TEST 1] Vérification des modules Python...")
required_modules = [
    'flask',
    'cryptography',
    'joblib',
    'pandas',
]

for module in required_modules:
    try:
        __import__(module)
        success.append(f"[OK] {module} installe")
    except ImportError:
        errors.append(f"[ERREUR] {module} MANQUANT")

# Test 2: Vérifier les fichiers
print("\n[TEST 2] Vérification des fichiers...")
required_files = [
    'app.py',
    'database_bot.py',
    'wallet_generator.py',
    'trading_service.py',
    'templates/index.html',
    'templates/bot.html',
]

for file in required_files:
    if Path(file).exists():
        success.append(f"[OK] {file} present")
    else:
        errors.append(f"[ERREUR] {file} MANQUANT")

# Test 3: Vérifier le modèle ML
print("\n[TEST 3] Vérification du modèle ML...")
model_path = Path('models/roi_predictor_latest.pkl')
if model_path.exists():
    success.append(f"[OK] Modele ML present")
else:
    warnings.append(f"[WARNING] Modele ML manquant (scanner AI ne marchera pas)")

# Test 4: Tester l'import des modules custom
print("\n[TEST 4] Test des imports...")
try:
    from database_bot import BotDatabase
    success.append("[OK] database_bot importable")
except Exception as e:
    errors.append(f"[ERREUR] database_bot: {e}")

try:
    from wallet_generator import SolanaWalletManager
    success.append("[OK] wallet_generator importable")
except Exception as e:
    errors.append(f"[ERREUR] wallet_generator: {e}")

try:
    from trading_service import start_bot_for_user
    success.append("[OK] trading_service importable")
except Exception as e:
    errors.append(f"[ERREUR] trading_service: {e}")

# Résumé
print("\n" + "="*80)
print("RESUME DES TESTS")
print("="*80)

print(f"\n[SUCCES] ({len(success)}):")
for s in success:
    print(f"  {s}")

if warnings:
    print(f"\n[WARNINGS] ({len(warnings)}):")
    for w in warnings:
        print(f"  {w}")

if errors:
    print(f"\n[ERREURS] ({len(errors)}):")
    for e in errors:
        print(f"  {e}")
    print("\n" + "="*80)
    print("ACTIONS REQUISES:")
    print("="*80)
    print("\n1. Installer les modules manquants:")
    print("   pip install Flask Flask-Session cryptography joblib pandas")
    print("\n2. Pour Solana (optionnel pour Phase 2):")
    print("   pip install solders solana base58")
    sys.exit(1)
else:
    print("\n" + "="*80)
    print("[OK] SYSTEME PRET!")
    print("="*80)
    print("\nTu peux lancer:")
    print("  python app.py")
    print("\nPuis ouvrir:")
    print("  http://localhost:5001/bot")
    sys.exit(0)

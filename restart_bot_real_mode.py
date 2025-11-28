import requests
import time
import json

# Configuration
BASE_URL = "http://localhost:5001"
EMAIL = "bnlnknp@gmail.com"
PASSWORD = "votre_password"  # Vous devrez peut-être le changer

print("\n" + "="*70)
print("REDEMARRAGE DU BOT EN MODE REEL")
print("="*70)

# Créer une session pour garder les cookies
session = requests.Session()

# 1. Se connecter (pour obtenir le session cookie)
print("\n[1/4] Connexion...")
# Note: Si vous êtes déjà connecté dans le navigateur, on peut skip cette étape
# et utiliser directement l'API

# 2. Arrêter le bot actuel
print("\n[2/4] Arret du bot actuel...")
try:
    response = session.post(f"{BASE_URL}/api/bot/stop")
    data = response.json()
    if data.get('success'):
        print(f"  [OK] Bot arrete: {data.get('message', '')}")
    else:
        print(f"  [INFO] {data.get('message', 'Bot deja arrete')}")
except Exception as e:
    print(f"  [INFO] Erreur (peut-etre deja arrete): {e}")

# Attendre un peu
time.sleep(2)

# 3. Démarrer le bot en MODE RÉEL
print("\n[3/4] Demarrage du bot en MODE REEL...")
try:
    response = session.post(
        f"{BASE_URL}/api/bot/start",
        json={
            "strategy": "AI_PREDICTIONS",
            "risk_level": "MEDIUM",
            "real_mode": True  # MODE RÉEL !
        }
    )

    if response.status_code == 401:
        print("\n[ERREUR] Non authentifie!")
        print("Solution: Connectez-vous sur http://localhost:5001 dans votre navigateur")
        print("Ensuite relancez ce script")
        exit(1)

    data = response.json()

    print(f"\nReponse du serveur:")
    print(f"  Success: {data.get('success')}")
    print(f"  Message: {data.get('message', '')}")
    print(f"  Mode: {data.get('mode', 'UNKNOWN')}")

    if data.get('mode') == 'REAL':
        print(f"  Balance: {data.get('wallet_balance', 0):.4f} SOL")
        print(f"  Warning: {data.get('warning', '')}")
        print("\n" + "="*70)
        print("[SUCCESS] BOT DEMARRE EN MODE REEL !")
        print("="*70)
    else:
        print(f"\n[INFO] Bot demarre en mode: {data.get('mode')}")
        if 'error' in data:
            print(f"[ERREUR] {data['error']}")
            if data.get('require_subscription'):
                print("[INFO] Abonnement requis pour le mode reel")
            if data.get('insufficient_balance'):
                print(f"[INFO] Solde insuffisant: {data.get('current_balance', 0)} SOL")

except Exception as e:
    print(f"[ERREUR] {e}")
    import traceback
    traceback.print_exc()

# 4. Surveiller les premiers trades
print("\n[4/4] Surveillance des trades (60 secondes)...")
print("Attente des premiers signaux d'achat...\n")

for i in range(12):  # 12 x 5 secondes = 60 secondes
    time.sleep(5)

    try:
        # Récupérer les trades récents
        response = session.get(f"{BASE_URL}/api/bot/trades")
        if response.status_code == 200:
            data = response.json()
            trades = data.get('trades', [])

            if trades:
                latest = trades[0]
                tx_sig = latest.get('tx_signature', '')

                # Vérifier si c'est un trade REEL
                if not tx_sig.startswith('sim_'):
                    print(f"\n{'='*70}")
                    print(f"[TRADE REEL DETECTE !]")
                    print(f"  Token: {latest.get('token_name', 'Unknown')}")
                    print(f"  Type: {latest.get('trade_type', '?')}")
                    print(f"  Montant: {latest.get('amount_sol', 0):.4f} SOL")
                    print(f"  MC: ${latest.get('price_usd', 0):,.0f}")
                    print(f"  Status: {latest.get('status', '?')}")
                    print(f"  TX: {tx_sig}")
                    print(f"  Solscan: https://solscan.io/tx/{tx_sig}")
                    print(f"{'='*70}\n")
                    break

            # Afficher un point d'attente
            if i % 2 == 0:
                print(f"  [{i*5}s] En attente de signaux... ({len(trades)} trades en DB)")

    except Exception as e:
        print(f"  [ERREUR] Impossible de recuperer les trades: {e}")

print("\n[FIN] Surveillance terminee")
print("\nPour continuer a surveiller:")
print("  1. Allez sur http://localhost:5001/bot")
print("  2. Ou executez: python check_user_email.py")
print("\n" + "="*70)

from database_bot import db
import sqlite3

email = "bnlnknp@gmail.com"

# Récupérer l'utilisateur
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
user = cursor.fetchone()

if not user:
    print("Utilisateur non trouve")
    exit()

user_id = user['id']

print(f"\n=== VERIFICATION ABONNEMENT ===")
print(f"User ID: {user_id}\n")

# Vérifier l'abonnement actif
cursor.execute("""
    SELECT * FROM subscriptions
    WHERE user_id = ?
    ORDER BY starts_at DESC
    LIMIT 1
""", (user_id,))

subscription = cursor.fetchone()

if subscription:
    print("[ABONNEMENT TROUVE]:")
    print(f"  ID: {subscription['id']}")
    print(f"  Boost Level: {subscription['boost_level']}")
    print(f"  Prix paye: {subscription['price_paid']} SOL")
    print(f"  Actif: {subscription['is_active']}")
    print(f"  Debut: {subscription['starts_at']}")
    print(f"  Expiration: {subscription['expires_at']}")
    print(f"  TX Paiement: {subscription['payment_tx']}")

    if subscription['is_active']:
        boost = subscription['boost_level']
        if boost in ['RISKY', 'SAFE']:
            print(f"\n[OK] Vous pouvez utiliser le MODE REEL!")
            print(f"  Abonnement {boost} est suffisant")
        else:
            print(f"\n[X] Abonnement insuffisant pour le MODE REEL")
            print(f"  Vous avez: {boost}")
            print(f"  Requis: RISKY ou SAFE")
    else:
        print(f"\n[X] Abonnement INACTIF - MODE REEL non disponible")
else:
    print("[AUCUN ABONNEMENT]")
    print("  Vous n'avez pas d'abonnement")
    print("  MODE REEL non disponible")
    print("  Seulement MODE SIMULATION disponible")

print("\n" + "="*60)

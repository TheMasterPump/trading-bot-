"""
Script pour activer un abonnement SAFE gratuit pour tester le mode réel
"""
from database_bot import db
from datetime import datetime, timedelta

user_id = 1

# Créer un abonnement SAFE gratuit valable 30 jours
expires_at = datetime.now() + timedelta(days=30)

# Vérifier si un abonnement existe déjà
existing = db.get_active_subscription(user_id)

if existing:
    print(f"❌ Abonnement existant trouvé: {existing['boost_level']}")
    print(f"   Expire le: {existing['expires_at']}")
    print("\nSuppression de l'ancien abonnement...")
    # On va mettre à jour au lieu de créer
    db.conn.execute("""
        UPDATE subscriptions
        SET boost_level = ?, expires_at = ?, is_active = 1
        WHERE user_id = ? AND is_active = 1
    """, ('SAFE', expires_at.isoformat(), user_id))
    db.conn.commit()
    print("✅ Abonnement mis à jour vers SAFE!")
else:
    # Créer un nouvel abonnement
    db.conn.execute("""
        INSERT INTO subscriptions (user_id, boost_level, expires_at, is_active)
        VALUES (?, ?, ?, 1)
    """, (user_id, 'SAFE', expires_at.isoformat()))
    db.conn.commit()
    print("✅ Nouvel abonnement SAFE créé!")

print(f"\n🎉 Abonnement SAFE activé pour l'utilisateur {user_id}")
print(f"📅 Valable jusqu'au: {expires_at.strftime('%d/%m/%Y %H:%M')}")
print(f"\n🚀 Vous pouvez maintenant utiliser le MODE RÉEL!")
print(f"💰 Le bot va trader avec 10% de votre solde (minimum 0.005 SOL)")

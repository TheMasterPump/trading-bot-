"""
Script pour créer des trades de démonstration dans la base de données
Utilise ce script pour tester l'affichage des trades sans avoir à lancer le bot
"""
import random
from datetime import datetime, timedelta
from database_bot import db

def create_demo_trades(user_id, num_trades=10):
    """Crée des trades de démonstration pour un utilisateur"""

    print(f"Creating {num_trades} demo trades for user {user_id}...")

    # Vérifier si l'utilisateur existe
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        print(f"ERROR: User {user_id} not found!")
        return

    # Créer des trades de démo
    for i in range(num_trades):
        # Générer des données aléatoires
        token_address = f"DEMO{random.randint(1000,9999)}x{random.randint(1000,9999)}"
        amount_sol = random.uniform(0.5, 2.0)
        profit_percent = random.uniform(-30, 150)  # -30% à +150%
        profit_sol = amount_sol * (profit_percent / 100)

        # Timestamp aléatoire dans les dernières 24h
        created_at = datetime.now() - timedelta(hours=random.randint(0, 24))

        db.create_trade(
            user_id=user_id,
            token_address=token_address,
            token_name=f'DemoToken_{i+1}',
            trade_type='BUY_SELL',
            amount_sol=amount_sol,
            profit_loss=profit_sol,
            profit_loss_percentage=profit_percent,
            prediction_category='GEM' if profit_sol > 0 else 'RUG',
            prediction_confidence=random.uniform(0.65, 0.95),
            status='SIMULATED',
            tx_signature=f'demo_tx_{token_address}',
            price_usd=random.uniform(10000, 50000)
        )

        print(f"  [{i+1}/{num_trades}] Created trade: {token_address[:12]}... | "
              f"P/L: {profit_percent:+.1f}% ({profit_sol:+.3f} SOL)")

    print(f"\n[SUCCESS] Successfully created {num_trades} demo trades!")
    print(f"Go to http://localhost:5001/bot and check the TRADES tab")

if __name__ == "__main__":
    # Creer des trades pour l'utilisateur avec ID 1
    # Change cet ID si ton utilisateur a un autre ID
    USER_ID = 1

    print("=" * 80)
    print("DEMO TRADES GENERATOR")
    print("=" * 80)
    print()

    create_demo_trades(USER_ID, num_trades=10)

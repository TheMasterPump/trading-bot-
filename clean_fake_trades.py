"""
Nettoie les faux trades de test dans la BDD
Supprime tous les trades avec profit = 0 et status != 'SIMULATED'
"""
from database_bot import db

print("=" * 60)
print("NETTOYAGE DES FAUX TRADES")
print("=" * 60)

conn = db.get_connection()
cursor = conn.cursor()

# Compter les trades à supprimer
cursor.execute("""
    SELECT COUNT(*) FROM trades
    WHERE profit_loss = 0
    AND profit_loss_percentage = 0
    AND status != 'SIMULATED'
""")
count = cursor.fetchone()[0]

print(f"\n[X] Trades a supprimer: {count}")

if count > 0:
    # Afficher quelques exemples
    cursor.execute("""
        SELECT token_name, status, amount_sol, profit_loss
        FROM trades
        WHERE profit_loss = 0
        AND profit_loss_percentage = 0
        AND status != 'SIMULATED'
        LIMIT 5
    """)

    print("\nExemples de trades à supprimer:")
    for row in cursor.fetchall():
        print(f"  - {row[0]} | Status: {row[1]} | Amount: {row[2]} SOL | P/L: {row[3]}")

    # Supprimer
    cursor.execute("""
        DELETE FROM trades
        WHERE profit_loss = 0
        AND profit_loss_percentage = 0
        AND status != 'SIMULATED'
    """)

    conn.commit()
    print(f"\n[OK] {count} faux trades supprimes!")

else:
    print("\n[OK] Aucun faux trade a supprimer!")

# Afficher les trades restants
cursor.execute("SELECT COUNT(*) FROM trades")
remaining = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'SIMULATED'")
simulated = cursor.fetchone()[0]

print(f"\n[INFO] Trades restants: {remaining}")
print(f"   - Simules: {simulated}")
print(f"   - Reels: {remaining - simulated}")

conn.close()

print("\n" + "=" * 60)
print("NETTOYAGE TERMINE!")
print("=" * 60)

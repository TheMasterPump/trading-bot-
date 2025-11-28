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

print(f"\n=== DEBUG POSITIONS - User {user_id} ===\n")

# 1. Vérifier les derniers trades (BUY)
print("[1] DERNIERS ACHATS (5 derniers):")
cursor.execute("""
    SELECT id, token_address, token_name, amount_sol, status, tx_signature, created_at
    FROM trades
    WHERE user_id = ? AND trade_type = 'BUY'
    ORDER BY created_at DESC
    LIMIT 5
""", (user_id,))

buys = cursor.fetchall()
if buys:
    for i, buy in enumerate(buys):
        print(f"\n  {i+1}. {buy['token_name']}")
        print(f"     Address: {buy['token_address']}")
        print(f"     Amount: {buy['amount_sol']:.4f} SOL")
        print(f"     Status: {buy['status']}")
        print(f"     TX: {buy['tx_signature']}")
        print(f"     Date: {buy['created_at']}")
else:
    print("  Aucun achat trouve")

# 2. Vérifier les positions ouvertes
print("\n[2] POSITIONS OUVERTES:")
cursor.execute("""
    SELECT id, token_address, token_name, amount_sol, entry_mc, entry_time
    FROM open_positions
    WHERE user_id = ?
    ORDER BY entry_time DESC
""", (user_id,))

positions = cursor.fetchall()
if positions:
    for i, pos in enumerate(positions):
        print(f"\n  {i+1}. {pos['token_name']}")
        print(f"     Address: {pos['token_address']}")
        print(f"     Amount: {pos['amount_sol']:.4f} SOL")
        print(f"     Entry MC: ${pos['entry_mc']:,.0f}")
        print(f"     Entry time: {pos['entry_time']}")
else:
    print("  Aucune position ouverte")

# 3. Comparer : trouver les achats sans position correspondante
print("\n[3] ACHATS SANS POSITION OUVERTE:")
missing_positions = []

for buy in buys:
    # Chercher si une position existe pour ce token
    cursor.execute("""
        SELECT id FROM open_positions
        WHERE user_id = ? AND token_address = ?
    """, (user_id, buy['token_address']))

    pos = cursor.fetchone()

    if not pos:
        missing_positions.append(buy)
        print(f"\n  [!] {buy['token_name']}")
        print(f"     Address: {buy['token_address']}")
        print(f"     Achete le: {buy['created_at']}")
        print(f"     Status: {buy['status']}")
        print(f"     >>> POSITION MANQUANTE DANS open_positions !")

if not missing_positions:
    print("  Aucun probleme detecte - Tous les achats ont une position")

print("\n" + "="*60)

from database_bot import db

# Vérifier les trades de l'utilisateur 1
trades = db.get_user_trades(1, limit=10)

print(f"\n=== DERNIERS TRADES UTILISATEUR ===")
print(f"Total: {len(trades)} trades\n")

if len(trades) == 0:
    print("❌ Aucun trade trouvé")
else:
    for i, t in enumerate(trades):
        print(f"{i+1}. Type: {t.get('trade_type', '?')}")
        print(f"   Market Cap: ${t.get('price_usd', 0):,.0f}")
        print(f"   Montant dépensé: {t.get('amount_sol', 0):.4f} SOL")
        print(f"   Status: {t.get('status', '?')}")
        print(f"   Token: {t.get('token_name', 'Unknown')}")
        print()

# Vérifier les positions ouvertes
positions = db.get_open_positions(1)
print(f"\n=== POSITIONS OUVERTES ===")
print(f"Total: {len(positions)} positions\n")

if len(positions) > 0:
    for i, p in enumerate(positions):
        print(f"{i+1}. Token: {p.get('token_name', 'Unknown')}")
        print(f"   Entry MC: ${p.get('entry_mc', 0):,.0f}")
        print(f"   Amount: {p.get('amount_sol', 0):.4f} SOL")
        print()

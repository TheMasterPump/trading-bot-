from database_bot import db

user_id = 1

print("\n=== VERIFICATION MODE BOT ===\n")

# 1. Vérifier le statut du bot
bot_status = db.get_bot_status(user_id)
if bot_status:
    print(f"Bot actif: {bot_status.get('is_running', False)}")
    print(f"Strategie: {bot_status.get('strategy', 'N/A')}")
else:
    print("Bot non actif")

# 2. Vérifier les trades
trades = db.get_user_trades(user_id, limit=10)
print(f"\n=== TRADES RECENTS ({len(trades)} trades) ===\n")

if len(trades) == 0:
    print("Aucun trade trouve")
else:
    for i, t in enumerate(trades):
        print(f"{i+1}. Type: {t.get('trade_type', '?')}")
        print(f"   Token: {t.get('token_name', 'Unknown')}")
        print(f"   Montant: {t.get('amount_sol', 0):.4f} SOL")
        print(f"   MC: ${t.get('price_usd', 0):,.0f}")
        print(f"   Status: {t.get('status', '?')}")
        print(f"   TX Signature: {t.get('tx_signature', 'N/A')}")

        # Identifier si simulation ou reel
        tx_sig = t.get('tx_signature', '')
        if tx_sig and tx_sig.startswith('sim_'):
            print(f"   MODE: SIMULATION")
        elif tx_sig and len(tx_sig) > 20:
            print(f"   MODE: REEL (Solscan: https://solscan.io/tx/{tx_sig})")
        else:
            print(f"   MODE: INCONNU")
        print()

# 3. Vérifier les positions ouvertes
positions = db.get_open_positions(user_id)
print(f"\n=== POSITIONS OUVERTES ({len(positions)} positions) ===\n")

if len(positions) > 0:
    for i, p in enumerate(positions):
        print(f"{i+1}. Token: {p.get('token_name', 'Unknown')}")
        print(f"   Entry MC: ${p.get('entry_mc', 0):,.0f}")
        print(f"   Amount: {p.get('amount_sol', 0):.4f} SOL")
        print(f"   Entry time: {p.get('entry_time', 'N/A')}")
        print()
else:
    print("Aucune position ouverte")

# 4. Vérifier session simulation
sim_session = db.get_simulation_session(user_id)
if sim_session and sim_session['is_active']:
    print(f"\n=== SESSION SIMULATION ACTIVE ===")
    print(f"Solde virtuel: {sim_session['final_balance']} SOL")
    print(f"Trades: {sim_session['total_trades']}")
else:
    print(f"\n=== PAS DE SESSION SIMULATION ACTIVE ===")

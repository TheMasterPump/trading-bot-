from database_bot import db
import sqlite3

email = "bnlnknp@gmail.com"

print(f"\n=== VERIFICATION UTILISATEUR: {email} ===\n")

# Récupérer l'utilisateur par email
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute("SELECT id, email, created_at, last_login FROM users WHERE email = ?", (email,))
user = cursor.fetchone()

if not user:
    print(f"[X] Utilisateur '{email}' non trouve dans la base de donnees")
    exit()

user_id = user['id']
print(f"[OK] Utilisateur trouve!")
print(f"   ID: {user_id}")
print(f"   Email: {user['email']}")
print(f"   Cree le: {user['created_at']}")
print(f"   Derniere connexion: {user['last_login']}")

# 1. Vérifier le statut du bot
print("\n" + "="*60)
bot_status = db.get_bot_status(user_id)
if bot_status:
    print(f"[BOT] STATUT:")
    print(f"   Bot actif: {bot_status.get('is_running', False)}")
    print(f"   Strategie: {bot_status.get('strategy', 'N/A')}")
    print(f"   Take Profit: {bot_status.get('take_profit', 0)}x")
    print(f"   Stop Loss: {bot_status.get('stop_loss', 0)}x")
else:
    print("[BOT] STATUT: Non configure")

# 2. Vérifier le wallet
wallet = db.get_wallet(user_id)
if wallet:
    print("\n" + "="*60)
    print(f"[WALLET]:")
    print(f"   Adresse: {wallet['address']}")
    print(f"   Balance SOL: {wallet.get('balance_sol', 0):.4f} SOL")
    print(f"   Balance USD: ${wallet.get('balance_usd', 0):.2f}")
else:
    print("\n[WALLET]: Non configure")

# 3. Vérifier les trades
trades = db.get_user_trades(user_id, limit=10)
print("\n" + "="*60)
print(f"[TRADES] RECENTS ({len(trades)} trades):\n")

if len(trades) == 0:
    print("   Aucun trade trouvé")
else:
    for i, t in enumerate(trades):
        print(f"{i+1}. Type: {t.get('trade_type', '?')}")
        print(f"   Token: {t.get('token_name', 'Unknown')}")
        print(f"   Montant: {t.get('amount_sol', 0):.4f} SOL")
        print(f"   MC: ${t.get('price_usd', 0):,.0f}")
        print(f"   Status: {t.get('status', '?')}")
        print(f"   P&L: {t.get('profit_loss_percentage', 0):.2f}%")
        print(f"   Date: {t.get('created_at', 'N/A')}")

        # TX Signature
        tx_sig = t.get('tx_signature', '')
        if tx_sig:
            print(f"   TX: {tx_sig}")
            # Identifier si simulation ou reel
            if tx_sig.startswith('sim_'):
                print(f"   [SIM] MODE: SIMULATION")
            elif len(tx_sig) > 20:
                print(f"   [REAL] MODE: REEL (https://solscan.io/tx/{tx_sig})")
        print()

# 4. Vérifier les positions ouvertes
positions = db.get_open_positions(user_id)
print("="*60)
print(f"[POSITIONS] OUVERTES ({len(positions)} positions):\n")

if len(positions) > 0:
    for i, p in enumerate(positions):
        print(f"{i+1}. Token: {p.get('token_name', 'Unknown')}")
        print(f"   Entry MC: ${p.get('entry_mc', 0):,.0f}")
        print(f"   Amount: {p.get('amount_sol', 0):.4f} SOL")
        print(f"   Entry time: {p.get('entry_time', 'N/A')}")
        print()
else:
    print("   Aucune position ouverte")

# 5. Vérifier session simulation
sim_session = db.get_simulation_session(user_id)
print("="*60)
if sim_session and sim_session['is_active']:
    print(f"[SIMULATION] SESSION: ACTIVE")
    print(f"   Solde initial: {sim_session.get('initial_balance', 0)} SOL")
    print(f"   Solde actuel: {sim_session.get('final_balance', 0)} SOL")
    print(f"   Trades: {sim_session.get('total_trades', 0)}")
    print(f"   Win Rate: {sim_session.get('win_rate', 0):.1f}%")
    print(f"   Profit/Loss: {sim_session.get('total_profit', 0):.4f} SOL")
else:
    print(f"[SIMULATION] SESSION: Inactive")

# 6. Stats globales
print("\n" + "="*60)
cursor.execute("""
    SELECT
        COUNT(*) as total_trades,
        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
        SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
        SUM(profit_loss) as total_pnl,
        AVG(profit_loss_percentage) as avg_pnl_pct
    FROM trades
    WHERE user_id = ? AND status = 'EXECUTED'
""", (user_id,))
stats = cursor.fetchone()

if stats and stats['total_trades'] > 0:
    win_rate = (stats['winning_trades'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0
    print(f"[STATS] STATISTIQUES GLOBALES:")
    print(f"   Total trades: {stats['total_trades']}")
    print(f"   Trades gagnants: {stats['winning_trades']}")
    print(f"   Trades perdants: {stats['losing_trades']}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   P&L Total: {stats['total_pnl']:.4f} SOL")
    print(f"   P&L Moyen: {stats['avg_pnl_pct']:.2f}%")
else:
    print(f"[STATS] STATISTIQUES GLOBALES: Aucune donnee")

print("\n" + "="*60)

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

print(f"\n=== VERIFICATION MODE SIMULATION ===")
print(f"User ID: {user_id}\n")

# 1. Vérifier le statut du bot
cursor.execute("SELECT * FROM bot_status WHERE user_id = ?", (user_id,))
bot_status = cursor.fetchone()

if bot_status:
    print("[BOT STATUS TABLE]:")
    print(f"  is_running: {bot_status['is_running']}")
    print(f"  strategy: {bot_status['strategy']}")
    print(f"  started_at: {bot_status['started_at']}")
    print(f"  stopped_at: {bot_status['stopped_at']}")
else:
    print("[BOT STATUS TABLE]: Aucune entree")

# 2. Vérifier la session de simulation
cursor.execute("SELECT * FROM simulation_sessions WHERE user_id = ? ORDER BY start_time DESC LIMIT 1", (user_id,))
sim_session = cursor.fetchone()

print(f"\n[SIMULATION SESSION TABLE]:")
if sim_session:
    print(f"  session_id: {sim_session['id']}")
    print(f"  is_active: {sim_session['is_active']}")
    print(f"  virtual_balance_sol: {sim_session['virtual_balance_sol']} SOL")
    print(f"  final_balance_sol: {sim_session['final_balance_sol']} SOL")
    print(f"  total_trades: {sim_session['total_trades']}")
    print(f"  start_time: {sim_session['start_time']}")
    print(f"  duration_minutes: {sim_session['duration_minutes']}")
else:
    print("  Aucune session de simulation")

# 3. Vérifier les derniers trades
cursor.execute("SELECT token_name, status, tx_signature FROM trades WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (user_id,))
recent_trades = cursor.fetchall()

print(f"\n[DERNIERS TRADES]:")
if recent_trades:
    for trade in recent_trades:
        tx = trade['tx_signature']
        mode = "SIMULATION" if tx.startswith('sim_') else "REEL"
        print(f"  - {trade['token_name']}: {trade['status']} ({mode})")
else:
    print("  Aucun trade")

# 4. Vérifier s'il y a une clé privée
try:
    private_key = db.get_wallet_private_key(user_id)
    if private_key and private_key != 'SIMULATION_KEY_DUMMY':
        print(f"\n[CLE PRIVEE]: Presente (longueur: {len(private_key)} caracteres)")
        print(f"[MODE THEORIQUE]: REEL (cle privee disponible)")
    else:
        print(f"\n[CLE PRIVEE]: Absente ou dummy")
        print(f"[MODE THEORIQUE]: SIMULATION")
except Exception as e:
    print(f"\n[CLE PRIVEE]: Erreur - {e}")

print("\n" + "="*60)
print("\n[CONCLUSION]:")
if sim_session and sim_session['is_active']:
    print("  Le bot est en MODE SIMULATION")
    print("  Une session de simulation active est presente")
    print("\n  Pour passer en mode REEL:")
    print("  1. Arretez le bot")
    print("  2. Fermez la session de simulation (si active)")
    print("  3. Redemarrez le bot en mode REEL depuis l'interface web")
else:
    print("  Aucune session de simulation active")
    print("  Le bot devrait trader en mode REEL")
    print("  Si les trades sont en simulation, verifier le code du bot")

print("\n" + "="*60)

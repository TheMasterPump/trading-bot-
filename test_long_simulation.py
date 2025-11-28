"""
Test LONG (3 minutes) pour attendre des signaux BUY de l'AI
"""
import time
from database_bot import db

print("=" * 80)
print("TEST SIMULATION LONGUE (3 MINUTES)")
print("=" * 80)
print()

user_id = 1

# Terminer session existante
existing_session = db.get_simulation_session(user_id)
if existing_session and existing_session['is_active']:
    print(f"[1/4] Ending existing simulation session: ID={existing_session['id']}")
    db.end_simulation(existing_session['id'])

# Creer nouvelle session
session_id = db.start_simulation(user_id)
if not session_id:
    print("[ERROR] Failed to create simulation session")
    exit(1)

print(f"[2/4] Simulation session created: ID={session_id}")
print()

# Demarrer le bot
from trading_service_optimized import start_bot_for_user

result = start_bot_for_user(user_id, config={
    'strategy': 'AI_PREDICTIONS',
    'risk_level': 'MEDIUM',
    'stop_loss': 25,
    'tp_strategy': 'SIMPLE_MULTIPLIER',
    'tp_config': {'multiplier': 2.0}
}, simulation_mode=True)

if not result['success']:
    print(f"[ERROR] Failed to start bot: {result.get('error')}")
    exit(1)

print(f"[3/4] Bot started successfully!")
print()
print("[4/4] Waiting 3 minutes for AI signals...")
print("-" * 80)
print("Le bot ecoute les tokens PumpFun en direct et va trader automatiquement")
print("quand il trouve un bon token (8K-30K MC, bons signaux IA, whales, etc.)")
print("-" * 80)
print()

# Attendre 3 minutes et afficher progression
for i in range(18):  # 18 x 10s = 180s = 3 minutes
    time.sleep(10)

    # Checker les trades toutes les 10 secondes
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM trades WHERE user_id = ? AND status = 'SIMULATED'
        """, (user_id,))
        trade_count = cursor.fetchone()[0]

        # Afficher dernier trade si existe
        if trade_count > 0:
            cursor.execute("""
                SELECT token_name, profit_loss, profit_loss_percentage, created_at
                FROM trades WHERE user_id = ? AND status = 'SIMULATED'
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            last_trade = cursor.fetchone()
            print(f"[{(i+1)*10}s] Trades: {trade_count} | Last: {last_trade[0]} ({last_trade[2]:+.1f}%)")
        else:
            print(f"[{(i+1)*10}s] Waiting for signals... ({trade_count} trades so far)")

        conn.close()
    except Exception as e:
        print(f"[{(i+1)*10}s] Error checking trades: {e}")

print()
print("=" * 80)
print("TEST COMPLETE!")
print("=" * 80)
print()

# Afficher resultats finaux
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute("""
    SELECT COUNT(*), SUM(profit_loss), AVG(profit_loss_percentage)
    FROM trades WHERE user_id = ? AND status = 'SIMULATED'
""", (user_id,))
stats = cursor.fetchone()
trade_count, total_profit, avg_percent = stats[0], stats[1] or 0, stats[2] or 0

print(f"Total Trades: {trade_count}")
print(f"Total P/L: {total_profit:+.3f} SOL")
print(f"Average: {avg_percent:+.1f}%")
print()

if trade_count > 0:
    print("Derniers trades:")
    cursor.execute("""
        SELECT token_name, profit_loss, profit_loss_percentage, created_at
        FROM trades WHERE user_id = ? AND status = 'SIMULATED'
        ORDER BY created_at DESC LIMIT 5
    """, (user_id,))
    for trade in cursor.fetchall():
        emoji = "+" if trade[1] > 0 else "-"
        print(f"  {emoji} {trade[0]}: {trade[2]:+.1f}% ({trade[1]:+.3f} SOL)")

conn.close()

# Arreter le bot
from trading_service_optimized import stop_bot_for_user
stop_result = stop_bot_for_user(user_id)
print()
print(f"Bot stopped: {stop_result['message']}")
print()
print("Ouvre http://localhost:5001/bot pour voir les trades dans l'interface!")

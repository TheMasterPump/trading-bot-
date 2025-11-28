"""
Test complet: Demarrer un bot en mode simulation
"""
import sys
import time
from database_bot import db

# Creer une session de simulation
print("[TEST] Creating simulation session...")
user_id = 1

# D'abord terminer toute session active existante
print("[TEST] Checking for existing simulation session...")
existing_session = db.get_simulation_session(user_id)
if existing_session and existing_session['is_active']:
    print(f"[TEST] Ending existing simulation session: ID={existing_session['id']}")
    db.end_simulation(existing_session['id'])

# Utiliser la fonction start_simulation de database_bot
session_id = db.start_simulation(user_id)
if session_id:
    print(f"[OK] Simulation session created: ID={session_id}")
else:
    print("[ERROR] Failed to create simulation session")
    sys.exit(1)

# Demarrer le bot
print("[TEST] Starting bot in simulation mode...")
from trading_service_optimized import start_bot_for_user

result = start_bot_for_user(user_id, config={
    'strategy': 'AI_PREDICTIONS',
    'risk_level': 'MEDIUM',
    'stop_loss': 25,
    'tp_strategy': 'SIMPLE_MULTIPLIER',
    'tp_config': {'multiplier': 2.0}
}, simulation_mode=True)

print(f"[TEST] Bot start result: {result}")

if result['success']:
    print("[SUCCESS] Bot started successfully!")
    print("[TEST] Bot will now receive signals from AI engine...")
    print("[TEST] Waiting 30 seconds to see if bot receives signals...")

    time.sleep(30)

    # Verifier les trades
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM trades WHERE user_id = ?
    """, (user_id,))
    trade_count = cursor.fetchone()[0]
    conn.close()

    print(f"[TEST] Trades count: {trade_count}")

    # Arreter le bot
    from trading_service_optimized import stop_bot_for_user
    stop_result = stop_bot_for_user(user_id)
    print(f"[TEST] Bot stop result: {stop_result}")
else:
    print(f"[ERROR] Failed to start bot: {result.get('error')}")

print("[TEST] Test complete!")

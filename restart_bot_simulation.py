"""
Script pour redémarrer le bot proprement en mode SIMULATION
"""
import time
from database_bot import db
from trading_service_optimized import start_bot_for_user, stop_bot_for_user, active_bots

print("=" * 80)
print("REDÉMARRAGE BOT EN MODE SIMULATION")
print("=" * 80)
print()

user_id = 1

# 1. Arrêter le bot existant s'il y en a un
print("[1/5] Arrêt du bot existant...")
if user_id in active_bots:
    result = stop_bot_for_user(user_id)
    print(f"   Bot arrêté: {result.get('message', 'OK')}")
    time.sleep(2)
else:
    print("   Aucun bot actif")

# 2. Supprimer tous les trades PENDING invalides
print()
print("[2/5] Nettoyage des trades PENDING invalides...")
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute('DELETE FROM trades WHERE status = "PENDING"')
deleted_count = cursor.rowcount
conn.commit()
print(f"   {deleted_count} trades PENDING supprimés")
# NE PAS fermer conn ici, db.get_simulation_session() va le réutiliser

# 3. Terminer ancienne session de simulation et en créer une nouvelle
print()
print("[3/5] Configuration session de simulation...")
existing_session = db.get_simulation_session(user_id)
if existing_session and existing_session['is_active']:
    db.end_simulation(existing_session['id'])
    print(f"   Ancienne session terminée: ID={existing_session['id']}")

session_id = db.start_simulation(user_id)
print(f"   Nouvelle session créée: ID={session_id} avec 10 SOL")

# 4. Démarrer le bot en mode SIMULATION
print()
print("[4/5] Démarrage du bot en mode SIMULATION...")
config = {
    'strategy': 'AI_PREDICTIONS',
    'risk_level': 'MEDIUM',
    'stop_loss': 25,
    'tp_strategy': 'SIMPLE_MULTIPLIER',
    'tp_config': {'multiplier': 2.0},
    'simulation_mode': True,
    'simulation_session_id': session_id,
    'virtual_balance': 10.0
}

result = start_bot_for_user(user_id, config, simulation_mode=True)

if result['success']:
    print(f"   ✅ Bot démarré avec succès!")
    print(f"   Message: {result.get('message')}")
else:
    print(f"   ❌ Erreur: {result.get('error')}")
    exit(1)

# 5. Vérifier que le bot est bien en mode simulation
print()
print("[5/5] Vérification du bot...")
time.sleep(1)

if user_id in active_bots:
    bot = active_bots[user_id]
    print(f"   Bot actif: ✅")
    print(f"   Mode simulation: {bot.simulation_mode}")
    print(f"   Balance virtuelle: {bot.virtual_balance} SOL")
    print(f"   Session ID: {bot.simulation_session_id}")
    print(f"   Config: {bot.config.get('tp_strategy', 'N/A')}")
else:
    print(f"   ❌ Bot non trouvé dans active_bots!")
    exit(1)

print()
print("=" * 80)
print("✅ BOT DÉMARRÉ EN MODE SIMULATION!")
print("=" * 80)
print()
print("Le bot va maintenant:")
print("  - Écouter les tokens PumpFun en temps réel")
print("  - Acheter quand l'IA trouve un bon signal (8K-30K MC)")
print("  - Tracker les prix toutes les 5 secondes")
print("  - Vendre au TP (2x) ou SL (-25%)")
print("  - Enregistrer les trades avec status SIMULATED")
print()
print("Ouvre http://localhost:5001/bot pour voir les trades!")
print()

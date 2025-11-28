"""
Script de démarrage manuel du bot pour user 5 avec logs complets
"""
import sys
import traceback
from database_bot import db
from trading_service_optimized import start_bot_for_user

print("=" * 80)
print("DÉMARRAGE BOT USER 5 - MODE SIMULATION FORCÉ")
print("=" * 80)

user_id = 5

try:
    # 1. Vérifier/créer session simulation
    print("\n[1] Vérification session simulation...")
    session = db.get_simulation_session(user_id)

    if session and session['is_active']:
        print(f"   Session active trouvée: ID={session['id']}, Balance={session['final_balance']}")
        session_id = session['id']
    else:
        if session:
            print(f"   Terminaison ancienne session: ID={session['id']}")
            db.end_simulation(session['id'])

        print(f"   Création nouvelle session...")
        session_id = db.start_simulation(user_id)
        print(f"   Session créée: ID={session_id}")

    # 2. Configuration
    print("\n[2] Configuration bot...")
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
    print(f"   Config: {config}")

    # 3. Démarrer le bot
    print("\n[3] Démarrage du bot...")
    result = start_bot_for_user(user_id, config, simulation_mode=True)

    if result['success']:
        print(f"   [OK] SUCCESS: {result.get('message')}")
    else:
        print(f"   [ERROR] ERREUR: {result.get('error')}")
        sys.exit(1)

    # 4. Vérifier que le bot tourne
    print("\n[4] Vérification...")
    from trading_service_optimized import active_bots

    if user_id in active_bots:
        bot = active_bots[user_id]
        print(f"   Bot actif: [OK]")
        print(f"   Simulation mode: {bot.simulation_mode}")
        print(f"   Virtual balance: {bot.virtual_balance}")
        print(f"   Session ID: {bot.simulation_session_id}")
    else:
        print(f"   [ERROR] Bot NON trouvé dans active_bots!")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("[OK] BOT DEMARRÉ AVEC SUCCES EN MODE SIMULATION!")
    print("=" * 80)
    print("\nLe bot va maintenant créer des trades avec status SIMULATED")
    print("Ouvre http://localhost:5001/bot pour voir les positions actives!")
    print("\nAppuie sur Ctrl+C pour arrêter...")

    # Garder le script en vie
    import time
    while True:
        time.sleep(10)

except KeyboardInterrupt:
    print("\n\nArrêt du bot...")
    from trading_service_optimized import stop_bot_for_user
    stop_bot_for_user(user_id)
    print("Bot arrêté!")

except Exception as e:
    print(f"\n[ERROR] ERREUR FATALE:")
    print(f"   {type(e).__name__}: {e}")
    print("\nTraceback complet:")
    traceback.print_exc()
    sys.exit(1)

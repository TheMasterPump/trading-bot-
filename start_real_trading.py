"""
Démarrage direct du bot en MODE RÉEL
Bypasse l'API web et utilise directement le service de trading
"""
import time
import asyncio
from database_bot import db
from trading_service_optimized import start_bot_for_user, stop_bot_for_user, get_bot_status

# Configuration
EMAIL = "bnlnknp@gmail.com"

print("\n" + "="*70)
print("DEMARRAGE DU BOT EN MODE REEL - DIRECT")
print("="*70)

# 1. Récupérer l'utilisateur
conn = db.get_connection()
cursor = conn.cursor()
cursor.execute("SELECT id FROM users WHERE email = ?", (EMAIL,))
user = cursor.fetchone()

if not user:
    print(f"[ERREUR] Utilisateur {EMAIL} non trouve")
    exit(1)

user_id = user['id']
print(f"\n[USER] ID: {user_id}, Email: {EMAIL}")

# 2. Vérifier l'abonnement
cursor.execute("""
    SELECT * FROM subscriptions
    WHERE user_id = ? AND is_active = 1
    ORDER BY starts_at DESC
    LIMIT 1
""", (user_id,))
subscription = cursor.fetchone()

if not subscription or subscription['boost_level'] not in ['RISKY', 'SAFE']:
    print(f"[ERREUR] Abonnement insuffisant pour le mode reel")
    exit(1)

print(f"[SUBSCRIPTION] Boost: {subscription['boost_level']}, Active: {subscription['is_active']}")

# 3. Vérifier le wallet et la balance
wallet = db.get_wallet(user_id)
if not wallet:
    print(f"[ERREUR] Wallet non trouve")
    exit(1)

print(f"[WALLET] Address: {wallet['address']}")
print(f"[WALLET] Balance DB: {wallet.get('balance_sol', 0):.4f} SOL")

# 4. Arrêter le bot s'il tourne
print("\n[STEP 1/3] Arret du bot actuel...")
try:
    result = stop_bot_for_user(user_id)
    if result.get('success'):
        print(f"  [OK] {result.get('message', 'Bot arrete')}")
        time.sleep(2)  # Attendre que le bot s'arrête proprement
    else:
        print(f"  [INFO] {result.get('message', 'Bot pas actif')}")
except Exception as e:
    print(f"  [INFO] {e}")

# 5. Démarrer le bot en MODE RÉEL
print("\n[STEP 2/3] Demarrage du bot en MODE REEL...")

config = {
    'strategy': 'AI_PREDICTIONS',
    'risk_level': 'MEDIUM',
    'stop_loss': 25,
    'tp_strategy': 'PROGRESSIVE_AFTER_MIGRATION',
    'tp_config': {
        'initial_percent': 50,
        'step_percent': 5,
        'step_interval': 20
    },
    'trailing_stop_enabled': True,
    'trailing_stop_activation_percent': 50,
    'trailing_stop_distance_percent': 20,
    'simulation_mode': False  # MODE RÉEL !
}

print("\n[CONFIG]:")
print(f"  Strategy: {config['strategy']}")
print(f"  Risk Level: {config['risk_level']}")
print(f"  Simulation Mode: {config['simulation_mode']}")
print(f"  TP Strategy: {config['tp_strategy']}")

try:
    result = start_bot_for_user(user_id, config, simulation_mode=False)

    if result.get('success'):
        print("\n" + "="*70)
        print("[SUCCESS] BOT DEMARRE EN MODE REEL !")
        print("="*70)
        print(f"  User ID: {user_id}")
        print(f"  Wallet: {wallet['address']}")
        print(f"  Balance: {wallet.get('balance_sol', 0):.4f} SOL")
        print(f"  Strategy: {config['strategy']}")
        print("\n  Le bot va maintenant analyser les tokens et acheter avec de VRAIS SOL!")
        print("="*70)

        # Mettre à jour la DB
        db.start_bot(user_id, config['strategy'], config['risk_level'])

    else:
        print(f"\n[ERREUR] Impossible de demarrer le bot")
        print(f"  Raison: {result.get('error', 'Unknown')}")
        exit(1)

except Exception as e:
    print(f"[ERREUR] Exception: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 6. Surveiller les trades
print("\n[STEP 3/3] Surveillance des trades (90 secondes)...")
print("En attente des premiers signaux d'achat...\n")

start_time = time.time()
last_trade_count = 0

for i in range(18):  # 18 x 5 secondes = 90 secondes
    time.sleep(5)

    try:
        # Récupérer les trades récents
        trades = db.get_user_trades(user_id, limit=5)

        if len(trades) > last_trade_count:
            # Nouveau trade détecté
            for trade in trades[:len(trades) - last_trade_count]:
                tx_sig = trade.get('tx_signature', '')

                # Vérifier si c'est un trade REEL (pas de préfixe sim_)
                if not tx_sig.startswith('sim_'):
                    print(f"\n{'='*70}")
                    print(f"[TRADE REEL DETECTE !]")
                    print(f"  Token: {trade.get('token_name', 'Unknown')}")
                    print(f"  Type: {trade.get('trade_type', '?')}")
                    print(f"  Montant: {trade.get('amount_sol', 0):.4f} SOL")
                    print(f"  MC: ${trade.get('price_usd', 0):,.0f}")
                    print(f"  Status: {trade.get('status', '?')}")
                    print(f"  TX: {tx_sig}")
                    if len(tx_sig) > 20:
                        print(f"  Solscan: https://solscan.io/tx/{tx_sig}")
                    print(f"{'='*70}\n")
                else:
                    print(f"  [INFO] Trade en simulation detecte (ignorer): {trade.get('token_name')}")

            last_trade_count = len(trades)

        # Afficher progression
        if i % 3 == 0:
            elapsed = int(time.time() - start_time)
            print(f"  [{elapsed}s] En attente... (Total trades en DB: {len(trades)})")

        # Vérifier que le bot tourne toujours
        status = get_bot_status(user_id)
        if status and not status.get('is_running'):
            print(f"\n[WARNING] Le bot s'est arrete!")
            break

    except Exception as e:
        print(f"  [ERREUR] {e}")

print("\n[FIN] Surveillance terminee")
print("\nLe bot continue de tourner en arriere-plan.")
print("Pour voir les trades en temps reel:")
print("  - Allez sur http://localhost:5001/bot")
print("  - Ou executez: python check_user_email.py")
print("\n" + "="*70)

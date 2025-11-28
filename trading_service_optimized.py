"""
OPTIMIZED TRADING SERVICE
Service optimisé pour gérer 200+ utilisateurs simultanés
Utilise le VRAI bot live_trading_bot.py qui FONCTIONNE
"""
import asyncio
import threading
from datetime import datetime
from database_bot import db
# CHANGEMENT: Utiliser le VRAI bot qui fonctionne !
from live_trading_bot import LiveTradingBot, PositionManager
from ai_trading_engine import get_ai_engine
from optimized_bot_worker import OptimizedBotWorker


# Variables globales
active_bots = {}  # {user_id: bot_instance}
bot_tasks = {}  # {user_id: asyncio.Task}
_main_loop = None
_engine_started = False


def ensure_engine_running():
    """
    S'assure que le moteur IA tourne
    À appeler 1 seule fois au démarrage de l'app
    """
    global _engine_started

    if _engine_started:
        return

    print("[SERVICE] Starting AI Trading Engine (FULL IA)...")

    # Démarrer le moteur IA dans un thread
    def run_engine():
        global _main_loop
        _main_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_main_loop)

        engine = get_ai_engine()

        try:
            _main_loop.run_until_complete(engine.start())
        except KeyboardInterrupt:
            print("[AI ENGINE] Interrupted")
        finally:
            _main_loop.close()

    engine_thread = threading.Thread(target=run_engine, daemon=True)
    engine_thread.start()

    _engine_started = True
    print("[SERVICE] AI Trading Engine started (with full AI, learning, adaptive config)!")


def start_bot_for_user(user_id, config=None, simulation_mode=False):
    """
    Démarre le bot optimisé pour un utilisateur
    simulation_mode: Si True, utilise le solde virtuel et ne fait pas de vraies transactions
    """
    global active_bots, _main_loop

    # S'assurer que l'infrastructure tourne
    ensure_engine_running()

    # Vérifier si le bot est déjà actif
    if user_id in active_bots:
        return {'success': False, 'error': 'Bot déjà actif'}

    # Vérifier si en mode simulation
    simulation_session = None
    if simulation_mode:
        simulation_session = db.get_simulation_session(user_id)
        if not simulation_session or not simulation_session['is_active']:
            return {'success': False, 'error': 'Aucune session de simulation active'}

    # En mode simulation, utiliser des valeurs dummy pour wallet et clé privée
    if simulation_mode:
        wallet_address = f'SIMULATION_WALLET_{user_id}'
        private_key = 'SIMULATION_KEY_DUMMY'
    else:
        # Récupérer le wallet de l'utilisateur
        wallet = db.get_wallet(user_id)
        if not wallet:
            return {'success': False, 'error': 'Wallet non trouvé'}

        wallet_address = wallet['address']

        # Récupérer la clé privée (déchiffrée)
        private_key = db.get_wallet_private_key(user_id)
        if not private_key:
            return {'success': False, 'error': 'Clé privée non trouvée'}

    # Récupérer la config TP depuis la BDD
    bot_status = db.get_bot_status(user_id)
    if bot_status:
        # Merge avec la config TP stockée
        import json
        stored_config = {
            'strategy': bot_status.get('strategy', 'AI_PREDICTIONS'),
            'risk_level': bot_status.get('risk_level', 'MEDIUM'),
            'stop_loss': bot_status.get('stop_loss', 25),
            'tp_strategy': bot_status.get('tp_strategy', 'SIMPLE_MULTIPLIER'),
            'tp_config': json.loads(bot_status.get('tp_config', '{}'))
        }
        config = {**stored_config, **(config or {})}

    # Ajouter les paramètres de simulation à la config
    if simulation_mode and simulation_session:
        config = config or {}
        config['simulation_mode'] = True
        config['simulation_session_id'] = simulation_session['id']
        config['virtual_balance'] = simulation_session['final_balance']

    # Créer le bot optimisé
    bot = OptimizedBotWorker(
        user_id=user_id,
        wallet_address=wallet_address,
        private_key=private_key,
        config=config or {}
    )

    # Démarrer le bot dans un thread séparé
    def run_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(bot.start())
        except Exception as e:
            print(f"[ERROR] Bot crashed pour user {user_id}: {e}")
        finally:
            loop.close()

    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()

    # Enregistrer
    active_bots[user_id] = bot

    return {'success': True, 'message': 'Bot démarré (Architecture optimisée)'}


def stop_bot_for_user(user_id):
    """
    Arrête le bot pour un utilisateur
    """
    global active_bots

    if user_id not in active_bots:
        return {'success': False, 'error': 'Bot non actif'}

    bot = active_bots[user_id]

    # Arrêter le bot
    asyncio.run(bot.stop())

    # Nettoyer
    del active_bots[user_id]

    return {'success': True, 'message': 'Bot arrêté'}


def get_bot_status(user_id):
    """
    Récupère le statut du bot pour un utilisateur
    """
    is_active = user_id in active_bots

    return {
        'is_running': is_active,
        'bot_exists': is_active
    }


async def get_bot_active_positions(user_id):
    """
    Récupère les positions actives du bot pour un utilisateur
    COPIE EXACTE de la logique de live_trading_bot.py ligne 1551-1594
    """
    if user_id not in active_bots:
        # FALLBACK: Si bot pas actif, lire depuis la BDD
        print(f"[SERVICE] Bot {user_id} not active, reading from DB")
        db_positions = db.get_open_positions(user_id)

        # Enrichir avec les prix LIVE depuis le WebSocket
        from ai_trading_engine import get_last_known_price
        positions = []
        for pos in db_positions:
            mint = pos['token_address']
            live_price = get_last_known_price(mint)

            if live_price['success'] and live_price['mc_usd'] > 0:
                current_mc = live_price['mc_usd']
            else:
                current_mc = pos['entry_mc']

            profit_ratio = current_mc / pos['entry_mc'] if pos['entry_mc'] > 0 else 1.0
            profit_pct = (profit_ratio - 1) * 100

            positions.append({
                'mint': mint,
                'token_name': pos['token_name'],
                'entry_mc': pos['entry_mc'],
                'current_mc': current_mc,
                'amount': pos['amount_sol'],
                'profit_percent': profit_pct,
                'profit_multiplier': profit_ratio,
                'partial_sold': False,
                'distance_to_migration': 53000 - current_mc,
                'migration_percent': (current_mc / 53000) * 100,
                'entry_time': pos['entry_time']
            })

        return positions

    bot = active_bots[user_id]
    positions = []

    # MÊME CODE QUE live_trading_bot.py ! (mais avec WebSocket au lieu d'API REST)
    from ai_trading_engine import get_last_known_price

    for mint, position in bot.active_positions.items():
        try:
            symbol = position.get('token_name', f'Token_{mint[:6]}')
            entry_mc = position.get('entry_mc', 0)
            partial_sold = position.get('partial_sold', False)

            # DEBUG: Log entry_mc value from position
            print(f"[SERVICE] DEBUG get_bot_active_positions - Token: {symbol} | entry_mc from position: {entry_mc} (type: {type(entry_mc).__name__})")

            # Récupérer le prix LIVE depuis le WebSocket (EXACTEMENT comme live_trading_bot.py ligne 1557)
            live_price = get_last_known_price(mint)

            if live_price['success'] and live_price['mc_usd'] > 0:
                current_mc = live_price['mc_usd']
            else:
                current_mc = position.get('last_mc', entry_mc)

            # Calculer le profit actuel (EXACTEMENT comme ligne 1565-1566)
            profit_ratio = current_mc / entry_mc
            profit_pct = (profit_ratio - 1) * 100

            # Distance à la migration
            distance_to_migration = 53000 - current_mc
            migration_pct = (current_mc / 53000) * 100

            positions.append({
                'mint': mint,
                'token_name': symbol,
                'entry_mc': entry_mc,  # EN USD COMPLET comme live_trading_bot !
                'current_mc': current_mc,  # EN USD COMPLET comme live_trading_bot !
                'amount': position['amount'],
                'profit_percent': profit_pct,
                'profit_multiplier': profit_ratio,
                'partial_sold': partial_sold,
                'distance_to_migration': distance_to_migration,
                'migration_percent': migration_pct,
                'entry_time': position['entry_time'].isoformat() if position.get('entry_time') else None
            })
        except Exception as e:
            print(f"[ERROR] Failed to get price for {mint}: {e}")
            continue

    return positions


def get_active_bots_count():
    """Retourne le nombre de bots actifs"""
    return len(active_bots)


def get_system_stats():
    """
    Stats globales du système
    """
    from shared_websocket_feed import get_shared_feed

    feed = get_shared_feed()
    engine = get_engine()

    return {
        'active_bots': len(active_bots),
        'feed_stats': feed.get_stats(),
        'engine_stats': engine.get_stats(),
        'architecture': 'OPTIMIZED_CENTRALIZED',
        'max_capacity': '200+ users'
    }


if __name__ == "__main__":
    print("Optimized Trading Service - Test")
    print("=" * 80)

    # Test
    ensure_engine_running()

    # Attendre
    import time
    time.sleep(2)

    # Stats
    stats = get_system_stats()
    print(f"System Stats: {stats}")

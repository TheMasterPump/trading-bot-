"""
TRADING SERVICE - Intégration du bot de trading dans le système web
Gère les instances de bots pour chaque utilisateur
"""
import asyncio
import threading
import sys
import os
from datetime import datetime
from pathlib import Path

# Import du bot de trading existant
sys.path.insert(0, str(Path(__file__).parent))
from database_bot import db
from wallet_generator import SolanaWalletManager

# Variables globales pour gérer les bots
active_bots = {}  # {user_id: bot_instance}
bot_threads = {}  # {user_id: thread}


class UserTradingBot:
    """
    Wrapper du bot de trading pour un utilisateur spécifique
    Adapte le bot existant pour utiliser le wallet de l'utilisateur
    """

    def __init__(self, user_id, wallet_address, private_key, config=None):
        self.user_id = user_id
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.config = config or {}
        self.is_running = False
        self.loop = None

    async def start(self):
        """Démarre le bot de trading"""
        self.is_running = True

        print(f"[TRADING SERVICE] Démarrage du bot pour l'utilisateur {self.user_id}")
        print(f"  Wallet: {self.wallet_address}")
        print(f"  Stratégie: {self.config.get('strategy', 'AI_PREDICTIONS')}")

        # TODO: Intégrer le bot existant ici
        # Pour l'instant, simulation
        await self.simulate_trading()

    async def simulate_trading(self):
        """
        Simulation de trading pour Phase 1
        En Phase 2, on remplacera par le vrai bot
        """
        trade_count = 0

        while self.is_running:
            # Attendre un peu
            await asyncio.sleep(60)  # 1 minute

            # Simuler un trade de temps en temps
            if trade_count < 5:  # Max 5 trades en simulation
                trade_count += 1

                # Créer un trade de simulation
                import random
                profit = random.uniform(-0.3, 3.0)  # -30% à +200%

                db.create_trade(
                    user_id=self.user_id,
                    token_address='DEMO' + str(trade_count),
                    trade_type='BUY_SELL',
                    amount_sol=0.01,
                    token_name=f'SimToken{trade_count}',
                    prediction_category='GEM' if profit > 0 else 'RUG',
                    prediction_confidence=random.uniform(0.7, 0.95),
                    tx_signature=f'demo_tx_{trade_count}',
                    price_usd=random.uniform(5000, 20000)
                )

                # Mettre à jour les stats
                db.update_bot_stats(self.user_id)

                print(f"[SIMULATION] Trade #{trade_count} enregistré pour user {self.user_id}")

    async def stop(self):
        """Arrête le bot"""
        self.is_running = False
        print(f"[TRADING SERVICE] Arrêt du bot pour l'utilisateur {self.user_id}")

    def record_trade(self, trade_data):
        """Enregistre un trade dans la base de données"""
        db.create_trade(
            user_id=self.user_id,
            token_address=trade_data['token_address'],
            trade_type=trade_data.get('type', 'BUY'),
            amount_sol=trade_data.get('amount_sol', 0.01),
            token_name=trade_data.get('token_name'),
            prediction_category=trade_data.get('prediction'),
            prediction_confidence=trade_data.get('confidence'),
            tx_signature=trade_data.get('tx_signature'),
            price_usd=trade_data.get('price_usd', 0)
        )

        # Mettre à jour les stats
        db.update_bot_stats(self.user_id)


def start_bot_for_user(user_id, config=None):
    """
    Démarre le bot de trading pour un utilisateur
    """
    global active_bots, bot_threads

    # Vérifier si le bot est déjà actif
    if user_id in active_bots:
        return {'success': False, 'error': 'Bot déjà actif'}

    # Récupérer le wallet de l'utilisateur
    wallet = db.get_wallet(user_id)
    if not wallet:
        return {'success': False, 'error': 'Wallet non trouvé'}

    # Récupérer la clé privée (déchiffrée)
    private_key = db.get_wallet_private_key(user_id)
    if not private_key:
        return {'success': False, 'error': 'Clé privée non trouvée'}

    # Créer l'instance du bot
    bot = UserTradingBot(
        user_id=user_id,
        wallet_address=wallet['address'],
        private_key=private_key,
        config=config or {}
    )

    # Démarrer le bot dans un thread séparé
    def run_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        bot.loop = loop

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
    bot_threads[user_id] = thread

    return {'success': True, 'message': 'Bot démarré'}


def stop_bot_for_user(user_id):
    """
    Arrête le bot de trading pour un utilisateur
    """
    global active_bots, bot_threads

    if user_id not in active_bots:
        return {'success': False, 'error': 'Bot non actif'}

    bot = active_bots[user_id]

    # Arrêter le bot
    if bot.loop:
        asyncio.run_coroutine_threadsafe(bot.stop(), bot.loop)

    # Nettoyer
    del active_bots[user_id]
    if user_id in bot_threads:
        del bot_threads[user_id]

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


def get_active_bots_count():
    """Retourne le nombre de bots actifs"""
    return len(active_bots)


# ============================================================================
# VERSION COMPLÈTE DU BOT (Phase 2)
# ============================================================================
"""
Pour Phase 2, on intégrera le bot complet live_trading_bot.py

Modifications nécessaires:
1. Adapter Config pour utiliser la clé privée de l'utilisateur
2. Modifier PositionManager pour enregistrer dans la BDD web
3. Gérer plusieurs instances en parallèle (une par utilisateur)
4. Ajouter des callbacks pour mettre à jour l'interface web

Exemple d'intégration:

class CompleteTradingBot(UserTradingBot):
    async def start(self):
        # Importer le bot existant
        from live_trading_bot import LiveTradingBot, Config

        # Configurer le wallet de l'utilisateur
        Config.WALLET_ADDRESS = self.wallet_address
        Config.WALLET_PRIVATE_KEY = self.private_key

        # Modifier la simulation
        Config.SIMULATION_MODE = False  # Trading réel!
        Config.TEST_MODE = True  # Montants faibles
        Config.BUY_AMOUNT_SOL = 0.01  # 0.01 SOL par trade

        # Créer le bot
        bot = LiveTradingBot()

        # Hook pour enregistrer les trades
        original_record = bot.positions.close_position
        def hooked_close(mint, exit_mc, reason, **kwargs):
            # Appeler l'original
            result = original_record(mint, exit_mc, reason, **kwargs)

            # Enregistrer dans notre BDD
            if mint in bot.positions.closed_positions:
                position = bot.positions.closed_positions[-1]
                self.record_trade({
                    'token_address': mint,
                    'token_name': position.get('symbol'),
                    'type': 'BUY_SELL',
                    'amount_sol': position.get('amount_sol'),
                    'prediction': position.get('reason'),
                    'confidence': position.get('confidence'),
                    'tx_signature': 'live_tx',
                    'price_usd': exit_mc
                })

            return result

        bot.positions.close_position = hooked_close

        # Lancer le bot
        await bot.run()
"""


if __name__ == "__main__":
    print("Trading Service - Test")
    print("=" * 80)

    # Exemple d'utilisation
    # result = start_bot_for_user(1)
    # print(result)

"""
OPTIMIZED BOT WORKER
Bot léger qui reçoit les signaux du moteur centralisé
Au lieu de 200 threads lourds, 200 workers légers!
"""
import asyncio
import json
from datetime import datetime
from database_bot import db
from ai_trading_engine import get_ai_engine as get_engine
from queue import Queue
from console_logger import get_console_logger

# Configuration du timeout des positions
POSITION_TIMEOUT_MINUTES = 45  # Même timeout que live_trading_bot.py


class OptimizedBotWorker:
    """
    Bot optimisé pour un utilisateur
    - NE fait PAS de connexion WebSocket
    - Reçoit les signaux du moteur centralisé via une queue
    - Léger et scalable
    """

    def __init__(self, user_id: int, wallet_address: str, private_key: str, config: dict):
        self.user_id = user_id
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.config = config
        self.is_running = False

        # Simulation mode
        self.simulation_mode = config.get('simulation_mode', False)
        self.simulation_session_id = config.get('simulation_session_id', None)
        self.virtual_balance = config.get('virtual_balance', 10.0)

        # Positions actives (pour simulation)
        self.active_positions = {}  # {mint: {'entry_mc': X, 'entry_time': Y, 'amount': Z, 'tokens': N}}

        # Stats
        self.trades_count = 0
        self.signals_processed = 0
        self.started_at = None

        # Engine
        self.engine = get_engine()

        # Queue thread-safe pour recevoir les signaux
        self.signal_queue = Queue()

        if self.simulation_mode:
            print(f"[BOT {self.user_id}] MODE SIMULATION active - Balance virtuelle: {self.virtual_balance} SOL")

    def on_signal(self, signal: dict):
        """
        Callback quand un signal arrive du moteur (thread-safe)
        Met le signal dans la queue pour traitement asynchrone
        """
        print(f"[BOT {self.user_id}] Signal received: {signal.get('action')} - {signal.get('name', 'Unknown')}")
        self.signal_queue.put(signal)

    async def process_signals(self):
        """
        Traite les signaux de la queue en boucle
        """
        while self.is_running:
            try:
                # Vérifier s'il y a des signaux (non-bloquant)
                if not self.signal_queue.empty():
                    signal = self.signal_queue.get_nowait()
                    self.signals_processed += 1

                    if signal['action'] == 'BUY':
                        await self.execute_buy(signal)
                else:
                    # Attendre un peu avant de revérifier
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(f"[BOT {self.user_id}] Error processing signal: {e}")

    async def execute_buy(self, signal: dict):
        """
        Exécute un achat selon la stratégie de l'utilisateur
        """
        mint = signal['mint']
        mc = signal['mc']
        confidence = signal['confidence']
        token_name = signal.get('name', f'Token_{mint[:6]}')  # Nom du token depuis le signal

        # DEBUG: Log exact MC value received
        print(f"[BOT {self.user_id}] DEBUG execute_buy - MC received: {mc} (type: {type(mc).__name__})")
        print(f"[BOT {self.user_id}] BUY signal: {token_name} @ ${mc/1000:.1f}K | Confidence: {confidence:.0%}")

        # Vérifier la stratégie TP de l'utilisateur
        tp_strategy = self.config.get('tp_strategy', 'SIMPLE_MULTIPLIER')
        tp_config = self.config.get('tp_config', {})

        # TODO: Exécuter le trade réel ici
        # Pour l'instant, simulation
        await self.simulate_trade(mint, mc, tp_strategy, tp_config, token_name)

    async def simulate_trade(self, mint: str, entry_mc: float, tp_strategy: str, tp_config: dict, token_name: str = None):
        """Simulation de trade (ou trade réel selon le mode)"""
        entry_time_now = datetime.now()

        # Calculer le montant du trade
        if self.simulation_mode:
            # En mode simulation, utiliser 10% du solde virtuel
            trade_amount = self.virtual_balance * 0.10

            # Vérifier qu'on a assez de solde
            if trade_amount <= 0 or self.virtual_balance < trade_amount:
                print(f"[BOT {self.user_id}] [SIMULATION] Solde insuffisant: {self.virtual_balance:.2f} SOL")
                return

            # Ouvrir une position (acheter virtuellement)
            self.virtual_balance -= trade_amount  # Déduire le montant investi

            # DEBUG: Log exact entry_mc value being stored
            print(f"[BOT {self.user_id}] DEBUG simulate_trade - Storing entry_mc: {entry_mc} (type: {type(entry_mc).__name__})")

            tokens_qty = trade_amount / (entry_mc / 1000000)  # Approximation du nombre de tokens
            tx_signature = f'sim_buy_{mint[:8]}'

            print(f"[BOT {self.user_id}] [SIMULATION] BOUGHT {token_name or mint[:8]} @ ${entry_mc/1000:.1f}K | "
                  f"Amount: {trade_amount:.3f} SOL | "
                  f"Remaining balance: {self.virtual_balance:.2f} SOL | "
                  f"Strategy: {tp_strategy}")

        else:
            # ============================================================
            # MODE RÉEL - VRAIES TRANSACTIONS SOLANA
            # ============================================================
            from wallet_generator import SolanaWalletManager
            wallet_manager = SolanaWalletManager()

            # Récupérer le solde réel du wallet
            real_balance = wallet_manager.get_balance(self.wallet_address)

            # Calculer montant du trade : 10% du capital avec minimum 0.005 SOL
            # TODO: Permettre configuration personnalisée (self.config.get('trade_amount', ...))
            trade_amount = max(real_balance * 0.10, 0.005)  # 10% avec min 0.005 SOL (MODE TEST)

            # Vérifier qu'on a assez de fonds (avec marge pour les frais)
            if real_balance < trade_amount + 0.003:  # +0.003 SOL pour frais
                print(f"[BOT {self.user_id}] ⚠️ [RÉEL] Solde insuffisant: {real_balance:.4f} SOL (besoin {trade_amount + 0.003:.4f} SOL)")
                return

            # Importer le trader Solana
            from solana_trader_instance import create_trader_for_wallet

            # Créer trader avec la clé privée de l'utilisateur
            trader = create_trader_for_wallet(self.wallet_address, self.private_key)

            if not trader:
                print(f"[BOT {self.user_id}] ❌ [RÉEL] Impossible de créer le trader")
                return

            # ACHAT RÉEL via PumpPortal
            print(f"[BOT {self.user_id}] 🚀 [RÉEL] ACHAT EN COURS: {token_name or mint[:8]} | "
                  f"Montant: {trade_amount:.4f} SOL (10% de {real_balance:.4f} SOL)")

            result = trader.buy_token(mint, trade_amount, slippage=25, priority_fee=0.001)

            if not result['success']:
                print(f"[BOT {self.user_id}] ❌ [RÉEL] ACHAT ÉCHOUÉ: {result['error']}")
                return

            tx_signature = result['signature']
            tokens_qty = trade_amount / (entry_mc / 1000000)  # Approximation

            print(f"[BOT {self.user_id}] ✅ [RÉEL] ACHETÉ {token_name or mint[:8]} @ ${entry_mc/1000:.1f}K | "
                  f"Montant: {trade_amount:.4f} SOL | "
                  f"TX: https://solscan.io/tx/{tx_signature}")

        # ============================================================
        # COMMUN : Enregistrement position et trade (simulation ET réel)
        # ============================================================

        # Calculer les take profits (EXACT comme live_trading_bot.py ligne 365-366)
        partial_take_profit_mc = entry_mc * 2.0  # Vendre 50% à 2x
        final_take_profit_mc = 58000  # Migration Raydium

        self.active_positions[mint] = {
            'entry_mc': entry_mc,
            'entry_time': entry_time_now,
            'amount': trade_amount,
            'tokens': tokens_qty,
            'token_name': token_name or f'Token_{mint[:6]}',  # Nom du token

            # NOUVEAUX CHAMPS (comme live_trading_bot.py ligne 364-380)
            'stop_loss_mc': entry_mc * (1 - 0.40),  # -40% stop loss initial
            'partial_take_profit_mc': partial_take_profit_mc,
            'final_take_profit_mc': final_take_profit_mc,
            'partial_sold': False,  # Pas encore vendu 50%
            'partial_profit_announced': False,  # Pas encore annoncé
            'last_mc': entry_mc,  # Dernier MC connu

            # Vente progressive après migration
            'migration_reached': False,
            'last_progressive_sell_time': None,
            'max_mc_since_migration': 0,
            'progressive_sell_count': 0,
            'amount_remaining': 1.0  # 100% au départ
        }

        # Persister en BDD pour ne pas perdre si bot redémarre
        db.create_open_position(
            user_id=self.user_id,
            token_address=mint,
            token_name=token_name or f'Token_{mint[:6]}',
            entry_mc=entry_mc,
            entry_time=entry_time_now.isoformat(),
            amount_sol=trade_amount,
            tokens=tokens_qty,
            simulation_session_id=self.simulation_session_id if self.simulation_mode else None
        )

        # Enregistrer le trade d'ACHAT immédiatement
        db.create_trade(
            user_id=self.user_id,
            token_address=mint,
            token_name=token_name or f'Token_{mint[:6]}',
            trade_type='BUY',
            amount_sol=trade_amount,
            price_usd=entry_mc,
            tokens_bought=tokens_qty,
            prediction_category='PENDING',
            prediction_confidence=0.75,
            status='OPEN',
            tx_signature=tx_signature
        )

        # Log au console web
        console_logger = get_console_logger()
        mode_label = "SIMULATION" if self.simulation_mode else "RÉEL"
        console_logger.log(f"[BOT #{self.user_id}] [{mode_label}] BOUGHT {token_name} @ ${entry_mc/1000:.1f}K ({trade_amount:.4f} SOL)", 'BUY', user_id=self.user_id)

    async def start(self):
        """Démarre le bot"""
        self.is_running = True
        self.started_at = datetime.now()

        print(f"[BOT {self.user_id}] Starting... | Strategy: {self.config.get('strategy', 'AI_PREDICTIONS')}")

        # Recharger les positions ouvertes depuis la BDD (au cas où bot a redémarré)
        if self.simulation_mode:
            saved_positions = db.get_open_positions(self.user_id)
            for pos in saved_positions:
                mint = pos['token_address']
                entry_mc = pos['entry_mc']

                # CORRECTION: Ne pas deviner partial_sold au chargement
                # Laisser la logique normale le détecter au prochain prix check
                self.active_positions[mint] = {
                    'entry_mc': entry_mc,
                    'entry_time': datetime.fromisoformat(pos['entry_time']),
                    'amount': pos['amount_sol'],
                    'tokens': pos['tokens'],
                    'token_name': pos['token_name'],

                    # Champs manquants (recalculer)
                    'stop_loss_mc': entry_mc * 0.60,  # -40% stop loss initial
                    'partial_take_profit_mc': entry_mc * 2.0,
                    'final_take_profit_mc': 58000,
                    'partial_sold': False,  # Laisser la logique le détecter
                    'partial_profit_announced': False,  # Pourra se réafficher si besoin
                    'last_mc': entry_mc,
                    'migration_reached': False,
                    'last_progressive_sell_time': None,
                    'max_mc_since_migration': 0,
                    'progressive_sell_count': 0,
                    'amount_remaining': 1.0
                }
            if saved_positions:
                print(f"[BOT {self.user_id}] ✅ Restored {len(saved_positions)} open positions from database")

        # S'enregistrer auprès du moteur centralisé (avec référence à self pour recevoir les signaux)
        self.engine.register_bot(self.user_id, self.config, bot_instance=self)

        print(f"[BOT {self.user_id}] Ready! Waiting for signals from engine...")

        # Log de démarrage dans la console web
        console_logger = get_console_logger()
        if self.simulation_mode:
            console_logger.log(f"[BOT #{self.user_id}] Bot started in SIMULATION mode - Balance: {self.virtual_balance:.2f} SOL", 'INFO', user_id=self.user_id)
        else:
            console_logger.log(f"[BOT #{self.user_id}] Bot started in REAL mode", 'INFO', user_id=self.user_id)

        # Demarrer le price tracker pour TOUS les modes (comme live_trading_bot.py ligne 1538!)
        asyncio.create_task(self.track_prices())

        # Demarrer le traitement des signaux
        await self.process_signals()

    async def stop(self):
        """Arrête le bot"""
        self.is_running = False

        # Se désinscrire du moteur
        self.engine.unregister_bot(self.user_id)

        uptime = (datetime.now() - self.started_at).total_seconds() if self.started_at else 0

        print(f"[BOT {self.user_id}] Stopped | "
              f"Uptime: {uptime:.0f}s | "
              f"Trades: {self.trades_count} | "
              f"Signals: {self.signals_processed}")

    async def track_prices(self):
        """Track les prix des positions actives en temps réel (COPIE DE live_trading_bot.py ligne 1538)"""
        print(f"[BOT {self.user_id}] Price tracker started - Checking every 3 seconds (TEMPS RÉEL!)")

        while self.is_running:
            try:
                if self.active_positions:
                    await self.update_positions_pnl()
                await asyncio.sleep(3)  # TEMPS RÉEL: 3 secondes comme live_trading_bot.py ligne 1598!
            except Exception as e:
                print(f"[BOT {self.user_id}] Error tracking prices: {e}")

    async def check_expired_positions(self):
        """
        Vérifie et ferme les positions expirées (timeout de 45 min)
        IMPORTANT CORRECTION:
        - Position normale → Timeout 40 min
        - Position partial_sold MAIS pas de migration → Timeout 40 min quand même !
        - Position en migration (58K atteint) → PAS de timeout (vente progressive)
        """
        now = datetime.now()
        timeout_seconds = POSITION_TIMEOUT_MINUTES * 60

        for mint, position in list(self.active_positions.items()):
            try:
                partial_sold = position.get('partial_sold', False)
                migration_reached = position.get('migration_reached', False)

                # CORRECTION: NE PAS TIMEOUT uniquement si MIGRATION ATTEINTE
                # Si juste partial_sold mais pas de migration, on timeout quand même après 40 min
                if migration_reached:
                    # Position en vente progressive après migration - PAS DE TIMEOUT !
                    # Elle vend 5% toutes les 20s jusqu'à épuisement
                    continue

                position_age = (now - position['entry_time']).total_seconds()

                if position_age > timeout_seconds:
                    # Position expirée - fermer avec le dernier MC connu
                    entry_mc = position['entry_mc']
                    last_mc = position.get('last_mc', entry_mc)

                    # Utiliser le dernier MC connu au lieu de -80%
                    exit_mc = last_mc
                    profit_percent = (exit_mc - entry_mc) / entry_mc
                    profit_sol = position['amount'] * profit_percent

                    if partial_sold:
                        print(f"[BOT {self.user_id}] ⏰ TIMEOUT (40 min): {position['token_name']} | "
                              f"Partial sold mais pas de migration - fermeture forcée")
                    else:
                        print(f"[BOT {self.user_id}] ⏰ TIMEOUT (40 min): {position['token_name']}")

                    await self.exit_position(mint, exit_mc, profit_sol, profit_percent)

            except Exception as e:
                print(f"[BOT {self.user_id}] Error checking timeout for {mint[:8]}: {e}")

    async def update_positions_pnl(self):
        """
        Met à jour le P&L de toutes les positions actives
        COPIE EXACTE de live_trading_bot.py avec trailing stop loss, vente partielle et progressive
        """
        from ai_trading_engine import get_last_known_price

        # D'abord vérifier les positions expirées
        await self.check_expired_positions()

        for mint, position in list(self.active_positions.items()):
            try:
                # Récupérer le prix LIVE depuis le WebSocket
                price_data = get_last_known_price(mint)

                if price_data['success'] and price_data['mc_usd'] > 0:
                    # Prix WebSocket disponible
                    current_mc = price_data['mc_usd']
                else:
                    # FALLBACK: Token mort (pas de trades WebSocket) → utiliser l'API REST
                    from pumpfun_price_fetcher import get_token_price_live
                    api_price = get_token_price_live(mint)

                    if api_price['success'] and api_price['mc_usd'] > 0:
                        current_mc = api_price['mc_usd']
                        print(f"[BOT {self.user_id}] 🔄 FALLBACK API pour {position['token_name']}: ${current_mc/1000:.1f}K")
                    else:
                        # Vraiment mort - utiliser le dernier prix connu
                        current_mc = position.get('last_mc', position['entry_mc'])
                        # Si token complètement mort depuis 5+ minutes, fermer avec -80%
                        position_age_minutes = (datetime.now() - position['entry_time']).total_seconds() / 60
                        if position_age_minutes > 5 and current_mc == position['entry_mc']:
                            print(f"[BOT {self.user_id}] 💀 TOKEN MORT détecté: {position['token_name']} - fermeture avec -80%")
                            exit_mc = position['entry_mc'] * 0.2
                            profit_percent = (exit_mc - position['entry_mc']) / position['entry_mc']
                            profit_sol = position['amount'] * profit_percent
                            await self.exit_position(mint, exit_mc, profit_sol, profit_percent / 100)
                            continue

                position['last_mc'] = current_mc  # Mettre à jour le dernier MC connu

                entry_mc = position['entry_mc']
                profit_ratio = current_mc / entry_mc
                profit_percent = (profit_ratio - 1) * 100

                # ====================================================================
                # TRAILING STOP LOSS INTELLIGENT (EXACT comme live_trading_bot.py ligne 615-642)
                # ====================================================================
                if profit_percent >= 80:
                    # +80% à +100% (proche de 2x) → Stop loss à +30%
                    new_stop_loss = entry_mc * 1.30
                elif profit_percent >= 50:
                    # +50% à +80% → Stop loss à breakeven (0%)
                    new_stop_loss = entry_mc * 1.00
                elif profit_percent >= 20:
                    # +20% à +50% → Stop loss à -20%
                    new_stop_loss = entry_mc * 0.80
                else:
                    # < +20% → Stop loss normal à -40%
                    new_stop_loss = entry_mc * 0.60

                # Mettre à jour le stop loss SI IL MONTE (jamais descendre!)
                if new_stop_loss > position['stop_loss_mc']:
                    old_stop_loss = position['stop_loss_mc']
                    position['stop_loss_mc'] = new_stop_loss
                    if profit_percent >= 20:
                        print(f"[BOT {self.user_id}] 📈 TRAILING STOP LOSS: {position['token_name']} | "
                              f"Profit: +{profit_percent:.1f}% | "
                              f"SL: ${old_stop_loss/1000:.1f}K → ${new_stop_loss/1000:.1f}K")

                # ====================================================================
                # VENTE PARTIELLE À X2 (EXACT comme live_trading_bot.py ligne 649-680)
                # ====================================================================
                if not position['partial_sold'] and current_mc >= position['partial_take_profit_mc']:
                    # CORRECTION: Afficher le message UNE SEULE FOIS (pas à chaque check!)
                    first_time = not position.get('partial_profit_announced', False)

                    if first_time:
                        print(f"[BOT {self.user_id}] 💰 PARTIAL PROFIT @ 2x: {position['token_name']} | "
                              f"MC: ${current_mc/1000:.1f}K | "
                              f"✅ Vente de 50% - INVESTISSEMENT RÉCUPÉRÉ!")

                    # VENTE RÉELLE de 50% si pas en simulation
                    if not self.simulation_mode:
                        from solana_trader_instance import create_trader_for_wallet

                        trader = create_trader_for_wallet(self.wallet_address, self.private_key)

                        if trader:
                            result = trader.sell_token(
                                mint=mint,
                                amount_percent=50,  # Vendre 50%
                                slippage=25,
                                priority_fee=0.001
                            )

                            if not result['success']:
                                print(f"[BOT {self.user_id}] ❌ [RÉEL] Vente partielle échouée: {result['error']}")
                                print(f"[BOT {self.user_id}] On réessayera au prochain check...")
                                return  # Ne pas marquer comme vendu si échec

                            print(f"[BOT {self.user_id}] ✅ [RÉEL] 50% vendus! TX: https://solscan.io/tx/{result['signature']}")

                    # Marquer comme partiellement vendu
                    position['partial_sold'] = True
                    position['partial_profit_mc'] = current_mc
                    position['partial_profit_announced'] = True  # Ne plus afficher le message

                    # Ajuster le stop loss à breakeven (on ne peut plus perdre!)
                    position['stop_loss_mc'] = entry_mc
                    position['amount_remaining'] = 0.50  # 50% restant

                    if first_time:
                        print(f"[BOT {self.user_id}] ✅ Nouveau Stop Loss: ${position['stop_loss_mc']/1000:.1f}K (breakeven - position GRATUITE!)")
                    return  # Sortir pour laisser la position respirer

                # ====================================================================
                # VENTE PROGRESSIVE APRÈS MIGRATION (EXACT comme live_trading_bot.py ligne 682-756)
                # ====================================================================
                if position['partial_sold'] and current_mc >= position['final_take_profit_mc']:
                    # Migration atteinte!
                    if not position['migration_reached']:
                        position['migration_reached'] = True
                        position['last_progressive_sell_time'] = datetime.now()
                        position['max_mc_since_migration'] = current_mc

                        print(f"[BOT {self.user_id}] 🚀 MIGRATION ATTEINTE: {position['token_name']} | "
                              f"MC: ${current_mc/1000:.1f}K | "
                              f"🔄 VENTE PROGRESSIVE: 5% toutes les 20s")

                    # Mettre à jour le MC max
                    if current_mc > position['max_mc_since_migration']:
                        position['max_mc_since_migration'] = current_mc

                    # Vérifier si besoin de vendre progressivement
                    time_since_last_sell = (datetime.now() - position['last_progressive_sell_time']).total_seconds()

                    # VENTE PROGRESSIVE toutes les 20 secondes
                    if time_since_last_sell >= 20:
                        print(f"[BOT {self.user_id}] 💰 VENTE PROGRESSIVE #{position['progressive_sell_count']+1}: {position['token_name']} | "
                              f"MC: ${current_mc/1000:.1f}K | Vente: 5%")

                        # VENTE RÉELLE de 5% si pas en simulation
                        if not self.simulation_mode:
                            from solana_trader_instance import create_trader_for_wallet

                            trader = create_trader_for_wallet(self.wallet_address, self.private_key)

                            if trader:
                                result = trader.sell_token(
                                    mint=mint,
                                    amount_percent=5,  # Vendre 5% de la position totale
                                    slippage=25,
                                    priority_fee=0.001
                                )

                                if not result['success']:
                                    print(f"[BOT {self.user_id}] ❌ [RÉEL] Vente progressive échouée: {result['error']}")
                                    print(f"[BOT {self.user_id}] On réessayera au prochain check...")
                                    return  # Ne pas incrémenter le compteur si échec

                                print(f"[BOT {self.user_id}] ✅ [RÉEL] 5% vendus! TX: https://solscan.io/tx/{result['signature']}")

                        position['progressive_sell_count'] += 1
                        position['last_progressive_sell_time'] = datetime.now()
                        position['amount_remaining'] -= 0.05

                        # Si moins de 5% restant, fermer complètement
                        if position['amount_remaining'] <= 0.05:
                            profit_percent_final = (current_mc - entry_mc) / entry_mc
                            profit_sol_final = position['amount'] * profit_percent_final
                            print(f"[BOT {self.user_id}] 🎯 VENTE FINALE: {position['token_name']} après {position['progressive_sell_count']} ventes progressives")
                            await self.exit_position(mint, current_mc, profit_sol_final, profit_percent_final / 100)
                        return

                    # PROTECTION: Si MC baisse de 15% depuis max, vendre tout le reste
                    mc_drop_from_max = 1 - (current_mc / position['max_mc_since_migration'])
                    if mc_drop_from_max >= 0.15:
                        print(f"[BOT {self.user_id}] ⚠️ STOP LOSS PROGRESSIF: {position['token_name']} | "
                              f"MC baisse de {mc_drop_from_max*100:.0f}% depuis max | "
                              f"Vente du reste ({position['amount_remaining']*100:.0f}%)")

                        # VENTE RÉELLE du reste si pas en simulation
                        if not self.simulation_mode:
                            from solana_trader_instance import create_trader_for_wallet

                            trader = create_trader_for_wallet(self.wallet_address, self.private_key)

                            if trader:
                                # Vendre 100% de ce qui reste
                                result = trader.sell_token(
                                    mint=mint,
                                    amount_percent=100,
                                    slippage=25,
                                    priority_fee=0.001
                                )

                                if result['success']:
                                    print(f"[BOT {self.user_id}] ✅ [RÉEL] Reste vendu! TX: https://solscan.io/tx/{result['signature']}")
                                else:
                                    print(f"[BOT {self.user_id}] ❌ [RÉEL] Vente finale échouée: {result['error']}")

                        profit_percent_final = (current_mc - entry_mc) / entry_mc
                        profit_sol_final = position['amount'] * profit_percent_final
                        await self.exit_position(mint, current_mc, profit_sol_final, profit_percent_final / 100)
                        return

                    # Continuer à surveiller
                    return

                # ====================================================================
                # STOP LOSS CLASSIQUE
                # ====================================================================
                if current_mc <= position['stop_loss_mc']:
                    print(f"[BOT {self.user_id}] 📉 STOP LOSS: {position['token_name']} | "
                          f"MC: ${current_mc/1000:.1f}K <= SL: ${position['stop_loss_mc']/1000:.1f}K")

                    # VENTE RÉELLE si pas en simulation
                    if not self.simulation_mode:
                        from solana_trader_instance import create_trader_for_wallet

                        trader = create_trader_for_wallet(self.wallet_address, self.private_key)

                        if trader:
                            # Vendre 100% de la position
                            result = trader.sell_token(
                                mint=mint,
                                amount_percent=100,
                                slippage=25,
                                priority_fee=0.001
                            )

                            if result['success']:
                                print(f"[BOT {self.user_id}] ✅ [RÉEL] Position fermée (SL)! TX: https://solscan.io/tx/{result['signature']}")
                            else:
                                print(f"[BOT {self.user_id}] ❌ [RÉEL] Vente SL échouée: {result['error']}")

                    profit_percent_final = (current_mc - entry_mc) / entry_mc
                    profit_sol_final = position['amount'] * profit_percent_final

                    if position['partial_sold']:
                        print(f"[BOT {self.user_id}] ✅ Mais 50% déjà vendu @ 2x - Toujours en profit!")

                    await self.exit_position(mint, current_mc, profit_sol_final, profit_percent_final / 100)

            except Exception as e:
                print(f"[BOT {self.user_id}] Error updating position {mint[:8]}: {e}")

    async def check_exit_conditions(self, mint, entry_mc, current_mc, profit_percent, tp_strategy, tp_config):
        """Vérifie si on doit sortir de la position"""
        # Stop Loss
        stop_loss = self.config.get('stop_loss', 25) / 100  # -25% par défaut
        if profit_percent <= -stop_loss:
            print(f"[BOT {self.user_id}] STOP LOSS hit for {mint[:8]} at {profit_percent:.1%}")
            return True

        # Take Profit selon stratégie
        if tp_strategy == 'SIMPLE_MULTIPLIER':
            multiplier = tp_config.get('multiplier', 2.0)
            if current_mc >= entry_mc * multiplier:
                print(f"[BOT {self.user_id}] TAKE PROFIT hit for {mint[:8]} at {multiplier}x")
                return True

        elif tp_strategy == 'EXIT_BEFORE_MIGRATION':
            # Migration est ~58K MC (varie avec prix SOL)
            if current_mc >= 50000:  # Vendre avant migration
                print(f"[BOT {self.user_id}] EXITING before migration for {mint[:8]} at ${current_mc/1000:.1f}K")
                return True

        # TODO: Ajouter d'autres stratégies TP

        return False

    async def exit_position(self, mint, exit_mc, profit_sol, profit_percent):
        """
        Ferme une position et enregistre le trade
        IMPORTANT: Calcul correct du profit avec partial_sold (EXACT comme live_trading_bot.py ligne 473-483)
        """
        position = self.active_positions.pop(mint, None)
        if not position:
            return

        # Supprimer de la BDD
        db.delete_open_position(self.user_id, mint)

        entry_mc = position['entry_mc']

        # ====================================================================
        # CALCUL DU PROFIT RÉEL (corrigé pour partial profit)
        # EXACT comme live_trading_bot.py ligne 473-483
        # ====================================================================
        if position.get('partial_sold', False):
            # Si 50% vendus à x2, on a déjà récupéré 100% de la mise
            # Les 50% restants sont GRATUITS
            # Profit réel = 100% récupéré + 50% du prix actuel
            profit_ratio = 1.0 + 0.5 * (exit_mc / entry_mc)
            profit_percent = (profit_ratio - 1) * 100
            profit_sol = position['amount'] * (profit_ratio - 1)  # Profit en SOL
            partial_adjustment = True
        else:
            # Position complète (pas de partial sold)
            profit_ratio = exit_mc / entry_mc
            profit_percent = (profit_ratio - 1) * 100
            profit_sol = position['amount'] * (profit_ratio - 1)
            partial_adjustment = False

        # Mettre à jour le solde virtuel
        self.virtual_balance += position['amount'] + profit_sol

        # Mettre à jour dans la BDD
        if self.simulation_session_id:
            db.update_simulation_balance(self.simulation_session_id, self.virtual_balance)
            db.increment_simulation_trades(self.simulation_session_id, is_win=(profit_sol > 0))

        # Récupérer le nom du token
        token_name = position.get('token_name', f'Token_{mint[:6]}')

        # Enregistrer le trade
        db.create_trade(
            user_id=self.user_id,
            token_address=mint,
            token_name=token_name,
            trade_type='BUY_SELL',
            amount_sol=position['amount'],
            profit_loss=profit_sol,
            profit_loss_percentage=profit_percent,
            prediction_category='GEM' if profit_sol > 0 else 'RUG',
            prediction_confidence=0.75,
            status='SIMULATED' if self.simulation_mode else 'EXECUTED',
            tx_signature=f'sim_{mint[:8]}' if self.simulation_mode else None,
            price_usd=exit_mc  # EXIT price
        )

        self.trades_count += 1

        result_text = "WIN" if profit_sol > 0 else "LOSS"

        if partial_adjustment:
            print(f"[BOT {self.user_id}] ✅ {result_text} POSITION CLOSED: {token_name} | "
                  f"Entry: ${entry_mc/1000:.1f}K → Exit: ${exit_mc/1000:.1f}K | "
                  f"Profit RÉEL: {profit_ratio:.2f}x ({profit_percent:+.1f}%) ({profit_sol:+.3f} SOL) | "
                  f"✅ AVEC 50% VENDU @ 2x | "
                  f"Balance: {self.virtual_balance:.2f} SOL")
        else:
            print(f"[BOT {self.user_id}] {result_text} POSITION CLOSED: {token_name} | "
                  f"Entry: ${entry_mc/1000:.1f}K → Exit: ${exit_mc/1000:.1f}K | "
                  f"P/L: {profit_ratio:.2f}x ({profit_percent:+.1f}%) ({profit_sol:+.3f} SOL) | "
                  f"Balance: {self.virtual_balance:.2f} SOL")

        # Log au console web
        console_logger = get_console_logger()
        console_logger.log(f"[BOT #{self.user_id}] {result_text} SOLD {token_name} | {profit_ratio:.2f}x ({profit_percent:+.1f}%) ({profit_sol:+.3f} SOL)", 'SELL', user_id=self.user_id)

    def get_stats(self):
        """Stats du bot"""
        uptime = (datetime.now() - self.started_at).total_seconds() if self.started_at else 0

        stats = {
            'user_id': self.user_id,
            'is_running': self.is_running,
            'uptime_seconds': uptime,
            'trades_count': self.trades_count,
            'signals_processed': self.signals_processed,
            'config': self.config
        }

        if self.simulation_mode:
            stats['simulation'] = {
                'virtual_balance': self.virtual_balance,
                'active_positions': len(self.active_positions)
            }

        return stats


if __name__ == "__main__":
    # Test
    print("Testing Optimized Bot Worker...")

    config = {
        'strategy': 'AI_PREDICTIONS',
        'risk_level': 'MEDIUM',
        'tp_strategy': 'PROGRESSIVE_AFTER_MIGRATION',
        'tp_config': {
            'initial_percent': 50,
            'step_percent': 5,
            'step_interval': 20
        }
    }

    bot = OptimizedBotWorker(
        user_id=1,
        wallet_address='TEST123',
        private_key='key123',
        config=config
    )

    asyncio.run(bot.start())

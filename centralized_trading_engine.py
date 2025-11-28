"""
CENTRALIZED TRADING ENGINE
Analyse les tokens 1 fois et distribue aux bots actifs
Optimisé pour 200+ utilisateurs simultanés
Inclut détection des RUNNERS (tokens qui vont monter fort)
"""
import asyncio
import json
from typing import Dict, List
from datetime import datetime
from shared_websocket_feed import get_shared_feed
from database_bot import db
from scanner_data_manager import scanner_manager
from runner_detector import get_runner_detector, RunnerPotential, RunnerPhase
from console_logger import get_console_logger

# Prix de SOL en USD (à ajuster selon le marché)
SOL_PRICE_USD = 200


class TradingEngine:
    """
    Moteur centralisé qui:
    1. Reçoit les tokens depuis le feed partagé
    2. Analyse UNIQUE fois (pas 200 fois!)
    3. Distribue aux bots actifs
    """

    def __init__(self):
        self.active_bots: Dict[int, dict] = {}  # {user_id: bot_config}
        self.feed = get_shared_feed()
        self.tokens_analyzed = 0
        self.signals_sent = 0
        self.runner_detector = get_runner_detector()
        self.runners_detected = 0  # Count of potential runners found

    def register_bot(self, user_id: int, config: dict, bot_instance=None):
        """Enregistre un bot actif"""
        self.active_bots[user_id] = {
            'config': config,
            'registered_at': datetime.now(),
            'signals_received': 0,
            'bot_instance': bot_instance  # Référence au bot pour appeler on_signal()
        }
        print(f"[ENGINE] Bot registered: User {user_id} | Total: {len(self.active_bots)}")

    def unregister_bot(self, user_id: int):
        """Retire un bot"""
        if user_id in self.active_bots:
            del self.active_bots[user_id]
            print(f"[ENGINE] Bot unregistered: User {user_id} | Total: {len(self.active_bots)}")

    async def analyze_token(self, token_data: dict) -> dict:
        """
        Analyse UNIQUE du token (au lieu de 200 fois!)
        Inclut détection des RUNNERS avec prédiction de target
        Retourne un signal de trading
        """
        self.tokens_analyzed += 1

        try:
            # Extract data
            mint = token_data.get('mint')
            # Le WebSocket PumpFun envoie marketCapSol, on doit le convertir en USD
            mc_sol = token_data.get('marketCapSol', 0)
            mc = mc_sol * SOL_PRICE_USD if mc_sol else 0
            txns = token_data.get('txnCount', 0)
            volume = token_data.get('volume', 0)
            name = token_data.get('name', f'Token_{mint[:6] if mint else "Unknown"}')

            # DEBUG: Log MC calculation
            if mc > 0:
                print(f"[ENGINE] DEBUG - Token: {name} | mc_sol: {mc_sol} | SOL_PRICE: {SOL_PRICE_USD} | mc_usd: {mc}")
            symbol = token_data.get('symbol', 'UNKNOWN')

            # Log nouveau token dans la console web (pour tous les utilisateurs connectés)
            console_logger = get_console_logger()
            if mc > 0:
                console_logger.log(f"NEW TOKEN: {name} @ ${mc/1000:.1f}K", 'NEW_TOKEN', user_id=0)
            else:
                console_logger.log(f"NEW TOKEN: {name} @ $0", 'NEW_TOKEN', user_id=0)

            # Analyse simple (à adapter selon ton bot)
            signal = {
                'mint': mint,
                'name': name,
                'symbol': symbol,
                'mc': mc,
                'timestamp': datetime.now().isoformat(),
                'action': None,  # BUY, SKIP, WAIT
                'confidence': 0.0,
                'reason': '',
                # Runner detection fields
                'is_runner': False,
                'runner_score': 0,
                'runner_potential': None,
                'runner_phase': None,
                'target_x_low': 0,
                'target_x_mid': 0,
                'target_x_high': 0,
                'runner_signals': [],
                'runner_warnings': []
            }

            # SWEET SPOT: 8K-30K MC (EXACT logique du live_trading_bot.py)
            if mc < 8000:
                signal['action'] = 'SKIP'
                signal['reason'] = 'MC too low (< 8K sweet spot)'
                console_logger.log(f"SKIP: {name} - MC too low (${mc:.0f})", 'SKIP', user_id=0)
                return signal

            if mc > 30000:
                signal['action'] = 'SKIP'
                signal['reason'] = 'MC too high (> 30K sweet spot)'
                console_logger.log(f"SKIP: {name} - MC too high (${mc/1000:.1f}K)", 'SKIP', user_id=0)
                return signal

            # SKIP automatique (EXACT logique du live_trading_bot.py)
            if txns < 5:
                signal['action'] = 'SKIP'
                signal['reason'] = 'Not enough transactions (< 5)'
                console_logger.log(f"SKIP: {name} - Not enough txns ({txns})", 'SKIP', user_id=0)
                return signal

            # Calculer buy_ratio (approximation - pas de données depuis PumpFun)
            # Pour le WebSocket PumpFun, on n'a pas buy_ratio directement
            # On va skip ce filtre pour l'instant et se concentrer sur MC + txns

            # ========== RUNNER DETECTION ==========
            try:
                runner_analysis = await self.runner_detector.analyze_runner_potential(token_data)

                signal['runner_score'] = runner_analysis.runner_score
                signal['runner_potential'] = runner_analysis.potential.value
                signal['runner_phase'] = runner_analysis.phase.value
                signal['target_x_low'] = runner_analysis.potential_x_low
                signal['target_x_mid'] = runner_analysis.potential_x_mid
                signal['target_x_high'] = runner_analysis.potential_x_high
                signal['runner_signals'] = runner_analysis.signals
                signal['runner_warnings'] = runner_analysis.warnings

                # Check if token is a potential RUNNER
                if runner_analysis.potential in [RunnerPotential.MOON, RunnerPotential.RUNNER]:
                    signal['is_runner'] = True
                    self.runners_detected += 1

                    # Adjust action based on runner score
                    if runner_analysis.runner_score >= 70:
                        signal['action'] = 'BUY'
                        signal['confidence'] = min(0.95, runner_analysis.runner_score / 100)
                        signal['reason'] = f"🚀 RUNNER DETECTED! Score: {runner_analysis.runner_score}/100 | Target: {runner_analysis.potential_x_mid}x"
                    elif runner_analysis.runner_score >= 55:
                        signal['action'] = 'BUY'
                        signal['confidence'] = runner_analysis.runner_score / 100
                        signal['reason'] = f"📈 Potential runner. Score: {runner_analysis.runner_score}/100"

                # Pre-migration detection (high priority)
                if runner_analysis.phase == RunnerPhase.PRE_MIGRATION and runner_analysis.runner_score >= 60:
                    signal['action'] = 'BUY'
                    signal['confidence'] = max(signal['confidence'], 0.8)
                    signal['reason'] = f"⚡ PRE-MIGRATION! Score: {runner_analysis.runner_score}/100 | Target: {runner_analysis.potential_x_mid}x"
                    signal['is_runner'] = True

            except Exception as runner_error:
                print(f"[WARNING] Runner detection failed: {runner_error}")
            # ========================================

            # Fallback: Signal d'achat standard (EXACT logique du live_trading_bot.py)
            if signal['action'] is None:
                # AUTO-BUY criteria (simplifié car on n'a pas tous les champs)
                # Dans le vrai bot: txns >= 22, traders >= 17, buy_ratio >= 0.72
                # Ici on simplifie: si dans sweet spot + txns >= 10
                if mc >= 8000 and mc <= 30000 and txns >= 10:
                    signal['action'] = 'BUY'
                    signal['confidence'] = 0.75
                    signal['reason'] = 'Sweet spot entry (8K-30K MC)'
                else:
                    signal['action'] = 'WAIT'
                    signal['reason'] = 'Waiting for better signal'

            # Log scanner activity for public/private display
            try:
                scanner_manager.log_token_scanned(token_data, signal)
            except Exception as log_error:
                print(f"[WARNING] Failed to log scanner activity: {log_error}")

            return signal

        except Exception as e:
            print(f"[ERROR] Token analysis failed: {e}")
            return {'action': 'SKIP', 'reason': f'Error: {e}'}

    async def distribute_signal(self, signal: dict):
        """
        Distribue le signal à tous les bots actifs
        Chaque bot décide ensuite selon sa stratégie
        """
        if signal['action'] == 'SKIP':
            return  # Ne pas spammer les bots avec des SKIP

        self.signals_sent += 1

        # Log le signal BUY dans la console (pour tous les utilisateurs)
        console_logger = get_console_logger()
        if signal['action'] == 'BUY':
            console_logger.log(f"BUY SIGNAL: {signal['name']} @ ${signal['mc']/1000:.1f}K | Confidence: {signal['confidence']:.0%}", 'INFO', user_id=0)

        # Distribuer à chaque bot actif
        for user_id, bot_info in self.active_bots.items():
            try:
                # Chaque bot va recevoir le signal et trader selon sa config
                bot_info['signals_received'] += 1

                # Envoyer le signal au bot
                bot_instance = bot_info.get('bot_instance')
                if bot_instance and signal['action'] == 'BUY':
                    print(f"[ENGINE] Signal BUY → User {user_id} | {signal['mint'][:8]}... @ ${signal['mc']/1000:.1f}K")
                    # Appeler on_signal() du bot (synchrone, met dans queue)
                    bot_instance.on_signal(signal)

            except Exception as e:
                print(f"[ERROR] Failed to distribute to user {user_id}: {e}")

    async def process_token(self, token_data: dict):
        """Pipeline complet: analyse + distribution"""
        # Analyse 1 fois
        signal = await self.analyze_token(token_data)

        # Distribue à tous
        await self.distribute_signal(signal)

    async def start(self):
        """Démarre le moteur"""
        print(f"[ENGINE] Starting trading engine...")

        # S'abonner au feed partagé
        self.feed.subscribe(self.process_token)

        print(f"[ENGINE] Engine ready! Monitoring for active bots...")

        # Keep alive
        while True:
            await asyncio.sleep(60)

            # Stats toutes les minutes
            print(f"[ENGINE] Stats: {len(self.active_bots)} bots | "
                  f"{self.tokens_analyzed} tokens | {self.signals_sent} signals")

    def get_stats(self):
        """Stats du moteur"""
        return {
            'active_bots': len(self.active_bots),
            'tokens_analyzed': self.tokens_analyzed,
            'signals_sent': self.signals_sent,
            'bots': [
                {
                    'user_id': user_id,
                    'signals_received': info['signals_received'],
                    'uptime': (datetime.now() - info['registered_at']).total_seconds()
                }
                for user_id, info in self.active_bots.items()
            ]
        }


# Instance globale
_engine = None


def get_engine() -> TradingEngine:
    """Récupère l'instance du moteur"""
    global _engine

    if _engine is None:
        _engine = TradingEngine()

    return _engine


if __name__ == "__main__":
    # Test
    engine = get_engine()

    # Simuler des bots
    engine.register_bot(1, {'strategy': 'RISQUER'})
    engine.register_bot(2, {'strategy': 'SAFE'})

    # Démarrer
    asyncio.run(engine.start())

"""
AI TRADING ENGINE - EXACT REPLICA of live_trading_bot.py
Utilise TOUTE l'IA + Learning Engine + Adaptive Config
Compatible avec le mode simulation du site web
"""
import asyncio
import json
import joblib
import pandas as pd
from datetime import datetime
import websockets
from typing import Dict, Callable

# Import des modules IA
from learning_engine import learning_engine
from adaptive_config import adaptive_config
from console_logger import get_console_logger

# PRIX EN TEMPS RÉEL (stockés depuis le WebSocket)
_last_known_prices = {}  # {mint: {'mc_usd': X, 'timestamp': Y}}

def get_last_known_price(mint):
    """
    Récupère le dernier prix connu d'un token depuis le WebSocket
    Alternative à get_token_price_live() qui utilise l'API REST bloquée
    """
    if mint in _last_known_prices:
        data = _last_known_prices[mint]
        return {
            'mc_usd': data['mc_usd'],
            'mc_sol': data['mc_usd'] / Config.get_sol_price(),
            'success': True,
            'source': 'websocket'
        }

    # Token pas encore vu dans le WebSocket
    return {
        'mc_usd': 0,
        'mc_sol': 0,
        'success': False,
        'source': 'not_found'
    }

# Configuration (copié depuis live_trading_bot.py)
class Config:
    # WebSocket PumpFun
    PUMPFUN_WS = "wss://pumpportal.fun/api/data"

    # Prix SOL (approximation)
    SOL_PRICE = 200.0

    @staticmethod
    def get_sol_price():
        return Config.SOL_PRICE

    # IA - SEUILS DE CONFIANCE
    THRESHOLD_8S = 0.50
    THRESHOLD_15S = 0.50

    # PRIX LIMITES (MC en USD)
    MAX_PRICE_8S = 12000
    MAX_PRICE_15S = 30000

    # AUTO-BUY (Niveau 1 - Bypass IA)
    AUTO_BUY_MIN_TXN = 22
    AUTO_BUY_MIN_TRADERS = 17
    AUTO_BUY_MIN_BUY_RATIO = 0.72
    AUTO_BUY_MAX_MC = 30000
    AUTO_BUY_MAX_TXN = 50
    AUTO_BUY_MAX_TRADERS = 35

    # Filtres IA (Niveau 2)
    AI_MIN_TXN = adaptive_config.get_param('AI_MIN_TXN')
    AI_MIN_TRADERS = adaptive_config.get_param('AI_MIN_TRADERS')
    AI_MIN_BUY_RATIO = adaptive_config.get_param('AI_MIN_BUY_RATIO')

    # SKIP automatique (Niveau 3)
    SKIP_IF_TXN_BELOW = 5
    SKIP_IF_BUY_RATIO_BELOW = 0.40

    # SWEET SPOT
    SWEET_SPOT_MIN_MC = 8000
    SWEET_SPOT_MAX_MC = 30000

    # Baleines
    WHALE_THRESHOLD = 400  # $400 minimum
    AI_MAX_WHALES_EARLY = 1  # Max 1 baleine si MC < 12K
    AI_MAX_WHALES_LATE = 3   # Max 3 baleines si MC >= 12K
    AI_STRICT_BUY_RATIO = 0.72

    # ELITE WALLETS
    ELITE_WALLETS = {
        '87rRdssFiTJKY4MGARa4G5vQ31hmR7MxSmhzeaJ5AAxJ',
        'CyaE1VxvBrahnPWkqm5VsdCvyS2QmNht2UFrKJHga54o',
        '5B79fMkcFeRTiwm7ehsZsFiKsC7m7n1Bgv9yLxPp9q2X',
        '4BdKaxN8G6ka4GYtQQWk4G4dZRUTX2vQH9GcXdBREFUk',
        '4Be9CvxqHW6BYiRAxW9Q3xu1ycTMWaL5z8NX4HR3ha7t',
        '2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f',
        'Av3xWHJ5EsoLZag6pr7LKbrGgLRTaykXomDD5kBhL9YQ',
        '78N177fzNJpp8pG49xDv1efYcTMSzo9tPTKEA9mAVkh2',
        'CA4keXLtGJWBcsWivjtMFBghQ8pFsGRWFxLrRCtirzu5',
        'BbwF4wSwmxMVp7xubA7qigCUU6RMcvK2soMu8VrDHjDH',
        'A8H8D8WegN7MgMdRAVYWU2uAcSTfZaC3c6pyLDF8CFXv',
        'iBH7W6i8i6dKmv5aoj7b6VRjx1UXMyjuxx1BichwVZd',
        '8yJFWmVTQq69p6VJxGwpzW7ii7c5J9GRAtHCNMMQPydj',
        'BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE',
        '5YkZmuaLhrPjFv4vtYE2mcR6J4JEXG1EARGh8YYFo8s4'
    }
    ELITE_WALLET_MAX_MC = adaptive_config.get_param('ELITE_WALLET_MAX_MC')
    ELITE_MIN_BUY_RATIO = adaptive_config.get_param('ELITE_MIN_BUY_RATIO')
    ELITE_MIN_WHALE_COUNT = adaptive_config.get_param('ELITE_MIN_WHALE_COUNT')

    PUMPFUN_WS = "wss://pumpportal.fun/api/data"


# Charger les modeles IA
print("[AI ENGINE] Loading AI models...")
try:
    model_10s = joblib.load('model_10s.pkl')
    model_15s = joblib.load('model_15s.pkl')
    print("  [OK] Modele @ 10s: OK")
    print("  [OK] Modele @ 15s: OK")
except Exception as e:
    print(f"  [ERROR] {e}")
    model_10s = None
    model_15s = None


class AITradingEngine:
    """
    Moteur de trading avec IA complet
    Réplique exacte de live_trading_bot.py
    """

    def __init__(self):
        self.ws = None
        self.tokens: Dict[str, dict] = {}  # {mint: token_data}
        self.signal_callbacks: list[Callable] = []
        self.registered_bots: Dict[int, dict] = {}  # {user_id: bot_instance}
        self.is_running = False

        # Stats
        self.tokens_tracked = 0
        self.signals_generated = 0

    def register_bot(self, user_id: int, config: dict, bot_instance=None):
        """Enregistrer un bot pour recevoir des signaux"""
        self.registered_bots[user_id] = bot_instance
        print(f"[ENGINE] Bot registered: User {user_id} | Total: {len(self.registered_bots)}")

    def unregister_bot(self, user_id: int):
        """Désinscrire un bot"""
        if user_id in self.registered_bots:
            del self.registered_bots[user_id]
            print(f"[ENGINE] Bot unregistered: User {user_id}")

    def subscribe_signals(self, callback: Callable):
        """S'abonner aux signaux de trading"""
        self.signal_callbacks.append(callback)
        print(f"[AI ENGINE] Signal callback registered")

    async def broadcast_signal(self, signal: dict):
        """Envoyer un signal à tous les bots enregistrés"""
        self.signals_generated += 1

        # Envoyer aux bots enregistrés (thread-safe via queue)
        for user_id, bot_instance in self.registered_bots.items():
            if bot_instance and hasattr(bot_instance, 'on_signal'):
                try:
                    # on_signal() met le signal dans une queue thread-safe
                    bot_instance.on_signal(signal)
                except Exception as e:
                    print(f"[AI ENGINE] Error sending to bot {user_id}: {e}")

        # Envoyer aux callbacks (legacy)
        for callback in self.signal_callbacks:
            try:
                asyncio.create_task(callback(signal))
            except Exception as e:
                print(f"[AI ENGINE] Callback error: {e}")

    def calculate_snapshot(self, token, max_age):
        """Calcule les features pour une période (EXACT copie de live_trading_bot.py)"""
        created_at = token['created_at']
        trades_in_period = [t for t in token['trades'] if (t['time'] - created_at) <= max_age]

        if not trades_in_period:
            return None

        buys = [t for t in trades_in_period if t['type'] == 'buy']
        sells = [t for t in trades_in_period if t['type'] == 'sell']
        unique_traders = len(set(t['trader'] for t in trades_in_period))

        # Calculer la vélocité (croissance MC)
        mc_current = trades_in_period[-1]['mc'] if trades_in_period else 0
        mc_initial = token.get('mc_initial', 0)
        velocity = (mc_current - mc_initial) / max_age if max_age > 0 else 0

        # Compter les baleines
        whale_count = len(set(t['trader'] for t in buys if t.get('amount_usd', 0) >= Config.WHALE_THRESHOLD))

        # Compter les WALLETS ELITE
        elite_wallet_count = len(set(t['trader'] for t in buys if t['trader'] in Config.ELITE_WALLETS))
        elite_wallets_found = [t['trader'][:8] for t in buys if t['trader'] in Config.ELITE_WALLETS]

        # DETECTER 2 BALEINES CONSECUTIVES
        consecutive_whales = False
        if len(buys) >= 2:
            recent_buys = buys[-5:]
            whale_buys = [b for b in recent_buys if b.get('amount_usd', 0) >= Config.WHALE_THRESHOLD]

            if len(whale_buys) >= 2:
                last_whale_idx = None
                second_last_whale_idx = None

                for i in range(len(recent_buys) - 1, -1, -1):
                    if recent_buys[i].get('amount_usd', 0) >= Config.WHALE_THRESHOLD:
                        if last_whale_idx is None:
                            last_whale_idx = i
                        elif second_last_whale_idx is None:
                            second_last_whale_idx = i
                            break

                if last_whale_idx is not None and second_last_whale_idx is not None:
                    if last_whale_idx - second_last_whale_idx == 1:
                        consecutive_whales = True

        return {
            'txn': len(trades_in_period),
            'buys': len(buys),
            'sells': len(sells),
            'buy_ratio': len(buys)/len(trades_in_period) if trades_in_period else 0,
            'traders': unique_traders,
            'mc': mc_current,
            'velocity': velocity,
            'whale_count': whale_count,
            'elite_wallet_count': elite_wallet_count,
            'elite_wallets': elite_wallets_found,
            'consecutive_whales': consecutive_whales
        }

    def predict_8s(self, snapshot_8s, mint=None):
        """Prédiction @ 8 secondes (EXACT copie de live_trading_bot.py)"""
        if not snapshot_8s:
            return None

        txn = snapshot_8s.get('txn', 0)
        traders = snapshot_8s.get('traders', 0)
        buy_ratio = snapshot_8s.get('buy_ratio', 0)
        mc = snapshot_8s.get('mc', 0)
        whale_count = snapshot_8s.get('whale_count', 0)
        elite_wallet_count = snapshot_8s.get('elite_wallet_count', 0)
        elite_wallets = snapshot_8s.get('elite_wallets', [])
        consecutive_whales = snapshot_8s.get('consecutive_whales', False)

        # SWEET SPOT CHECK
        if mc < Config.SWEET_SPOT_MIN_MC or mc > Config.SWEET_SPOT_MAX_MC:
            return {
                'confidence': 0.0,
                'mc': mc,
                'should_buy': False,
                'reason': f'SKIP: MC hors sweet spot (${mc:,.0f})'
            }

        # NIVEAU 0A: 2 BALEINES CONSECUTIVES
        if (consecutive_whales and
            mc < Config.ELITE_WALLET_MAX_MC and
            buy_ratio >= Config.ELITE_MIN_BUY_RATIO and
            whale_count >= Config.ELITE_MIN_WHALE_COUNT):
            return {
                'confidence': 1.0,
                'mc': mc,
                'should_buy': True,
                'reason': f'2 BALEINES CONSECUTIVES! ({whale_count} whales, {buy_ratio*100:.0f}% buy)'
            }

        # NIVEAU 0B: WALLETS ELITE
        if (elite_wallet_count >= 1 and
            mc < Config.ELITE_WALLET_MAX_MC and
            buy_ratio >= Config.ELITE_MIN_BUY_RATIO and
            whale_count >= Config.ELITE_MIN_WHALE_COUNT):
            wallets_str = ', '.join(elite_wallets[:3])
            return {
                'confidence': 1.0,
                'mc': mc,
                'should_buy': True,
                'reason': f'ELITE WALLET: {elite_wallet_count} VIP ({wallets_str})'
            }

        # NIVEAU 1: AUTO-BUY
        if (txn >= Config.AUTO_BUY_MIN_TXN and
            traders >= Config.AUTO_BUY_MIN_TRADERS and
            buy_ratio >= Config.AUTO_BUY_MIN_BUY_RATIO and
            mc < Config.AUTO_BUY_MAX_MC):

            max_whales_allowed = Config.AI_MAX_WHALES_EARLY if mc < 12000 else Config.AI_MAX_WHALES_LATE

            if whale_count > max_whales_allowed:
                return {
                    'confidence': 0.0,
                    'mc': mc,
                    'should_buy': False,
                    'reason': f'SKIP AUTO-BUY: {whale_count} baleines (max {max_whales_allowed})'
                }

            if txn > Config.AUTO_BUY_MAX_TXN or traders > Config.AUTO_BUY_MAX_TRADERS:
                return {
                    'confidence': 0.0,
                    'mc': mc,
                    'should_buy': False,
                    'reason': f'SKIP AUTO-BUY: Volume trop élevé (probable bots)'
                }

            return {
                'confidence': 1.0,
                'mc': mc,
                'should_buy': True,
                'reason': f'AUTO-BUY: {txn}txn, {traders}traders, {buy_ratio*100:.0f}% buy'
            }

        # NIVEAU 3: SKIP AUTOMATIQUE
        if (txn < Config.SKIP_IF_TXN_BELOW or
            buy_ratio < Config.SKIP_IF_BUY_RATIO_BELOW or
            mc >= Config.MAX_PRICE_8S):
            return {
                'confidence': 0.0,
                'mc': mc,
                'should_buy': False,
                'reason': 'SKIP: Critères trop faibles'
            }

        # NIVEAU 2: IA
        if buy_ratio < Config.AI_STRICT_BUY_RATIO:
            return {
                'confidence': 0.0,
                'mc': mc,
                'should_buy': False,
                'reason': f'SKIP: Buy ratio trop faible ({buy_ratio*100:.0f}%)'
            }

        max_whales_allowed = Config.AI_MAX_WHALES_EARLY if mc < 12000 else Config.AI_MAX_WHALES_LATE
        if whale_count > max_whales_allowed:
            return {
                'confidence': 0.0,
                'mc': mc,
                'should_buy': False,
                'reason': f'SKIP IA: {whale_count} baleines (max {max_whales_allowed})'
            }

        # Prédiction avec modèle IA (EXACT comme live_trading_bot.py)
        if model_10s:
            try:
                features = pd.DataFrame([{
                    'txn': txn,
                    'traders': traders,
                    'buy_ratio': buy_ratio,
                    'mc': mc,
                    'velocity': snapshot_8s.get('velocity', 0),
                    'whale_count': whale_count  # ← Features exactes du modèle!
                }])

                prob = model_10s.predict_proba(features)[0][1]

                if prob >= Config.THRESHOLD_8S:
                    return {
                        'confidence': prob,
                        'mc': mc,
                        'should_buy': True,
                        'reason': f'AI @ 8s: {prob*100:.0f}% confidence'
                    }
            except Exception as e:
                print(f"[AI ENGINE] AI prediction error: {e}")

        return {
            'confidence': 0.0,
            'mc': mc,
            'should_buy': False,
            'reason': 'WAIT: En observation'
        }

    async def handle_new_token(self, data, ws):
        """Nouveau token détecté"""
        mint = data.get('mint')
        symbol = data.get('symbol', 'UNKNOWN')
        name = data.get('name', 'Unknown')
        mc_usd = data.get('usd_market_cap', 0)

        print(f"[AI ENGINE] NEW TOKEN: {symbol} @ ${mc_usd:,.0f}")

        # Créer le token tracking
        self.tokens[mint] = {
            'mint': mint,
            'symbol': symbol,
            'name': name,
            'created_at': datetime.now().timestamp(),
            'mc_initial': mc_usd,
            'trades': [],
            'snapshot_8s': None,
            'snapshot_15s': None
        }

        self.tokens_tracked += 1

        # S'abonner aux trades de ce token
        await ws.send(json.dumps({
            "method": "subscribeTokenTrade",
            "keys": [mint]
        }))

        # Programmer l'analyse à 8s et 15s
        asyncio.create_task(self.track_token(mint))

    async def handle_trade(self, data):
        """Trade détecté"""
        mint = data.get('mint')
        if mint not in self.tokens:
            return

        token = self.tokens[mint]

        # Ajouter le trade (EXACT comme live_trading_bot.py)
        sol_amount = data.get('solAmount', 0)
        amount_usd = sol_amount * Config.get_sol_price()
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * Config.get_sol_price()

        # STOCKER LE PRIX EN TEMPS RÉEL (pour get_last_known_price)
        global _last_known_prices
        _last_known_prices[mint] = {
            'mc_usd': mc_usd,
            'timestamp': datetime.now().timestamp()
        }

        trade = {
            'time': datetime.now().timestamp(),
            'type': data.get('txType'),  # 'buy' ou 'sell'
            'trader': data.get('traderPublicKey', 'unknown'),
            'amount_sol': sol_amount,
            'amount_usd': amount_usd,
            'mc': mc_usd
        }

        token['trades'].append(trade)

    async def track_token(self, mint):
        """Tracker un token et générer des signaux"""
        # Attendre 8 secondes
        await asyncio.sleep(8)

        if mint not in self.tokens:
            return

        token = self.tokens[mint]

        # Calculer snapshot @ 8s
        snapshot_8s = self.calculate_snapshot(token, 8)
        token['snapshot_8s'] = snapshot_8s

        console_logger = get_console_logger()

        if snapshot_8s:
            mc = snapshot_8s.get('mc', 0)
            # Log NEW TOKEN avec le vrai MC @ 8s
            console_logger.log(f"[NEW TOKEN] {token['symbol']} ({mint[:8]}...) @ ${mc:,.0f}", 'NEW_TOKEN')

            # Prédiction @ 8s
            prediction = self.predict_8s(snapshot_8s, mint)

            if prediction and prediction['should_buy']:
                # SIGNAL BUY!
                signal = {
                    'mint': mint,
                    'name': token['name'],
                    'symbol': token['symbol'],
                    'mc': prediction['mc'],
                    'action': 'BUY',
                    'confidence': prediction['confidence'],
                    'reason': prediction['reason'],
                    'timestamp': datetime.now().isoformat()
                }

                print(f"[AI ENGINE] BUY SIGNAL: {token['symbol']} @ ${prediction['mc']:,.0f} | {prediction['reason']}")

                # Log au console web
                console_logger.log(f"🟢 BUY: {token['symbol']} @ ${prediction['mc']:,.0f} | Confidence: {prediction['confidence']:.0%}", 'BUY')

                # Broadcaster le signal
                await self.broadcast_signal(signal)

            elif prediction and not prediction['should_buy']:
                # SKIP - Log la raison
                console_logger.log(f"[SKIP @ 8s] {token['symbol']}: {prediction['reason']}", 'SKIP')

        else:
            # Pas assez de trades pour analyser
            console_logger.log(f"[NO DATA @ 8s] {token['symbol']}: Not enough trades to analyze", 'INFO')

        # Attendre 7 secondes de plus (total 15s)
        await asyncio.sleep(7)

        # TODO: Ajouter prédiction @ 15s si pas déjà acheté

        # Nettoyer après 10 minutes
        await asyncio.sleep(585)
        if mint in self.tokens:
            del self.tokens[mint]

    async def connect_websocket(self):
        """Connexion au WebSocket PumpFun"""
        print("[AI ENGINE] Connexion au WebSocket PumpFun...")

        try:
            async with websockets.connect(
                Config.PUMPFUN_WS,
                ping_interval=20,
                ping_timeout=30,
                close_timeout=10,
                max_size=10485760
            ) as ws:
                self.ws = ws

                # S'abonner aux nouveaux tokens
                await ws.send(json.dumps({
                    "method": "subscribeNewToken"
                }))

                print("[AI ENGINE] Connected! Listening for tokens...")

                # Écouter les messages
                async for message in ws:
                    try:
                        data = json.loads(message)
                        tx_type = data.get('txType')

                        # Nouveau token
                        if tx_type == 'create':
                            await self.handle_new_token(data, ws)
                        # Trade
                        elif tx_type in ['buy', 'sell']:
                            await self.handle_trade(data)

                    except Exception as e:
                        print(f"[AI ENGINE] Erreur message: {e}")

        except Exception as e:
            print(f"[AI ENGINE] Erreur WebSocket: {e}")
            print("  Reconnexion dans 10s...")
            await asyncio.sleep(10)
            await self.connect_websocket()

    async def start(self):
        """Démarrer le moteur IA"""
        self.is_running = True
        print("[AI ENGINE] AI Engine started!")

        # Créer une task pour le WebSocket (ne pas bloquer)
        asyncio.create_task(self.connect_websocket())

        # Garder l'engine en vie
        while self.is_running:
            await asyncio.sleep(1)


# Instance globale
_ai_engine = None

def get_ai_engine() -> AITradingEngine:
    """Récupère l'instance du moteur IA"""
    global _ai_engine

    if _ai_engine is None:
        _ai_engine = AITradingEngine()

    return _ai_engine

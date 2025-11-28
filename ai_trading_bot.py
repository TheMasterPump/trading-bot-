import asyncio
import json
import joblib
import pandas as pd
from datetime import datetime
import websockets

print('='*80)
print('AI TRADING BOT - TRADING AUTOMATIQUE AVEC IA')
print('='*80)

# ============================================================================
# CONFIGURATION
# ============================================================================
class Config:
    # Mode
    SIMULATION_MODE = True  # True = simulation, False = trading reel

    # Seuils IA
    THRESHOLD_10S = 0.65  # 65% confiance minimum @ 10s
    THRESHOLD_15S = 0.70  # 70% confiance minimum @ 15s

    # Prix limites
    MAX_PRICE_10S = 15000  # Prix max pour entrer @ 10s
    MAX_PRICE_15S = 20000  # Prix max pour entrer @ 15s

    # Trading
    BUY_AMOUNT_SOL = 0.1  # Montant a acheter (en SOL)
    TAKE_PROFIT_TARGET = 69000  # Vendre quand MC atteint $69K (migration)
    STOP_LOSS_PERCENT = 0.30  # Stop loss a -30%

    # WebSocket PumpFun
    PUMPFUN_WS = "wss://pumpportal.fun/api/data"

print(f'\n[CONFIGURATION]')
print(f'  Mode: {"SIMULATION" if Config.SIMULATION_MODE else "LIVE TRADING"}')
print(f'  IA @ 10s: {Config.THRESHOLD_10S*100:.0f}% confiance, MC < ${Config.MAX_PRICE_10S:,}')
print(f'  IA @ 15s: {Config.THRESHOLD_15S*100:.0f}% confiance, MC < ${Config.MAX_PRICE_15S:,}')
print(f'  Montant par trade: {Config.BUY_AMOUNT_SOL} SOL')
print(f'  Take Profit: ${Config.TAKE_PROFIT_TARGET:,} MC')
print(f'  Stop Loss: -{Config.STOP_LOSS_PERCENT*100:.0f}%')

# ============================================================================
# CHARGEMENT DES MODELES IA
# ============================================================================
print(f'\n[CHARGEMENT DES MODELES IA]')
try:
    model_10s = joblib.load('model_10s.pkl')
    model_15s = joblib.load('model_15s.pkl')
    print(f'  Model @ 10s: OK')
    print(f'  Model @ 15s: OK')
except Exception as e:
    print(f'  ERREUR: {e}')
    print(f'  Lance d\'abord: python train_models.py')
    exit(1)

# ============================================================================
# GESTIONNAIRE DE POSITIONS
# ============================================================================
class PositionManager:
    def __init__(self):
        self.open_positions = {}  # {token_address: position_data}
        self.closed_positions = []
        self.total_profit = 0
        self.total_loss = 0

    def open_position(self, token_address, symbol, entry_price, entry_time, amount_sol, confidence):
        position = {
            'symbol': symbol,
            'token_address': token_address,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'entry_timestamp': datetime.now(),
            'amount_sol': amount_sol,
            'confidence': confidence,
            'stop_loss_price': entry_price * (1 - Config.STOP_LOSS_PERCENT),
            'take_profit_price': Config.TAKE_PROFIT_TARGET,
            'status': 'OPEN'
        }

        self.open_positions[token_address] = position

        print(f'\n[ACHAT] {symbol}')
        print(f'  Prix entree: ${entry_price:,.0f}')
        print(f'  Montant: {amount_sol} SOL')
        print(f'  Confiance IA: {confidence*100:.0f}%')
        print(f'  Stop Loss: ${position["stop_loss_price"]:,.0f}')
        print(f'  Take Profit: ${position["take_profit_price"]:,.0f}')

        return position

    def close_position(self, token_address, exit_price, reason):
        if token_address not in self.open_positions:
            return

        position = self.open_positions[token_address]
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now()
        position['exit_reason'] = reason
        position['status'] = 'CLOSED'

        # Calculer profit/perte
        profit_ratio = exit_price / position['entry_price']
        profit_percent = (profit_ratio - 1) * 100

        position['profit_ratio'] = profit_ratio
        position['profit_percent'] = profit_percent

        if profit_percent > 0:
            self.total_profit += 1
        else:
            self.total_loss += 1

        self.closed_positions.append(position)
        del self.open_positions[token_address]

        print(f'\n[VENTE] {position["symbol"]} - {reason}')
        print(f'  Prix entree: ${position["entry_price"]:,.0f}')
        print(f'  Prix sortie: ${exit_price:,.0f}')
        print(f'  Profit: {profit_ratio:.2f}x ({profit_percent:+.1f}%)')

        return position

    def check_positions(self, token_address, current_mc):
        """Verifie si un stop loss ou take profit est atteint"""
        if token_address not in self.open_positions:
            return

        position = self.open_positions[token_address]

        # Take Profit
        if current_mc >= position['take_profit_price']:
            self.close_position(token_address, current_mc, 'TAKE PROFIT (Migration)')
            return 'CLOSED'

        # Stop Loss
        if current_mc <= position['stop_loss_price']:
            self.close_position(token_address, current_mc, 'STOP LOSS')
            return 'CLOSED'

        return 'OPEN'

    def show_summary(self):
        print(f'\n{"="*80}')
        print('RESUME DES TRADES')
        print('='*80)

        total_trades = len(self.closed_positions)

        if total_trades == 0:
            print('  Aucun trade ferme')
            return

        print(f'\n[STATISTIQUES]')
        print(f'  Total trades: {total_trades}')
        print(f'  Gagnants: {self.total_profit}')
        print(f'  Perdants: {self.total_loss}')

        win_rate = (self.total_profit / total_trades * 100) if total_trades > 0 else 0
        print(f'  Win Rate: {win_rate:.1f}%')

        # Profit moyen
        profits = [p['profit_ratio'] for p in self.closed_positions]
        avg_profit = sum(profits) / len(profits) if profits else 0

        print(f'\n[PROFITS]')
        print(f'  Profit moyen: {avg_profit:.2f}x')
        print(f'  Meilleur: {max(profits):.2f}x' if profits else '  N/A')
        print(f'  Pire: {min(profits):.2f}x' if profits else '  N/A')

        print(f'\n[DERNIERS TRADES]')
        for i, pos in enumerate(self.closed_positions[-5:], 1):
            print(f'  {i}. {pos["symbol"]:12} | {pos["profit_ratio"]:.2f}x ({pos["profit_percent"]:+.1f}%) | {pos["exit_reason"]}')

# ============================================================================
# SYSTEME DE PREDICTION IA
# ============================================================================
class AIPredictionSystem:
    def __init__(self, model_10s, model_15s):
        self.model_10s = model_10s
        self.model_15s = model_15s
        self.token_data = {}  # Stocke les donnees des tokens

    def store_snapshot(self, token_address, snapshot_time, data):
        """Stocke un snapshot pour un token"""
        if token_address not in self.token_data:
            self.token_data[token_address] = {}

        self.token_data[token_address][snapshot_time] = data

    def predict_10s(self, token_address):
        """Prediction @ 10 secondes"""
        if token_address not in self.token_data:
            return None

        if '10s' not in self.token_data[token_address]:
            return None

        snap = self.token_data[token_address]['10s']

        features = pd.DataFrame([{
            'txn': snap.get('txn', 0),
            'traders': snap.get('traders', 0),
            'buy_ratio': snap.get('buy_ratio', 0),
            'mc': snap.get('mc', 0),
            'velocity': snap.get('velocity', 0),
            'whale_count': snap.get('whale_count', 0)
        }])

        proba = self.model_10s.predict_proba(features)[0, 1]
        mc = snap.get('mc', 0)

        return {
            'confidence': proba,
            'mc': mc,
            'should_buy': proba >= Config.THRESHOLD_10S and mc < Config.MAX_PRICE_10S,
            'reason': '10s'
        }

    def predict_15s(self, token_address):
        """Prediction @ 15 secondes"""
        if token_address not in self.token_data:
            return None

        if '10s' not in self.token_data[token_address] or '15s' not in self.token_data[token_address]:
            return None

        snap_10s = self.token_data[token_address]['10s']
        snap_15s = self.token_data[token_address]['15s']

        mc_growth = 0
        if snap_10s.get('mc', 0) > 0:
            mc_growth = (snap_15s.get('mc', 0) - snap_10s.get('mc', 0)) / snap_10s.get('mc', 1)

        features = pd.DataFrame([{
            '10s_txn': snap_10s.get('txn', 0),
            '10s_traders': snap_10s.get('traders', 0),
            '10s_buy_ratio': snap_10s.get('buy_ratio', 0),
            '10s_mc': snap_10s.get('mc', 0),
            '10s_velocity': snap_10s.get('velocity', 0),
            '15s_txn': snap_15s.get('txn', 0),
            '15s_traders': snap_15s.get('traders', 0),
            '15s_buy_ratio': snap_15s.get('buy_ratio', 0),
            '15s_mc': snap_15s.get('mc', 0),
            '15s_velocity': snap_15s.get('velocity', 0),
            'mc_growth_10s_15s': mc_growth,
            'txn_growth_10s_15s': snap_15s.get('txn', 0) - snap_10s.get('txn', 0),
            'traders_growth_10s_15s': snap_15s.get('traders', 0) - snap_10s.get('traders', 0),
            'whale_count': snap_10s.get('whale_count', 0)
        }])

        proba = self.model_15s.predict_proba(features)[0, 1]
        mc = snap_15s.get('mc', 0)

        return {
            'confidence': proba,
            'mc': mc,
            'should_buy': proba >= Config.THRESHOLD_15S and mc < Config.MAX_PRICE_15S,
            'reason': '15s'
        }

# ============================================================================
# BOT DE TRADING PRINCIPAL
# ============================================================================
class AITradingBot:
    def __init__(self):
        self.ai_system = AIPredictionSystem(model_10s, model_15s)
        self.position_manager = PositionManager()
        self.tokens_tracking = {}  # Tokens en cours de tracking

    async def on_new_token(self, token_data):
        """Nouveau token detecte"""
        token_address = token_data.get('mint', 'unknown')
        symbol = token_data.get('symbol', 'N/A')

        print(f'\n[NOUVEAU TOKEN] {symbol} ({token_address[:8]}...)')

        # Commencer le tracking
        self.tokens_tracking[token_address] = {
            'symbol': symbol,
            'start_time': datetime.now(),
            'data': token_data
        }

        # Programmer les snapshots @ 10s et 15s
        asyncio.create_task(self.schedule_snapshots(token_address, symbol))

    async def schedule_snapshots(self, token_address, symbol):
        """Programme les snapshots @ 10s et 15s"""

        # Attendre 10 secondes
        await asyncio.sleep(10)

        # Snapshot @ 10s
        snap_10s = await self.get_token_snapshot(token_address)
        if snap_10s:
            self.ai_system.store_snapshot(token_address, '10s', snap_10s)

            # Prediction @ 10s
            prediction = self.ai_system.predict_10s(token_address)
            if prediction and prediction['should_buy']:
                # ACHETER !
                if Config.SIMULATION_MODE:
                    self.position_manager.open_position(
                        token_address, symbol,
                        prediction['mc'], '10s',
                        Config.BUY_AMOUNT_SOL,
                        prediction['confidence']
                    )
                else:
                    # TODO: Executer vraie transaction Solana
                    print(f'  [LIVE TRADING] Achat de {symbol}...')

        # Attendre 5 secondes de plus (total 15s)
        await asyncio.sleep(5)

        # Snapshot @ 15s
        snap_15s = await self.get_token_snapshot(token_address)
        if snap_15s:
            self.ai_system.store_snapshot(token_address, '15s', snap_15s)

            # Prediction @ 15s (si pas deja achete @ 10s)
            if token_address not in self.position_manager.open_positions:
                prediction = self.ai_system.predict_15s(token_address)
                if prediction and prediction['should_buy']:
                    # ACHETER !
                    if Config.SIMULATION_MODE:
                        self.position_manager.open_position(
                            token_address, symbol,
                            prediction['mc'], '15s',
                            Config.BUY_AMOUNT_SOL,
                            prediction['confidence']
                        )
                    else:
                        # TODO: Executer vraie transaction Solana
                        print(f'  [LIVE TRADING] Achat de {symbol}...')

    async def get_token_snapshot(self, token_address):
        """Recupere les donnees actuelles d'un token"""
        # TODO: Implementer la recuperation reelle des donnees
        # Pour l'instant retourne des donnees simulees basees sur bot_data.json
        return {
            'txn': 0,
            'traders': 0,
            'buy_ratio': 0,
            'mc': 0,
            'velocity': 0,
            'whale_count': 0
        }

    async def monitor_positions(self):
        """Monitore les positions ouvertes"""
        while True:
            for token_address in list(self.position_manager.open_positions.keys()):
                # TODO: Recuperer MC actuel du token
                current_mc = 0  # Placeholder

                # Verifier stop loss / take profit
                self.position_manager.check_positions(token_address, current_mc)

            await asyncio.sleep(5)  # Check toutes les 5 secondes

    async def run(self):
        """Lance le bot"""
        print(f'\n{"="*80}')
        print('BOT DE TRADING EN COURS...')
        print('='*80)
        print(f'\nMode: {"SIMULATION" if Config.SIMULATION_MODE else "LIVE"}')
        print(f'En attente de nouveaux tokens...')

        # TODO: Se connecter au WebSocket PumpFun
        # Pour l'instant, mode test avec donnees existantes

        # Lancer le monitoring des positions
        monitor_task = asyncio.create_task(self.monitor_positions())

        # Simuler quelques tokens pour tester
        await self.test_with_existing_data()

        # Attendre
        await monitor_task

    async def test_with_existing_data(self):
        """Test avec les donnees existantes"""
        print(f'\n[MODE TEST] Utilisation des donnees existantes...')

        # Charger bot_data.json
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

            runners = data.get('runners', [])[:5]  # Limiter a 5 pour le test

            for token in runners:
                symbol = token.get('symbol', 'N/A')
                address = token.get('address', f'test_{symbol}')

                # Simuler nouveau token
                await self.on_new_token({'mint': address, 'symbol': symbol})

                # Simuler les snapshots
                snap_10s = token.get('10s', {})
                snap_15s = token.get('15s', {})

                if snap_10s:
                    snap_10s['whale_count'] = token.get('whale_count', 0)
                    self.ai_system.store_snapshot(address, '10s', snap_10s)

                    # Prediction @ 10s
                    prediction = self.ai_system.predict_10s(address)
                    if prediction and prediction['should_buy']:
                        self.position_manager.open_position(
                            address, symbol,
                            prediction['mc'], '10s',
                            Config.BUY_AMOUNT_SOL,
                            prediction['confidence']
                        )

                if snap_15s:
                    self.ai_system.store_snapshot(address, '15s', snap_15s)

                    # Prediction @ 15s si pas deja achete
                    if address not in self.position_manager.open_positions:
                        prediction = self.ai_system.predict_15s(address)
                        if prediction and prediction['should_buy']:
                            self.position_manager.open_position(
                                address, symbol,
                                prediction['mc'], '15s',
                                Config.BUY_AMOUNT_SOL,
                                prediction['confidence']
                            )

                # Simuler la migration
                if token.get('migration_detected'):
                    final_mc = token.get('final_mc', Config.TAKE_PROFIT_TARGET)
                    if address in self.position_manager.open_positions:
                        self.position_manager.close_position(address, final_mc, 'MIGRATION DETECTED')

                await asyncio.sleep(0.5)  # Petit delai entre tokens

            # Afficher le resume
            self.position_manager.show_summary()

        except Exception as e:
            print(f'Erreur: {e}')

# ============================================================================
# LANCEMENT DU BOT
# ============================================================================
if __name__ == '__main__':
    print(f'\n{"="*80}')
    print('DEMARRAGE DU BOT...')
    print('='*80)

    bot = AITradingBot()

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print(f'\n\nBot arrete par l\'utilisateur')
        bot.position_manager.show_summary()

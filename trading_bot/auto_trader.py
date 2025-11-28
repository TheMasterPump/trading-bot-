import asyncio
import websockets
import json
import time
from datetime import datetime
from config import *

class AutoTrader:
    def __init__(self):
        self.active_tokens = {}  # Tokens en surveillance
        self.positions = {}  # Positions ouvertes
        self.trade_history = []  # Historique des trades
        self.wallet_balance = 1000  # Balance simulée (Paper trading)

        print(f'{'='*80}')
        print(f'AUTO TRADER INITIALISE')
        print(f'Mode: {TRADING_MODE}')
        print(f'Balance: ${self.wallet_balance}')
        print(f'{'='*80}\n')

    def calculate_metrics(self, token, max_age):
        """Calculer les métriques pour une période"""
        created_at = token['created_at']
        trades = [t for t in token['trades'] if (t['time'] - created_at) <= max_age]

        if not trades:
            return None

        buys = [t for t in trades if t['is_buy']]
        sells = [t for t in trades if not t['is_buy']]

        # Compter les traders uniques
        unique_traders = set(t['wallet'] for t in trades)

        # Big buys
        big_buys_100 = len([t for t in buys if t.get('sol_amount', 0) * t.get('sol_price_usd', 220) >= 100])
        big_buys_500 = len([t for t in buys if t.get('sol_amount', 0) * t.get('sol_price_usd', 220) >= 500])

        # Volume d'achat
        total_buy_volume = sum(t.get('sol_amount', 0) * t.get('sol_price_usd', 220) for t in buys)

        return {
            'txn': len(trades),
            'buys': len(buys),
            'sells': len(sells),
            'buy_ratio': len(buys) / len(trades) if trades else 0,
            'traders': len(unique_traders),
            'big_buys_100': big_buys_100,
            'big_buys_500': big_buys_500,
            'total_buy_volume': total_buy_volume
        }

    def check_entry_signal(self, token, mc_usd):
        """Vérifier si le token respecte les filtres d'entrée"""
        age = time.time() - token['created_at']

        # Vérifier à 15 secondes
        if age < ENTRY_FILTERS['check_at_seconds']:
            return False

        # Calculer les métriques à 15s
        metrics = self.calculate_metrics(token, 15)

        if not metrics:
            return False

        # Vérifier les conditions
        buy_ratio_pct = metrics['buy_ratio'] * 100
        conditions_met = (
            buy_ratio_pct >= ENTRY_FILTERS['buy_ratio_min'] and
            metrics['txn'] >= ENTRY_FILTERS['transactions_min'] and
            metrics['traders'] >= ENTRY_FILTERS['traders_min'] and
            metrics['big_buys_100'] >= ENTRY_FILTERS['big_buys_min']
        )

        if conditions_met:
            print(f'\n[SIGNAL D\'ENTREE] {token["symbol"]} @ ${mc_usd:,.0f}')
            print(f'  Buy Ratio: {buy_ratio_pct:.1f}% (>= {ENTRY_FILTERS["buy_ratio_min"]}%)')
            print(f'  Transactions: {metrics["txn"]} (>= {ENTRY_FILTERS["transactions_min"]})')
            print(f'  Traders: {metrics["traders"]} (>= {ENTRY_FILTERS["traders_min"]})')
            print(f'  Big Buys: {metrics["big_buys_100"]} (>= {ENTRY_FILTERS["big_buys_min"]})')
            print(f'  Volume: ${metrics["total_buy_volume"]:.0f}')

        return conditions_met

    def check_exit_signal(self, mint, mc_usd):
        """Vérifier si on doit sortir de la position"""
        if mint not in self.positions:
            return False

        position = self.positions[mint]
        token = self.active_tokens.get(mint)

        if not token:
            return False

        # Calculer le profit/loss
        entry_price = position['entry_price']
        current_pnl_pct = ((mc_usd - entry_price) / entry_price) * 100

        # Check targets
        for target_name, target_price in TARGETS.items():
            if mc_usd >= target_price and not position.get(f'{target_name}_hit'):
                sell_pct = SELL_PERCENTAGES[target_name]
                print(f'\n[TARGET HIT] {token["symbol"]} @ ${mc_usd:,.0f}')
                print(f'  Target: {target_name} (${target_price:,.0f})')
                print(f'  PnL: +{current_pnl_pct:.1f}%')
                print(f'  Vendre: {sell_pct}% de la position')
                position[f'{target_name}_hit'] = True
                return True

        # Check stop loss
        if current_pnl_pct <= STOP_LOSS['max_loss_percent']:
            print(f'\n[STOP LOSS] {token["symbol"]} @ ${mc_usd:,.0f}')
            print(f'  PnL: {current_pnl_pct:.1f}%')
            return True

        # Check buy ratio stop
        age = time.time() - token['created_at']
        if age >= 30:
            metrics = self.calculate_metrics(token, 30)
            if metrics and metrics['buy_ratio'] * 100 < STOP_LOSS['buy_ratio_min']:
                print(f'\n[STOP LOSS - BUY RATIO] {token["symbol"]} @ ${mc_usd:,.0f}')
                print(f'  Buy Ratio: {metrics["buy_ratio"] * 100:.1f}% < {STOP_LOSS["buy_ratio_min"]}%')
                return True

        # Check no volume stop
        time_since_last_trade = time.time() - token.get('last_trade_time', time.time())
        if time_since_last_trade >= STOP_LOSS['no_volume_seconds']:
            print(f'\n[STOP LOSS - NO VOLUME] {token["symbol"]} @ ${mc_usd:,.0f}')
            print(f'  Pas de volume depuis {time_since_last_trade:.0f}s')
            return True

        return False

    def execute_buy(self, mint, symbol, mc_usd):
        """Exécuter un achat (Paper ou Live)"""
        # Check risk management
        if len(self.positions) >= RISK_MANAGEMENT['max_concurrent_positions']:
            print(f'  [SKIP] Maximum de positions simultanées atteint ({RISK_MANAGEMENT["max_concurrent_positions"]})')
            return False

        if self.wallet_balance < RISK_MANAGEMENT['min_wallet_balance']:
            print(f'  [SKIP] Balance trop basse (${self.wallet_balance:.2f})')
            return False

        position_size = min(RISK_MANAGEMENT['max_position_size_usd'], self.wallet_balance * 0.33)

        if TRADING_MODE == 'PAPER':
            # Paper trading
            self.positions[mint] = {
                'symbol': symbol,
                'entry_price': mc_usd,
                'entry_time': time.time(),
                'position_size': position_size,
                'amount_held': position_size,
                'target_1_hit': False,
                'target_2_hit': False,
                'target_3_hit': False
            }

            self.wallet_balance -= position_size

            print(f'\n[BUY EXECUTED - PAPER] {symbol}')
            print(f'  Entry: ${mc_usd:,.0f}')
            print(f'  Size: ${position_size:.2f}')
            print(f'  Balance restante: ${self.wallet_balance:.2f}')

            self.trade_history.append({
                'type': 'BUY',
                'symbol': symbol,
                'mint': mint,
                'price': mc_usd,
                'size': position_size,
                'time': datetime.now().isoformat()
            })

            return True

        elif TRADING_MODE == 'LIVE':
            # TODO: Implémenter le trading réel avec Solana
            print(f'  [INFO] Trading LIVE non implémenté - utiliser PAPER mode')
            return False

    def execute_sell(self, mint, mc_usd, sell_percentage=100):
        """Exécuter une vente (Paper ou Live)"""
        if mint not in self.positions:
            return False

        position = self.positions[mint]
        amount_to_sell = position['amount_held'] * (sell_percentage / 100)

        if TRADING_MODE == 'PAPER':
            # Calculer le profit
            entry_price = position['entry_price']
            current_value = (mc_usd / entry_price) * amount_to_sell
            profit = current_value - amount_to_sell
            profit_pct = ((mc_usd - entry_price) / entry_price) * 100

            self.wallet_balance += current_value
            position['amount_held'] -= amount_to_sell

            print(f'\n[SELL EXECUTED - PAPER] {position["symbol"]}')
            print(f'  Exit: ${mc_usd:,.0f}')
            print(f'  Entry: ${entry_price:,.0f}')
            print(f'  Profit: ${profit:.2f} ({profit_pct:+.1f}%)')
            print(f'  Amount vendu: {sell_percentage}%')
            print(f'  Balance: ${self.wallet_balance:.2f}')

            self.trade_history.append({
                'type': 'SELL',
                'symbol': position['symbol'],
                'mint': mint,
                'price': mc_usd,
                'size': amount_to_sell,
                'profit': profit,
                'profit_pct': profit_pct,
                'time': datetime.now().isoformat()
            })

            # Supprimer la position si tout vendu
            if position['amount_held'] <= 0.01:
                del self.positions[mint]

            return True

        elif TRADING_MODE == 'LIVE':
            # TODO: Implémenter le trading réel
            print(f'  [INFO] Trading LIVE non implémenté - utiliser PAPER mode')
            return False

    async def process_trade(self, trade_data):
        """Traiter un trade du WebSocket"""
        mint = trade_data.get('mint')
        symbol = trade_data.get('symbol', '???')
        mc_usd = trade_data.get('marketCapSol', 0) * 220  # Approximation SOL = $220

        # DEBUG: afficher les premiers trades
        if mint not in self.active_tokens:
            print(f'  [TRADE DEBUG] Premier trade pour {symbol} - Type: {trade_data.get("txType")}')

        # Créer ou mettre à jour le token
        if mint not in self.active_tokens:
            self.active_tokens[mint] = {
                'symbol': symbol,
                'mint': mint,
                'created_at': time.time(),
                'trades': [],
                'last_trade_time': time.time()
            }

        token = self.active_tokens[mint]
        token['last_trade_time'] = time.time()
        token['trades'].append({
            'time': time.time(),
            'is_buy': trade_data.get('txType') == 'buy',
            'sol_amount': trade_data.get('solAmount', 0),
            'sol_price_usd': 220,
            'wallet': trade_data.get('user', '')
        })

        # Check exit signal pour les positions existantes
        if mint in self.positions:
            if self.check_exit_signal(mint, mc_usd):
                self.execute_sell(mint, mc_usd)

        # Check entry signal pour les nouveaux tokens
        elif mint not in self.positions:
            if self.check_entry_signal(token, mc_usd):
                self.execute_buy(mint, symbol, mc_usd)

    async def connect_and_run(self):
        """Se connecter au WebSocket et trader"""
        async with websockets.connect(WEBSOCKET_URL) as ws:
            # Subscribe aux nouveaux tokens
            await ws.send(json.dumps({"method": "subscribeNewToken"}))
            print('[CONNECTED] WebSocket actif - En attente de nouveaux tokens...\n')

            async for message in ws:
                try:
                    data = json.loads(message)

                    # Nouveau token créé
                    if data.get('txType') == 'create':
                        mint = data.get('mint')
                        symbol = data.get('name', '???')
                        print(f'[NEW TOKEN] {symbol} ({mint[:8]}...)')

                        # Subscribe aux trades de ce token
                        await ws.send(json.dumps({
                            "method": "subscribeTokenTrade",
                            "keys": [mint]
                        }))

                    # Trade (buy ou sell)
                    elif data.get('txType') in ['buy', 'sell']:
                        await self.process_trade(data)

                except Exception as e:
                    print(f'[ERROR] {e}')
                    continue

async def main():
    trader = AutoTrader()
    await trader.connect_and_run()

if __name__ == "__main__":
    asyncio.run(main())

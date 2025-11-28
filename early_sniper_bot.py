"""
EARLY SNIPER BOT - ACHETER AVANT LES BALEINES
Surveille les nouveaux tokens pump.fun et achète AVANT les baleines
Utilise ML + critères de sécurité pour sélectionner les meilleurs tokens
"""
import json
import asyncio
import websockets
import httpx
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from config import HELIUS_API_KEY

class EarlySniperBot:
    def __init__(self):
        self.config = {}
        self.whale_wallets = set()
        self.positions = {}
        self.trade_history = []
        self.processed_tokens = {}  # Tokens déjà analysés
        self.whale_buys = {}  # Track whale purchases
        self.client = httpx.AsyncClient(timeout=30.0)
        self.ml_model = None
        self.ml_scaler = None

    def load_config(self):
        """Charge la configuration"""
        config_file = Path(__file__).parent / "auto_trading_config.json"

        with open(config_file, 'r') as f:
            self.config = json.load(f)

        print("\n" + "=" * 70)
        print("EARLY SNIPER BOT - CONFIGURATION")
        print("=" * 70)
        print(f"Trading Enabled: {self.config['trading_enabled']}")
        print(f"Simulation Mode: {self.config['simulation_mode']}")
        print(f"Max SOL per trade: {self.config['max_sol_per_trade']} SOL")
        print(f"Stop Loss: {self.config['stop_loss_percent']}%")
        print(f"Take Profit: {self.config['take_profit_percent']}%")
        print("=" * 70)

    def load_ml_model(self):
        """Charge le modèle ML si disponible"""
        model_file = Path(__file__).parent / "token_classifier_model.pkl"
        scaler_file = Path(__file__).parent / "token_classifier_scaler.pkl"

        if model_file.exists() and scaler_file.exists():
            try:
                with open(model_file, 'rb') as f:
                    self.ml_model = pickle.load(f)
                with open(scaler_file, 'rb') as f:
                    self.ml_scaler = pickle.load(f)
                print("[+] ML model loaded successfully")
                return True
            except Exception as e:
                print(f"[!] Could not load ML model: {e}")
                return False
        else:
            print("[!] ML model not found - will use basic criteria only")
            return False

    async def load_whale_wallets(self):
        """Charge les wallets des baleines"""
        wallet_file = Path(__file__).parent / "comprehensive_wallets.json"

        with open(wallet_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            wallets = data.get('wallets', [])
            self.whale_wallets = set([w['address'] for w in wallets if not w['address'].startswith('EXEMPLE')])

        print(f"[+] Loaded {len(self.whale_wallets)} whale wallets")

    async def get_token_info(self, mint: str):
        """Récupère les infos d'un token depuis DexScreener"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
            response = await self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])

                # Chercher le pair pump.fun
                for pair in pairs:
                    dex_id = pair.get('dexId', '').lower()
                    if 'pump' in dex_id or 'pumpfun' in dex_id:
                        return pair

                if pairs:
                    return pairs[0]

            return None

        except Exception:
            return None

    def extract_features(self, token_info):
        """Extrait les features pour le ML"""
        if not token_info:
            return None

        try:
            features = {
                'price_usd': float(token_info.get('priceUsd', 0)),
                'price_change_24h': float(token_info.get('priceChange', {}).get('h24', 0)),
                'liquidity_usd': float(token_info.get('liquidity', {}).get('usd', 0)),
                'volume_24h': float(token_info.get('volume', {}).get('h24', 0)),
                'market_cap': float(token_info.get('marketCap', 0)),
                'fdv': float(token_info.get('fdv', 0)),
                'txns_24h_buys': int(token_info.get('txns', {}).get('h24', {}).get('buys', 0)),
                'txns_24h_sells': int(token_info.get('txns', {}).get('h24', {}).get('sells', 0)),
            }

            # Ratios calculés
            if features['volume_24h'] > 0 and features['market_cap'] > 0:
                features['volume_mcap_ratio'] = features['volume_24h'] / features['market_cap']
            else:
                features['volume_mcap_ratio'] = 0

            if features['txns_24h_sells'] > 0:
                features['buy_sell_ratio'] = features['txns_24h_buys'] / features['txns_24h_sells']
            else:
                features['buy_sell_ratio'] = features['txns_24h_buys']

            if features['liquidity_usd'] > 0 and features['market_cap'] > 0:
                features['liquidity_per_mcap'] = features['liquidity_usd'] / features['market_cap']
            else:
                features['liquidity_per_mcap'] = 0

            if features['txns_24h_buys'] > 0 and features['volume_24h'] > 0:
                features['avg_buy_size'] = features['volume_24h'] / features['txns_24h_buys']
            else:
                features['avg_buy_size'] = 0

            if features['txns_24h_sells'] > 0 and features['volume_24h'] > 0:
                features['avg_sell_size'] = features['volume_24h'] / features['txns_24h_sells']
            else:
                features['avg_sell_size'] = 0

            return features

        except Exception as e:
            return None

    def predict_with_ml(self, token_info):
        """Prédit si le token est un GEM avec le ML"""
        if not self.ml_model or not self.ml_scaler:
            return None, 0.5

        features = self.extract_features(token_info)
        if not features:
            return None, 0.5

        try:
            # Ordre des features (important!)
            feature_names = [
                'price_usd', 'price_change_24h', 'liquidity_usd', 'volume_24h',
                'volume_mcap_ratio', 'market_cap', 'fdv', 'txns_24h_buys',
                'txns_24h_sells', 'buy_sell_ratio', 'liquidity_per_mcap',
                'avg_buy_size', 'avg_sell_size'
            ]

            feature_vector = [[features[f] for f in feature_names]]
            feature_vector_scaled = self.ml_scaler.transform(feature_vector)

            prediction = self.ml_model.predict(feature_vector_scaled)[0]
            probability = self.ml_model.predict_proba(feature_vector_scaled)[0]

            gem_probability = probability[1] if len(probability) > 1 else 0.5

            return prediction, gem_probability

        except Exception as e:
            print(f"[!] ML prediction error: {e}")
            return None, 0.5

    def check_basic_safety(self, token_info):
        """Vérifie les critères de sécurité basiques"""
        if not token_info:
            return False, "No token info"

        checks = []

        # Liquidity check
        liquidity = float(token_info.get('liquidity', {}).get('usd', 0))
        if liquidity < 500:
            return False, f"Liquidity too low: ${liquidity:.2f}"
        checks.append(f"Liquidity: ${liquidity:.2f}")

        # Market cap check
        mcap = float(token_info.get('marketCap', 0))
        if mcap < 1000:
            return False, f"Market cap too low: ${mcap:.2f}"
        checks.append(f"MCap: ${mcap:.2f}")

        # Volume check
        volume = float(token_info.get('volume', {}).get('h24', 0))
        if volume < 100:
            return False, f"Volume too low: ${volume:.2f}"
        checks.append(f"Volume: ${volume:.2f}")

        # Price change check (avoid dumping tokens)
        price_change = float(token_info.get('priceChange', {}).get('h24', 0))
        if price_change < -80:
            return False, f"Dumping: {price_change:.1f}%"
        checks.append(f"Price change: {price_change:+.1f}%")

        # Buy/sell ratio check
        buys = int(token_info.get('txns', {}).get('h24', {}).get('buys', 0))
        sells = int(token_info.get('txns', {}).get('h24', {}).get('sells', 0))

        if buys > 0 and sells > 0:
            ratio = buys / sells
            if ratio < 0.5:
                return False, f"Too many sells (ratio: {ratio:.2f})"
            checks.append(f"Buy/Sell: {ratio:.2f}")

        return True, " | ".join(checks)

    def is_pump_fun(self, token_info):
        """Vérifie si le token est sur pump.fun"""
        if not token_info:
            return False

        dex_id = token_info.get('dexId', '').lower()
        return 'pump' in dex_id or 'pumpfun' in dex_id

    async def analyze_new_token(self, mint: str, creator: str = None):
        """Analyse un nouveau token et décide d'acheter ou non"""

        # Éviter de traiter 2 fois
        if mint in self.processed_tokens:
            return

        self.processed_tokens[mint] = datetime.now().isoformat()

        print(f"\n[NEW TOKEN] {mint}")
        if creator:
            print(f"  Creator: {creator[:16]}...")

        # Récupérer les infos
        token_info = await self.get_token_info(mint)

        if not token_info:
            print(f"  [SKIP] No token info found")
            return

        token_name = token_info.get('baseToken', {}).get('name', 'Unknown')
        token_symbol = token_info.get('baseToken', {}).get('symbol', 'Unknown')

        print(f"  Name: {token_name} (${token_symbol})")

        # Vérifier si pump.fun
        if not self.is_pump_fun(token_info):
            print(f"  [SKIP] Not on Pump.fun")
            return

        print(f"  [OK] On Pump.fun")

        # Vérifier critères basiques
        safe, safety_info = self.check_basic_safety(token_info)

        if not safe:
            print(f"  [SKIP] Safety check failed: {safety_info}")
            return

        print(f"  [OK] Safety checks passed")
        print(f"      {safety_info}")

        # Prédiction ML (si disponible)
        ml_score = 0.5

        if self.ml_model:
            prediction, ml_score = self.predict_with_ml(token_info)
            print(f"  [ML] Score: {ml_score*100:.1f}% (Gem probability)")

            # Threshold ML
            if ml_score < 0.6:
                print(f"  [SKIP] ML score too low ({ml_score*100:.1f}%)")
                return
        else:
            print(f"  [!] ML not available - using basic criteria only")

        # Vérifier limite de positions
        if len(self.positions) >= self.config.get('max_concurrent_positions', 3):
            print(f"  [SKIP] Max positions reached ({len(self.positions)})")
            return

        # ACHETER!
        print(f"\n  [BUY SIGNAL] All criteria met!")
        await self.simulate_buy(mint, token_info, ml_score)

    async def simulate_buy(self, mint: str, token_info, ml_score: float):
        """Simule un achat"""
        price = float(token_info.get('priceUsd', 0))
        liquidity = float(token_info.get('liquidity', {}).get('usd', 0))
        mcap = float(token_info.get('marketCap', 0))

        print("\n" + "=" * 70)
        print("[EARLY SNIPER] BUY ORDER - BEFORE WHALES")
        print("=" * 70)
        print(f"Token: {token_info.get('baseToken', {}).get('name', 'Unknown')}")
        print(f"Symbol: {token_info.get('baseToken', {}).get('symbol', 'Unknown')}")
        print(f"Mint: {mint}")
        print(f"Price: ${price:.8f}")
        print(f"Liquidity: ${liquidity:,.2f}")
        print(f"Market Cap: ${mcap:,.2f}")
        print(f"ML Score: {ml_score*100:.1f}%")
        print(f"Amount: {self.config['max_sol_per_trade']} SOL")
        print(f"Mode: SIMULATION")
        print("=" * 70)

        # Sauvegarder position
        self.positions[mint] = {
            'buy_price': price,
            'amount_sol': self.config['max_sol_per_trade'],
            'buy_time': datetime.now().isoformat(),
            'token_name': token_info.get('baseToken', {}).get('name', 'Unknown'),
            'ml_score': ml_score,
            'simulated': True
        }

        # Logger
        self.trade_history.append({
            'action': 'BUY',
            'token': mint,
            'price': price,
            'amount_sol': self.config['max_sol_per_trade'],
            'ml_score': ml_score,
            'time': datetime.now().isoformat(),
            'simulated': True,
            'strategy': 'early_sniper'
        })

        self.save_trades()

    async def check_whale_activity(self, mint: str, trader: str, tx_type: str):
        """Vérifie si une baleine achète un token qu'on détient"""

        # Seulement si c'est une baleine
        if trader not in self.whale_wallets:
            return

        # Seulement si on détient ce token
        if mint not in self.positions:
            return

        # Seulement si c'est un achat
        if tx_type != 'buy':
            return

        position = self.positions[mint]

        print(f"\n[!] WHALE BUYING OUR TOKEN!")
        print(f"    Token: {mint[:16]}...")
        print(f"    Whale: {trader[:16]}...")
        print(f"    We bought at: ${position['buy_price']:.8f}")

        # Récupérer le prix actuel
        token_info = await self.get_token_info(mint)

        if token_info:
            current_price = float(token_info.get('priceUsd', 0))
            profit = ((current_price - position['buy_price']) / position['buy_price']) * 100

            print(f"    Current price: ${current_price:.8f}")
            print(f"    Profit: {profit:+.2f}%")

            # Vendre si profit > 30% ou configurable
            whale_sell_threshold = 30  # Vendre dès qu'une baleine achète et on a +30%

            if profit > whale_sell_threshold:
                await self.simulate_sell(mint, f"Whale buy detected ({profit:+.1f}%)", current_price)
            else:
                print(f"    [WAIT] Profit too low, waiting for more...")
                # Track cette baleine pour ce token
                if mint not in self.whale_buys:
                    self.whale_buys[mint] = []
                self.whale_buys[mint].append({
                    'whale': trader,
                    'time': datetime.now().isoformat()
                })

    async def check_positions(self):
        """Vérifie stop-loss/take-profit"""
        for mint, position in list(self.positions.items()):
            token_info = await self.get_token_info(mint)

            if not token_info:
                continue

            current_price = float(token_info.get('priceUsd', 0))
            buy_price = position['buy_price']

            if buy_price == 0:
                continue

            profit_percent = ((current_price - buy_price) / buy_price) * 100

            # Take profit
            if profit_percent >= self.config['take_profit_percent']:
                await self.simulate_sell(mint, f"Take Profit ({profit_percent:+.1f}%)", current_price)

            # Stop loss
            elif profit_percent <= self.config['stop_loss_percent']:
                await self.simulate_sell(mint, f"Stop Loss ({profit_percent:+.1f}%)", current_price)

    async def simulate_sell(self, mint: str, reason: str, sell_price: float):
        """Simule une vente"""
        if mint not in self.positions:
            return

        position = self.positions[mint]
        buy_price = position['buy_price']
        profit_percent = ((sell_price - buy_price) / buy_price) * 100

        print("\n" + "=" * 70)
        print(f"[SIMULATION] SELL ORDER - {reason}")
        print("=" * 70)
        print(f"Token: {position['token_name']}")
        print(f"Buy Price: ${buy_price:.8f}")
        print(f"Sell Price: ${sell_price:.8f}")
        print(f"Profit: {profit_percent:+.2f}%")
        print(f"ML Score: {position.get('ml_score', 0)*100:.1f}%")

        # Whale activity
        if mint in self.whale_buys:
            print(f"Whales that bought: {len(self.whale_buys[mint])}")

        print("=" * 70)

        # Logger
        self.trade_history.append({
            'action': 'SELL',
            'token': mint,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'profit_percent': profit_percent,
            'reason': reason,
            'time': datetime.now().isoformat(),
            'simulated': True
        })

        # Supprimer position
        del self.positions[mint]
        if mint in self.whale_buys:
            del self.whale_buys[mint]

        self.save_trades()

    async def process_websocket_event(self, data):
        """Process les events du websocket PumpPortal"""
        try:
            event_type = data.get('type') or data.get('txType')

            # Nouveau token créé
            if event_type in ['newToken', 'create']:
                mint = data.get('mint')
                creator = data.get('traderPublicKey') or data.get('creator')

                if mint:
                    await self.analyze_new_token(mint, creator)

            # Trade sur un token existant
            elif event_type in ['trade', 'buy', 'sell']:
                mint = data.get('mint')
                trader = data.get('traderPublicKey')
                tx_type = data.get('txType', 'buy')

                if mint and trader:
                    await self.check_whale_activity(mint, trader, tx_type)

        except Exception as e:
            print(f"[!] Error processing event: {e}")

    async def connect_pumpportal(self):
        """Se connecte au websocket PumpPortal"""
        uri = "wss://pumpportal.fun/api/data"

        print("\n[*] Connecting to PumpPortal...")

        try:
            async with websockets.connect(uri) as websocket:
                print("[+] Connected!")

                # S'abonner aux nouveaux tokens
                subscribe_message = {
                    "method": "subscribeNewToken"
                }
                await websocket.send(json.dumps(subscribe_message))
                print("[+] Subscribed to new tokens")

                # Aussi s'abonner aux trades
                subscribe_trades = {
                    "method": "subscribeTrades"
                }
                await websocket.send(json.dumps(subscribe_trades))
                print("[+] Subscribed to trades")

                message_count = 0
                last_position_check = datetime.now()

                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)

                        message_count += 1

                        # Status update tous les 100 messages
                        if message_count % 100 == 0:
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Messages: {message_count}")
                            print(f"    Active positions: {len(self.positions)}")
                            print(f"    Tokens analyzed: {len(self.processed_tokens)}")

                        # Process l'event
                        await self.process_websocket_event(data)

                        # Check positions toutes les 30s
                        if (datetime.now() - last_position_check).seconds >= 30:
                            if self.positions:
                                await self.check_positions()
                            last_position_check = datetime.now()

                    except websockets.exceptions.ConnectionClosed:
                        print("[!] Connection closed")
                        break
                    except Exception as e:
                        print(f"[!] Error: {e}")
                        await asyncio.sleep(1)

        except Exception as e:
            print(f"[!] Connection error: {e}")

    def save_trades(self):
        """Sauvegarde l'historique"""
        trades_file = Path(__file__).parent / "early_sniper_history.json"

        with open(trades_file, 'w', encoding='utf-8') as f:
            json.dump({
                'trades': self.trade_history,
                'total_trades': len(self.trade_history),
                'active_positions': len(self.positions),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)

    async def run(self):
        """Lance le bot"""
        self.load_config()
        self.load_ml_model()
        await self.load_whale_wallets()

        if not self.config['trading_enabled']:
            print("\n[!] Trading is DISABLED")
            return

        print("\n" + "=" * 70)
        print("EARLY SNIPER BOT - STARTED")
        print("=" * 70)
        print(f"Mode: {'SIMULATION' if self.config['simulation_mode'] else 'REAL'}")
        print(f"ML Model: {'LOADED' if self.ml_model else 'NOT AVAILABLE'}")
        print(f"Whale Wallets: {len(self.whale_wallets)}")
        print(f"Strategy: Buy NEW tokens BEFORE whales")
        print("=" * 70)

        # Boucle avec reconnexion
        while True:
            try:
                await self.connect_pumpportal()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[!] Error: {e}")
                await asyncio.sleep(5)

    async def close(self):
        await self.client.aclose()


async def main():
    bot = EarlySniperBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\n[!] Stopping...")
    finally:
        await bot.close()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("EARLY SNIPER BOT")
    print("Achète les nouveaux tokens AVANT les baleines")
    print("Vend quand les baleines achètent")
    print("=" * 70)

    asyncio.run(main())

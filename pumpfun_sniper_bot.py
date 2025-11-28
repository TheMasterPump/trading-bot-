"""
PUMP.FUN SNIPER BOT
Trade automatiquement les tokens pump.fun AVANT migration
Suit les achats des baleines en temps réel via PumpPortal API
"""
import json
import asyncio
import websockets
from datetime import datetime
from pathlib import Path
from config import HELIUS_API_KEY
import httpx

class PumpFunSniperBot:
    def __init__(self):
        self.config = {}
        self.whale_wallets = set()
        self.positions = {}
        self.trade_history = []
        self.seen_tokens = {}  # Track tokens we've already processed
        self.client = httpx.AsyncClient(timeout=30.0)

    def load_config(self):
        """Charge la configuration"""
        config_file = Path(__file__).parent / "auto_trading_config.json"

        with open(config_file, 'r') as f:
            self.config = json.load(f)

        print("\n" + "=" * 70)
        print("PUMP.FUN SNIPER BOT - CONFIGURATION")
        print("=" * 70)
        print(f"Trading Enabled: {self.config['trading_enabled']}")
        print(f"Simulation Mode: {self.config['simulation_mode']}")
        print(f"Max SOL per trade: {self.config['max_sol_per_trade']} SOL")
        print(f"Stop Loss: {self.config['stop_loss_percent']}%")
        print(f"Take Profit: {self.config['take_profit_percent']}%")
        print("=" * 70)

    async def load_whale_wallets(self):
        """Charge les wallets des baleines"""
        wallet_file = Path(__file__).parent / "comprehensive_wallets.json"

        with open(wallet_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            wallets = data.get('wallets', [])
            self.whale_wallets = set([w['address'] for w in wallets if not w['address'].startswith('EXEMPLE')])

        print(f"[+] Loaded {len(self.whale_wallets)} whale wallets to track")

    async def get_token_info_dexscreener(self, token_address: str):
        """Récupère les infos du token depuis DexScreener"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            response = await self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])

                # Chercher spécifiquement le pair pump.fun
                for pair in pairs:
                    dex_id = pair.get('dexId', '').lower()
                    if 'pump' in dex_id or 'pumpfun' in dex_id:
                        return pair

                # Si pas trouvé pump.fun, retourner le premier
                if pairs:
                    return pairs[0]

            return None

        except Exception as e:
            return None

    def is_pumpfun_token(self, pair_info):
        """Vérifie si le token est sur pump.fun (pas encore migré)"""
        if not pair_info:
            return False

        dex_id = pair_info.get('dexId', '').lower()

        # Vérifier que c'est pump.fun
        if 'pump' in dex_id or 'pumpfun' in dex_id:
            return True

        return False

    def check_bonding_curve(self, pair_info):
        """Vérifie le % de la bonding curve (optionnel pour DexScreener)"""
        # DexScreener ne donne pas toujours cette info
        # On peut l'estimer via la liquidity
        liquidity = float(pair_info.get('liquidity', {}).get('usd', 0))

        # Bonding curve pump.fun = ~85 SOL = ~$17,000 (si SOL=$200)
        # Si liquidity < $17k, pas encore migré
        if liquidity > 0 and liquidity < 20000:
            percent = (liquidity / 17000) * 100
            return True, f"{percent:.1f}%"
        elif liquidity >= 20000:
            return False, "Already migrated (high liquidity)"
        else:
            return False, "Unknown liquidity"

    async def simulate_buy(self, token_address: str, mint: str, whale_wallet: str, token_info=None):
        """Simule un achat de token pump.fun"""
        print("\n" + "=" * 70)
        print("[PUMP.FUN SNIPER] BUY SIGNAL")
        print("=" * 70)
        print(f"Token Mint: {mint}")
        print(f"Whale Wallet: {whale_wallet[:16]}...")

        if token_info:
            print(f"Token Name: {token_info.get('baseToken', {}).get('name', 'Unknown')}")
            print(f"Symbol: {token_info.get('baseToken', {}).get('symbol', 'Unknown')}")
            print(f"Price: ${float(token_info.get('priceUsd', 0)):.8f}")
            print(f"Liquidity: ${float(token_info.get('liquidity', {}).get('usd', 0)):,.2f}")
            print(f"Market Cap: ${float(token_info.get('marketCap', 0)):,.2f}")

            is_pumpfun = self.is_pumpfun_token(token_info)
            bonding_ok, bonding_info = self.check_bonding_curve(token_info)

            print(f"On Pump.fun: {'YES' if is_pumpfun else 'NO'}")
            print(f"Bonding Curve: {bonding_info}")

        print(f"Amount: {self.config['max_sol_per_trade']} SOL")
        print(f"Mode: SIMULATION")
        print("=" * 70)

        # Sauvegarder la position
        self.positions[mint] = {
            'buy_price': float(token_info.get('priceUsd', 0)) if token_info else 0,
            'amount_sol': self.config['max_sol_per_trade'],
            'buy_time': datetime.now().isoformat(),
            'whale_wallet': whale_wallet,
            'token_address': mint,
            'simulated': True
        }

        # Logger
        self.trade_history.append({
            'action': 'BUY',
            'token': mint,
            'price': float(token_info.get('priceUsd', 0)) if token_info else 0,
            'amount_sol': self.config['max_sol_per_trade'],
            'whale_wallet': whale_wallet,
            'time': datetime.now().isoformat(),
            'simulated': True,
            'platform': 'pump.fun'
        })

        self.save_trades()

    async def check_positions(self):
        """Vérifie les positions pour stop-loss/take-profit"""
        for mint, position in list(self.positions.items()):
            token_info = await self.get_token_info_dexscreener(mint)

            if not token_info:
                continue

            current_price = float(token_info.get('priceUsd', 0))
            buy_price = position['buy_price']

            if buy_price == 0:
                continue

            profit_percent = ((current_price - buy_price) / buy_price) * 100

            # Check take-profit
            if profit_percent >= self.config['take_profit_percent']:
                await self.simulate_sell(mint, f"Take Profit ({profit_percent:+.1f}%)", current_price)

            # Check stop-loss
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
        print(f"Token: {mint[:16]}...")
        print(f"Buy Price: ${buy_price:.8f}")
        print(f"Sell Price: ${sell_price:.8f}")
        print(f"Profit: {profit_percent:+.2f}%")
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

        # Supprimer la position
        del self.positions[mint]

        self.save_trades()

    async def process_trade_event(self, data):
        """Process un event de trade du websocket"""
        try:
            # Structure typique d'un event PumpPortal
            mint = data.get('mint')
            trader = data.get('traderPublicKey')
            tx_type = data.get('txType')  # 'buy' ou 'sell'
            sol_amount = data.get('solAmount', 0)
            token_amount = data.get('tokenAmount', 0)

            # Vérifier que c'est un achat d'une baleine
            if tx_type != 'buy':
                return

            if trader not in self.whale_wallets:
                return

            # Éviter de trader le même token plusieurs fois
            if mint in self.seen_tokens:
                return

            self.seen_tokens[mint] = datetime.now().isoformat()

            print(f"\n[!] WHALE BUY DETECTED on Pump.fun!")
            print(f"    Whale: {trader[:16]}...")
            print(f"    Token: {mint}")
            print(f"    Amount: {sol_amount} SOL")

            # Récupérer les infos du token
            token_info = await self.get_token_info_dexscreener(mint)

            # Vérifier si c'est encore sur pump.fun
            if token_info:
                is_pumpfun = self.is_pumpfun_token(token_info)
                bonding_ok, bonding_info = self.check_bonding_curve(token_info)

                if is_pumpfun and bonding_ok:
                    print(f"    [OK] Token on Pump.fun, bonding curve: {bonding_info}")

                    # Vérifier limite de positions
                    if len(self.positions) >= self.config.get('max_concurrent_positions', 3):
                        print(f"    [SKIP] Max positions reached ({len(self.positions)})")
                        return

                    # ACHETER!
                    await self.simulate_buy(mint, mint, trader, token_info)
                else:
                    if not is_pumpfun:
                        print(f"    [SKIP] Token already migrated or not on Pump.fun")
                    else:
                        print(f"    [SKIP] {bonding_info}")
            else:
                print(f"    [ERROR] Could not fetch token info")

        except Exception as e:
            print(f"[!] Error processing trade: {e}")

    async def connect_pumpportal(self):
        """Se connecte au websocket PumpPortal"""
        uri = "wss://pumpportal.fun/api/data"

        print("\n[*] Connecting to PumpPortal websocket...")

        try:
            async with websockets.connect(uri) as websocket:
                print("[+] Connected to PumpPortal!")

                # S'abonner aux trades
                subscribe_message = {
                    "method": "subscribeNewToken"  # ou "subscribeTrades" selon l'API
                }

                await websocket.send(json.dumps(subscribe_message))
                print("[+] Subscribed to trades")

                # Boucle de réception
                cycle = 0
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)

                        cycle += 1
                        if cycle % 100 == 0:
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Messages received: {cycle}")
                            print(f"    Active positions: {len(self.positions)}")

                        # Process le trade
                        await self.process_trade_event(data)

                        # Check positions tous les 50 messages
                        if cycle % 50 == 0 and self.positions:
                            await self.check_positions()

                    except websockets.exceptions.ConnectionClosed:
                        print("[!] Connection closed, reconnecting...")
                        break
                    except Exception as e:
                        print(f"[!] Error: {e}")
                        await asyncio.sleep(1)

        except Exception as e:
            print(f"[!] Connection error: {e}")
            print("[!] Retrying in 5s...")
            await asyncio.sleep(5)

    def save_trades(self):
        """Sauvegarde l'historique"""
        trades_file = Path(__file__).parent / "pumpfun_sniper_history.json"

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
        await self.load_whale_wallets()

        if not self.config['trading_enabled']:
            print("\n[!] Trading is DISABLED in config")
            print("[!] Set 'trading_enabled': true to enable")
            return

        print("\n" + "=" * 70)
        print("PUMP.FUN SNIPER BOT - STARTED")
        print("=" * 70)
        print(f"Mode: {'SIMULATION' if self.config['simulation_mode'] else 'REAL TRADING'}")
        print(f"Tracking {len(self.whale_wallets)} whale wallets")
        print(f"Strategy: Buy tokens on Pump.fun BEFORE migration")
        print("=" * 70)

        # Boucle de connexion avec reconnexion auto
        while True:
            try:
                await self.connect_pumpportal()
            except KeyboardInterrupt:
                print("\n[!] Stopping bot...")
                break
            except Exception as e:
                print(f"[!] Error: {e}")
                print("[!] Reconnecting in 5s...")
                await asyncio.sleep(5)

    async def close(self):
        """Ferme le client"""
        await self.client.aclose()


async def main():
    bot = PumpFunSniperBot()

    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
    finally:
        await bot.close()
        print("[+] Bot stopped")


if __name__ == "__main__":
    print("\n[PUMP.FUN SNIPER BOT]")
    print("Sniping pump.fun tokens BEFORE migration")
    print("Following whale wallets in real-time\n")

    asyncio.run(main())

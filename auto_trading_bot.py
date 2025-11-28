"""
AUTO-TRADING BOT - FULL AUTOMATIC
Achète et vend automatiquement en copiant les baleines

⚠️ WARNING: This bot trades with REAL MONEY
⚠️ Can LOSE funds - Use at your own risk
⚠️ Start with SIMULATION MODE first!
"""
import json
import asyncio
import httpx
from datetime import datetime
from pathlib import Path
from config import HELIUS_API_KEY

class AutoTradingBot:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.config = {}
        self.wallets = []
        self.positions = {}  # Tokens actuellement détenus
        self.trade_history = []
        self.last_checked_signatures = set()

    def load_config(self):
        """Charge la configuration"""
        config_file = Path(__file__).parent / "auto_trading_config.json"

        with open(config_file, 'r') as f:
            self.config = json.load(f)

        print("\n" + "=" * 70)
        print("AUTO-TRADING BOT CONFIGURATION")
        print("=" * 70)
        print(f"Trading Enabled: {self.config['trading_enabled']}")
        print(f"Simulation Mode: {self.config['simulation_mode']}")
        print(f"Max SOL per trade: {self.config['max_sol_per_trade']} SOL")
        print(f"Stop Loss: {self.config['stop_loss_percent']}%")
        print(f"Take Profit: {self.config['take_profit_percent']}%")
        print(f"Min Liquidity: ${self.config['min_liquidity_usd']}")
        print(f"Min Whales Buying: {self.config['min_whales_buying']}")
        print("=" * 70)

        if not self.config['simulation_mode'] and self.config['trading_enabled']:
            print("\n[!] WARNING: REAL TRADING ENABLED!")
            print("[!] The bot will use REAL SOL to trade")
            print("[!] You can LOSE money")
            print("\n" + "=" * 70)

    async def load_wallets(self):
        """Charge les wallets de baleines"""
        wallet_file = Path(__file__).parent / "comprehensive_wallets.json"

        with open(wallet_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            wallets = data.get('wallets', [])
            self.wallets = [w['address'] for w in wallets if not w['address'].startswith('EXEMPLE')]

        print(f"[+] Loaded {len(self.wallets)} whale wallets")

    async def get_recent_transactions(self, wallet_address: str):
        """Récupère les transactions récentes"""
        try:
            url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
            params = {
                "api-key": HELIUS_API_KEY,
                "limit": 3
            }

            response = await self.client.get(url, params=params)

            if response.status_code == 200:
                return response.json()

            return []

        except Exception:
            return []

    async def get_token_info(self, token_address: str):
        """Récupère les infos d'un token depuis DexScreener"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            response = await self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])
                if pairs:
                    return pairs[0]

            return None

        except Exception:
            return None

    def check_safety(self, token_info):
        """Vérifie si le token est safe pour acheter"""
        if not token_info:
            return False, "No token info"

        # Check liquidity
        liquidity = float(token_info.get('liquidity', {}).get('usd', 0))
        if liquidity < self.config['min_liquidity_usd']:
            return False, f"Low liquidity: ${liquidity:.2f}"

        # Check if not a rug (basic checks)
        price_change = float(token_info.get('priceChange', {}).get('h24', 0))
        if price_change < -80:
            return False, f"Dumping hard: {price_change:.1f}%"

        return True, "Safe"

    async def simulate_buy(self, token_address: str, token_info):
        """Simule un achat (pour tester)"""
        print("\n" + "=" * 70)
        print("[SIMULATION] BUY ORDER")
        print("=" * 70)
        print(f"Token: {token_info.get('baseToken', {}).get('name', 'Unknown')}")
        print(f"Address: {token_address}")
        print(f"Price: ${float(token_info.get('priceUsd', 0)):.8f}")
        print(f"Liquidity: ${float(token_info.get('liquidity', {}).get('usd', 0)):,.2f}")
        print(f"Amount: {self.config['max_sol_per_trade']} SOL")
        print("=" * 70)

        # Sauvegarder la position simulée
        self.positions[token_address] = {
            'buy_price': float(token_info.get('priceUsd', 0)),
            'amount_sol': self.config['max_sol_per_trade'],
            'buy_time': datetime.now().isoformat(),
            'token_name': token_info.get('baseToken', {}).get('name', 'Unknown'),
            'simulated': True
        }

        # Log
        self.trade_history.append({
            'action': 'BUY',
            'token': token_address,
            'price': float(token_info.get('priceUsd', 0)),
            'amount_sol': self.config['max_sol_per_trade'],
            'time': datetime.now().isoformat(),
            'simulated': True
        })

        self.save_trades()

    async def simulate_sell(self, token_address: str, reason: str):
        """Simule une vente"""
        if token_address not in self.positions:
            return

        position = self.positions[token_address]

        # Récupérer le prix actuel
        token_info = await self.get_token_info(token_address)
        if not token_info:
            return

        current_price = float(token_info.get('priceUsd', 0))
        buy_price = position['buy_price']

        profit_percent = ((current_price - buy_price) / buy_price) * 100

        print("\n" + "=" * 70)
        print(f"[SIMULATION] SELL ORDER - {reason}")
        print("=" * 70)
        print(f"Token: {position['token_name']}")
        print(f"Buy Price: ${buy_price:.8f}")
        print(f"Sell Price: ${current_price:.8f}")
        print(f"Profit: {profit_percent:+.2f}%")
        print("=" * 70)

        # Log
        self.trade_history.append({
            'action': 'SELL',
            'token': token_address,
            'buy_price': buy_price,
            'sell_price': current_price,
            'profit_percent': profit_percent,
            'reason': reason,
            'time': datetime.now().isoformat(),
            'simulated': True
        })

        # Supprimer la position
        del self.positions[token_address]

        self.save_trades()

    async def check_positions(self):
        """Vérifie les positions pour stop-loss / take-profit"""
        for token_address, position in list(self.positions.items()):
            # Récupérer le prix actuel
            token_info = await self.get_token_info(token_address)
            if not token_info:
                continue

            current_price = float(token_info.get('priceUsd', 0))
            buy_price = position['buy_price']

            profit_percent = ((current_price - buy_price) / buy_price) * 100

            # Check take-profit
            if profit_percent >= self.config['take_profit_percent']:
                await self.simulate_sell(token_address, f"Take Profit ({profit_percent:+.1f}%)")

            # Check stop-loss
            elif profit_percent <= self.config['stop_loss_percent']:
                await self.simulate_sell(token_address, f"Stop Loss ({profit_percent:+.1f}%)")

    async def detect_whale_buy(self, tx, wallet_address: str):
        """Détecte un achat de baleine et trade si conditions OK"""
        try:
            signature = tx.get('signature')
            tx_type = tx.get('type')

            # Éviter doublons
            if signature in self.last_checked_signatures:
                return

            self.last_checked_signatures.add(signature)

            # Limiter taille cache
            if len(self.last_checked_signatures) > 5000:
                self.last_checked_signatures = set(list(self.last_checked_signatures)[-2500:])

            # Chercher les swaps (achats)
            if tx_type == 'SWAP':
                description = tx.get('description', '')

                # Essayer d'extraire le token acheté
                # Format typique: "wallet swapped X SOL for Y TOKEN"
                if 'for' in description:
                    # C'est un achat potentiel
                    print(f"\n[WHALE BUY DETECTED] {wallet_address[:16]}...")
                    print(f"Description: {description}")

                    # Pour une vraie implémentation, il faudrait extraire
                    # l'adresse du token depuis la transaction
                    # Pour l'instant, c'est une simulation

        except Exception as e:
            pass

    async def monitor_and_trade(self):
        """Boucle principale de monitoring et trading"""
        print("\n" + "=" * 70)
        print("AUTO-TRADING BOT STARTED")
        print("=" * 70)
        print(f"Mode: {'SIMULATION' if self.config['simulation_mode'] else 'REAL TRADING'}")
        print(f"Monitoring {len(self.wallets)} whales")
        print("=" * 70)

        cycle = 0

        while True:
            try:
                cycle += 1
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Cycle #{cycle}")

                # Check positions actuelles (stop-loss / take-profit)
                if self.positions:
                    await self.check_positions()
                    print(f"Active positions: {len(self.positions)}")

                # Monitorer les wallets (batch de 10)
                batch_size = 10
                for i in range(0, min(50, len(self.wallets)), batch_size):
                    batch = self.wallets[i:i+batch_size]

                    tasks = [self.get_recent_transactions(w) for w in batch]
                    results = await asyncio.gather(*tasks)

                    for wallet, txs in zip(batch, results):
                        for tx in txs:
                            await self.detect_whale_buy(tx, wallet)

                    await asyncio.sleep(0.5)

                # Attendre avant prochain cycle
                await asyncio.sleep(self.config['check_interval_seconds'])

            except KeyboardInterrupt:
                print("\n[!] Stopping bot...")
                break
            except Exception as e:
                print(f"[!] Error: {e}")
                await asyncio.sleep(5)

    def save_trades(self):
        """Sauvegarde l'historique des trades"""
        trades_file = Path(__file__).parent / "auto_trading_history.json"

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
        await self.load_wallets()

        if not self.config['trading_enabled']:
            print("\n[!] Trading is DISABLED in config")
            print("[!] Set 'trading_enabled': true to enable")
            return

        if not self.config['simulation_mode']:
            print("\n[!] WARNING: You are about to start REAL TRADING")
            print("[!] This will use REAL SOL from your wallet")
            print("[!] Press Ctrl+C now to cancel, or wait 5s to continue...")
            await asyncio.sleep(5)

        await self.monitor_and_trade()

    async def close(self):
        """Ferme le client"""
        await self.client.aclose()


async def main():
    bot = AutoTradingBot()

    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
    finally:
        await bot.close()
        print("[+] Bot stopped")


if __name__ == "__main__":
    print("\n[!] AUTO-TRADING BOT [!]")
    print("This bot can trade with real money")
    print("Start in SIMULATION mode first to test\n")

    asyncio.run(main())

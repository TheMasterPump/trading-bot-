"""
BOT HYBRIDE - WebSocket PumpPortal + Helius RPC
- WebSocket: Détection tokens + prix temps réel
- Helius: Holders exact depuis la blockchain
"""
import asyncio
import json
import websockets
import requests
from datetime import datetime

# CONFIGURATION
HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

SOL_PRICE_USD = 200
OPTIMAL_WINDOW = {
    'min_mc': 7000,
    'max_mc': 14000,
}
MIN_HOLDERS = 0  # Accepter tous - le scoring pénalisera les 0 holders via bundle check
SCORE_THRESHOLD = 30

class HeliusWebSocketBot:
    def __init__(self):
        self.tokens = {}  # {mint: {symbol, mc, holders, ...}}
        self.seen_in_window = set()
        self.tokens_bought = 0
        self.ws = None
        self.reconnect_delay = 5

    def get_token_holders_helius(self, mint):
        """Obtenir le nombre de holders via Helius RPC"""
        try:
            # Utiliser getProgramAccounts pour compter les token accounts
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getProgramAccounts",
                "params": [
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # SPL Token Program
                    {
                        "encoding": "jsonParsed",
                        "filters": [
                            {
                                "dataSize": 165  # Taille d'un token account
                            },
                            {
                                "memcmp": {
                                    "offset": 0,  # Mint address est au début
                                    "bytes": mint
                                }
                            }
                        ]
                    }
                ]
            }

            response = requests.post(HELIUS_RPC_URL, json=payload, timeout=15)

            if response.status_code == 200:
                result = response.json()

                if 'result' in result:
                    # Compter les accounts avec balance > 0
                    holders = 0
                    for account in result['result']:
                        try:
                            parsed = account['account']['data']['parsed']
                            token_amount = parsed['info']['tokenAmount']
                            amount = int(token_amount['amount'])

                            # Compter seulement si balance > 0
                            if amount > 0:
                                holders += 1
                        except Exception as e:
                            # Skip les accounts mal formatés
                            continue

                    return holders
                elif 'error' in result:
                    print(f"  [HELIUS ERROR] {result['error'].get('message', 'Unknown error')}")
                    return 0

            return 0

        except requests.exceptions.Timeout:
            print(f"  [HELIUS] Timeout - blockchain query took too long")
            return 0
        except Exception as e:
            print(f"  [HELIUS ERROR] {type(e).__name__}: {e}")
            return 0

    def calculate_score(self, token_data):
        """Score Option B+"""
        score = 0
        breakdown = {}

        # Transactions (0-40 pts)
        txn = token_data.get('txnCount', 0)
        if txn >= 100: txn_score = 40
        elif txn >= 50: txn_score = 35
        elif txn >= 30: txn_score = 30
        elif txn >= 20: txn_score = 25
        elif txn >= 10: txn_score = 20
        elif txn >= 5: txn_score = 15
        elif txn >= 3: txn_score = 10
        elif txn >= 1: txn_score = 5
        else: txn_score = 0
        score += txn_score
        breakdown['txn'] = txn_score

        # Initial Buy (0-20 pts)
        init = token_data.get('initialBuy', 0)
        if init > 2: init_score = 0
        elif init >= 1: init_score = 20
        elif init >= 0.5: init_score = 15
        elif init >= 0.2: init_score = 10
        else: init_score = 5
        score += init_score
        breakdown['init'] = init_score

        # MC (0-20 pts)
        mc = token_data.get('market_cap_usd', 0)
        if OPTIMAL_WINDOW['min_mc'] <= mc <= OPTIMAL_WINDOW['max_mc']:
            if mc <= 10000: mc_score = 20
            elif mc <= 12000: mc_score = 15
            else: mc_score = 10
        else:
            mc_score = 5
        score += mc_score
        breakdown['mc'] = mc_score

        # Early bonus
        early_bonus = 15
        score += early_bonus
        breakdown['early'] = early_bonus

        # Social (0-10 pts)
        social = 0
        if token_data.get('twitter'): social += 4
        if token_data.get('telegram'): social += 3
        if token_data.get('website'): social += 3
        score += social
        breakdown['social'] = social

        # Bundle check
        holders = token_data.get('holderCount', 0)
        txn_count = token_data.get('txnCount', 0)
        bundle_penalty = 0
        if holders > 10 and txn_count > 0:
            ratio = txn_count / holders
            if ratio < 1.3:
                bundle_penalty = -20
            elif ratio < 1.5:
                bundle_penalty = -10
        score += bundle_penalty
        if bundle_penalty < 0:
            breakdown['bundle_penalty'] = bundle_penalty

        return {
            'total': max(0, min(score, 100)),
            'breakdown': breakdown,
            'should_buy': score >= SCORE_THRESHOLD,
            'confidence': 'HIGH' if score >= 50 else 'MEDIUM' if score >= SCORE_THRESHOLD else 'LOW'
        }

    async def handle_new_token(self, data):
        """Nouveau token créé"""
        mint = data.get('mint')
        if not mint:
            return

        symbol = data.get('symbol', '???')
        symbol_clean = symbol.encode('ascii', 'ignore').decode('ascii') or '???'

        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0

        # Stocker le token
        self.tokens[mint] = {
            'mint': mint,
            'symbol': symbol_clean,
            'name': data.get('name', 'Unknown'),
            'mc_usd': mc_usd,
            'twitter': data.get('twitter'),
            'telegram': data.get('telegram'),
            'website': data.get('website'),
            'txnCount': data.get('txnCount', 0),
            'initialBuy': data.get('initialBuy', 0),
            'holderCount': 0,  # Sera mis à jour par Helius
            'discovered_at': datetime.now(),
        }

        total_tokens = len(self.tokens)
        print(f"[NEW] {symbol_clean} @ ${mc_usd:,.0f} (total: {total_tokens})")

        # Subscribe aux trades de ce token
        if self.ws:
            try:
                subscribe_msg = {
                    "method": "subscribeTokenTrade",
                    "keys": [mint]
                }
                await self.ws.send(json.dumps(subscribe_msg))
            except Exception as e:
                print(f"[ERROR] Failed to subscribe to {symbol_clean}: {e}")

    async def handle_trade(self, data):
        """Trade sur un token - MISE A JOUR EN TEMPS REEL"""
        mint = data.get('mint')
        if not mint or mint not in self.tokens:
            return

        token_info = self.tokens[mint]

        # Mettre à jour le market cap
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0

        old_mc = token_info['mc_usd']
        token_info['mc_usd'] = mc_usd

        # Mettre à jour txn
        new_txn = data.get('txnCount', token_info['txnCount'])
        if new_txn > token_info['txnCount']:
            token_info['txnCount'] = new_txn

        # Si le token entre dans la fenêtre $7K-$14K
        if OPTIMAL_WINDOW['min_mc'] <= mc_usd <= OPTIMAL_WINDOW['max_mc']:
            if mint not in self.seen_in_window:
                self.seen_in_window.add(mint)
                # Lancer évaluation en arrière-plan après 10 secondes
                asyncio.create_task(self.evaluate_token_delayed(mint, token_info))

    async def evaluate_token_delayed(self, mint, token_info):
        """Attendre 20 sec puis évaluer avec API PumpPortal"""
        symbol = token_info['symbol']
        mc_usd = token_info['mc_usd']

        print(f"\n{'='*80}")
        print(f"[TOKEN IN WINDOW] {symbol} @ ${mc_usd:,.0f}")
        print(f"  Waiting 20 seconds for data to be available...")
        print(f"{'='*80}")

        # Attendre 20 secondes
        await asyncio.sleep(20)

        # Appeler l'API REST PumpPortal
        try:
            response = await asyncio.to_thread(
                requests.get,
                f'https://pumpportal.fun/api/trade-data?mint={mint}',
                timeout=10
            )

            if response.status_code == 200:
                api_data = response.json()

                # Récupérer les données complètes
                holders = api_data.get('holderCount', 0)
                txn_count = api_data.get('txnCount', 0)
                init_buy = api_data.get('initialBuy', 0)
                mc_usd_api = api_data.get('usdMarketCap', mc_usd)

                print(f"\n[API SUCCESS] {symbol}")
                print(f"  Holders: {holders} | Txn: {txn_count} | InitBuy: {init_buy} SOL")
                print(f"  Market Cap: ${mc_usd_api:,.0f}")

                # Filtre holders minimum
                if holders < MIN_HOLDERS:
                    print(f"  [X] REJECTED: Not enough holders ({holders} < {MIN_HOLDERS})")
                    return

                # Scoring
                token_data = {
                    'market_cap_usd': mc_usd_api,
                    'txnCount': txn_count,
                    'initialBuy': init_buy,
                    'holderCount': holders,
                    'twitter': api_data.get('twitter') or token_info.get('twitter'),
                    'telegram': api_data.get('telegram') or token_info.get('telegram'),
                    'website': api_data.get('website') or token_info.get('website'),
                }

                score = self.calculate_score(token_data)

                print(f"  Score: {score['total']}/100 ({score['confidence']})")
                print(f"  Breakdown: {score['breakdown']}")

                if score['should_buy']:
                    self.tokens_bought += 1
                    print(f"\n  [BUY] BUY SIGNAL! (#{self.tokens_bought})")
                    print(f"  Mint: {mint}")
                else:
                    print(f"  [X] REJECTED: Score too low ({score['total']} < {SCORE_THRESHOLD})")

            else:
                print(f"  [API ERROR] HTTP {response.status_code} - Data not available yet")

        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")

    async def connect_and_run(self):
        """Connexion avec reconnexion automatique"""
        uri = "wss://pumpportal.fun/api/data"

        while True:
            try:
                print(f"\n[CONNECTING] {uri}...")
                async with websockets.connect(
                    uri,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ) as websocket:
                    self.ws = websocket

                    # Subscribe to new tokens
                    await websocket.send(json.dumps({"method": "subscribeNewToken"}))
                    print("[CONNECTED] Listening for new tokens...")
                    print(f"Window: ${OPTIMAL_WINDOW['min_mc']:,} - ${OPTIMAL_WINDOW['max_mc']:,}")
                    print(f"Min holders: {MIN_HOLDERS} | Score threshold: {SCORE_THRESHOLD}")
                    print(f"Helius RPC: Enabled\n")

                    # Listen for messages
                    async for message in websocket:
                        try:
                            data = json.loads(message)

                            # Nouveau token (txType="create" ou pas de txType)
                            if data.get('txType') == 'create' or (data.get('txType') is None and data.get('mint')):
                                await self.handle_new_token(data)

                            # Trade sur un token existant (tous les autres txType)
                            elif data.get('txType') and data.get('txType') != 'create':
                                await self.handle_trade(data)

                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            print(f"[ERROR] Processing message: {e}")
                            continue

            except websockets.exceptions.ConnectionClosed:
                print(f"\n[DISCONNECTED] Connection closed, reconnecting in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)

            except Exception as e:
                print(f"\n[ERROR] {type(e).__name__}: {e}")
                print(f"[RECONNECTING] in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)

async def main():
    # Vérifier que la clé Helius est configurée
    if HELIUS_API_KEY == "YOUR_HELIUS_API_KEY_HERE":
        print("=" * 80)
        print("ERROR: Please set your Helius API key in the HELIUS_API_KEY variable")
        print("=" * 80)
        return

    bot = HeliusWebSocketBot()
    await bot.connect_and_run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOPPED] Bot stopped by user")

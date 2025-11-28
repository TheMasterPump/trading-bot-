"""
BOT WEBSOCKET - Suit les prix en TEMPS RÉEL
Utilise subscribeNewToken + subscribeTokenTrade
"""
import asyncio
import json
import websockets
from datetime import datetime
from collections import defaultdict

SOL_PRICE_USD = 200
OPTIMAL_WINDOW = {
    'min_mc': 7000,
    'max_mc': 14000,
}
MIN_HOLDERS = 1  # Au minimum le créateur
SCORE_THRESHOLD = 30

class LiveWebSocketBot:
    def __init__(self):
        self.tokens = {}  # {mint: {symbol, mc, data, ...}}
        self.seen_above_8k = set()
        self.tokens_bought = 0
        self.ws = None

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
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0

        # Stocker le token
        self.tokens[mint] = {
            'mint': mint,
            'symbol': symbol,
            'name': data.get('name', 'Unknown'),
            'mc_usd': mc_usd,
            'twitter': data.get('twitter'),
            'telegram': data.get('telegram'),
            'website': data.get('website'),
            'txnCount': data.get('txnCount', 0),
            'initialBuy': data.get('initialBuy', 0),
            'holderCount': data.get('holderCount', 0),
            'discovered_at': datetime.now(),
        }

        print(f"[NEW] {symbol} @ ${mc_usd:,.0f} (total: {len(self.tokens)})")

        # SUBSCRIBE aux trades de ce token pour suivre le prix!
        subscribe_payload = {
            "method": "subscribeTokenTrade",
            "keys": [mint]
        }
        await self.ws.send(json.dumps(subscribe_payload))

    async def handle_trade(self, data):
        """Trade sur un token (mise à jour prix)"""
        mint = data.get('mint')
        if not mint or mint not in self.tokens:
            return

        # Mettre à jour le market cap
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0

        token_info = self.tokens[mint]
        old_mc = token_info['mc_usd']
        token_info['mc_usd'] = mc_usd

        # Mettre à jour les stats
        token_info['txnCount'] = data.get('txnCount', token_info['txnCount'])
        token_info['holderCount'] = data.get('newHolderCount', token_info['holderCount'])

        # Afficher si dans la fenêtre $7K-$14K et pas encore vu
        if OPTIMAL_WINDOW['min_mc'] <= mc_usd <= OPTIMAL_WINDOW['max_mc'] and mint not in self.seen_above_8k:
            self.seen_above_8k.add(mint)
            await self.evaluate_token(mint, token_info)

        # Afficher les pumps intéressants
        if old_mc > 0 and mc_usd >= old_mc * 1.5:  # +50% pump
            print(f"[PUMP] {token_info['symbol']}: ${old_mc:,.0f} -> ${mc_usd:,.0f} (+{((mc_usd/old_mc)-1)*100:.0f}%)")

    async def evaluate_token(self, mint, token_info):
        """Évaluer un token dans la fenêtre $7K-$14K"""
        mc_usd = token_info['mc_usd']
        symbol = token_info['symbol']
        holders = token_info['holderCount']

        print(f"\n{'='*80}")
        print(f"[TOKEN IN WINDOW] {symbol} @ ${mc_usd:,.0f}")
        print(f"{'='*80}")

        # Filtres de base
        if holders < MIN_HOLDERS:
            print(f"  [X] REJECTED: Not enough holders ({holders} < {MIN_HOLDERS})")
            return

        # Scoring
        token_data = {
            'market_cap_usd': mc_usd,
            'txnCount': token_info['txnCount'],
            'initialBuy': token_info['initialBuy'],
            'holderCount': holders,
            'twitter': token_info.get('twitter'),
            'telegram': token_info.get('telegram'),
            'website': token_info.get('website'),
        }

        score = self.calculate_score(token_data)

        print(f"  Holders: {holders} | Txn: {token_info['txnCount']}")
        print(f"  Score: {score['total']}/100 ({score['confidence']})")
        print(f"  Breakdown: {score['breakdown']}")

        if score['should_buy']:
            self.tokens_bought += 1
            print(f"\n  [BUY] BUY SIGNAL! (#{self.tokens_bought})")
            print(f"  Mint: {mint}")
        else:
            print(f"  [X] REJECTED: Score too low ({score['total']} < {SCORE_THRESHOLD})")

    async def run(self):
        """Run bot"""
        print("="*80)
        print("LIVE WEBSOCKET BOT - Temps réel avec subscribeTokenTrade")
        print("="*80)
        print(f"Window: ${OPTIMAL_WINDOW['min_mc']:,} - ${OPTIMAL_WINDOW['max_mc']:,}")
        print(f"Min holders: {MIN_HOLDERS}")
        print(f"Score threshold: {SCORE_THRESHOLD} points")
        print("="*80 + "\n")

        uri = "wss://pumpportal.fun/api/data"

        async with websockets.connect(uri) as websocket:
            self.ws = websocket

            # Subscribe to new tokens
            payload = {"method": "subscribeNewToken"}
            await websocket.send(json.dumps(payload))
            print("[WEBSOCKET] Subscribed to new tokens\n")

            # Listen for messages
            async for message in websocket:
                try:
                    data = json.loads(message)

                    # Nouveau token
                    if data.get('txType') is None and data.get('mint'):
                        await self.handle_new_token(data)

                    # Trade sur un token
                    elif data.get('txType'):
                        await self.handle_trade(data)

                except Exception as e:
                    print(f"[ERROR] {e}")
                    continue

async def main():
    bot = LiveWebSocketBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOPPED]")

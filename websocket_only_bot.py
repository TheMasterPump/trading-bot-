"""
BOT WEBSOCKET ONLY - Utilise UNIQUEMENT le WebSocket, pas d'API
Plus rapide, pas de 404!
"""
import asyncio
import json
import websockets
from datetime import datetime

SOL_PRICE_USD = 200
OPTIMAL_WINDOW = {
    'min_mc': 7000,
    'max_mc': 14000,
}
MIN_HOLDERS = 0  # Accepter tous - WebSocket envoie 0 au début
SCORE_THRESHOLD = 30

class WebSocketOnlyBot:
    def __init__(self):
        self.seen_tokens = set()
        self.tokens_bought = 0

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

    async def process_token(self, data):
        """Process token directement depuis WebSocket"""
        if not isinstance(data, dict):
            return

        mint = data.get('mint')
        if not mint or mint in self.seen_tokens:
            return

        # Nettoyer le symbole
        symbol = data.get('symbol', '???')
        symbol_clean = symbol.encode('ascii', 'ignore').decode('ascii') or '???'

        # Calculer le market cap
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0

        # Check si dans la fenêtre
        if not (OPTIMAL_WINDOW['min_mc'] <= mc_usd <= OPTIMAL_WINDOW['max_mc']):
            return

        # On a trouvé un token dans la fenêtre!
        self.seen_tokens.add(mint)

        holders = data.get('holderCount', 0)
        volume_usd = data.get('usdMarketCap', mc_usd)
        txn = data.get('txnCount', 0)
        init_buy = data.get('initialBuy', 0)

        print(f"\n{'='*80}")
        print(f"[TOKEN IN WINDOW] {symbol_clean} @ ${mc_usd:,.0f}")
        print(f"{'='*80}")
        print(f"  Holders: {holders} | Volume: ${volume_usd:,.0f} | Txn: {txn}")

        # Filtres de base
        if holders < MIN_HOLDERS:
            print(f"  [X] REJECTED: Not enough holders ({holders} < {MIN_HOLDERS})")
            return

        # Pas de filtre volume minimum - le score s'en occupe
        # if volume_usd < 1500:
        #     print(f"  [X] REJECTED: Not enough volume (${volume_usd:.0f} < $1.5K)")
        #     return

        # Scoring
        token_data = {
            'market_cap_usd': mc_usd,
            'txnCount': txn,
            'initialBuy': init_buy,
            'holderCount': holders,
            'twitter': data.get('twitter'),
            'telegram': data.get('telegram'),
            'website': data.get('website'),
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

    async def run(self):
        """Run bot"""
        print("="*80)
        print("WEBSOCKET ONLY BOT - No API, Direct from WebSocket!")
        print("="*80)
        print(f"Window: ${OPTIMAL_WINDOW['min_mc']:,} - ${OPTIMAL_WINDOW['max_mc']:,}")
        print(f"Min holders: {MIN_HOLDERS}")
        print(f"Score threshold: {SCORE_THRESHOLD} points")
        print("="*80 + "\n")

        async with websockets.connect('wss://pumpportal.fun/api/data') as ws:
            await ws.send(json.dumps({'method': 'subscribeNewToken'}))
            print("[CONNECTED] Listening for tokens...\n")

            token_count = 0
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(msg)

                    token_count += 1
                    if token_count % 10 == 0:
                        print(f"[STATS] Scanned: {token_count} | Bought: {self.tokens_bought}")

                    await self.process_token(data)

                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"[ERROR] {e}")

async def main():
    bot = WebSocketOnlyBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOPPED]")

"""
SIMPLE SNIPER - Achète directement les tokens dans la fenêtre
Sans watch list, sans complications
"""
import asyncio
import json
import websockets
from datetime import datetime

OPTIMAL_WINDOW = {
    'min_mc': 7000,
    'max_mc': 14000,
}
SOL_PRICE_USD = 200
BUY_AMOUNT_SOL = 2.5

class SimpleSniperBot:
    def __init__(self):
        self.wallet_sol = 100.0
        self.seen_tokens = set()
        self.tokens_scanned = 0
        self.tokens_bought = 0

    def calculate_score(self, token_data):
        """Score (0-100)"""
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
            if mc <= 10500: mc_score = 20
            elif mc <= 11500: mc_score = 15
            else: mc_score = 10
        else:
            mc_score = 0
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
                breakdown['bundle_warning'] = 'HIGH RISK'
            elif ratio < 1.5:
                bundle_penalty = -10
                breakdown['bundle_warning'] = 'MEDIUM RISK'
        score += bundle_penalty
        if bundle_penalty < 0:
            breakdown['bundle_penalty'] = bundle_penalty

        return {
            'total': max(0, min(score, 100)),
            'breakdown': breakdown,
            'should_buy': score >= 40,
            'confidence': 'HIGH' if score >= 60 else 'MEDIUM' if score >= 40 else 'LOW'
        }

    async def process_token(self, data):
        """Process token"""
        if not isinstance(data, dict):
            return

        mint = data.get('mint')
        if not mint or mint in self.seen_tokens:
            return

        self.seen_tokens.add(mint)
        self.tokens_scanned += 1

        symbol = data.get('symbol', '???')
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0
        holders = data.get('holderCount', 0)
        volume_usd = data.get('usdMarketCap', mc_usd)
        txn = data.get('txnCount', 0)
        init_buy = data.get('initialBuy', 0)

        # Afficher TOUS les tokens
        print(f"\n[{self.tokens_scanned}] {symbol} @ ${mc_usd:,.0f} | H:{holders} V:${volume_usd:,.0f} T:{txn}")

        # Check fenêtre UNIQUEMENT
        if not (OPTIMAL_WINDOW['min_mc'] <= mc_usd <= OPTIMAL_WINDOW['max_mc']):
            if mc_usd < OPTIMAL_WINDOW['min_mc']:
                print(f"  [LOW] Below window (${mc_usd:,.0f} < ${OPTIMAL_WINDOW['min_mc']:,})")
            else:
                print(f"  [HIGH] Above window (${mc_usd:,.0f} > ${OPTIMAL_WINDOW['max_mc']:,})")
            return

        print(f"  [IN WINDOW] ${OPTIMAL_WINDOW['min_mc']:,} - ${OPTIMAL_WINDOW['max_mc']:,}")

        # Filtres de base
        if holders < 9:
            print(f"  [X] REJECTED: Holders ({holders}) < 9")
            return

        if volume_usd < 2000:
            print(f"  [X] REJECTED: Volume (${volume_usd:.0f}) < $2K")
            return

        # Score
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
            if self.wallet_sol >= BUY_AMOUNT_SOL:
                self.wallet_sol -= BUY_AMOUNT_SOL
                self.tokens_bought += 1
                print(f"\n{'='*80}")
                print(f"[BUY] PURCHASE #{self.tokens_bought}: {symbol} @ ${mc_usd:,.0f}")
                print(f"  Amount: {BUY_AMOUNT_SOL} SOL")
                print(f"  Wallet remaining: {self.wallet_sol:.2f} SOL")
                print(f"  Mint: {mint}")
                print(f"{'='*80}\n")
            else:
                print(f"  [LOW SOL] Not enough SOL (wallet: {self.wallet_sol:.2f})")
        else:
            print(f"  [X] REJECTED: Score too low ({score['total']} < 40)")

    async def run(self, duration_minutes=30):
        """Run"""
        print("\n" + "="*80)
        print("SIMPLE SNIPER - Achète directement dans la fenêtre")
        print("="*80)
        print(f"Wallet: {self.wallet_sol:.2f} FAKE SOL")
        print(f"Fenêtre: ${OPTIMAL_WINDOW['min_mc']:,} - ${OPTIMAL_WINDOW['max_mc']:,}")
        print(f"Durée: {duration_minutes} minutes")
        print("="*80 + "\n")

        try:
            async with websockets.connect('wss://pumpportal.fun/api/data') as ws:
                await ws.send(json.dumps({'method': 'subscribeNewToken'}))
                print("[CONNECTED] En écoute...\n")

                start = datetime.now().timestamp()
                end = start + (duration_minutes * 60)

                while datetime.now().timestamp() < end:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        data = json.loads(msg)
                        await self.process_token(data)

                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        continue

                print(f"\n{'='*80}")
                print("SESSION TERMINÉE")
                print(f"{'='*80}")
                print(f"Tokens scannés: {self.tokens_scanned}")
                print(f"Tokens achetés: {self.tokens_bought}")
                print(f"Wallet final: {self.wallet_sol:.2f} SOL")
                print(f"{'='*80}\n")

        except KeyboardInterrupt:
            print(f"\n{'='*80}")
            print("INTERROMPU")
            print(f"{'='*80}")
            print(f"Tokens scannés: {self.tokens_scanned}")
            print(f"Tokens achetés: {self.tokens_bought}")
            print(f"Wallet final: {self.wallet_sol:.2f} SOL")
            print(f"{'='*80}\n")

async def main():
    bot = SimpleSniperBot()
    await bot.run(duration_minutes=30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOPPED]")

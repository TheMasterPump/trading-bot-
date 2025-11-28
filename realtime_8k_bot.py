"""
BOT TEMPS RÉEL - Affiche tous les tokens >= $8K en temps réel
Pas de fenêtre compliquée, juste $8K minimum
"""
import asyncio
import json
import websockets
import requests
from datetime import datetime, timedelta

SOL_PRICE_USD = 200
MIN_MC = 8000  # $8K minimum

class RealTimeBot:
    def __init__(self):
        self.all_tokens = {}  # Tous les tokens découverts {mint: {...}}
        self.seen_tokens = set()
        self.tokens_bought = 0
        self.running = True

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
        if 9500 <= mc <= 13000:
            if mc <= 10500: mc_score = 20
            elif mc <= 11500: mc_score = 15
            else: mc_score = 10
        else:
            mc_score = 5  # Bonus minimal si hors fenêtre optimale
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
            'should_buy': score >= 40,
            'confidence': 'HIGH' if score >= 60 else 'MEDIUM' if score >= 40 else 'LOW'
        }

    async def discover_tokens(self):
        """WebSocket - Découvre les nouveaux tokens"""
        print("[WEBSOCKET] Connecting...")

        async with websockets.connect('wss://pumpportal.fun/api/data') as ws:
            await ws.send(json.dumps({'method': 'subscribeNewToken'}))
            print("[WEBSOCKET] Connected! Discovering tokens...\n")

            while self.running:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(msg)

                    if not isinstance(data, dict):
                        continue

                    mint = data.get('mint')
                    if not mint or mint in self.all_tokens:
                        continue

                    # Ajouter à la liste de tracking
                    self.all_tokens[mint] = {
                        'mint': mint,
                        'symbol': data.get('symbol', '???'),
                        'name': data.get('name', 'Unknown'),
                        'discovered_at': datetime.now(),
                        'last_check': None,
                        'current_mc': 0,
                    }

                    print(f"[NEW] {data.get('symbol')} discovered (total: {len(self.all_tokens)})")

                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"[ERROR] WebSocket: {e}")
                    await asyncio.sleep(5)

    async def track_prices(self):
        """API - Track prix en temps réel de TOUS les tokens"""
        print("[API TRACKER] Starting price tracker...")
        print("[API TRACKER] Waiting 5 seconds for tokens to be discovered...\n")
        await asyncio.sleep(5)  # Laisser le temps de découvrir quelques tokens

        print("[API TRACKER] Starting price checking loop!\n")

        cycle = 0
        while self.running:
            if not self.all_tokens:
                await asyncio.sleep(1)
                continue

            cycle += 1
            # Check tous les tokens (max 50 par cycle pour ne pas surcharger)
            tokens_to_check = list(self.all_tokens.items())[:50]

            print(f"\n[CYCLE #{cycle}] Checking {len(tokens_to_check)} tokens...")
            found_above_8k = 0

            for mint, info in tokens_to_check:
                # Skip si token trop récent (< 30 secondes)
                age = (datetime.now() - info['discovered_at']).total_seconds()
                if age < 30:
                    print(f"  {info['symbol']}: Too new ({age:.0f}s), waiting...")
                    continue

                try:
                    # API call pour prix actuel
                    response = requests.get(
                        f'https://pumpportal.fun/api/trade-data?mint={mint}',
                        timeout=5
                    )

                    print(f"  {info['symbol']}: HTTP {response.status_code}", end='')

                    if response.status_code == 200:
                        api_data = response.json()
                        mc_sol = api_data.get('marketCapSol', 0)
                        mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0

                        info['current_mc'] = mc_usd
                        info['last_check'] = datetime.now()
                        info['data'] = api_data

                        # DEBUG: Afficher tous les MC
                        print(f" - ${mc_usd:,.0f}", end='')

                        # Si >= $8K, afficher et évaluer
                        if mc_usd >= MIN_MC and mint not in self.seen_tokens:
                            print(f" ✅ >= $8K!")
                            found_above_8k += 1
                            self.seen_tokens.add(mint)
                            await self.evaluate_token(mint, info, api_data)
                        else:
                            print()  # Nouvelle ligne
                    else:
                        print(f" - API failed")

                except Exception as e:
                    print(f"  {info['symbol']}: ERROR - {e}")

                await asyncio.sleep(0.1)  # 100ms entre chaque API call

            print(f"[CYCLE #{cycle}] Found {found_above_8k} tokens >= $8K")

            # Nettoyer les vieux tokens (> 1 heure)
            cutoff = datetime.now() - timedelta(hours=1)
            old_tokens = [m for m, i in self.all_tokens.items() if i['discovered_at'] < cutoff]
            for mint in old_tokens:
                del self.all_tokens[mint]

            await asyncio.sleep(1)  # Pause avant le prochain cycle

    async def evaluate_token(self, mint, info, api_data):
        """Évaluer un token >= $8K"""
        mc_usd = info['current_mc']
        symbol = info['symbol']

        print(f"\n{'='*80}")
        print(f"[TOKEN >= $8K] {symbol} @ ${mc_usd:,.0f}")
        print(f"{'='*80}")

        holders = api_data.get('holderCount', 0)
        volume_usd = api_data.get('usdMarketCap', mc_usd)
        txn = api_data.get('txnCount', 0)

        print(f"  Holders: {holders} | Volume: ${volume_usd:,.0f} | Txn: {txn}")

        # Filtres de base
        if holders < 9:
            print(f"  ❌ REJECTED: Not enough holders ({holders} < 9)")
            return

        if volume_usd < 2000:
            print(f"  ❌ REJECTED: Not enough volume (${volume_usd:.0f} < $2K)")
            return

        # Scoring
        token_data = {
            'market_cap_usd': mc_usd,
            'txnCount': txn,
            'initialBuy': api_data.get('initialBuy', 0),
            'holderCount': holders,
            'twitter': api_data.get('twitter'),
            'telegram': api_data.get('telegram'),
            'website': api_data.get('website'),
        }

        score = self.calculate_score(token_data)

        print(f"  Score: {score['total']}/100 ({score['confidence']})")
        print(f"  Breakdown: {score['breakdown']}")

        if score['should_buy']:
            self.tokens_bought += 1
            print(f"\n  ✅✅✅ BUY SIGNAL! (#{self.tokens_bought})")
            print(f"  Mint: {mint}")
        else:
            print(f"  ❌ REJECTED: Score too low ({score['total']} < 40)")

    async def run(self):
        """Run both tasks"""
        print("="*80)
        print("REAL-TIME BOT - Tous les tokens >= $8K")
        print("="*80)
        print(f"Minimum MC: ${MIN_MC:,}")
        print(f"Score threshold: 40 points")
        print("="*80 + "\n")

        # Run both tasks in parallel
        await asyncio.gather(
            self.discover_tokens(),
            self.track_prices()
        )

async def main():
    bot = RealTimeBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOPPED]")

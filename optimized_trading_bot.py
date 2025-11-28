"""
OPTIMIZED TRADING BOT
Combine ML prediction + whale monitoring + multi-sell strategy
Objectif: Passer de 9.3% a 50%+ win rate
"""
import asyncio
import httpx
import json
from datetime import datetime
from collections import defaultdict

HELIUS_API_KEY = "530a1718-a4f6-4bf6-95ca-69c6b8a23e7b"
SOL_PRICE = 200.0

# Configuration
CONFIG = {
    'min_market_cap': 10000,      # $10k min
    'max_market_cap': 50000,      # $50k max
    'max_age_hours': 24,          # Token < 24h
    'min_score': 80,              # Score minimum pour acheter
    'max_daily_buys': 15,         # Max 15 tokens/jour
    'buy_amount_sol': 2.0,        # 2 SOL par token
    'stop_loss_pct': -50,         # -50% stop loss
    'multi_sell_portions': 60,    # 60 ventes
    'take_profit_pct': 200,       # +200% take profit partiel
}


class TokenScorer:
    """Score tokens based on multiple factors"""

    async def get_whale_activity(self, token_mint):
        """Check if whales are trading this token"""
        # Simule le whale monitoring
        # En prod: vraiment checker nos 259 whale wallets
        return {
            'whale_count': 3,
            'whale_volume_sol': 15.5,
            'score': 50  # 0-50 pts based on whale activity
        }

    async def get_social_metrics(self, token_mint):
        """Get social media presence"""
        client = httpx.AsyncClient(timeout=30.0)

        try:
            url = f"https://frontend-api.pump.fun/coins/{token_mint}"
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()

                has_twitter = bool(data.get('twitter'))
                has_telegram = bool(data.get('telegram'))
                has_website = bool(data.get('website'))

                # Score: 40 pts max for social
                social_score = 0
                if has_twitter: social_score += 15
                if has_telegram: social_score += 15
                if has_website: social_score += 10

                await client.aclose()
                return {
                    'twitter': has_twitter,
                    'telegram': has_telegram,
                    'website': has_website,
                    'score': social_score
                }
        except:
            pass

        await client.aclose()
        return {'score': 0}

    async def get_holder_metrics(self, token_mint):
        """Get holder distribution"""
        # Simule l'analyse des holders
        # En prod: vraiment checker la distribution
        return {
            'holder_count': 150,
            'top_10_pct': 35,  # Top 10 holders own 35%
            'score': 20  # 0-20 pts based on distribution
        }

    async def calculate_score(self, token_data):
        """Calculate overall score for a token"""
        token_mint = token_data['mint']
        market_cap = token_data.get('usd_market_cap', 0)
        age_hours = token_data.get('age_hours', 999)

        # Check basic filters
        if market_cap < CONFIG['min_market_cap']:
            return {'score': 0, 'reason': 'Market cap too low'}

        if market_cap > CONFIG['max_market_cap']:
            return {'score': 0, 'reason': 'Market cap too high'}

        if age_hours > CONFIG['max_age_hours']:
            return {'score': 0, 'reason': 'Token too old'}

        # Calculate component scores
        whale_data = await self.get_whale_activity(token_mint)
        social_data = await self.get_social_metrics(token_mint)
        holder_data = await self.get_holder_metrics(token_mint)

        total_score = (
            whale_data['score'] +      # 0-50 pts
            social_data['score'] +     # 0-40 pts
            holder_data['score']       # 0-20 pts
        )

        # Volume score (0-30 pts)
        volume_24h = token_data.get('volume_24h', 0)
        volume_score = min(30, int(volume_24h / 1000))  # 1pt per $1k volume
        total_score += volume_score

        return {
            'score': total_score,
            'whale_score': whale_data['score'],
            'social_score': social_data['score'],
            'holder_score': holder_data['score'],
            'volume_score': volume_score,
            'whale_count': whale_data.get('whale_count', 0),
            'social': social_data,
            'should_buy': total_score >= CONFIG['min_score']
        }


class OptimizedBot:
    """Optimized trading bot"""

    def __init__(self):
        self.scorer = TokenScorer()
        self.daily_buys = 0
        self.positions = {}

    async def scan_new_tokens(self):
        """Scan for new tokens on pump.fun"""
        client = httpx.AsyncClient(timeout=30.0)

        try:
            # Get recent tokens from pump.fun
            url = "https://frontend-api.pump.fun/coins?limit=50&sort=created_timestamp&order=DESC"
            response = await client.get(url)

            if response.status_code == 200:
                tokens = response.json()
                await client.aclose()
                return tokens
        except:
            pass

        await client.aclose()
        return []

    async def evaluate_token(self, token):
        """Evaluate if we should buy a token"""
        mint = token['mint']
        name = token.get('name', 'Unknown')
        symbol = token.get('symbol', '???')
        market_cap = token.get('usd_market_cap', 0)

        # Calculate age
        created_ts = token.get('created_timestamp', 0)
        age_hours = (datetime.now().timestamp() * 1000 - created_ts) / 3600000

        token_data = {
            'mint': mint,
            'name': name,
            'symbol': symbol,
            'usd_market_cap': market_cap,
            'age_hours': age_hours,
            'volume_24h': token.get('volume_24h', 0)
        }

        # Score the token
        score_result = await self.scorer.calculate_score(token_data)

        return {
            'token': token_data,
            'score': score_result
        }

    async def execute_buy(self, token_data, score_data):
        """Execute buy order (simulation)"""
        print(f"\n[BUY ORDER]")
        print(f"  Token: {token_data['name']} (${token_data['symbol']})")
        print(f"  Mint: {token_data['mint'][:16]}...")
        print(f"  Score: {score_data['score']}/140")
        print(f"    - Whale score: {score_data['whale_score']}/50")
        print(f"    - Social score: {score_data['social_score']}/40")
        print(f"    - Holder score: {score_data['holder_score']}/20")
        print(f"    - Volume score: {score_data['volume_score']}/30")
        print(f"  Amount: {CONFIG['buy_amount_sol']} SOL (${CONFIG['buy_amount_sol'] * SOL_PRICE})")
        print(f"  Market Cap: ${token_data['usd_market_cap']:,.0f}")

        # En production: vraiment acheter via Solana
        # Pour l'instant: simulation
        self.positions[token_data['mint']] = {
            'bought_at': datetime.now().timestamp(),
            'buy_price_sol': CONFIG['buy_amount_sol'],
            'buy_market_cap': token_data['usd_market_cap'],
            'token_data': token_data,
            'score_data': score_data
        }

        self.daily_buys += 1

    async def monitor_positions(self):
        """Monitor open positions and execute multi-sell"""
        print(f"\n[MONITORING {len(self.positions)} POSITIONS]")

        for mint, position in list(self.positions.items()):
            # En production: vraiment checker le prix actuel
            # Simulation: random si pump ou dump
            import random
            current_mc = position['buy_market_cap'] * random.uniform(0.5, 5.0)

            roi = ((current_mc / position['buy_market_cap']) - 1) * 100

            print(f"\n  {position['token_data']['symbol']}: {roi:+.1f}% ROI")

            # Multi-sell strategy si pump
            if roi > CONFIG['take_profit_pct']:
                print(f"    [PUMP DETECTED] Starting multi-sell...")
                await self.execute_multi_sell(mint, position)

            # Stop loss si dump
            elif roi < CONFIG['stop_loss_pct']:
                print(f"    [DUMP DETECTED] Stop loss triggered...")
                await self.execute_stop_loss(mint, position)

    async def execute_multi_sell(self, mint, position):
        """Execute multi-sell strategy (60-80 portions)"""
        print(f"    Selling in {CONFIG['multi_sell_portions']} portions...")

        # En production: vraiment vendre en 60 portions sur 1 heure
        # Simulation
        total_profit = CONFIG['buy_amount_sol'] * (CONFIG['take_profit_pct'] / 100)
        print(f"    Expected profit: {total_profit:.2f} SOL (${total_profit * SOL_PRICE:.2f})")

        del self.positions[mint]

    async def execute_stop_loss(self, mint, position):
        """Execute stop loss"""
        print(f"    Selling at loss...")

        # En production: vraiment vendre
        # Simulation
        loss = CONFIG['buy_amount_sol'] * (CONFIG['stop_loss_pct'] / 100)
        print(f"    Loss: {loss:.2f} SOL (${abs(loss) * SOL_PRICE:.2f})")

        del self.positions[mint]

    async def run(self):
        """Main bot loop"""
        print("=" * 70)
        print("OPTIMIZED TRADING BOT")
        print("=" * 70)
        print(f"Config:")
        print(f"  Market Cap Range: ${CONFIG['min_market_cap']:,} - ${CONFIG['max_market_cap']:,}")
        print(f"  Min Score: {CONFIG['min_score']}/140")
        print(f"  Max Daily Buys: {CONFIG['max_daily_buys']}")
        print(f"  Buy Amount: {CONFIG['buy_amount_sol']} SOL")
        print(f"  Multi-sell: {CONFIG['multi_sell_portions']} portions")
        print("=" * 70)

        iteration = 0

        while iteration < 3:  # Demo: 3 iterations
            iteration += 1
            print(f"\n\n[ITERATION {iteration}]")
            print(f"Daily buys so far: {self.daily_buys}/{CONFIG['max_daily_buys']}")

            # Scan new tokens
            print(f"\n[SCANNING NEW TOKENS...]")
            new_tokens = await self.scan_new_tokens()
            print(f"Found {len(new_tokens)} new tokens")

            # Evaluate each token
            buy_candidates = []

            for token in new_tokens[:10]:  # Check first 10
                evaluation = await self.evaluate_token(token)

                if evaluation['score']['should_buy']:
                    print(f"\n[CANDIDATE] {token['symbol']} - Score: {evaluation['score']['score']}/140")
                    buy_candidates.append(evaluation)

            # Buy top candidates
            buy_candidates.sort(key=lambda x: x['score']['score'], reverse=True)

            for candidate in buy_candidates:
                if self.daily_buys >= CONFIG['max_daily_buys']:
                    print(f"\n[LIMIT REACHED] Daily buy limit reached ({CONFIG['max_daily_buys']})")
                    break

                await self.execute_buy(candidate['token'], candidate['score'])

            # Monitor existing positions
            await self.monitor_positions()

            await asyncio.sleep(2)  # Demo delay

        print("\n" + "=" * 70)
        print("BOT DEMO COMPLETED")
        print("=" * 70)


async def main():
    bot = OptimizedBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())

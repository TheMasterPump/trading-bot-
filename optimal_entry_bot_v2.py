"""
OPTIMAL ENTRY BOT V2 - WebSocket Version
Utilise wss://pumpportal.fun/api/data pour données en temps réel
Acheter UNIQUEMENT dans la fenêtre $9.5k - $13k MC
"""
import asyncio
import json
import websockets
from datetime import datetime
from collections import defaultdict

# OPTIMAL ENTRY WINDOW
OPTIMAL_WINDOW = {
    'min_mc': 9500,      # $9.5k minimum
    'max_mc': 13000,     # $13k maximum
    'migration_mc': 69000,  # $69k migration
}

# WebSocket URL
PUMPPORTAL_WS = "wss://pumpportal.fun/api/data"

# ROI calculations
def calculate_potential_roi(entry_mc):
    """Calculate potential ROI if bought at entry_mc"""
    migration_mc = OPTIMAL_WINDOW['migration_mc']
    multiplier = migration_mc / entry_mc
    roi_pct = (multiplier - 1) * 100
    return {
        'multiplier': multiplier,
        'roi_pct': roi_pct,
        'entry_mc': entry_mc,
        'target_mc': migration_mc
    }


class OptimalEntryScorer:
    """Score tokens in optimal entry window"""

    def calculate_score(self, token_data):
        """Calculate migration probability score - SYSTÈME OPTIMISÉ B+"""

        score = 0
        breakdown = {}

        # 1. Transactions/Volume (0-40 pts) - LE PLUS IMPORTANT! PERMISSIF pour early tokens
        txn_count = token_data.get('txnCount', 0)
        volume_score = 0

        if txn_count >= 100:
            volume_score = 40
        elif txn_count >= 50:
            volume_score = 35
        elif txn_count >= 30:
            volume_score = 30
        elif txn_count >= 20:
            volume_score = 25
        elif txn_count >= 10:
            volume_score = 20   # AUGMENTÉ
        elif txn_count >= 5:
            volume_score = 15   # AUGMENTÉ
        elif txn_count >= 3:
            volume_score = 10   # NOUVEAU
        elif txn_count >= 1:
            volume_score = 5    # NOUVEAU

        score += volume_score
        breakdown['txn'] = volume_score

        # 2. Initial Buy (0-20 pts) - 0-2 SOL acceptable, >2 SOL = red flag
        initial_buy = token_data.get('initialBuy', 0)
        liquidity_score = 0

        if initial_buy > 2:
            liquidity_score = 0       # RED FLAG: Dev farmer (>2 SOL)
        elif initial_buy >= 1:
            liquidity_score = 20      # OPTIMAL (1-2 SOL)
        elif initial_buy >= 0.5:
            liquidity_score = 15      # Bon (0.5-1 SOL)
        elif initial_buy >= 0.2:
            liquidity_score = 10      # Acceptable (0.2-0.5 SOL)
        else:
            liquidity_score = 5       # Acceptable (0-0.2 SOL, dev confiant)

        score += liquidity_score
        breakdown['init'] = liquidity_score

        # 3. Market Cap Position (0-20 pts) - Potentiel de gain
        mc = token_data.get('marketCapSol', 0) * 200  # Convert SOL to USD (approx)
        mc_score = 0

        if OPTIMAL_WINDOW['min_mc'] <= mc <= OPTIMAL_WINDOW['max_mc']:
            if mc <= 10500:  # Lower = better
                mc_score = 20
            elif mc <= 11500:
                mc_score = 15
            else:
                mc_score = 10

        score += mc_score
        breakdown['mc'] = mc_score

        # 4. Early Bonus (0-15 pts) - NOUVEAU! Tous tokens WebSocket sont frais
        early_bonus = 15
        score += early_bonus
        breakdown['early'] = early_bonus

        # 5. Social Bonus (0-10 pts) - Nice to have, pas obligatoire
        social_score = 0
        if token_data.get('twitter'):
            social_score += 4
        if token_data.get('telegram'):
            social_score += 3
        if token_data.get('website'):
            social_score += 3

        score += social_score
        breakdown['social'] = social_score

        # 6. Quick Bundle Check (Penalty 0 to -20 pts) - NOUVEAU!
        holders = token_data.get('holderCount', 0)
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

        # Calculate potential ROI
        roi_data = calculate_potential_roi(mc) if mc > 0 else None

        return {
            'total_score': max(0, min(score, 100)),
            'breakdown': breakdown,
            'potential_roi': roi_data,
            'should_buy': score >= 40,  # BAISSÉ de 50 à 40
            'confidence': 'HIGH' if score >= 60 else 'MEDIUM' if score >= 40 else 'LOW'
        }


class OptimalEntryBotWS:
    """Bot using WebSocket for real-time data"""

    def __init__(self):
        self.scorer = OptimalEntryScorer()
        self.seen_tokens = set()
        self.candidates = []

    async def connect_and_monitor(self, duration_minutes=120):
        """Connect to WebSocket and monitor new tokens"""

        print("="*70)
        print("OPTIMAL ENTRY BOT V2 - WebSocket Version")
        print("="*70)
        print(f"Target Window: ${OPTIMAL_WINDOW['min_mc']:,} - ${OPTIMAL_WINDOW['max_mc']:,}")
        print(f"Expected ROI: 5x-7x (430%-630%)")
        print(f"Monitoring for: {duration_minutes} minutes")
        print("="*70)

        subscription_payload = {
            "method": "subscribeNewToken"
        }

        try:
            async with websockets.connect(PUMPPORTAL_WS) as websocket:
                # Subscribe to new tokens
                await websocket.send(json.dumps(subscription_payload))
                print(f"\n[CONNECTED] Listening to PumpPortal WebSocket...")
                print(f"Waiting for new tokens in ${OPTIMAL_WINDOW['min_mc']:,}-${OPTIMAL_WINDOW['max_mc']:,} window...\n")

                start_time = datetime.now()
                end_time = start_time.timestamp() + (duration_minutes * 60)

                while datetime.now().timestamp() < end_time:
                    try:
                        # Receive data with timeout
                        message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        data = json.loads(message)

                        # Process new token
                        await self.process_token(data)

                    except asyncio.TimeoutError:
                        # No data in 30 seconds, continue
                        continue
                    except json.JSONDecodeError:
                        print(f"[!] Invalid JSON received")
                        continue

                print(f"\n[MONITORING COMPLETE] Ran for {duration_minutes} minutes")
                self.print_summary()

        except websockets.exceptions.WebSocketException as e:
            print(f"[!] WebSocket error: {e}")
        except Exception as e:
            print(f"[!] Error: {e}")

    async def process_token(self, data):
        """Process a new token from WebSocket"""

        # Check if it's a new token event
        if not isinstance(data, dict):
            return

        mint = data.get('mint')
        if not mint or mint in self.seen_tokens:
            return

        self.seen_tokens.add(mint)

        # Extract token info
        name = data.get('name', 'Unknown')
        symbol = data.get('symbol', '???')
        twitter = data.get('twitter')
        telegram = data.get('telegram')
        website = data.get('website')

        # Market cap in SOL, convert to USD (approx $200/SOL)
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * 200 if mc_sol else 0

        # Check if in optimal window
        if not (OPTIMAL_WINDOW['min_mc'] <= mc_usd <= OPTIMAL_WINDOW['max_mc']):
            return

        # FILTRES DE BASE - Activité minimale requise
        holders = data.get('holderCount', 0)
        volume_usd = data.get('usdMarketCap', mc_usd)

        if holders < 9:
            return  # Minimum 9 holders requis

        if volume_usd < 2000:
            return  # Minimum $2K volume requis

        # Prepare token data for scoring
        token_data = {
            'mint': mint,
            'symbol': symbol,
            'name': name,
            'marketCapSol': mc_sol,
            'market_cap_usd': mc_usd,
            'twitter': twitter,
            'telegram': telegram,
            'website': website,
            'txnCount': data.get('txnCount', 0),
            'initialBuy': data.get('initialBuy', 0),
            'holderCount': data.get('holderCount', 0),
        }

        # Score it
        scoring = self.scorer.calculate_score(token_data)

        if scoring['should_buy']:
            token_data['scoring'] = scoring
            self.candidates.append(token_data)

            # Display immediately
            self.display_candidate(token_data)

    def display_candidate(self, token):
        """Display a candidate token"""

        score = token['scoring']
        roi = score['potential_roi']

        print(f"\n{'='*70}")
        print(f"🚨 NEW OPPORTUNITY DETECTED!")
        print(f"{'='*70}")
        print(f"\n[{len(self.candidates)}] {token['symbol']} - {token['name']}")
        print(f"  Mint: {token['mint'][:32]}...")
        print(f"  Market Cap: ${token['market_cap_usd']:,.0f} ({token['marketCapSol']:.2f} SOL)")
        print(f"  Transactions: {token['txnCount']}")
        print(f"  Initial Buy: {token['initialBuy']:.2f} SOL")

        # Social
        socials = []
        if token['twitter']: socials.append('Twitter')
        if token['telegram']: socials.append('Telegram')
        if token['website']: socials.append('Website')
        print(f"  Social: {', '.join(socials) if socials else 'None'}")

        # Potential ROI
        if roi:
            print(f"\n  >> POTENTIAL ROI:")
            print(f"     Entry: ${roi['entry_mc']:,.0f}")
            print(f"     Target: ${roi['target_mc']:,.0f} (migration)")
            print(f"     Multiplier: {roi['multiplier']:.1f}x")
            print(f"     ROI: +{roi['roi_pct']:.0f}%")

        # Score
        print(f"\n  >> MIGRATION SCORE: {score['total_score']}/100")
        print(f"     Confidence: {score['confidence']}")
        print(f"     Breakdown:")
        for component, pts in score['breakdown'].items():
            print(f"       - {component}: {pts} pts")

        # Recommendation
        if score['total_score'] >= 65:
            print(f"\n  >> RECOMMENDATION: BUY NOW (3 SOL) - HIGH CONFIDENCE 🚀")
        elif score['total_score'] >= 50:
            print(f"\n  >> RECOMMENDATION: BUY (2 SOL) - MEDIUM CONFIDENCE")

        print(f"{'='*70}\n")

    def print_summary(self):
        """Print summary of session"""

        print("\n" + "="*70)
        print("SESSION SUMMARY")
        print("="*70)

        print(f"\nTotal tokens scanned: {len(self.seen_tokens)}")
        print(f"Opportunities found: {len(self.candidates)}")

        if self.candidates:
            high_conf = [c for c in self.candidates if c['scoring']['confidence'] == 'HIGH']
            medium_conf = [c for c in self.candidates if c['scoring']['confidence'] == 'MEDIUM']

            print(f"\nHigh Confidence (>=65): {len(high_conf)}")
            print(f"Medium Confidence (50-64): {len(medium_conf)}")

            # Average potential ROI
            rois = [c['scoring']['potential_roi']['roi_pct'] for c in self.candidates if c['scoring']['potential_roi']]
            if rois:
                avg_roi = sum(rois) / len(rois)
                print(f"\nAverage Potential ROI: +{avg_roi:.0f}%")

            # Save to file
            output = {
                'timestamp': datetime.now().isoformat(),
                'window': OPTIMAL_WINDOW,
                'total_scanned': len(self.seen_tokens),
                'candidates': len(self.candidates),
                'high_confidence': len(high_conf),
                'medium_confidence': len(medium_conf),
                'tokens': self.candidates,
            }

            filename = f"optimal_entry_ws_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(output, f, indent=2, default=str)

            print(f"\n[SAVED] {filename}")
        else:
            print(f"\nNo opportunities found in optimal window")
            print(f"Try running for longer period or during peak hours")

        print("\n" + "="*70)


async def main():
    print("\n=== OPTIMAL ENTRY BOT V2 - WebSocket ===\n")
    print("Sweet spot: $9,500 - $13,000 market cap")
    print("Potential: 5x-7x ROI (430%-630%)")
    print("Using: wss://pumpportal.fun/api/data\n")

    duration = input("Monitor duration in minutes (default 60): ").strip()

    try:
        duration = int(duration) if duration else 60
        duration = max(5, min(480, duration))  # 5 min to 8 hours
    except:
        duration = 60

    print(f"\n[STARTING] Monitoring for {duration} minutes...\n")

    bot = OptimalEntryBotWS()
    await bot.connect_and_monitor(duration_minutes=duration)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[!] Stopped by user")

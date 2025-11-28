"""
BOT WEBSOCKET ROBUSTE - Suit les tokens en temps réel avec reconnexion
Utilise subscribeNewToken + subscribeTokenTrade pour les mises à jour live
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
MIN_HOLDERS = 10  # Au moins 10 traders uniques pour filtrer wash trading
MIN_VOLUME_USD = 3000  # Volume minimum $3K
SCORE_THRESHOLD = 35  # Score minimum plus strict

# NOUVEAUX FILTRES - Vélocité précoce (basé sur analyse de 3 tokens migrés: KATIE, INCOG, PLOPPER)
MIN_EARLY_TXN_2MIN = 40  # 20 txn/min * 2 min = 40 txn minimum (pattern gagnant)
MIN_EARLY_TRADERS_2MIN = 8  # Au moins 8 traders uniques dans les 2 premières minutes
MIN_EARLY_BUY_RATIO = 0.55  # 55% de buys minimum (tous les gagnants avaient 55-60%)

class RobustWebSocketBot:
    def __init__(self):
        self.tokens = {}  # {mint: {symbol, mc, holders, txn, ...}}
        self.unique_traders = {}  # {mint: set(traderPublicKey)} - REAL-TIME HOLDERS
        self.seen_in_window = set()
        self.tokens_bought = 0
        self.ws = None
        self.reconnect_delay = 5
        self.last_watchlist_display = datetime.now()

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

        # NOUVEAU - Vélocité précoce (2 premières minutes)
        early_txn_2min = token_data.get('first_2min_txn', 0)
        early_traders_2min = token_data.get('first_2min_traders_count', 0)
        early_buys = token_data.get('first_2min_buys', 0)
        early_sells = token_data.get('first_2min_sells', 0)

        # Points pour vélocité (0-30 pts) - PATTERN GAGNANT: 40+ txn en 2 min
        velocity_score = 0
        if early_txn_2min >= 60:
            velocity_score = 30  # PLOPPER: 31 txn/min = 62 en 2 min
        elif early_txn_2min >= 50:
            velocity_score = 25  # KATIE: 28 txn/min = 56 en 2 min
        elif early_txn_2min >= 40:
            velocity_score = 20  # INCOG: 20 txn/min = 40 en 2 min (seuil minimum)
        elif early_txn_2min >= 30:
            velocity_score = 15
        elif early_txn_2min >= 20:
            velocity_score = 10
        elif early_txn_2min >= 10:
            velocity_score = 5

        score += velocity_score
        if velocity_score > 0:
            breakdown['velocity_2min'] = velocity_score

        # Points pour traders uniques précoces (0-15 pts)
        early_traders_score = 0
        if early_traders_2min >= 10:
            early_traders_score = 15
        elif early_traders_2min >= 8:
            early_traders_score = 12
        elif early_traders_2min >= 6:
            early_traders_score = 10
        elif early_traders_2min >= 4:
            early_traders_score = 5

        score += early_traders_score
        if early_traders_score > 0:
            breakdown['early_traders'] = early_traders_score

        # Points pour ratio buy/sell précoce (0-15 pts) - PATTERN GAGNANT: 55-60% buys
        buy_ratio_score = 0
        if early_txn_2min >= 20:  # Seulement si activité significative (20+ txn)
            total_early = early_buys + early_sells
            if total_early > 0:
                buy_ratio = early_buys / total_early
                if buy_ratio >= 0.60:  # 60%+ de buys = INCOG niveau (meilleur)
                    buy_ratio_score = 15
                elif buy_ratio >= 0.58:  # 58%+ de buys = KATIE niveau
                    buy_ratio_score = 12
                elif buy_ratio >= 0.55:  # 55%+ de buys = seuil minimum des gagnants
                    buy_ratio_score = 10
                elif buy_ratio >= 0.50:  # 50%+ = PLOPPER niveau (acceptable)
                    buy_ratio_score = 5

        score += buy_ratio_score
        if buy_ratio_score > 0:
            breakdown['buy_ratio'] = buy_ratio_score

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
            'txnCount': 0,  # Will be updated from trades
            'initialBuy': data.get('initialBuy', 0),
            'holderCount': 0,  # Will be updated from unique traders
            'discovered_at': datetime.now(),
            # NOUVEAUX - Tracking vélocité précoce
            'first_2min_txn': 0,
            'first_2min_buys': 0,
            'first_2min_sells': 0,
            'first_2min_traders': set(),
            'first_5min_txn': 0,
        }

        # Initialiser le set de traders uniques
        self.unique_traders[mint] = set()

        total_tokens = len(self.tokens)
        print(f"[NEW] {symbol} @ ${mc_usd:,.0f} (total: {total_tokens})")

        # Subscribe aux trades de ce token
        if self.ws:
            try:
                subscribe_msg = {
                    "method": "subscribeTokenTrade",
                    "keys": [mint]
                }
                await self.ws.send(json.dumps(subscribe_msg))
            except Exception as e:
                print(f"[ERROR] Failed to subscribe to {symbol}: {e}")

    async def handle_trade(self, data):
        """Trade sur un token - MISE A JOUR EN TEMPS REEL avec traders uniques"""
        mint = data.get('mint')
        if not mint or mint not in self.tokens:
            return

        token_info = self.tokens[mint]

        # Calculer le temps écoulé depuis la création
        time_elapsed = (datetime.now() - token_info['discovered_at']).total_seconds()

        # Ajouter le trader au set de traders uniques
        trader = data.get('traderPublicKey')
        if trader:
            self.unique_traders[mint].add(trader)
            # Mettre à jour holderCount = nombre de traders uniques
            token_info['holderCount'] = len(self.unique_traders[mint])

        # Incrémenter le compteur de transactions
        token_info['txnCount'] += 1

        # TRACKING VÉLOCITÉ PRÉCOCE - 2 premières minutes
        if time_elapsed <= 120:  # 2 minutes = 120 secondes
            token_info['first_2min_txn'] += 1
            tx_type = data.get('txType', '')
            if tx_type == 'buy':
                token_info['first_2min_buys'] += 1
            elif tx_type == 'sell':
                token_info['first_2min_sells'] += 1

            # Tracker les traders uniques des 2 premières minutes
            if trader:
                token_info['first_2min_traders'].add(trader)

        # TRACKING VÉLOCITÉ PRÉCOCE - 5 premières minutes
        if time_elapsed <= 300:  # 5 minutes = 300 secondes
            token_info['first_5min_txn'] += 1

        # Mettre à jour le market cap
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * SOL_PRICE_USD if mc_sol else 0
        token_info['mc_usd'] = mc_usd

        # Afficher la watchlist toutes les 30 secondes
        now = datetime.now()
        if (now - self.last_watchlist_display).total_seconds() >= 30:
            self.display_watchlist()

        # Si le token entre dans la fenêtre $7K-$14K
        if OPTIMAL_WINDOW['min_mc'] <= mc_usd <= OPTIMAL_WINDOW['max_mc']:
            # Évaluer si pas encore vu OU si c'était rejeté pour holders insuffisants mais maintenant >= MIN_HOLDERS
            should_evaluate = False

            if mint not in self.seen_in_window:
                should_evaluate = True
                self.seen_in_window.add(mint)
            elif token_info.get('rejected_for_low_holders') and token_info['holderCount'] >= MIN_HOLDERS:
                # Re-évaluer si holders ont augmenté depuis le rejet initial
                should_evaluate = True
                token_info['rejected_for_low_holders'] = False

            if should_evaluate:
                await self.evaluate_token(mint, token_info)

    def display_watchlist(self):
        """Afficher les tokens à surveiller (5-9 traders)"""
        watchlist = []

        for mint, token_info in self.tokens.items():
            holders = token_info['holderCount']
            mc = token_info['mc_usd']

            # Tokens avec 5-9 traders dans la fenêtre de prix
            if 5 <= holders <= 9 and OPTIMAL_WINDOW['min_mc'] <= mc <= OPTIMAL_WINDOW['max_mc']:
                watchlist.append({
                    'symbol': token_info['symbol'],
                    'holders': holders,
                    'mc': mc,
                    'txn': token_info['txnCount'],
                    'mint': mint
                })

        if watchlist:
            # Trier par nombre de traders (descendant)
            watchlist.sort(key=lambda x: x['holders'], reverse=True)

            print(f"\n{'='*80}")
            print(f"WATCHLIST - Tokens en tendance ({len(watchlist)} tokens)")
            print(f"{'='*80}")
            for token in watchlist[:10]:  # Top 10
                print(f"  {token['symbol']:12} | {token['holders']} traders | ${token['mc']:>7,.0f} | {token['txn']} txn")
            print(f"{'='*80}\n")

        self.last_watchlist_display = datetime.now()

    async def evaluate_token(self, mint, token_info):
        """Évaluer un token dans la fenêtre $7K-$14K"""
        mc_usd = token_info['mc_usd']
        symbol = token_info['symbol']
        holders = token_info['holderCount']

        print(f"\n{'='*80}")
        print(f"[TOKEN IN WINDOW] {symbol} @ ${mc_usd:,.0f}")
        print(f"{'='*80}")

        # Filtre volume minimum (market cap = volume pour les tokens récents)
        if mc_usd < MIN_VOLUME_USD:
            print(f"  [X] REJECTED: Volume too low (${mc_usd:,.0f} < ${MIN_VOLUME_USD:,.0f})")
            return

        # Filtre holders minimum (traders uniques)
        if holders < MIN_HOLDERS:
            print(f"  [X] REJECTED: Not enough unique traders ({holders} < {MIN_HOLDERS})")
            # Marquer pour ré-évaluation future quand holders augmentent
            token_info['rejected_for_low_holders'] = True
            return

        # Statistiques vélocité précoce
        early_txn_2min = token_info.get('first_2min_txn', 0)
        early_buys = token_info.get('first_2min_buys', 0)
        early_sells = token_info.get('first_2min_sells', 0)
        early_traders = len(token_info.get('first_2min_traders', set()))

        # Calculer le ratio buy/sell des 2 premières minutes
        early_buy_ratio = 0
        if (early_buys + early_sells) > 0:
            early_buy_ratio = early_buys / (early_buys + early_sells)

        # Scoring
        token_data = {
            'market_cap_usd': mc_usd,
            'txnCount': token_info['txnCount'],
            'initialBuy': token_info['initialBuy'],
            'holderCount': holders,
            'twitter': token_info.get('twitter'),
            'telegram': token_info.get('telegram'),
            'website': token_info.get('website'),
            # Nouvelles métriques vélocité
            'first_2min_txn': early_txn_2min,
            'first_2min_traders_count': early_traders,
            'first_2min_buys': early_buys,
            'first_2min_sells': early_sells,
        }

        score = self.calculate_score(token_data)

        print(f"  Unique Traders: {holders} | Txn: {token_info['txnCount']}")
        print(f"  VÉLOCITÉ PRÉCOCE (2 min): {early_txn_2min} txn | {early_traders} traders | {early_buys}B/{early_sells}S (ratio: {early_buy_ratio:.1%})")
        print(f"  Score: {score['total']}/100 ({score['confidence']})")
        print(f"  Breakdown: {score['breakdown']}")

        if score['should_buy']:
            self.tokens_bought += 1
            print(f"\n  [BUY] BUY SIGNAL! (#{self.tokens_bought})")
            print(f"  Mint: {mint}")
        else:
            print(f"  [X] REJECTED: Score too low ({score['total']} < {SCORE_THRESHOLD})")

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
                    print(f"Min holders: {MIN_HOLDERS} | Score threshold: {SCORE_THRESHOLD}\n")

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
    bot = RobustWebSocketBot()
    await bot.connect_and_run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOPPED] Bot stopped by user")

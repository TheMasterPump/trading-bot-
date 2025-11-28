"""
Script pour créer le bot V3 corrigé avec whale tracking + holders/traders
À partir du bot original qui fonctionne
"""

# Lire le bot original qui fonctionne
with open('pattern_discovery_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ÉTAPE 1: Ajouter le chargement des wallets de baleines
whale_loading_code = '''
# === CHARGEMENT DES WALLETS DE BALEINES ===
WHALE_WALLETS = set()
try:
    import json
    with open('whale_wallets.json', 'r', encoding='utf-8') as f:
        whale_data = json.load(f)
        WHALE_WALLETS = {w['trackedWalletAddress'] for w in whale_data}
    print(f"[WHALE TRACKER] {len(WHALE_WALLETS)} wallets de baleines charges")
except Exception as e:
    print(f"[WARNING] Impossible de charger whale_wallets.json: {e}")
'''

# Insérer après SOL_PRICE_USD = 200
if 'SOL_PRICE_USD = 200' in content:
    content = content.replace(
        'SOL_PRICE_USD = 200',
        'SOL_PRICE_USD = 200\n' + whale_loading_code
    )
else:
    print("[ERROR] Impossible de trouver 'SOL_PRICE_USD = 200'")

# ÉTAPE 2: Ajouter le tracking des wallets dans __init__
init_addition = '''
        self.whale_activity = {}  # {mint: {wallets, volume, timing}}
'''

# Trouver et ajouter avant self.data_file
if "        self.data_file = 'bot_data.json'" in content:
    content = content.replace(
        "        self.data_file = 'bot_data.json'",
        init_addition + "        self.data_file = 'bot_data.json'"
    )
else:
    print("[ERROR] Impossible de trouver self.data_file")

# ÉTAPE 3: Enrichir les données de trade avec whale tracking
old_trade = '''            # Enregistrer le trade
            self.tokens[mint]['trades'].append({
                'time': time.time(),
                'is_buy': is_buy,
                'sol_amount': sol_amount,
                'sol_price_usd': SOL_PRICE_USD,
                'user': user
            })'''

new_trade = '''            # Enregistrer le trade avec whale tracking
            trade_data = {
                'time': time.time(),
                'is_buy': is_buy,
                'sol_amount': sol_amount,
                'sol_price_usd': SOL_PRICE_USD,
                'user': user,
                'value_usd': sol_amount * SOL_PRICE_USD,
                'is_whale': user in WHALE_WALLETS
            }
            self.tokens[mint]['trades'].append(trade_data)

            # Tracker l'activité des baleines
            if user in WHALE_WALLETS:
                if mint not in self.whale_activity:
                    self.whale_activity[mint] = {
                        'wallets': [],
                        'total_volume_usd': 0,
                        'first_whale_entry_time': time.time()
                    }
                if user not in self.whale_activity[mint]['wallets']:
                    self.whale_activity[mint]['wallets'].append(user)
                self.whale_activity[mint]['total_volume_usd'] += sol_amount * SOL_PRICE_USD

                # Log whale entry
                age = time.time() - self.tokens[mint]['created_at']
                mc_usd = data.get('marketCapSol', 0) * SOL_PRICE_USD
                print(f"  [WHALE DETECTED] {self.tokens[mint]['symbol']} @ {age:.0f}s, MC=${mc_usd:,.0f}, {'BUY' if is_buy else 'SELL'} ${sol_amount * SOL_PRICE_USD:.0f}")'''

if old_trade in content:
    content = content.replace(old_trade, new_trade)
else:
    print("[ERROR] Impossible de trouver le code de trade à remplacer")

# ÉTAPE 4: Ajouter les metrics de wallets dans calculate_snapshot
old_snapshot_calc = '''        # Compter les traders uniques
        unique_traders = set(t['user'] for t in trades)'''

new_snapshot_calc = '''        # Compter les traders uniques et analyser les wallets
        unique_traders = set(t['user'] for t in trades)
        whale_trades = [t for t in trades if t.get('is_whale', False)]
        whale_wallets_in_period = set(t['user'] for t in whale_trades if t.get('is_whale', False))
        whale_volume_usd = sum(t.get('value_usd', 0) for t in whale_trades)'''

if old_snapshot_calc in content:
    content = content.replace(old_snapshot_calc, new_snapshot_calc)
else:
    print("[ERROR] Impossible de trouver le calcul de snapshot")

# ÉTAPE 5: Ajouter les metrics whale dans le return du snapshot
old_snapshot_return = '''        return {
            'mc': mc_usd,
            'txn': len(trades),
            'buys': len(buys),
            'sells': len(sells),
            'buy_ratio': len(buys) / len(trades) if trades else 0,
            'traders': len(unique_traders),
            'big_buys_100': big_buys_100,
            'big_buys_500': big_buys_500,
            'buy_volume': total_buy_volume,
            'sell_volume': total_sell_volume,
            'volume_ratio': total_buy_volume / total_sell_volume if total_sell_volume > 0 else 0
        }'''

new_snapshot_return = '''        return {
            'mc': mc_usd,
            'txn': len(trades),
            'buys': len(buys),
            'sells': len(sells),
            'buy_ratio': len(buys) / len(trades) if trades else 0,
            'traders': len(unique_traders),
            'big_buys_100': big_buys_100,
            'big_buys_500': big_buys_500,
            'buy_volume': total_buy_volume,
            'sell_volume': total_sell_volume,
            'volume_ratio': total_buy_volume / total_sell_volume if total_sell_volume > 0 else 0,
            # === NOUVEAUX METRICS WALLETS ===
            'whale_count': len(whale_wallets_in_period),
            'whale_volume_usd': whale_volume_usd,
            'whale_ratio': len(whale_trades) / len(trades) if trades else 0,
            'whale_wallets': list(whale_wallets_in_period)[:10]
        }'''

if old_snapshot_return in content:
    content = content.replace(old_snapshot_return, new_snapshot_return)
else:
    print("[ERROR] Impossible de trouver le return du snapshot")

# ÉTAPE 6: Ajouter la fonction calculate_holders_and_traders
holders_function = '''
    def calculate_holders_and_traders(self, token_data):
        """Calculer les top holders et traders d'un token"""
        trades = token_data.get('trades', [])

        # Dictionnaires pour tracking
        wallet_balances = {}  # {wallet: balance en tokens}
        wallet_volumes = {}   # {wallet: volume total en USD}
        wallet_buy_volume = {}
        wallet_sell_volume = {}

        # Process all trades
        for trade in trades:
            wallet = trade.get('user', '')
            sol_amount = trade.get('sol_amount', 0)
            value_usd = trade.get('value_usd', 0)
            is_buy = trade.get('is_buy', False)

            # Initialiser le wallet s'il n'existe pas
            if wallet not in wallet_balances:
                wallet_balances[wallet] = 0
                wallet_volumes[wallet] = 0
                wallet_buy_volume[wallet] = 0
                wallet_sell_volume[wallet] = 0

            # Mettre à jour le volume
            wallet_volumes[wallet] += value_usd

            if is_buy:
                wallet_balances[wallet] += sol_amount  # Approximation
                wallet_buy_volume[wallet] += value_usd
            else:
                wallet_balances[wallet] -= sol_amount
                wallet_sell_volume[wallet] += value_usd

        # Trier pour obtenir les tops
        top_holders = sorted(
            [(wallet, balance) for wallet, balance in wallet_balances.items() if balance > 0],
            key=lambda x: x[1],
            reverse=True
        )[:10]

        top_traders = sorted(
            [(wallet, volume, wallet_buy_volume[wallet], wallet_sell_volume[wallet])
             for wallet, volume in wallet_volumes.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Calculer la distribution
        total_balance = sum(balance for wallet, balance in wallet_balances.items() if balance > 0)
        top_3_balance = sum(balance for wallet, balance in top_holders[:3])
        top_5_balance = sum(balance for wallet, balance in top_holders[:5])
        top_10_balance = sum(balance for wallet, balance in top_holders[:10])

        return {
            'top_10_holders': [
                {
                    'wallet': wallet,
                    'balance': balance,
                    'is_whale': wallet in WHALE_WALLETS
                }
                for wallet, balance in top_holders
            ],
            'top_10_traders': [
                {
                    'wallet': wallet,
                    'total_volume_usd': volume,
                    'buy_volume_usd': buy_vol,
                    'sell_volume_usd': sell_vol,
                    'buy_sell_ratio': buy_vol / sell_vol if sell_vol > 0 else 0,
                    'is_whale': wallet in WHALE_WALLETS
                }
                for wallet, volume, buy_vol, sell_vol in top_traders
            ],
            'supply_distribution': {
                'total_holders': len([b for b in wallet_balances.values() if b > 0]),
                'top_3_percent': (top_3_balance / total_balance * 100) if total_balance > 0 else 0,
                'top_5_percent': (top_5_balance / total_balance * 100) if total_balance > 0 else 0,
                'top_10_percent': (top_10_balance / total_balance * 100) if total_balance > 0 else 0
            }
        }

'''

# Insérer avant complete_token_analysis
insert_pos = content.find('    def complete_token_analysis(self, mint):')
if insert_pos > 0:
    content = content[:insert_pos] + holders_function + content[insert_pos:]
else:
    print("[ERROR] Impossible de trouver complete_token_analysis")

# ÉTAPE 7: Modifier complete_token_analysis pour ajouter les données whale
old_completion = '''        # Préparer les données pour sauvegarde
        result = {
            'mint': mint,
            'symbol': token_data['symbol'],
            'created_at': token_data['created_at'],
            'mc_initial': token_data['mc_initial'],
            'final_mc': final_mc,
            'is_runner': is_runner,
            'is_flop': is_flop,
            'migration_detected': migration_detected,'''

new_completion = '''        # Calculer holders et traders
        holders_traders_data = self.calculate_holders_and_traders(token_data)

        # Préparer les données pour sauvegarde
        whale_info = self.whale_activity.get(mint, {})
        result = {
            'mint': mint,
            'symbol': token_data['symbol'],
            'created_at': token_data['created_at'],
            'mc_initial': token_data['mc_initial'],
            'final_mc': final_mc,
            'is_runner': is_runner,
            'is_flop': is_flop,
            'migration_detected': migration_detected,
            # === WHALE ACTIVITY ===
            'whale_wallets_detected': whale_info.get('wallets', []),
            'whale_count': len(whale_info.get('wallets', [])),
            'whale_total_volume_usd': whale_info.get('total_volume_usd', 0),
            # === HOLDERS & TRADERS ===
            'top_10_holders': holders_traders_data['top_10_holders'],
            'top_10_traders': holders_traders_data['top_10_traders'],
            'supply_distribution': holders_traders_data['supply_distribution'],'''

if old_completion in content:
    content = content.replace(old_completion, new_completion)
else:
    print("[ERROR] Impossible de trouver le code de completion à remplacer")

# Sauvegarder le nouveau bot V3
with open('pattern_discovery_bot_v3_fixed.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Bot V3 fixed cree avec succes !")
print("Nouvelles fonctionnalites:")
print("  - Tracking de 652 wallets de baleines")
print("  - Detection en temps reel quand une baleine entre")
print("  - Top 10 holders (qui detient le plus)")
print("  - Top 10 traders (qui a le plus trade)")
print("  - Distribution du supply (concentration)")
print("  - Identification des whales parmi holders/traders")
print("  - Toutes les fonctions de completion preservees !")

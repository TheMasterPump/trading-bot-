"""
Script pour ajouter le tracking des wallets au pattern_discovery_bot.py
"""

# Lire le bot actuel
with open('pattern_discovery_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Ajouter l'import et le chargement des wallets de baleines après la ligne SOL_PRICE_USD = 200
whale_loading_code = '''
# === CHARGEMENT DES WALLETS DE BALEINES ===
WHALE_WALLETS = set()
try:
    import json
    with open('whale_wallets.json', 'r', encoding='utf-8') as f:
        whale_data = json.load(f)
        WHALE_WALLETS = {w['trackedWalletAddress'] for w in whale_data}
    print(f"[WHALE TRACKER] {len(WHALE_WALLETS)} wallets de baleines chargés")
except Exception as e:
    print(f"[WARNING] Impossible de charger whale_wallets.json: {e}")
'''

# Insérer après SOL_PRICE_USD = 200
content = content.replace(
    'SOL_PRICE_USD = 200',
    'SOL_PRICE_USD = 200\n' + whale_loading_code
)

# 2. Dans __init__, ajouter le tracking des wallets
init_addition = '''
        self.whale_activity = {}  # {mint: {wallets, volume, timing}}
'''

# Trouver la ligne où on initialise self.data_file et ajouter avant
content = content.replace(
    "        self.data_file = 'bot_data.json'",
    init_addition + "        self.data_file = 'bot_data.json'"
)

# 3. Dans handle_trade, enrichir les données de trade
# Trouver la section où on ajoute le trade et remplacer
old_trade_code = """            # Enregistrer le trade
            self.tokens[mint]['trades'].append({
                'time': time.time(),
                'is_buy': is_buy,
                'sol_amount': sol_amount,
                'sol_price_usd': SOL_PRICE_USD,
                'user': user
            })"""

new_trade_code = """            # Enregistrer le trade avec tracking wallet enrichi
            trade_data = {
                'time': time.time(),
                'is_buy': is_buy,
                'sol_amount': sol_amount,
                'sol_price_usd': SOL_PRICE_USD,
                'user': user,
                'value_usd': sol_amount * SOL_PRICE_USD,
                'is_whale': user in WHALE_WALLETS  # Marquer si c'est une baleine connue
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
                print(f"  [🐋 WHALE DETECTED] {self.tokens[mint]['symbol']} @ {age:.0f}s, MC=${mc_usd:,.0f}, {'BUY' if is_buy else 'SELL'} ${sol_amount * SOL_PRICE_USD:.0f}")"""

content = content.replace(old_trade_code, new_trade_code)

# 4. Dans calculate_snapshot, ajouter les metrics de wallets
old_snapshot_calc = """        # Compter les traders uniques
        unique_traders = set(t['user'] for t in trades)"""

new_snapshot_calc = """        # Compter les traders uniques et analyser les wallets
        unique_traders = set(t['user'] for t in trades)
        whale_trades = [t for t in trades if t.get('is_whale', False)]
        whale_wallets_in_period = set(t['user'] for t in whale_trades if t.get('is_whale', False))
        whale_volume_usd = sum(t.get('value_usd', 0) for t in whale_trades)"""

content = content.replace(old_snapshot_calc, new_snapshot_calc)

# 5. Dans le return du snapshot, ajouter les metrics de wallets
old_snapshot_return = """        return {
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
        }"""

new_snapshot_return = """        return {
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
            'whale_wallets': list(whale_wallets_in_period)[:10]  # Top 10
        }"""

content = content.replace(old_snapshot_return, new_snapshot_return)

# 6. Dans complete_token_analysis, ajouter les données whale_activity
old_completion = """        # Préparer les données pour sauvegarde
        result = {
            'mint': mint,
            'symbol': token_data['symbol'],
            'created_at': token_data['created_at'],
            'mc_initial': token_data['mc_initial'],
            'final_mc': final_mc,
            'is_runner': is_runner,
            'is_flop': is_flop,
            'migration_detected': migration_detected,"""

new_completion = """        # Préparer les données pour sauvegarde
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
            'whale_total_volume_usd': whale_info.get('total_volume_usd', 0),"""

content = content.replace(old_completion, new_completion)

# Sauvegarder le nouveau bot
with open('pattern_discovery_bot_v2.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Bot enrichi créé : pattern_discovery_bot_v2.py")
print("Nouvelles fonctionnalités ajoutées:")
print("  - Chargement de 652 wallets de baleines")
print("  - Détection en temps réel quand une baleine entre")
print("  - Tracking du volume et timing des baleines")
print("  - Metrics enrichis dans les snapshots")
print("  - Données de baleines dans les tokens complétés")

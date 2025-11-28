"""
Script pour restaurer le bot original fonctionnel
en inversant toutes les modifications de whale tracking
"""

# Lire le bot cassé
with open('pattern_discovery_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ========== INVERSER LES MODIFICATIONS ==========

# 1. ENLEVER le chargement des wallets de baleines (lignes 16-25)
whale_loading_to_remove = '''
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

content = content.replace(whale_loading_to_remove, '')

# 2. ENLEVER self.whale_activity dans __init__
content = content.replace(
    "        self.whale_activity = {}  # {mint: {wallets, volume, timing}}\n        self.data_file = 'bot_data.json'",
    "        self.data_file = 'bot_data.json'"
)

# 3. REVENIR au code de trade original (SANS whale tracking)
new_trade_code = '''            # Enregistrer le trade avec whale tracking
            trade_data = {
                'time': current_time,
                'is_buy': is_buy,
                'sol_amount': sol_amount,
                'sol_price_usd': SOL_PRICE_USD,
                'user': user,
                'value_usd': sol_amount * SOL_PRICE_USD,
                'is_whale': user in WHALE_WALLETS
            }
            self.tokens[mint]['trades'].append(trade_data)

            # Tracker l'activite des baleines
            if user in WHALE_WALLETS:
                if mint not in self.whale_activity:
                    self.whale_activity[mint] = {
                        'wallets': [],
                        'total_volume_usd': 0,
                        'first_whale_entry_time': current_time
                    }
                if user not in self.whale_activity[mint]['wallets']:
                    self.whale_activity[mint]['wallets'].append(user)
                self.whale_activity[mint]['total_volume_usd'] += sol_amount * SOL_PRICE_USD

                print(f"  [WHALE DETECTED] {self.tokens[mint]['symbol']} @ {age:.0f}s, MC=${mc_usd:,.0f}, {tx_type.upper()} ${sol_amount * SOL_PRICE_USD:.0f}")'''

# ATTENTION : Le code actuel utilise 'trade_data' différemment
# Cherchons le vrai pattern dans le fichier actuel

# Pour pattern_discovery_bot.py, le code de trade est aux lignes 159-182 environ
old_trade_code_correct = '''            token['trades'].append({
                'type': tx_type,
                'trader': trader,
                'mc': mc_usd,
                'time': current_time,
                'amount_sol': sol_amount,
                'amount_usd': amount_usd,
                'token_amount': token_amount,
                'is_whale': trader in WHALE_WALLETS
            })

            # Tracker l'activite des baleines
            if trader in WHALE_WALLETS:
                if mint not in self.whale_activity:
                    self.whale_activity[mint] = {
                        'wallets': [],
                        'total_volume_usd': 0,
                        'first_whale_entry_time': current_time
                    }
                if trader not in self.whale_activity[mint]['wallets']:
                    self.whale_activity[mint]['wallets'].append(trader)
                self.whale_activity[mint]['total_volume_usd'] += amount_usd

                print(f"  [WHALE DETECTED] {token['symbol']} @ {age:.0f}s, MC=${mc_usd:,.0f}, {tx_type.upper()} ${amount_usd:.0f}")'''

new_trade_code_simple = '''            token['trades'].append({
                'type': tx_type,
                'trader': trader,
                'mc': mc_usd,
                'time': current_time,
                'amount_sol': sol_amount,
                'amount_usd': amount_usd,
                'token_amount': token_amount
            })'''

content = content.replace(old_trade_code_correct, new_trade_code_simple)

# 4. ENLEVER les metrics whale des snapshots
old_snapshot_calc = '''        # Compter les traders uniques et analyser les wallets
        unique_traders = set(t['trader'] for t in trades_in_period)
        whale_trades = [t for t in trades_in_period if t.get('is_whale', False)]
        whale_wallets_in_period = set(t['trader'] for t in whale_trades)
        whale_volume_usd = sum(t.get('amount_usd', 0) for t in whale_trades)'''

new_snapshot_calc = '''        buys = [t for t in trades_in_period if t['type'] == 'buy']
        sells = [t for t in trades_in_period if t['type'] == 'sell']
        unique_traders = len(set(t['trader'] for t in trades_in_period))'''

content = content.replace(old_snapshot_calc, new_snapshot_calc)

# 5. ENLEVER les whale metrics du return de calculate_snapshot
old_whale_metrics = '''        # WHALE METRICS
        whale_trades = [t for t in trades_in_period if t.get('is_whale', False)]
        whale_wallets_in_period = set(t['trader'] for t in whale_trades)
        whale_volume_usd = sum(t.get('amount_usd', 0) for t in whale_trades)

        # WALLET INTELLIGENCE: Comptage des gros achats'''

new_wallet_intelligence = '''        # WALLET INTELLIGENCE: Comptage des gros achats'''

content = content.replace(old_whale_metrics, new_wallet_intelligence)

# 6. Simplifier le return de calculate_snapshot (enlever whale metrics)
content = content.replace(
    '''            'whale_ratio': big_buys_500 / len(buys) if buys else 0,  # % de whales
            # WHALE METRICS
            'whale_count': len(whale_wallets_in_period),
            'whale_volume_usd': whale_volume_usd,
            'whale_trades_ratio': len(whale_trades) / len(trades_in_period) if trades_in_period else 0,
            'whale_wallets': list(whale_wallets_in_period)[:10]''',
    '''            'whale_ratio': big_buys_500 / len(buys) if buys else 0  # % de whales'''
)

# 7. ENLEVER calculate_holders_and_traders complètement
# Trouver le début et la fin de la fonction
start_marker = '    def calculate_holders_and_traders(self, token):'
end_marker = '    def detect_acceleration(self, token, current_mc):'

start_pos = content.find(start_marker)
end_pos = content.find(end_marker)

if start_pos > 0 and end_pos > start_pos:
    content = content[:start_pos] + content[end_pos:]
    print("[INFO] Fonction calculate_holders_and_traders supprimée")

# 8. ENLEVER les appels à calculate_holders_and_traders dans handle_trade

# Dans migration detection (ligne ~221)
content = content.replace(
    '''                # Calculer holders et traders
                holders_traders_data = self.calculate_holders_and_traders(token)
                whale_info = self.whale_activity.get(mint, {})

                # SAUVEGARDER LE TOKEN IMMÉDIATEMENT''',
    '''                # SAUVEGARDER LE TOKEN IMMÉDIATEMENT'''
)

content = content.replace(
    '''                    'migration_detected': True,
                    'migration_price': mc_usd,
                    # === WHALE ACTIVITY ===
                    'whale_wallets_detected': whale_info.get('wallets', []),
                    'whale_count': len(whale_info.get('wallets', [])),
                    'whale_total_volume_usd': whale_info.get('total_volume_usd', 0),
                    # === HOLDERS & TRADERS ===
                    'top_10_holders': holders_traders_data['top_10_holders'],
                    'top_10_traders': holders_traders_data['top_10_traders'],
                    'supply_distribution': holders_traders_data['supply_distribution']''',
    '''                    'migration_detected': True,
                    'migration_price': mc_usd'''
)

# Dans strong runner detection (ligne ~304)
content = content.replace(
    '''                # Calculer holders et traders
                holders_traders_data = self.calculate_holders_and_traders(token)
                whale_info = self.whale_activity.get(mint, {})

                result = {''',
    '''                result = {'''
)

content = content.replace(
    '''                    'early_runner': True,
                    'migration_detected': token['migration_detected'],
                    # === WHALE ACTIVITY ===
                    'whale_wallets_detected': whale_info.get('wallets', []),
                    'whale_count': len(whale_info.get('wallets', [])),
                    'whale_total_volume_usd': whale_info.get('total_volume_usd', 0),
                    # === HOLDERS & TRADERS ===
                    'top_10_holders': holders_traders_data['top_10_holders'],
                    'top_10_traders': holders_traders_data['top_10_traders'],
                    'supply_distribution': holders_traders_data['supply_distribution']''',
    '''                    'early_runner': True,
                    'migration_detected': token['migration_detected']'''
)

# Dans token mort (ligne ~512)
content = content.replace(
    '''                # Calculer holders et traders
                holders_traders_data = self.calculate_holders_and_traders(token)
                whale_info = self.whale_activity.get(mint, {})

                result = {''',
    '''                result = {'''
)

content = content.replace(
    '''                    'death_time': age,
                    'migration_detected': token['migration_detected'],
                    # === WHALE ACTIVITY ===
                    'whale_wallets_detected': whale_info.get('wallets', []),
                    'whale_count': len(whale_info.get('wallets', [])),
                    'whale_total_volume_usd': whale_info.get('total_volume_usd', 0),
                    # === HOLDERS & TRADERS ===
                    'top_10_holders': holders_traders_data['top_10_holders'],
                    'top_10_traders': holders_traders_data['top_10_traders'],
                    'supply_distribution': holders_traders_data['supply_distribution']''',
    '''                    'death_time': age,
                    'migration_detected': token['migration_detected']'''
)

# Sauvegarder le bot restauré
with open('pattern_discovery_bot_RESTORED.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Bot restauré créé : pattern_discovery_bot_RESTORED.py")
print("Ce bot devrait fonctionner correctement (sans whale tracking)")
print("\nProchaines étapes:")
print("1. Tester pattern_discovery_bot_RESTORED.py")
print("2. Si ça fonctionne, réappliquer les modifications whale tracking proprement")

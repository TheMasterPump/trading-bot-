"""
Ajouter le tracking des top holders et top traders au bot v2
"""

# Lire le bot v2
with open('pattern_discovery_bot_v2.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Ajouter une fonction pour calculer les holders et traders
holders_function = '''
    def calculate_holders_and_traders(self, token_data):
        """Calculer les top holders et traders d'un token"""
        trades = token_data.get('trades', [])

        # Dictionnaires pour tracking
        wallet_balances = {}  # {wallet: balance en tokens}
        wallet_volumes = {}   # {wallet: volume total en USD}
        wallet_buy_volume = {}
        wallet_sell_volume = {}

        # Approximation: 1 SOL = X tokens au début
        # On va calculer relativement
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

# Trouver où insérer la fonction (après calculate_snapshot)
insert_position = content.find('    def complete_token_analysis(self, mint):')
if insert_position > 0:
    content = content[:insert_position] + holders_function + '\n' + content[insert_position:]

# 2. Dans complete_token_analysis, appeler la nouvelle fonction et ajouter les données
old_whale_info = '''        # Préparer les données pour sauvegarde
        whale_info = self.whale_activity.get(mint, {})
        result = {'''

new_whale_info = '''        # Calculer holders et traders
        holders_traders_data = self.calculate_holders_and_traders(token_data)

        # Préparer les données pour sauvegarde
        whale_info = self.whale_activity.get(mint, {})
        result = {'''

content = content.replace(old_whale_info, new_whale_info)

# 3. Ajouter les données holders/traders dans le résultat final
old_result_end = '''            # === WHALE ACTIVITY ===
            'whale_wallets_detected': whale_info.get('wallets', []),
            'whale_count': len(whale_info.get('wallets', [])),
            'whale_total_volume_usd': whale_info.get('total_volume_usd', 0),'''

new_result_end = '''            # === WHALE ACTIVITY ===
            'whale_wallets_detected': whale_info.get('wallets', []),
            'whale_count': len(whale_info.get('wallets', [])),
            'whale_total_volume_usd': whale_info.get('total_volume_usd', 0),
            # === HOLDERS & TRADERS ===
            'top_10_holders': holders_traders_data['top_10_holders'],
            'top_10_traders': holders_traders_data['top_10_traders'],
            'supply_distribution': holders_traders_data['supply_distribution'],'''

content = content.replace(old_result_end, new_result_end)

# Sauvegarder le nouveau bot
with open('pattern_discovery_bot_v3.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Bot v3 cree avec succes !")
print("Nouvelles fonctionnalites ajoutees:")
print("  - Top 10 holders (qui detient le plus)")
print("  - Top 10 traders (qui a le plus trade)")
print("  - Distribution du supply (concentration)")
print("  - Identification des whales parmi les holders/traders")

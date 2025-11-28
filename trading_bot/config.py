# Configuration du Trading Bot

# === FILTRES D'ENTREE (Optimaux basés sur analyse) ===
ENTRY_FILTERS = {
    'buy_ratio_min': 50,      # Minimum 50% de buy ratio à 15s
    'transactions_min': 20,   # Minimum 20 transactions à 15s
    'traders_min': 12,        # Minimum 12 traders à 15s
    'big_buys_min': 5,        # Minimum 5 big buys (>$100) à 15s
    'check_at_seconds': 15    # Vérifier les conditions à 15 secondes
}

# === TARGETS DE SORTIE ===
TARGETS = {
    'target_1': 25000,  # Target 1: $25K (+150-200%)
    'target_2': 50000,  # Target 2: $50K (+300-400%)
    'target_3': 69000,  # Target 3: $69K Migration (+500-600%)
}

# Pourcentage à vendre à chaque target
SELL_PERCENTAGES = {
    'target_1': 30,  # Vendre 30% à $25K
    'target_2': 40,  # Vendre 40% à $50K
    'target_3': 30,  # Vendre le reste à $69K
}

# === STOP LOSS ===
STOP_LOSS = {
    'buy_ratio_min': 40,  # Stop si buy ratio < 40%
    'no_volume_seconds': 180,  # Stop si pas de volume pendant 3 minutes
    'max_loss_percent': -30,  # Stop si perte > 30%
}

# === RISK MANAGEMENT ===
RISK_MANAGEMENT = {
    'max_position_size_usd': 100,  # Maximum $100 par position
    'max_concurrent_positions': 3,  # Maximum 3 positions simultanées
    'min_wallet_balance': 50,  # Minimum $50 dans le wallet
}

# === SOLANA WALLET ===
WALLET = {
    'private_key': 'YOUR_PRIVATE_KEY_HERE',  # REMPLACER PAR TA CLEF PRIVEE
    'rpc_url': 'https://api.mainnet-beta.solana.com'
}

# === WEBSOCKET ===
WEBSOCKET_URL = 'wss://pumpportal.fun/api/data'

# === MODE ===
TRADING_MODE = 'PAPER'  # 'PAPER' pour simulation, 'LIVE' pour trading réel

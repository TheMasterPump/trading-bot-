"""
PAYMENT CONFIGURATION
Adresse du wallet qui recevra les paiements d'abonnement
"""
import os

# IMPORTANT: Change cette adresse par TON wallet Solana
# C'est ici que tu recevras tous les paiements des utilisateurs
# Force use of configured wallet address (ignore environment variable)
PAYMENT_WALLET_ADDRESS = '89WT9zM1um2prDXqaGaYPh9KjcrjgNe4n5HYwHHX9ji5'  # Wallet principal pour les paiements
print(f"[payment_config.py] PAYMENT_WALLET_ADDRESS = {PAYMENT_WALLET_ADDRESS}")

# Prix des abonnements (en SOL)
SUBSCRIPTION_PRICES = {
    'RISKY': 1.5,
    'SAFE': 2.0,
    'ULTRA': 3.0
}

# Configuration RPC Solana
SOLANA_RPC_URL = os.environ.get(
    'SOLANA_RPC_URL',
    'https://api.mainnet-beta.solana.com'
)

# Tolérance pour vérifier les montants (pour gérer les frais de transaction)
# Si l'utilisateur envoie 0.149 SOL au lieu de 0.15, on accepte
PAYMENT_TOLERANCE_SOL = 0.005

# Durée de validité d'une demande de paiement (en minutes)
PAYMENT_REQUEST_TIMEOUT = 30

# Note: Pour éviter les erreurs, assure-toi de définir PAYMENT_WALLET_ADDRESS
# dans les variables d'environnement avant de lancer en production
if PAYMENT_WALLET_ADDRESS == 'CHANGE_ME_TO_YOUR_SOLANA_WALLET_ADDRESS':
    print("=" * 80)
    print("WARNING: PAYMENT_WALLET_ADDRESS not configured!")
    print("=" * 80)
    print("Tu dois changer l'adresse dans payment_config.py")
    print("ou definir la variable d'environnement PAYMENT_WALLET_ADDRESS")
    print("=" * 80)

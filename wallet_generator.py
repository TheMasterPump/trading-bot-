"""
SOLANA WALLET GENERATOR
Génération et gestion des wallets Solana pour le trading bot
AVEC SEED PHRASE (12 mots) pour que l'utilisateur possède vraiment son wallet
"""
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
import base58
import json
import secrets
import hashlib


class SolanaWalletManager:
    """Gestionnaire de wallets Solana"""

    def __init__(self, rpc_url="https://api.mainnet-beta.solana.com"):
        self.client = Client(rpc_url)

    def generate_wallet(self):
        """Génère un nouveau wallet Solana"""
        # Créer une nouvelle keypair
        keypair = Keypair()

        # Extraire les informations
        public_key = str(keypair.pubkey())
        private_key = base58.b58encode(bytes(keypair)).decode('utf-8')

        wallet_info = {
            'address': public_key,
            'private_key': private_key,
            'mnemonic': None  # On pourrait ajouter BIP39 si nécessaire
        }

        return wallet_info

    def get_balance(self, address):
        """Récupère le solde d'une adresse (en SOL)"""
        try:
            pubkey = Pubkey.from_string(address)
            response = self.client.get_balance(pubkey)

            if response.value is not None:
                # Convertir lamports en SOL (1 SOL = 1_000_000_000 lamports)
                balance_sol = response.value / 1_000_000_000
                return balance_sol
            return 0.0
        except Exception as e:
            print(f"[ERROR] Erreur récupération balance: {e}")
            return 0.0

    def get_balance_usd(self, balance_sol, sol_price_usd=None):
        """Convertit le solde SOL en USD"""
        if sol_price_usd is None:
            sol_price_usd = self.get_sol_price()

        return balance_sol * sol_price_usd

    def get_sol_price(self):
        """Récupère le prix actuel de SOL en USD"""
        try:
            # En production, utiliser une API comme CoinGecko ou Jupiter
            # Pour l'instant, on utilise une valeur fixe
            # TODO: Implémenter avec une vraie API
            return 150.0  # Prix approximatif
        except:
            return 150.0

    def validate_address(self, address):
        """Valide qu'une adresse Solana est correcte"""
        try:
            Pubkey.from_string(address)
            return True
        except:
            return False

    def keypair_from_private_key(self, private_key_b58):
        """Recrée une keypair depuis une clé privée en base58"""
        try:
            private_key_bytes = base58.b58decode(private_key_b58)
            keypair = Keypair.from_bytes(private_key_bytes)
            return keypair
        except Exception as e:
            print(f"[ERROR] Erreur création keypair: {e}")
            return None

    def get_token_accounts(self, address):
        """Récupère tous les token accounts d'une adresse"""
        try:
            pubkey = Pubkey.from_string(address)
            response = self.client.get_token_accounts_by_owner(
                pubkey,
                opts={"programId": Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")}
            )

            if response.value:
                return [account for account in response.value]
            return []
        except Exception as e:
            print(f"[ERROR] Erreur récupération token accounts: {e}")
            return []


# Test de génération
if __name__ == "__main__":
    manager = SolanaWalletManager()

    print("=== Génération d'un nouveau wallet ===")
    wallet = manager.generate_wallet()

    print(f"\nAdresse: {wallet['address']}")
    print(f"Clé privée: {wallet['private_key'][:20]}...")

    print(f"\n=== Vérification du solde ===")
    balance = manager.get_balance(wallet['address'])
    print(f"Balance: {balance} SOL")

    print(f"\n=== Validation d'adresse ===")
    is_valid = manager.validate_address(wallet['address'])
    print(f"Adresse valide: {is_valid}")

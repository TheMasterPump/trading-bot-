"""
Helper pour créer des instances de SolanaTrader avec différents wallets
Permet à chaque utilisateur d'avoir son propre trader avec sa clé privée
"""
import os


class UserSolanaTrader:
    """Trader Solana pour un utilisateur spécifique"""

    def __init__(self, public_key: str, private_key: str):
        self.public_key = public_key
        self.private_key = private_key
        self.rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        self.api_url = "https://pumpportal.fun/api/trade-local"

        # Détecter le format de la clé privée
        self.private_key_format = self._detect_key_format()

        if not self.private_key_format:
            print(f'[TRADER] ❌ Format de clé privée non reconnu pour {public_key[:8]}...')
            self.enabled = False
        else:
            self.enabled = True
            print(f'[TRADER] ✅ Trader créé pour {public_key[:8]}...{public_key[-8:]}')

    def _detect_key_format(self):
        """Détecte le format de la clé privée (base58, array, ou hex)"""
        key = self.private_key.strip()

        # Format array JSON: [123, 45, 67, ...]
        if key.startswith('[') and key.endswith(']'):
            return 'array'

        # Format base58 (lettres et chiffres, ~88 caractères)
        elif len(key) > 80 and any(c.isalpha() for c in key):
            return 'base58'

        # Format hex (0-9 et a-f uniquement)
        elif all(c in '0123456789abcdefABCDEF' for c in key) and len(key) >= 64:
            return 'hex'

        return None

    def _get_keypair(self):
        """Convertit la clé privée en Keypair selon son format"""
        try:
            from solders.keypair import Keypair
            import json

            if self.private_key_format == 'base58':
                return Keypair.from_base58_string(self.private_key)

            elif self.private_key_format == 'array':
                # Convertir [123, 45, 67, ...] en bytes
                key_array = json.loads(self.private_key)
                key_bytes = bytes(key_array)
                return Keypair.from_bytes(key_bytes)

            elif self.private_key_format == 'hex':
                # Convertir hex en bytes
                key_bytes = bytes.fromhex(self.private_key)
                return Keypair.from_bytes(key_bytes)

            return None
        except Exception as e:
            print(f'[TRADER] ❌ Impossible de charger la clé privée: {e}')
            return None

    def buy_token(self, mint, amount_sol, slippage=25, priority_fee=0.001):
        """
        Achète un token sur PumpFun

        Args:
            mint: Adresse du token à acheter
            amount_sol: Montant en SOL à dépenser
            slippage: Slippage autorisé en % (default: 25%)
            priority_fee: Frais de priorité en SOL (default: 0.001)

        Returns:
            dict: {'success': bool, 'signature': str, 'error': str}
        """
        if not self.enabled:
            return {'success': False, 'error': 'Trader non configuré'}

        try:
            import requests

            # Préparer la requête pour obtenir la transaction
            payload = {
                "publicKey": self.public_key,
                "action": "buy",
                "mint": mint,
                "amount": amount_sol,
                "denominatedInSol": "true",
                "slippage": slippage,
                "priorityFee": priority_fee,
                "pool": "pump"
            }

            print(f'[TRADER] 🛒 Préparation achat: {amount_sol:.4f} SOL sur {mint[:8]}...')

            # Obtenir la transaction sérialisée
            response = requests.post(self.api_url, data=payload, timeout=10)

            if response.status_code != 200:
                error_msg = f'Erreur API: {response.status_code} - {response.text}'
                print(f'[TRADER] ❌ {error_msg}')
                return {'success': False, 'error': error_msg}

            # Importer les bibliothèques Solana
            try:
                from solders.transaction import VersionedTransaction
                from solders.commitment_config import CommitmentLevel
                from solders.rpc.config import RpcSendTransactionConfig
                from solders.rpc.requests import SendVersionedTransaction
            except ImportError:
                error_msg = 'Bibliothèque solders non installée'
                print(f'[TRADER] ❌ {error_msg}')
                return {'success': False, 'error': error_msg}

            # Signer la transaction
            keypair = self._get_keypair()
            if not keypair:
                return {'success': False, 'error': 'Impossible de charger la clé privée'}

            tx = VersionedTransaction(
                VersionedTransaction.from_bytes(response.content).message,
                [keypair]
            )

            # Envoyer la transaction
            commitment = CommitmentLevel.Confirmed
            config = RpcSendTransactionConfig(preflight_commitment=commitment)
            tx_payload = SendVersionedTransaction(tx, config)

            print(f'[TRADER] 📡 Envoi transaction...')
            rpc_response = requests.post(
                url=self.rpc_url,
                headers={"Content-Type": "application/json"},
                data=tx_payload.to_json(),
                timeout=30
            )

            rpc_data = rpc_response.json()

            if 'result' in rpc_data:
                signature = rpc_data['result']
                print(f'[TRADER] ✅ Achat réussi! TX: {signature}')
                return {'success': True, 'signature': signature, 'error': None}
            else:
                error = rpc_data.get('error', 'Erreur inconnue')
                print(f'[TRADER] ❌ Échec: {error}')
                return {'success': False, 'signature': None, 'error': str(error)}

        except Exception as e:
            error_msg = f'Exception: {str(e)}'
            print(f'[TRADER] ❌ Erreur: {error_msg}')
            return {'success': False, 'signature': None, 'error': error_msg}

    def sell_token(self, mint, amount_percent=100, slippage=25, priority_fee=0.001):
        """
        Vend un token sur PumpFun

        Args:
            mint: Adresse du token à vendre
            amount_percent: Pourcentage à vendre (default: 100%)
            slippage: Slippage autorisé en % (default: 25%)
            priority_fee: Frais de priorité en SOL (default: 0.001)

        Returns:
            dict: {'success': bool, 'signature': str, 'error': str}
        """
        if not self.enabled:
            return {'success': False, 'error': 'Trader non configuré'}

        try:
            import requests

            # Préparer la requête
            payload = {
                "publicKey": self.public_key,
                "action": "sell",
                "mint": mint,
                "amount": f"{amount_percent}%",
                "denominatedInSol": "false",
                "slippage": slippage,
                "priorityFee": priority_fee,
                "pool": "pump"
            }

            print(f'[TRADER] 💰 Préparation vente: {amount_percent}% de {mint[:8]}...')

            # Obtenir la transaction sérialisée
            response = requests.post(self.api_url, data=payload, timeout=10)

            if response.status_code != 200:
                error_msg = f'Erreur API: {response.status_code} - {response.text}'
                print(f'[TRADER] ❌ {error_msg}')
                return {'success': False, 'error': error_msg}

            # Importer les bibliothèques Solana
            try:
                from solders.transaction import VersionedTransaction
                from solders.commitment_config import CommitmentLevel
                from solders.rpc.config import RpcSendTransactionConfig
                from solders.rpc.requests import SendVersionedTransaction
            except ImportError:
                error_msg = 'Bibliothèque solders non installée'
                print(f'[TRADER] ❌ {error_msg}')
                return {'success': False, 'error': error_msg}

            # Signer la transaction
            keypair = self._get_keypair()
            if not keypair:
                return {'success': False, 'error': 'Impossible de charger la clé privée'}

            tx = VersionedTransaction(
                VersionedTransaction.from_bytes(response.content).message,
                [keypair]
            )

            # Envoyer la transaction
            commitment = CommitmentLevel.Confirmed
            config = RpcSendTransactionConfig(preflight_commitment=commitment)
            tx_payload = SendVersionedTransaction(tx, config)

            print(f'[TRADER] 📡 Envoi transaction...')
            rpc_response = requests.post(
                url=self.rpc_url,
                headers={"Content-Type": "application/json"},
                data=tx_payload.to_json(),
                timeout=30
            )

            rpc_data = rpc_response.json()

            if 'result' in rpc_data:
                signature = rpc_data['result']
                print(f'[TRADER] ✅ Vente réussie! TX: {signature}')
                return {'success': True, 'signature': signature, 'error': None}
            else:
                error = rpc_data.get('error', 'Erreur inconnue')
                print(f'[TRADER] ❌ Échec: {error}')
                return {'success': False, 'signature': None, 'error': str(error)}

        except Exception as e:
            error_msg = f'Exception: {str(e)}'
            print(f'[TRADER] ❌ Erreur: {error_msg}')
            return {'success': False, 'signature': None, 'error': error_msg}


def create_trader_for_wallet(public_key: str, private_key: str):
    """
    Crée une instance de trader pour un wallet spécifique

    Args:
        public_key: Adresse publique du wallet
        private_key: Clé privée du wallet (déchiffrée)

    Returns:
        UserSolanaTrader ou None si erreur
    """
    trader = UserSolanaTrader(public_key, private_key)

    if not trader.enabled:
        return None

    return trader

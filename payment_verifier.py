"""
PAYMENT VERIFIER - Vérifie les transactions Solana sur la blockchain
"""
import asyncio
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from datetime import datetime, timedelta
from payment_config import PAYMENT_WALLET_ADDRESS, PAYMENT_TOLERANCE_SOL, SOLANA_RPC_URL
from database_bot import db


class PaymentVerifier:
    """Vérifie les paiements sur la blockchain Solana"""

    def __init__(self):
        self.rpc_url = SOLANA_RPC_URL
        self.payment_address = PAYMENT_WALLET_ADDRESS

    async def check_recent_transactions(self, expected_amount_sol, user_wallet_address=None):
        """
        Vérifie si un paiement a été reçu récemment

        Args:
            expected_amount_sol: Montant attendu en SOL
            user_wallet_address: Adresse du wallet de l'utilisateur (optionnel)

        Returns:
            dict avec 'found': bool et 'signature': str si trouvé
        """
        try:
            async with AsyncClient(self.rpc_url) as client:
                # Récupérer la clé publique
                pubkey = Pubkey.from_string(self.payment_address)

                # Récupérer les dernières transactions (limit=20 pour les 20 dernières)
                response = await client.get_signatures_for_address(
                    pubkey,
                    limit=20
                )

                if not response.value:
                    return {'found': False, 'signature': None}

                # Vérifier chaque transaction
                for tx_info in response.value:
                    signature = str(tx_info.signature)

                    # Récupérer les détails de la transaction
                    tx_response = await client.get_transaction(
                        signature,
                        encoding="jsonParsed",
                        max_supported_transaction_version=0
                    )

                    if not tx_response.value:
                        continue

                    tx = tx_response.value.transaction
                    meta = tx_response.value.transaction.meta

                    if not meta:
                        continue

                    # Vérifier les changements de balance
                    pre_balances = meta.pre_balances
                    post_balances = meta.post_balances

                    # Trouver l'index de notre adresse de paiement
                    account_keys = tx.transaction.message.account_keys
                    payment_idx = None

                    for idx, key in enumerate(account_keys):
                        if str(key) == self.payment_address:
                            payment_idx = idx
                            break

                    if payment_idx is None:
                        continue

                    # Calculer le montant reçu
                    amount_lamports = post_balances[payment_idx] - pre_balances[payment_idx]
                    amount_sol = amount_lamports / 1_000_000_000

                    # Vérifier si le montant correspond (avec tolérance)
                    if abs(amount_sol - expected_amount_sol) <= PAYMENT_TOLERANCE_SOL:
                        # Si on cherche un wallet spécifique, vérifier l'expéditeur
                        if user_wallet_address:
                            sender_idx = 0  # L'expéditeur est généralement le premier account
                            sender_address = str(account_keys[sender_idx])

                            if sender_address != user_wallet_address:
                                continue

                        return {
                            'found': True,
                            'signature': signature,
                            'amount_sol': amount_sol,
                            'timestamp': tx_info.block_time
                        }

                return {'found': False, 'signature': None}

        except Exception as e:
            print(f"[ERROR] Erreur vérification paiement: {e}")
            return {'found': False, 'signature': None, 'error': str(e)}

    async def verify_payment_request(self, payment_id):
        """
        Vérifie si un paiement en attente a été effectué

        Args:
            payment_id: ID de la demande de paiement

        Returns:
            dict avec 'verified': bool et 'signature': str si vérifié
        """
        # Récupérer la demande de paiement
        payment = db.get_pending_payment(payment_id)

        if not payment:
            return {'verified': False, 'error': 'Payment not found'}

        # Vérifier si expiré
        expires_at = datetime.fromisoformat(payment['expires_at'])
        if datetime.now() > expires_at:
            db.expire_payment(payment_id)
            return {'verified': False, 'error': 'Payment expired'}

        # Vérifier la transaction
        result = await self.check_recent_transactions(
            expected_amount_sol=payment['amount_sol'],
            user_wallet_address=None  # On accepte de n'importe quelle adresse
        )

        if result['found']:
            # Marquer le paiement comme vérifié
            db.verify_payment(payment_id, result['signature'])
            return {
                'verified': True,
                'signature': result['signature'],
                'amount_sol': result['amount_sol']
            }

        return {'verified': False, 'error': 'Transaction not found'}

    async def auto_verify_payment(self, payment_id, max_attempts=30, interval_seconds=10):
        """
        Vérifie automatiquement un paiement toutes les X secondes

        Args:
            payment_id: ID de la demande de paiement
            max_attempts: Nombre maximum de tentatives
            interval_seconds: Délai entre chaque vérification

        Returns:
            dict avec 'verified': bool
        """
        attempts = 0

        while attempts < max_attempts:
            result = await self.verify_payment_request(payment_id)

            if result['verified']:
                return result

            if 'error' in result and result['error'] == 'Payment expired':
                return result

            attempts += 1
            await asyncio.sleep(interval_seconds)

        return {'verified': False, 'error': 'Timeout - no transaction found'}


# Fonction helper pour utiliser depuis Flask (synchrone)
def verify_payment_sync(payment_id):
    """Vérifie un paiement de manière synchrone (pour Flask)"""
    verifier = PaymentVerifier()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(verifier.verify_payment_request(payment_id))
        return result
    finally:
        loop.close()


if __name__ == "__main__":
    # Test
    print("Testing payment verifier...")
    verifier = PaymentVerifier()

    # Test de vérification
    result = asyncio.run(verifier.check_recent_transactions(0.1))
    print(f"Result: {result}")

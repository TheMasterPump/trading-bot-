"""
FIND MORE WHALE WALLETS
Collecte des wallets de baleines à partir de tokens à succès sur Solana
"""
import json
import httpx
import time
from pathlib import Path
from datetime import datetime
from config import HELIUS_API_KEY, SOLANA_RPC_URL

# Tokens populaires et réussis sur Solana (avec leurs adresses)
POPULAR_TOKENS = {
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "POPCAT": "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",
    "BOME": "ukHH6c7mMyiWCf1b9pnWe25TSpkDDt3H5pQZgZ74J82",
    "MEW": "MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5",
    "SLERF": "7BgBvyjrZX1YKz4oh9mjb8ZScatkkwb8DzFx7LoiVkM3",
    "MYRO": "HhJpBhRRn4g56VsyLuT8DL5Bv31HkXqsrahTTUCZeZg4",
    "WEN": "WENWENvqqNya429ubCdR81ZmD69brwQaaBYY6p3LCpk",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "PYTH": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
}

MIN_SOL_BALANCE = 5.0
MIN_TRANSACTIONS = 50

class WhaleCollector:
    def __init__(self):
        self.client = httpx.Client(timeout=60.0)
        self.found_wallets = []
        self.existing_addresses = set()

    def get_sol_balance(self, wallet_address: str) -> float:
        """Récupère le solde SOL d'un wallet"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [wallet_address]
            }

            response = self.client.post(SOLANA_RPC_URL, json=payload)

            if response.status_code == 200:
                data = response.json()
                lamports = data.get("result", {}).get("value", 0)
                return lamports / 1_000_000_000

            return 0.0

        except Exception:
            return 0.0

    def get_transaction_count(self, wallet_address: str) -> int:
        """Compte le nombre de transactions d'un wallet"""
        try:
            # Utiliser l'API Helius
            url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions"
            params = {
                "api-key": HELIUS_API_KEY,
                "limit": 100
            }

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                transactions = response.json()
                return len(transactions)

            return 0

        except Exception:
            return 0

    def get_token_largest_accounts(self, token_address: str, limit: int = 20) -> list:
        """Récupère les plus gros holders d'un token"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenLargestAccounts",
                "params": [token_address]
            }

            response = self.client.post(SOLANA_RPC_URL, json=payload)

            if response.status_code == 200:
                data = response.json()
                accounts = data.get("result", {}).get("value", [])
                return accounts[:limit]

            return []

        except Exception as e:
            print(f"Error getting largest accounts: {e}")
            return []

    def get_account_owner(self, token_account_address: str) -> str:
        """Récupère le owner d'un token account"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    token_account_address,
                    {"encoding": "jsonParsed"}
                ]
            }

            response = self.client.post(SOLANA_RPC_URL, json=payload)

            if response.status_code == 200:
                data = response.json()
                result = data.get("result", {})

                if result and result.get("value"):
                    parsed_data = result["value"].get("data", {})
                    if isinstance(parsed_data, dict):
                        parsed = parsed_data.get("parsed", {})
                        info = parsed.get("info", {})
                        owner = info.get("owner")
                        return owner

            return None

        except Exception:
            return None

    def collect_from_token(self, token_name: str, token_address: str):
        """Collecte les wallets depuis les holders d'un token"""
        print(f"\n[*] Analyzing {token_name}...", flush=True)

        # Récupérer les plus gros holders
        largest_accounts = self.get_token_largest_accounts(token_address, limit=30)

        if not largest_accounts:
            print(f"  [-] No holders found for {token_name}", flush=True)
            return

        print(f"  [+] Found {len(largest_accounts)} top holders", flush=True)

        valid_count = 0

        for idx, account in enumerate(largest_accounts):
            token_account = account.get("address")

            # Récupérer le owner (wallet address)
            owner = self.get_account_owner(token_account)

            if not owner or owner in self.existing_addresses:
                continue

            # Vérifier le solde SOL
            balance = self.get_sol_balance(owner)

            if balance < MIN_SOL_BALANCE:
                continue

            # Vérifier l'activité
            tx_count = self.get_transaction_count(owner)

            if tx_count < MIN_TRANSACTIONS:
                continue

            # Wallet valide !
            self.found_wallets.append({
                "address": owner,
                "name": f"Whale holder of {token_name}",
                "source": f"Top holder of {token_name}",
                "tokens_held": [token_name],
                "sol_balance": balance,
                "estimated_success_rate": 85,
                "total_transactions": tx_count,
                "notes": f"Top holder with {tx_count} transactions, {balance:.2f} SOL balance",
                "discovered_at": datetime.now().isoformat(),
                "whale_status": True
            })

            self.existing_addresses.add(owner)
            valid_count += 1

            print(f"  [+] Added wallet: {owner[:16]}... (Balance: {balance:.2f} SOL, Txs: {tx_count})", flush=True)

            # Pause pour éviter le rate limit
            time.sleep(0.5)

        print(f"  [+] Added {valid_count} valid wallets from {token_name}", flush=True)

    def load_existing_wallets(self):
        """Charge les wallets existants"""
        wallet_file = Path(__file__).parent / "comprehensive_wallets.json"

        if wallet_file.exists():
            with open(wallet_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing = data.get('wallets', [])
                self.existing_addresses = {w['address'] for w in existing if 'address' in w}
                print(f"[*] Loaded {len(self.existing_addresses)} existing wallets", flush=True)

    def save_new_wallets(self):
        """Sauvegarde les nouveaux wallets"""
        if not self.found_wallets:
            print("\n[!] No new wallets found", flush=True)
            return

        # Charger les wallets existants
        wallet_file = Path(__file__).parent / "comprehensive_wallets.json"

        with open(wallet_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        existing_wallets = data.get('wallets', [])

        # Fusionner
        all_wallets = existing_wallets + self.found_wallets

        # Mettre à jour
        updated_data = {
            "wallets": all_wallets,
            "total": len(all_wallets),
            "last_updated": datetime.now().isoformat(),
            "sources": data.get('sources', []) + [f"Whale collection from popular tokens - {datetime.now().date()}"],
            "stats": {
                **data.get('stats', {}),
                "unique_wallets": len(all_wallets),
                "new_whales_found": len(self.found_wallets)
            }
        }

        # Sauvegarder
        with open(wallet_file, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)

        print(f"\n[+] Saved {len(self.found_wallets)} new wallets", flush=True)
        print(f"[+] Total wallets: {len(all_wallets)}", flush=True)

        # Sauvegarder aussi les nouveaux wallets séparément
        new_wallets_file = Path(__file__).parent / "new_whales_found.json"
        with open(new_wallets_file, 'w', encoding='utf-8') as f:
            json.dump({
                "new_wallets": self.found_wallets,
                "total_found": len(self.found_wallets),
                "collection_date": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)

        print(f"[+] New wallets also saved to: {new_wallets_file}", flush=True)

    def run(self):
        """Lance la collecte"""
        print("\n" + "=" * 70, flush=True)
        print("WHALE WALLET COLLECTOR", flush=True)
        print("=" * 70, flush=True)
        print(f"Minimum SOL balance: {MIN_SOL_BALANCE}", flush=True)
        print(f"Minimum transactions: {MIN_TRANSACTIONS}", flush=True)

        # Charger les wallets existants
        self.load_existing_wallets()

        # Collecter depuis chaque token
        for token_name, token_address in POPULAR_TOKENS.items():
            try:
                self.collect_from_token(token_name, token_address)
                time.sleep(1)  # Pause entre les tokens
            except Exception as e:
                print(f"  [-] Error with {token_name}: {e}", flush=True)
                continue

        # Sauvegarder les résultats
        self.save_new_wallets()

        print("\n" + "=" * 70, flush=True)
        print("COLLECTION COMPLETE!", flush=True)
        print("=" * 70, flush=True)
        print(f"\nNew whales found: {len(self.found_wallets)}", flush=True)

    def close(self):
        """Ferme le client HTTP"""
        self.client.close()


def main():
    collector = WhaleCollector()
    try:
        collector.run()
    finally:
        collector.close()


if __name__ == "__main__":
    main()

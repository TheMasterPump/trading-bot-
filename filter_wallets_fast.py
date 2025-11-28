"""
FILTER WALLETS BY SOL BALANCE - FAST VERSION
Retire les wallets qui ont moins de 5 SOL
"""
import json
import httpx
import sqlite3
import sys
from pathlib import Path
from config import SOLANA_RPC_URL

MIN_SOL_BALANCE = 5.0

def get_sol_balance(wallet_address: str, client: httpx.Client) -> float:
    """Récupère le solde SOL d'un wallet"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [wallet_address]
        }

        response = client.post(SOLANA_RPC_URL, json=payload)

        if response.status_code == 200:
            data = response.json()
            lamports = data.get("result", {}).get("value", 0)
            sol_balance = lamports / 1_000_000_000
            return sol_balance

        return 0.0

    except Exception as e:
        print(f"Error: {e}", flush=True)
        return 0.0

def main():
    print("\n" + "=" * 70, flush=True)
    print("FILTERING WALLETS BY SOL BALANCE", flush=True)
    print("=" * 70, flush=True)
    print(f"Minimum SOL required: {MIN_SOL_BALANCE} SOL\n", flush=True)

    # Charger les wallets
    wallet_file = Path(__file__).parent / "comprehensive_wallets.json"

    with open(wallet_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    wallets = data.get('wallets', [])
    real_wallets = [w for w in wallets if not w['address'].startswith('EXEMPLE')]

    print(f"Total wallets to check: {len(real_wallets)}\n", flush=True)

    valid_wallets = []
    removed_wallets = []

    # Créer un client HTTP réutilisable
    client = httpx.Client(timeout=30.0)

    try:
        for idx, wallet in enumerate(real_wallets, 1):
            address = wallet['address']
            balance = get_sol_balance(address, client)

            if balance >= MIN_SOL_BALANCE:
                valid_wallets.append(wallet)
                symbol = "+"
                status = "KEEP"
            else:
                removed_wallets.append({
                    "address": address,
                    "name": wallet.get('name', 'Unknown'),
                    "balance": balance
                })
                symbol = "-"
                status = "REMOVE"

            # Afficher chaque 10 wallets
            if idx % 10 == 0:
                print(f"[{idx}/{len(real_wallets)}] Progress: {(idx/len(real_wallets))*100:.1f}% - Valid: {len(valid_wallets)}, Removed: {len(removed_wallets)}", flush=True)

    finally:
        client.close()

    print("\n" + "=" * 70, flush=True)
    print("FILTERING COMPLETE", flush=True)
    print("=" * 70, flush=True)
    print(f"\nValid wallets (>= {MIN_SOL_BALANCE} SOL): {len(valid_wallets)}", flush=True)
    print(f"Removed wallets (< {MIN_SOL_BALANCE} SOL): {len(removed_wallets)}", flush=True)

    # Afficher quelques exemples de wallets retirés
    if removed_wallets:
        print("\nExamples of removed wallets:", flush=True)
        for wallet in removed_wallets[:5]:
            print(f"  - {wallet['address'][:16]}... ({wallet['name']}) - {wallet['balance']:.4f} SOL", flush=True)

    # Mettre à jour le fichier JSON
    updated_data = {
        "wallets": valid_wallets,
        "total": len(valid_wallets),
        "last_updated": data.get('last_updated'),
        "filtered_date": "2025-11-08",
        "filter_criteria": f"Minimum {MIN_SOL_BALANCE} SOL balance",
        "sources": data.get('sources', []),
        "stats": {
            **data.get('stats', {}),
            "unique_wallets": len(valid_wallets),
            "removed_low_balance": len(removed_wallets),
            "min_sol_balance": MIN_SOL_BALANCE
        }
    }

    with open(wallet_file, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Updated: {wallet_file}", flush=True)

    # Sauvegarder les wallets retirés
    removed_file = Path(__file__).parent / "removed_wallets_low_balance.json"
    with open(removed_file, 'w', encoding='utf-8') as f:
        json.dump({
            "removed_wallets": removed_wallets,
            "total_removed": len(removed_wallets),
            "filter_criteria": f"Less than {MIN_SOL_BALANCE} SOL",
            "date": "2025-11-08"
        }, f, indent=2, ensure_ascii=False)

    print(f"[+] Saved removed wallets: {removed_file}", flush=True)

    # Mettre à jour la base de données
    print("\n" + "=" * 70, flush=True)
    print("UPDATING DATABASE", flush=True)
    print("=" * 70, flush=True)

    db_file = Path(__file__).parent / "smart_wallets.db"

    if db_file.exists():
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM tracked_wallets')
        count_before = cursor.fetchone()[0]

        valid_addresses_set = set(w['address'] for w in valid_wallets)

        cursor.execute('SELECT wallet_address FROM tracked_wallets')
        all_wallets = [row[0] for row in cursor.fetchall()]

        removed_count = 0
        for wallet in all_wallets:
            if wallet not in valid_addresses_set:
                cursor.execute('DELETE FROM tracked_wallets WHERE wallet_address = ?', (wallet,))
                removed_count += 1

        conn.commit()

        cursor.execute('SELECT COUNT(*) FROM tracked_wallets')
        count_after = cursor.fetchone()[0]

        conn.close()

        print(f"\nWallets before: {count_before}", flush=True)
        print(f"Wallets removed: {removed_count}", flush=True)
        print(f"Wallets after: {count_after}", flush=True)
        print(f"\n[+] Database updated!", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("ALL DONE!", flush=True)
    print("=" * 70, flush=True)
    print(f"\nRemaining wallets: {len(valid_wallets)}", flush=True)
    print(f"All wallets now have at least {MIN_SOL_BALANCE} SOL", flush=True)

if __name__ == "__main__":
    main()

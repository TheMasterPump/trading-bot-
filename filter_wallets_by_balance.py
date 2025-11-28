"""
FILTER WALLETS BY SOL BALANCE
Retire les wallets qui ont moins de 5 SOL (probablement des amis, pas des baleines)
"""
import json
import httpx
import asyncio
import sqlite3
from pathlib import Path
from config import SOLANA_RPC_URL

MIN_SOL_BALANCE = 5.0  # Minimum 5 SOL pour être considéré comme une baleine

def get_sol_balance(wallet_address: str) -> float:
    """Récupère le solde SOL d'un wallet"""
    try:
        client = httpx.Client(timeout=30.0)

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [wallet_address]
        }

        response = client.post(SOLANA_RPC_URL, json=payload)

        if response.status_code == 200:
            data = response.json()
            # Le solde est en lamports (1 SOL = 1,000,000,000 lamports)
            lamports = data.get("result", {}).get("value", 0)
            sol_balance = lamports / 1_000_000_000
            return sol_balance

        return 0.0

    except Exception as e:
        print(f"Error checking balance for {wallet_address[:8]}...: {e}")
        return 0.0
    finally:
        client.close()

def filter_wallets():
    """Filtre les wallets par solde SOL"""

    print("\n" + "=" * 70)
    print("FILTERING WALLETS BY SOL BALANCE")
    print("=" * 70)
    print(f"Minimum SOL required: {MIN_SOL_BALANCE} SOL")

    # Charger les wallets
    wallet_file = Path(__file__).parent / "comprehensive_wallets.json"

    with open(wallet_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    wallets = data.get('wallets', [])

    # Filtrer les wallets d'exemple
    real_wallets = [w for w in wallets if not w['address'].startswith('EXEMPLE')]

    print(f"\nTotal wallets to check: {len(real_wallets)}")

    # Vérifier les soldes
    valid_wallets = []
    removed_wallets = []

    for idx, wallet in enumerate(real_wallets, 1):
        address = wallet['address']

        # Vérifier le solde
        balance = get_sol_balance(address)

        if balance >= MIN_SOL_BALANCE:
            valid_wallets.append(wallet)
            status = "KEEP"
            symbol = "+"
        else:
            removed_wallets.append({
                "address": address,
                "name": wallet.get('name', 'Unknown'),
                "balance": balance
            })
            status = "REMOVE"
            symbol = "-"

        # Afficher la progression
        if idx % 10 == 0 or idx == len(real_wallets):
            print(f"Progress: {idx}/{len(real_wallets)} ({(idx/len(real_wallets))*100:.1f}%) - [{symbol}] {address[:16]}... ({balance:.2f} SOL) - {status}")
        else:
            print(f"[{symbol}] {address[:16]}... ({balance:.2f} SOL) - {status}")

    print("\n" + "=" * 70)
    print("FILTERING COMPLETE")
    print("=" * 70)

    print(f"\nValid wallets (>= {MIN_SOL_BALANCE} SOL): {len(valid_wallets)}")
    print(f"Removed wallets (< {MIN_SOL_BALANCE} SOL): {len(removed_wallets)}")

    # Afficher quelques wallets retirés
    if removed_wallets:
        print("\nExamples of removed wallets:")
        for wallet in removed_wallets[:10]:
            print(f"  - {wallet['address'][:16]}... ({wallet['name']}) - {wallet['balance']:.4f} SOL")

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

    # Sauvegarder
    with open(wallet_file, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Updated: {wallet_file}")

    # Sauvegarder la liste des wallets retirés
    removed_file = Path(__file__).parent / "removed_wallets_low_balance.json"
    with open(removed_file, 'w', encoding='utf-8') as f:
        json.dump({
            "removed_wallets": removed_wallets,
            "total_removed": len(removed_wallets),
            "filter_criteria": f"Less than {MIN_SOL_BALANCE} SOL",
            "date": "2025-11-08"
        }, f, indent=2, ensure_ascii=False)

    print(f"[+] Saved removed wallets list: {removed_file}")

    return valid_wallets, removed_wallets

def update_database(valid_wallet_addresses: list):
    """Met à jour la base de données pour retirer les wallets invalides"""

    print("\n" + "=" * 70)
    print("UPDATING DATABASE")
    print("=" * 70)

    db_file = Path(__file__).parent / "smart_wallets.db"

    if not db_file.exists():
        print("Database not found, skipping...")
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Compter avant
    cursor.execute('SELECT COUNT(*) FROM tracked_wallets')
    count_before = cursor.fetchone()[0]

    # Créer un set des adresses valides
    valid_addresses_set = set(valid_wallet_addresses)

    # Récupérer tous les wallets
    cursor.execute('SELECT wallet_address FROM tracked_wallets')
    all_wallets = [row[0] for row in cursor.fetchall()]

    # Supprimer ceux qui ne sont pas dans la liste valide
    removed_count = 0
    for wallet in all_wallets:
        if wallet not in valid_addresses_set:
            cursor.execute('DELETE FROM tracked_wallets WHERE wallet_address = ?', (wallet,))
            removed_count += 1

    conn.commit()

    # Compter après
    cursor.execute('SELECT COUNT(*) FROM tracked_wallets')
    count_after = cursor.fetchone()[0]

    conn.close()

    print(f"\nWallets before: {count_before}")
    print(f"Wallets removed: {removed_count}")
    print(f"Wallets after: {count_after}")
    print(f"\n[+] Database updated successfully!")

def main():
    """Fonction principale"""

    # Filtrer les wallets
    valid_wallets, removed_wallets = filter_wallets()

    # Mettre à jour la base de données
    valid_addresses = [w['address'] for w in valid_wallets]
    update_database(valid_addresses)

    print("\n" + "=" * 70)
    print("ALL DONE!")
    print("=" * 70)
    print(f"\nYour wallet list has been cleaned!")
    print(f"Remaining wallets: {len(valid_wallets)}")
    print(f"All wallets now have at least {MIN_SOL_BALANCE} SOL")

if __name__ == "__main__":
    main()

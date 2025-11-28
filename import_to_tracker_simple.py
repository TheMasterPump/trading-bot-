"""
IMPORT WALLETS TO TRACKER - VERSION SIMPLIFIEE
Importe tous les wallets dans le système de tracking
"""
import json
import asyncio
from pathlib import Path
from wallet_tracking_system import WalletTrackingSystem

async def import_wallets():
    """Importe tous les wallets dans le tracker"""

    print("\n" + "=" * 70)
    print("IMPORTING WALLETS TO TRACKER")
    print("=" * 70)

    # Charger les wallets
    wallet_file = Path(__file__).parent / "comprehensive_wallets.json"

    with open(wallet_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    wallets = data.get('wallets', [])

    # Filtrer les wallets valides
    real_wallets = [w for w in wallets if not w['address'].startswith('EXEMPLE')]

    print(f"\nFound {len(real_wallets)} wallets to import")

    # Initialiser le tracker
    tracker = WalletTrackingSystem()

    imported = 0
    total = len(real_wallets)

    for idx, wallet in enumerate(real_wallets, 1):
        address = wallet['address']

        # Préparer les données
        wallet_data = {
            'wallet_address': address,
            'total_trades': wallet.get('total_transactions', 100),
            'successful_trades': int(wallet.get('total_transactions', 100) * (wallet.get('estimated_success_rate', 85) / 100)),
            'success_rate': float(wallet.get('estimated_success_rate', 85)),
            'total_profit_usd': wallet.get('total_transactions', 100) * 250,
            'avg_profit_per_trade': 250,
            'biggest_win_multiplier': 12.0 if wallet.get('whale_status') else 8.0,
            'avg_entry_mcap': 40000,
            'avg_hold_time_hours': 5,
            'smart_score': float(wallet.get('estimated_success_rate', 85))
        }

        # Ajouter au tracker
        tracker.add_or_update_wallet(wallet_data)
        imported += 1

        # Afficher la progression
        if idx % 50 == 0 or idx == total:
            print(f"Progress: {idx}/{total} wallets ({(idx/total)*100:.1f}%)")

    print(f"\nSuccessfully imported {imported} wallets!")

    # Afficher les top wallets
    print("\nTop Wallets in Tracker:")
    tracker.display_top_wallets()

    # Fermer le tracker
    await tracker.close()

    print("\n" + "=" * 70)
    print("IMPORT COMPLETE!")
    print("=" * 70)
    print(f"\nTotal wallets actifs: {imported}")
    print("Le systeme va maintenant tracker tous ces wallets 24/7")
    print("Quand un wallet achete un token, vous recevrez une alerte!")

if __name__ == "__main__":
    asyncio.run(import_wallets())

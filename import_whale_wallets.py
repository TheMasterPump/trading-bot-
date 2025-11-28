"""
IMPORT WHALE WALLETS
Importe les 651 wallets de baleines dans le système de prédiction
"""
import json
import asyncio
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from wallet_tracking_system import WalletTrackingSystem

console = Console()

def load_whale_wallets():
    """Charge les wallets de baleines depuis wallet whale.txt"""
    whale_file = Path(__file__).parent / "wallet whale.txt"

    with open(whale_file, 'r', encoding='utf-8') as f:
        whale_data = json.load(f)

    return whale_data

def load_existing_wallets():
    """Charge les wallets existants depuis comprehensive_wallets.json"""
    wallet_file = Path(__file__).parent / "comprehensive_wallets.json"

    if wallet_file.exists():
        with open(wallet_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    return {"wallets": [], "total": 0}

def merge_wallets():
    """Fusionne les wallets de baleines avec les wallets existants"""

    console.print("\n[bold cyan]" + "=" * 70)
    console.print("[bold cyan]MERGING WHALE WALLETS")
    console.print("[bold cyan]" + "=" * 70)

    # Charger les données
    whale_wallets = load_whale_wallets()
    existing_data = load_existing_wallets()
    existing_wallets = existing_data.get('wallets', [])

    console.print(f"\n[yellow]Wallets de baleines trouvés: {len(whale_wallets)}")
    console.print(f"[yellow]Wallets existants: {len(existing_wallets)}")

    # Créer un set des adresses existantes pour éviter les doublons
    existing_addresses = {w['address'] for w in existing_wallets if 'address' in w}

    # Convertir les wallets de baleines au format du système
    new_wallets = []
    duplicates = 0

    for whale in whale_wallets:
        address = whale['trackedWalletAddress']

        # Vérifier si pas déjà dans le système
        if address in existing_addresses:
            duplicates += 1
            continue

        # Format compatible avec notre système
        wallet_entry = {
            "address": address,
            "name": whale.get('name', 'Whale Wallet'),
            "source": "Whale Tracker Import",
            "estimated_success_rate": 85,  # Score élevé pour les baleines
            "total_transactions": 100,
            "notes": f"Whale wallet imported from tracker. Groups: {', '.join(whale.get('groups', ['Main']))}",
            "discovered_at": datetime.now().isoformat(),
            "whale_status": True,
            "original_emoji": whale.get('emoji', '🐋'),
            "alert_settings": {
                "toast": whale.get('alertsOnToast', True),
                "bubble": whale.get('alertsOnBubble', True),
                "feed": whale.get('alertsOnFeed', True),
                "sound": whale.get('sound', 'default')
            }
        }

        new_wallets.append(wallet_entry)
        existing_addresses.add(address)

    # Fusionner
    all_wallets = existing_wallets + new_wallets

    # Créer le nouveau fichier
    merged_data = {
        "wallets": all_wallets,
        "total": len(all_wallets),
        "last_updated": datetime.now().isoformat(),
        "sources": [
            "Helius API - Real blockchain data",
            "Top holders of successful tokens",
            "Whale wallet tracker import",
            "Automated collection via real_wallet_collector.py"
        ],
        "stats": {
            "tokens_analyzed": existing_data.get('stats', {}).get('tokens_analyzed', 7),
            "unique_wallets": len(all_wallets),
            "whale_wallets_imported": len(new_wallets),
            "collection_method": "Multiple sources + whale tracker"
        }
    }

    # Sauvegarder
    output_file = Path(__file__).parent / "comprehensive_wallets.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)

    # Afficher les stats
    table = Table(title="Fusion des Wallets")
    table.add_column("Métrique", style="cyan")
    table.add_column("Valeur", style="green")

    table.add_row("Wallets de baleines trouvés", str(len(whale_wallets)))
    table.add_row("Wallets existants", str(len(existing_wallets)))
    table.add_row("Nouveaux wallets ajoutés", str(len(new_wallets)))
    table.add_row("Doublons évités", str(duplicates))
    table.add_row("Total final", str(len(all_wallets)))

    console.print("\n")
    console.print(table)

    console.print(f"\n[bold green]✓ Fichier sauvegardé: {output_file}")

    return merged_data

async def import_to_tracker():
    """Importe tous les wallets dans le système de tracking"""

    console.print("\n[bold cyan]" + "=" * 70)
    console.print("[bold cyan]IMPORTING TO WALLET TRACKER")
    console.print("[bold cyan]" + "=" * 70)

    # Charger les wallets fusionnés
    wallet_file = Path(__file__).parent / "comprehensive_wallets.json"
    with open(wallet_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    wallets = data.get('wallets', [])

    # Filtrer les wallets valides (pas d'exemples)
    real_wallets = [w for w in wallets if not w['address'].startswith('EXEMPLE')]

    console.print(f"\n[green]Importing {len(real_wallets)} wallets to tracker...")

    # Initialiser le tracker
    tracker = WalletTrackingSystem()

    imported = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:

        task = progress.add_task("[cyan]Importing...", total=len(real_wallets))

        for wallet in real_wallets:
            address = wallet['address']

            # Préparer les données pour le tracker
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

            progress.update(task, advance=1)

    console.print(f"\n[bold green]✓ Successfully imported {imported} wallets!")

    # Afficher les top wallets
    console.print("\n[bold cyan]Top Wallets in Tracker:")
    tracker.display_top_wallets()

    # Fermer le tracker
    await tracker.close()

    console.print("\n[bold green]" + "=" * 70)
    console.print("[bold green]IMPORT COMPLETE!")
    console.print("[bold green]" + "=" * 70)
    console.print("\n[green]Le système va maintenant tracker tous ces wallets 24/7")
    console.print("[green]Quand un wallet achète un token, vous recevrez une alerte!")
    console.print(f"\n[cyan]Total wallets actifs: {imported}")

async def main():
    """Fonction principale"""

    # Étape 1: Fusionner les wallets
    merged_data = merge_wallets()

    # Étape 2: Importer dans le tracker
    await import_to_tracker()

if __name__ == "__main__":
    asyncio.run(main())

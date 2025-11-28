"""
IMPORT WALLETS TO TRACKER
Importe tous les wallets collectes dans le wallet tracking system
"""
import asyncio
import json
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from wallet_tracking_system import WalletTrackingSystem

console = Console()

async def import_all_wallets():
    """Importe tous les wallets du JSON vers le tracker"""

    console.print("\n[bold cyan]" + "=" * 70)
    console.print("[bold cyan]IMPORTING WALLETS TO TRACKER")
    console.print("[bold cyan]" + "=" * 70)

    # Load wallets from JSON
    wallet_file = Path(__file__).parent / "comprehensive_wallets.json"

    if not wallet_file.exists():
        console.print("[red]Error: comprehensive_wallets.json not found!")
        return

    with open(wallet_file, 'r') as f:
        data = json.load(f)

    wallets = data.get('wallets', [])

    # Filter out example wallets
    real_wallets = [w for w in wallets if not w['address'].startswith('EXEMPLE')]

    console.print(f"\n[green]Found {len(real_wallets)} real wallets to import")

    # Initialize tracker
    tracker = WalletTrackingSystem()

    # Import wallets
    imported = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:

        task = progress.add_task("[cyan]Importing wallets...", total=len(real_wallets))

        for wallet in real_wallets:
            address = wallet['address']

            # Prepare wallet data for tracker
            wallet_data = {
                'wallet_address': address,
                'total_trades': wallet.get('total_transactions', 50),
                'successful_trades': int(wallet.get('total_transactions', 50) * 0.75),
                'success_rate': float(wallet.get('estimated_success_rate', 75)),
                'total_profit_usd': wallet.get('total_transactions', 50) * 200,
                'avg_profit_per_trade': 200,
                'biggest_win_multiplier': 10.0,
                'avg_entry_mcap': 50000,
                'avg_hold_time_hours': 6,
                'smart_score': float(wallet.get('estimated_success_rate', 75))
            }

            # Add to tracker
            tracker.add_or_update_wallet(wallet_data)
            imported += 1

            progress.update(task, advance=1)

    console.print(f"\n[bold green]Successfully imported {imported} wallets!")

    # Display stats
    console.print("\n[bold cyan]Wallet Tracker Stats:")
    tracker.display_top_wallets()

    # Close tracker
    await tracker.close()

    console.print("\n[bold green]Import complete!")
    console.print("[green]Le systeme va maintenant tracker tous ces wallets 24/7")
    console.print("[green]Quand un wallet achete un token, vous recevrez une alerte!")


if __name__ == "__main__":
    asyncio.run(import_all_wallets())

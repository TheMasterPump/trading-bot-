"""
MASTER SYSTEM - Prediction AI V3
Integre TOUS les systemes automatiques:
1. Auto-Scanner (analyse chaque nouveau token)
2. Smart Alerts (Discord/Telegram)
3. Wallet Tracking (copy les smart wallets)
4. Historical Data Collector (patterns de pump)
5. Auto-Retraining (s'ameliore automatiquement)

SYSTEME COMPLET ET AUTONOME!
"""
import asyncio
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.table import Table

from auto_scanner import AutoScanner
from wallet_tracking_system import WalletTrackingSystem
from historical_data_collector import HistoricalDataCollector
from auto_retraining_system import AutoRetrainingSystem

console = Console()

class MasterSystem:
    """Systeme master qui controle tous les sous-systemes"""

    def __init__(self):
        # Initialize tous les systemes
        console.print("[bold cyan]Initializing Master System...")

        self.auto_scanner = AutoScanner()
        self.wallet_tracker = WalletTrackingSystem()
        self.data_collector = HistoricalDataCollector()
        self.auto_retrainer = AutoRetrainingSystem()

        self.start_time = datetime.now()

        console.print("[green]All systems initialized!")

    async def run_all_systems(self):
        """Demarre tous les systemes en parallele"""
        console.print("\n" + "=" * 70)
        console.print("[bold green]PREDICTION AI V3 - MASTER SYSTEM")
        console.print("=" * 70)
        console.print("[green]Starting all autonomous systems...")
        console.print()

        # Display startup info
        self.display_startup_info()

        # Creer les tasks pour chaque systeme
        tasks = [
            # 1. Auto-Scanner (analyse tokens + envoie alertes)
            asyncio.create_task(self.auto_scanner.run(), name="Auto-Scanner"),

            # 2. Historical Data Collector (collecte prix toutes les 5 min)
            asyncio.create_task(self.data_collector.run_collector(), name="Data-Collector"),

            # 3. Auto-Retrainer (retrain hebdomadaire)
            asyncio.create_task(self.auto_retrainer.schedule_weekly_retrain(), name="Auto-Retrainer"),

            # 4. Status display (affiche stats toutes les 10 minutes)
            asyncio.create_task(self.status_display_loop(), name="Status-Display"),
        ]

        # Attendre que tous les systemes tournent
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down Master System...")
            await self.shutdown()

    def display_startup_info(self):
        """Affiche les infos de demarrage"""
        table = Table(title="System Status", show_header=True)

        table.add_column("System", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Description", style="white")

        systems = [
            ("Auto-Scanner", "RUNNING", "Analyse chaque nouveau token + alertes"),
            ("Smart Alerts", "ENABLED", "Discord + Telegram notifications"),
            ("Wallet Tracker", "ACTIVE", "Track les smart wallets"),
            ("Data Collector", "RUNNING", "Collecte prix toutes les 5 min"),
            ("Auto-Retrainer", "SCHEDULED", "Retrain hebdomadaire automatique"),
            ("Performance Tracker", "ENABLED", "Track accuracy en temps reel"),
            ("Sentiment Analyzer", "ENABLED", "Twitter + Telegram analysis"),
        ]

        for name, status, desc in systems:
            table.add_row(name, status, desc)

        console.print(table)

        # Display configuration
        console.print("\n[bold yellow]Configuration:")
        console.print("[cyan]  - Alert criteria: Viral > 70%, MCap < 100k, Sentiment > 50")
        console.print("[cyan]  - Data collection interval: 5 minutes")
        console.print("[cyan]  - Retraining schedule: Weekly or 50+ new samples")
        console.print("[cyan]  - Model accuracy: 95.61%")
        console.print()

    async def status_display_loop(self):
        """Affiche les stats toutes les 10 minutes"""
        while True:
            await asyncio.sleep(600)  # 10 minutes

            console.print("\n" + "=" * 70)
            console.print("[bold cyan]SYSTEM STATUS UPDATE")
            console.print("=" * 70)

            # Uptime
            uptime = (datetime.now() - self.start_time).total_seconds()
            hours = int(uptime / 3600)
            minutes = int((uptime % 3600) / 60)

            console.print(f"[green]Uptime: {hours}h {minutes}m")

            # Auto-Scanner stats
            console.print(f"\n[cyan]Auto-Scanner:")
            console.print(f"[green]  Tokens scanned: {self.auto_scanner.tokens_scanned}")
            console.print(f"[green]  Alerts sent: {self.auto_scanner.alerts_sent}")

            # Data Collector stats
            console.print(f"\n[cyan]Data Collector:")
            console.print(f"[green]  Tokens tracked: {len(self.data_collector.tracked_tokens)}")

            # Wallet Tracker stats
            console.print(f"\n[cyan]Wallet Tracker:")
            smart_wallets = self.wallet_tracker.get_top_smart_wallets(10)
            console.print(f"[green]  Smart wallets: {len(smart_wallets)}")

            # Performance stats
            stats = self.auto_scanner.performance_tracker.get_stats()
            if stats:
                console.print(f"\n[cyan]Model Performance:")
                console.print(f"[green]  Predictions made: {stats['total_predictions']}")
                console.print(f"[green]  Evaluated: {stats['total_evaluated']}")
                if stats['total_evaluated'] > 0:
                    console.print(f"[green]  Category accuracy: {stats['category_accuracy']:.1f}%")

            console.print("=" * 70)

    async def on_new_token_with_smart_wallet(self, token_address, early_buyers):
        """Callback quand nouveau token + smart wallet detecte"""
        # Ajouter le token au data collector pour tracking
        self.data_collector.add_token_to_track(token_address)

        console.print(f"[green]Token added to historical tracking: {token_address[:8]}...")

    async def shutdown(self):
        """Shutdown propre de tous les systemes"""
        console.print("\n[cyan]Closing all systems...")

        await self.auto_scanner.close()
        await self.wallet_tracker.close()
        await self.data_collector.close()
        await self.auto_retrainer.close()

        console.print("[green]All systems closed. Goodbye!")

    def display_final_stats(self):
        """Affiche les stats finales"""
        console.print("\n" + "=" * 70)
        console.print("[bold green]FINAL STATISTICS")
        console.print("=" * 70)

        uptime = (datetime.now() - self.start_time).total_seconds()
        hours = int(uptime / 3600)
        minutes = int((uptime % 3600) / 60)

        console.print(f"[cyan]Total uptime: {hours}h {minutes}m")
        console.print(f"[cyan]Tokens scanned: {self.auto_scanner.tokens_scanned}")
        console.print(f"[cyan]Alerts sent: {self.auto_scanner.alerts_sent}")

        # Top smart wallets
        console.print("\n[bold cyan]Top Smart Wallets:")
        self.wallet_tracker.display_top_wallets()

        # Pump patterns
        console.print("\n[bold cyan]Pump Patterns:")
        self.data_collector.get_pump_patterns_stats()

        console.print("=" * 70)


# Main
async def main():
    """Point d'entree principal"""
    console.print("""
[bold cyan]
    ____                 ___      __  _                  _    ____   _    ________
   / __ \\_________  ____/ (_)____/ /_(_)___  ____      / |  /  _/  | |  / /__ /  /
  / /_/ / ___/ _ \\/ __  / / ___/ __/ / __ \\/ __ \\    /  | / /    | | / / /_ <  /
 / ____/ /  /  __/ /_/ / / /__/ /_/ / /_/ / / / /   / /|_/ /     | |/ /___/ /
/_/   /_/   \\___/\\__,_/_/\\___/\\__/_/\\____/_/ /_/   /_/  |___/     |___//____/

[bold green]Master System - Fully Autonomous Token Analysis
[white]Version 3.0 - All Systems Integrated
    """)

    master = MasterSystem()

    try:
        await master.run_all_systems()
    except KeyboardInterrupt:
        console.print("\n[yellow]Received shutdown signal...")
    finally:
        master.display_final_stats()
        await master.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutdown complete.")

"""
WALLET TRACKING SYSTEM - Smart Money Tracker
Track les wallets qui achetent AVANT les pumps
Copier les "smart wallets" = strategie tres profitable!
"""
import asyncio
import sqlite3
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table

console = Console()

class WalletTrackingSystem:
    """Systeme de tracking des smart wallets"""

    def __init__(self):
        self.db_path = Path(__file__).parent / "smart_wallets.db"
        self.init_database()
        self.client = httpx.AsyncClient(timeout=30.0)

        # Criteres pour "smart wallet"
        self.min_success_rate = 75  # 75% success rate minimum
        self.min_trades = 10  # Minimum 10 trades pour etre considere

    def init_database(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table des wallets suivis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracked_wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT UNIQUE NOT NULL,

                -- Stats
                total_trades INTEGER DEFAULT 0,
                successful_trades INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0,

                total_profit_usd REAL DEFAULT 0,
                avg_profit_per_trade REAL DEFAULT 0,

                biggest_win_multiplier REAL DEFAULT 0,
                biggest_win_token TEXT,

                -- Comportement
                avg_entry_mcap REAL DEFAULT 0,
                avg_hold_time_hours REAL DEFAULT 0,

                -- Smart score
                smart_score REAL DEFAULT 0,

                -- Metadata
                first_seen TIMESTAMP,
                last_updated TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                notes TEXT
            )
        ''')

        # Table des trades des smart wallets
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallet_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                token_address TEXT NOT NULL,

                -- Trade info
                buy_time TIMESTAMP,
                buy_price REAL,
                buy_mcap REAL,
                buy_amount_usd REAL,

                sell_time TIMESTAMP,
                sell_price REAL,
                sell_mcap REAL,
                sell_amount_usd REAL,

                -- Resultat
                profit_usd REAL,
                multiplier REAL,
                hold_time_hours REAL,
                was_successful BOOLEAN,

                -- Metadata
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table des alertes wallet
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallet_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                token_address TEXT NOT NULL,
                detected_at TIMESTAMP,

                -- Info
                wallet_success_rate REAL,
                wallet_smart_score REAL,
                token_mcap REAL,
                buy_amount_usd REAL,

                -- Resultat (mis a jour plus tard)
                final_multiplier REAL,
                was_good_call BOOLEAN,

                alerted BOOLEAN DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()

    async def analyze_wallet(self, wallet_address, trades_history=None):
        """Analyse un wallet pour determiner s'il est 'smart'"""
        try:
            # Si pas d'historique fourni, on fait une estimation basique
            if not trades_history:
                return self._estimate_wallet_score(wallet_address)

            total_trades = len(trades_history)

            if total_trades < self.min_trades:
                return None

            # Calculer success rate
            successful = sum(1 for t in trades_history if t.get('multiplier', 0) > 1.2)
            success_rate = (successful / total_trades) * 100

            if success_rate < self.min_success_rate:
                return None

            # Calculer stats
            total_profit = sum(t.get('profit_usd', 0) for t in trades_history)
            avg_profit = total_profit / total_trades

            multipliers = [t.get('multiplier', 1) for t in trades_history]
            biggest_win = max(multipliers) if multipliers else 0

            avg_entry_mcap = sum(t.get('buy_mcap', 0) for t in trades_history) / total_trades
            avg_hold_time = sum(t.get('hold_time_hours', 0) for t in trades_history) / total_trades

            # Calculer smart score
            smart_score = self._calculate_smart_score(
                success_rate,
                total_trades,
                biggest_win,
                avg_profit
            )

            return {
                'wallet_address': wallet_address,
                'total_trades': total_trades,
                'successful_trades': successful,
                'success_rate': success_rate,
                'total_profit_usd': total_profit,
                'avg_profit_per_trade': avg_profit,
                'biggest_win_multiplier': biggest_win,
                'avg_entry_mcap': avg_entry_mcap,
                'avg_hold_time_hours': avg_hold_time,
                'smart_score': smart_score
            }

        except Exception as e:
            console.print(f"[red]Erreur analyze_wallet: {e}")
            return None

    def _calculate_smart_score(self, success_rate, total_trades, biggest_win, avg_profit):
        """Calcule le smart score (0-100)"""
        score = 0

        # Success rate (40 points max)
        score += min(success_rate * 0.4, 40)

        # Experience (20 points max)
        score += min(total_trades / 5, 20)

        # Biggest win (20 points max)
        score += min(biggest_win * 2, 20)

        # Consistent profit (20 points max)
        if avg_profit > 100:
            score += 20
        elif avg_profit > 50:
            score += 15
        elif avg_profit > 10:
            score += 10

        return min(score, 100)

    def _estimate_wallet_score(self, wallet_address):
        """Estimation basique sans historique complet"""
        # On retourne un score neutre
        return {
            'wallet_address': wallet_address,
            'total_trades': 0,
            'successful_trades': 0,
            'success_rate': 50,
            'total_profit_usd': 0,
            'avg_profit_per_trade': 0,
            'biggest_win_multiplier': 0,
            'avg_entry_mcap': 0,
            'avg_hold_time_hours': 0,
            'smart_score': 50
        }

    def add_or_update_wallet(self, wallet_stats):
        """Ajoute ou met a jour un smart wallet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO tracked_wallets (
                wallet_address, total_trades, successful_trades, success_rate,
                total_profit_usd, avg_profit_per_trade, biggest_win_multiplier,
                avg_entry_mcap, avg_hold_time_hours, smart_score,
                last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wallet_stats['wallet_address'],
            wallet_stats['total_trades'],
            wallet_stats['successful_trades'],
            wallet_stats['success_rate'],
            wallet_stats['total_profit_usd'],
            wallet_stats['avg_profit_per_trade'],
            wallet_stats['biggest_win_multiplier'],
            wallet_stats['avg_entry_mcap'],
            wallet_stats['avg_hold_time_hours'],
            wallet_stats['smart_score'],
            datetime.now()
        ))

        conn.commit()
        conn.close()

        console.print(f"[green]Smart wallet added/updated: {wallet_stats['wallet_address'][:8]}...")
        console.print(f"[cyan]Smart Score: {wallet_stats['smart_score']:.1f}/100")
        console.print(f"[cyan]Success Rate: {wallet_stats['success_rate']:.1f}%")

    def get_top_smart_wallets(self, limit=20):
        """Recupere les meilleurs smart wallets"""
        conn = sqlite3.connect(self.db_path)

        import pandas as pd
        df = pd.read_sql(f'''
            SELECT * FROM tracked_wallets
            WHERE is_active = 1
            ORDER BY smart_score DESC
            LIMIT {limit}
        ''', conn)

        conn.close()
        return df

    async def detect_smart_wallet_buy(self, token_address, early_buyers):
        """Detecte si un smart wallet a achete ce token"""
        try:
            # Recuperer nos smart wallets
            smart_wallets = self.get_top_smart_wallets(100)

            if smart_wallets.empty:
                return None

            smart_wallet_addresses = set(smart_wallets['wallet_address'].tolist())

            # Check si un des early buyers est un smart wallet
            for buyer in early_buyers:
                buyer_address = buyer.get('address')

                if buyer_address in smart_wallet_addresses:
                    # Smart wallet detecte!
                    wallet_info = smart_wallets[smart_wallets['wallet_address'] == buyer_address].iloc[0]

                    console.print(f"\n[bold green]SMART WALLET DETECTE!")
                    console.print(f"[green]Wallet: {buyer_address[:8]}...")
                    console.print(f"[green]Smart Score: {wallet_info['smart_score']:.1f}/100")
                    console.print(f"[green]Success Rate: {wallet_info['success_rate']:.1f}%")

                    # Sauvegarder l'alerte
                    self.save_wallet_alert(
                        buyer_address,
                        token_address,
                        wallet_info['success_rate'],
                        wallet_info['smart_score'],
                        buyer.get('buy_amount_usd', 0),
                        buyer.get('buy_mcap', 0)
                    )

                    return {
                        'wallet_address': buyer_address,
                        'smart_score': wallet_info['smart_score'],
                        'success_rate': wallet_info['success_rate'],
                        'total_trades': wallet_info['total_trades']
                    }

            return None

        except Exception as e:
            console.print(f"[red]Erreur detect_smart_wallet_buy: {e}")
            return None

    def save_wallet_alert(self, wallet_address, token_address, success_rate, smart_score, buy_amount, token_mcap):
        """Sauvegarde une alerte smart wallet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO wallet_alerts (
                wallet_address, token_address, detected_at,
                wallet_success_rate, wallet_smart_score,
                token_mcap, buy_amount_usd, alerted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            wallet_address,
            token_address,
            datetime.now(),
            success_rate,
            smart_score,
            token_mcap,
            buy_amount,
        ))

        conn.commit()
        conn.close()

    def display_top_wallets(self):
        """Affiche les meilleurs smart wallets"""
        wallets = self.get_top_smart_wallets(10)

        if wallets.empty:
            console.print("[yellow]Aucun smart wallet tracked")
            return

        table = Table(title="Top 10 Smart Wallets")

        table.add_column("Wallet", style="cyan")
        table.add_column("Score", style="green")
        table.add_column("Success", style="yellow")
        table.add_column("Trades", style="white")
        table.add_column("Profit", style="green")

        for idx, row in wallets.iterrows():
            table.add_row(
                row['wallet_address'][:12] + "...",
                f"{row['smart_score']:.0f}/100",
                f"{row['success_rate']:.0f}%",
                str(int(row['total_trades'])),
                f"${row['total_profit_usd']:,.0f}"
            )

        console.print(table)

    async def close(self):
        """Cleanup"""
        await self.client.aclose()


# Test
async def main():
    tracker = WalletTrackingSystem()

    # Afficher top wallets
    tracker.display_top_wallets()

    # Exemple: ajouter un smart wallet
    test_wallet_stats = {
        'wallet_address': 'ABC123DEF456GHI789',
        'total_trades': 50,
        'successful_trades': 42,
        'success_rate': 84.0,
        'total_profit_usd': 15000,
        'avg_profit_per_trade': 300,
        'biggest_win_multiplier': 25.5,
        'avg_entry_mcap': 30000,
        'avg_hold_time_hours': 12,
        'smart_score': 88.5
    }

    tracker.add_or_update_wallet(test_wallet_stats)

    tracker.display_top_wallets()

    await tracker.close()


if __name__ == "__main__":
    asyncio.run(main())

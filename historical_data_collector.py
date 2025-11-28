"""
HISTORICAL DATA COLLECTOR
Collecte les donnees de prix toutes les 5 minutes
Ameliore le price predictor avec des vraies donnees de pump patterns
"""
import asyncio
import sqlite3
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
import pandas as pd

console = Console()

class HistoricalDataCollector:
    """Collecteur de donnees historiques"""

    def __init__(self):
        self.db_path = Path(__file__).parent / "price_history.db"
        self.init_database()
        self.client = httpx.AsyncClient(timeout=30.0)

        # Tokens a suivre (ajoutés dynamiquement)
        self.tracked_tokens = set()

    def init_database(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table des prix historiques
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,

                -- Prix et market cap
                price_usd REAL,
                market_cap_usd REAL,
                liquidity_usd REAL,

                -- Volume
                volume_5m REAL,
                volume_1h REAL,
                volume_24h REAL,

                -- Trading
                txns_5m INTEGER,
                buys_5m INTEGER,
                sells_5m INTEGER,

                -- Change
                price_change_5m REAL,
                price_change_1h REAL,

                -- Holder stats
                holder_count INTEGER,

                -- Metadata
                still_exists BOOLEAN DEFAULT 1,
                is_rugged BOOLEAN DEFAULT 0
            )
        ''')

        # Index pour performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_token_time ON price_snapshots(token_address, timestamp)')

        # Table des pump patterns detectés
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pump_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,

                -- Detection
                pump_detected_at TIMESTAMP,
                pump_start_price REAL,
                pump_start_mcap REAL,

                -- Peak
                peak_time TIMESTAMP,
                peak_price REAL,
                peak_mcap REAL,
                peak_multiplier REAL,

                -- Dump (si arrive)
                dump_time TIMESTAMP,
                dump_price REAL,
                dump_multiplier_from_peak REAL,

                -- Pattern stats
                pump_duration_minutes INTEGER,
                pump_volume_total REAL,
                max_price_spike_5m REAL,

                -- Classification
                pattern_type TEXT,  -- fast_pump, slow_pump, pump_dump, sustained
                was_sustainable BOOLEAN
            )
        ''')

        conn.commit()
        conn.close()

    def add_token_to_track(self, token_address):
        """Ajoute un token a suivre"""
        if token_address not in self.tracked_tokens:
            self.tracked_tokens.add(token_address)
            console.print(f"[green]Tracking {token_address[:8]}...")

    async def collect_snapshot(self, token_address):
        """Collecte un snapshot des donnees actuelles"""
        try:
            # Fetch data from DexScreener
            response = await self.client.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            )

            if response.status_code != 200:
                return False

            data = response.json()
            pairs = data.get('pairs', [])

            if not pairs:
                # Token n'existe plus ou a été rug
                self.mark_token_rugged(token_address)
                return False

            pair = pairs[0]

            # Extract data
            price = float(pair.get('priceUsd', 0))
            mcap = float(pair.get('marketCap', 0))
            liquidity = float(pair.get('liquidity', {}).get('usd', 0))

            volume_5m = float(pair.get('volume', {}).get('m5', 0) or 0)
            volume_1h = float(pair.get('volume', {}).get('h1', 0) or 0)
            volume_24h = float(pair.get('volume', {}).get('h24', 0) or 0)

            txns = pair.get('txns', {}).get('m5', {})
            txns_5m = txns.get('buys', 0) + txns.get('sells', 0)
            buys_5m = txns.get('buys', 0)
            sells_5m = txns.get('sells', 0)

            price_change_5m = float(pair.get('priceChange', {}).get('m5', 0) or 0)
            price_change_1h = float(pair.get('priceChange', {}).get('h1', 0) or 0)

            # Save snapshot
            self.save_snapshot(
                token_address,
                price,
                mcap,
                liquidity,
                volume_5m,
                volume_1h,
                volume_24h,
                txns_5m,
                buys_5m,
                sells_5m,
                price_change_5m,
                price_change_1h
            )

            # Check for pump pattern
            self.detect_pump_pattern(token_address)

            return True

        except Exception as e:
            console.print(f"[red]Erreur collect_snapshot: {e}")
            return False

    def save_snapshot(self, token_address, price, mcap, liquidity, vol_5m, vol_1h, vol_24h,
                     txns_5m, buys_5m, sells_5m, change_5m, change_1h):
        """Sauvegarde un snapshot"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO price_snapshots (
                token_address, timestamp, price_usd, market_cap_usd, liquidity_usd,
                volume_5m, volume_1h, volume_24h, txns_5m, buys_5m, sells_5m,
                price_change_5m, price_change_1h
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            token_address, datetime.now(), price, mcap, liquidity,
            vol_5m, vol_1h, vol_24h, txns_5m, buys_5m, sells_5m,
            change_5m, change_1h
        ))

        conn.commit()
        conn.close()

    def mark_token_rugged(self, token_address):
        """Marque un token comme rugged"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE price_snapshots
            SET is_rugged = 1, still_exists = 0
            WHERE token_address = ?
        ''', (token_address,))

        conn.commit()
        conn.close()

        # Retirer du tracking
        if token_address in self.tracked_tokens:
            self.tracked_tokens.remove(token_address)

        console.print(f"[red]Token rugged: {token_address[:8]}...")

    def detect_pump_pattern(self, token_address):
        """Detecte un pattern de pump"""
        try:
            conn = sqlite3.connect(self.db_path)

            # Get last 24 snapshots (2 hours de data a 5min intervals)
            df = pd.read_sql(f'''
                SELECT * FROM price_snapshots
                WHERE token_address = ?
                ORDER BY timestamp DESC
                LIMIT 24
            ''', conn, params=(token_address,))

            conn.close()

            if len(df) < 6:  # Need au moins 30 min de data
                return

            # Calculer le max price spike
            prices = df['price_usd'].tolist()
            max_price = max(prices)
            min_price = min(prices)

            if min_price > 0:
                multiplier = max_price / min_price

                # Pump detecte si >2x en 2h
                if multiplier > 2.0:
                    self.save_pump_pattern(token_address, df, multiplier)

        except Exception as e:
            console.print(f"[red]Erreur detect_pump_pattern: {e}")

    def save_pump_pattern(self, token_address, df, multiplier):
        """Sauvegarde un pump pattern"""
        try:
            # Trouver le start et peak
            start_row = df.iloc[-1]  # Plus ancien
            peak_idx = df['price_usd'].idxmax()
            peak_row = df.loc[peak_idx]

            # Calculer duration
            start_time = pd.to_datetime(start_row['timestamp'])
            peak_time = pd.to_datetime(peak_row['timestamp'])
            duration_minutes = (peak_time - start_time).total_seconds() / 60

            # Total volume
            total_volume = df['volume_5m'].sum()

            # Max price spike in 5m
            max_spike = df['price_change_5m'].max()

            # Pattern type
            if duration_minutes < 30 and multiplier > 5:
                pattern_type = "fast_pump"
            elif duration_minutes < 60:
                pattern_type = "slow_pump"
            elif max_spike > 100:
                pattern_type = "pump_dump"
            else:
                pattern_type = "sustained"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO pump_patterns (
                    token_address, pump_detected_at,
                    pump_start_price, pump_start_mcap,
                    peak_time, peak_price, peak_mcap, peak_multiplier,
                    pump_duration_minutes, pump_volume_total,
                    max_price_spike_5m, pattern_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                token_address,
                datetime.now(),
                start_row['price_usd'],
                start_row['market_cap_usd'],
                peak_time,
                peak_row['price_usd'],
                peak_row['market_cap_usd'],
                multiplier,
                duration_minutes,
                total_volume,
                max_spike,
                pattern_type
            ))

            conn.commit()
            conn.close()

            console.print(f"\n[bold green]PUMP PATTERN DETECTE!")
            console.print(f"[green]Token: {token_address[:8]}...")
            console.print(f"[green]Multiplier: {multiplier:.1f}x")
            console.print(f"[green]Type: {pattern_type}")
            console.print(f"[green]Duration: {duration_minutes:.0f} minutes")

        except Exception as e:
            console.print(f"[red]Erreur save_pump_pattern: {e}")

    async def run_collector(self):
        """Collecte les donnees en boucle"""
        console.print("[bold green]HISTORICAL DATA COLLECTOR STARTED")
        console.print("[green]Collecting snapshots every 5 minutes...")

        while True:
            try:
                if len(self.tracked_tokens) == 0:
                    console.print("[yellow]No tokens to track")
                else:
                    console.print(f"\n[cyan]Collecting data for {len(self.tracked_tokens)} tokens...")

                    for token_address in list(self.tracked_tokens):
                        success = await self.collect_snapshot(token_address)

                        if success:
                            console.print(f"[green]Snapshot saved: {token_address[:8]}...")

                        await asyncio.sleep(1)  # Rate limiting

                # Wait 5 minutes
                await asyncio.sleep(300)

            except Exception as e:
                console.print(f"[red]Erreur collector loop: {e}")
                await asyncio.sleep(60)

    def get_pump_patterns_stats(self):
        """Stats des pump patterns detectes"""
        conn = sqlite3.connect(self.db_path)

        df = pd.read_sql('SELECT * FROM pump_patterns', conn)

        conn.close()

        if df.empty:
            console.print("[yellow]Aucun pump pattern detecte")
            return

        console.print(f"\n[bold cyan]PUMP PATTERNS STATS")
        console.print(f"[cyan]Total patterns: {len(df)}")
        console.print(f"[cyan]Avg multiplier: {df['peak_multiplier'].mean():.1f}x")
        console.print(f"[cyan]Max multiplier: {df['peak_multiplier'].max():.1f}x")
        console.print(f"[cyan]Avg duration: {df['pump_duration_minutes'].mean():.0f} min")

        # Par type
        console.print("\n[cyan]Par type:")
        type_counts = df['pattern_type'].value_counts()
        for ptype, count in type_counts.items():
            console.print(f"[cyan]  {ptype}: {count}")

    async def close(self):
        """Cleanup"""
        await self.client.aclose()


# Main
async def main():
    collector = HistoricalDataCollector()

    # Exemple: tracker quelques tokens
    test_tokens = [
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC (stable, pour test)
    ]

    for token in test_tokens:
        collector.add_token_to_track(token)

    # Run collector
    try:
        await collector.run_collector()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping collector...")
        collector.get_pump_patterns_stats()
    finally:
        await collector.close()


if __name__ == "__main__":
    asyncio.run(main())

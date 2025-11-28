"""
RUNNER TRAINING DATA COLLECTOR
Collecte les donnees temporelles des tokens pour entrainer l'IA a detecter les runners
Objectif: Apprendre quels tokens vont "run" avant et apres migration
"""

import asyncio
import httpx
import json
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class TokenSnapshot:
    """Snapshot d'un token a un moment donne"""
    mint: str
    timestamp: str
    age_minutes: float

    # Price/Market data
    market_cap: float
    price_usd: float
    price_change_5m: float
    price_change_1h: float

    # Volume
    volume_5m: float
    volume_1h: float
    volume_24h: float

    # Holders
    holder_count: int
    holder_growth_rate: float  # % change depuis dernier snapshot

    # Transactions
    txn_count_5m: int
    buy_count_5m: int
    sell_count_5m: int
    buy_sell_ratio: float

    # Bonding curve (PumpFun specific)
    bonding_curve_progress: float
    is_migrated: bool

    # Social
    has_twitter: bool
    has_telegram: bool
    has_website: bool

    # Computed momentum
    momentum_score: float
    velocity_score: float


@dataclass
class RunnerTrainingData:
    """Donnees d'entrainement pour un token runner"""
    mint: str
    symbol: str
    name: str

    # Label
    is_runner: bool           # True si le token a fait >3x
    max_multiplier: float     # Max ROI atteint (ex: 5.2 = 5.2x)
    time_to_peak_minutes: int # Temps pour atteindre le peak
    phase_at_peak: str        # pre_migration ou post_migration

    # Snapshots temporels
    snapshots: List[TokenSnapshot]

    # Final outcome
    final_mcap: float
    rugged: bool


class RunnerDataCollector:
    """Collecte des donnees temporelles pour entrainement runner"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.pump_api = "https://frontend-api-v2.pump.fun"
        self.dex_api = "https://api.dexscreener.com/latest/dex"
        self.training_data: List[RunnerTrainingData] = []

    async def track_token_over_time(self, mint: str, duration_minutes: int = 240,
                                     interval_seconds: int = 5) -> Optional[RunnerTrainingData]:
        """
        Track un token pendant X minutes et collecte des snapshots

        Args:
            mint: Token mint address
            duration_minutes: Duree du tracking
            interval_seconds: Intervalle entre snapshots

        Returns:
            RunnerTrainingData avec tous les snapshots
        """
        print(f"[TRACK] Starting {duration_minutes}min tracking for {mint[:8]}...")

        snapshots = []
        start_time = datetime.now()
        initial_mcap = 0
        max_mcap = 0
        time_to_peak = 0
        phase_at_peak = "early_pump"

        iterations = (duration_minutes * 60) // interval_seconds

        for i in range(iterations):
            try:
                # Get token data
                snapshot = await self._get_token_snapshot(mint, start_time)

                if snapshot:
                    snapshots.append(snapshot)

                    # Track initial mcap
                    if initial_mcap == 0:
                        initial_mcap = snapshot.market_cap

                    # Track max mcap
                    if snapshot.market_cap > max_mcap:
                        max_mcap = snapshot.market_cap
                        time_to_peak = int((datetime.now() - start_time).total_seconds() / 60)

                        if snapshot.is_migrated:
                            phase_at_peak = "post_migration"
                        elif snapshot.bonding_curve_progress >= 70:
                            phase_at_peak = "pre_migration"
                        else:
                            phase_at_peak = "early_pump"

                    print(f"  [{i+1}/{iterations}] MCap: ${snapshot.market_cap:,.0f} | "
                          f"Holders: {snapshot.holder_count} | "
                          f"Migrated: {snapshot.is_migrated}")

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                print(f"  [ERROR] Snapshot failed: {e}")
                await asyncio.sleep(interval_seconds)
                continue

        if not snapshots or initial_mcap == 0:
            return None

        # Calculate multiplier
        max_multiplier = max_mcap / initial_mcap if initial_mcap > 0 else 1
        is_runner = max_multiplier >= 3.0  # 3x+ = runner

        # Get token info
        token_info = await self._get_token_info(mint)

        return RunnerTrainingData(
            mint=mint,
            symbol=token_info.get('symbol', '???'),
            name=token_info.get('name', 'Unknown'),
            is_runner=is_runner,
            max_multiplier=round(max_multiplier, 2),
            time_to_peak_minutes=time_to_peak,
            phase_at_peak=phase_at_peak,
            snapshots=snapshots,
            final_mcap=snapshots[-1].market_cap if snapshots else 0,
            rugged=snapshots[-1].market_cap < initial_mcap * 0.2 if snapshots else False
        )

    async def _get_token_snapshot(self, mint: str, start_time: datetime) -> Optional[TokenSnapshot]:
        """Get snapshot of token at current moment"""
        try:
            # Get data from Pump.fun
            pump_data = await self._fetch_pump_data(mint)
            dex_data = await self._fetch_dex_data(mint)

            if not pump_data and not dex_data:
                return None

            # Calculate age
            created_ts = pump_data.get('created_timestamp', 0) if pump_data else 0
            age_minutes = (datetime.now().timestamp() * 1000 - created_ts) / 60000 if created_ts else 0

            # Get market cap and price
            market_cap = 0
            price_usd = 0
            if dex_data:
                market_cap = float(dex_data.get('marketCap', 0) or 0)
                price_usd = float(dex_data.get('priceUsd', 0) or 0)
            elif pump_data:
                market_cap = pump_data.get('usd_market_cap', 0)

            # Get price changes
            price_change_5m = float(dex_data.get('priceChange', {}).get('m5', 0) or 0) if dex_data else 0
            price_change_1h = float(dex_data.get('priceChange', {}).get('h1', 0) or 0) if dex_data else 0

            # Get volume
            volume_5m = float(dex_data.get('volume', {}).get('m5', 0) or 0) if dex_data else 0
            volume_1h = float(dex_data.get('volume', {}).get('h1', 0) or 0) if dex_data else 0
            volume_24h = float(dex_data.get('volume', {}).get('h24', 0) or 0) if dex_data else 0

            # Get transactions
            txns = dex_data.get('txns', {}) if dex_data else {}
            txns_5m = txns.get('m5', {})
            buy_count = txns_5m.get('buys', 0)
            sell_count = txns_5m.get('sells', 0)
            txn_count_5m = buy_count + sell_count

            # Get holders
            holder_count = pump_data.get('holder_count', 0) if pump_data else 0

            # Bonding curve progress
            bonding_progress = 0
            is_migrated = False
            if pump_data:
                is_migrated = bool(pump_data.get('raydium_pool') or pump_data.get('complete'))
                if not is_migrated:
                    # Estimate from market cap (PumpFun migrates around $69k)
                    bonding_progress = min(100, (market_cap / 69000) * 100)
                else:
                    bonding_progress = 100

            # Social
            has_twitter = bool(pump_data.get('twitter')) if pump_data else False
            has_telegram = bool(pump_data.get('telegram')) if pump_data else False
            has_website = bool(pump_data.get('website')) if pump_data else False

            # Calculate momentum
            buy_sell_ratio = buy_count / max(sell_count, 1)
            momentum_score = min(100, (price_change_5m + 50) + (buy_sell_ratio * 10))
            velocity_score = min(100, volume_5m / 1000 + holder_count / 10)

            return TokenSnapshot(
                mint=mint,
                timestamp=datetime.now().isoformat(),
                age_minutes=age_minutes,
                market_cap=market_cap,
                price_usd=price_usd,
                price_change_5m=price_change_5m,
                price_change_1h=price_change_1h,
                volume_5m=volume_5m,
                volume_1h=volume_1h,
                volume_24h=volume_24h,
                holder_count=holder_count,
                holder_growth_rate=0,  # Calculated on next snapshot
                txn_count_5m=txn_count_5m,
                buy_count_5m=buy_count,
                sell_count_5m=sell_count,
                buy_sell_ratio=round(buy_sell_ratio, 2),
                bonding_curve_progress=round(bonding_progress, 1),
                is_migrated=is_migrated,
                has_twitter=has_twitter,
                has_telegram=has_telegram,
                has_website=has_website,
                momentum_score=round(momentum_score, 1),
                velocity_score=round(velocity_score, 1)
            )

        except Exception as e:
            print(f"[ERROR] Failed to get snapshot: {e}")
            return None

    async def _fetch_pump_data(self, mint: str) -> Optional[Dict]:
        """Fetch from Pump.fun API"""
        try:
            response = await self.client.get(f"{self.pump_api}/coins/{mint}")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    async def _fetch_dex_data(self, mint: str) -> Optional[Dict]:
        """Fetch from DexScreener API"""
        try:
            response = await self.client.get(f"{self.dex_api}/tokens/{mint}")
            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])
                return pairs[0] if pairs else None
        except:
            pass
        return None

    async def _get_token_info(self, mint: str) -> Dict:
        """Get basic token info"""
        pump_data = await self._fetch_pump_data(mint)
        if pump_data:
            return {
                'symbol': pump_data.get('symbol', '???'),
                'name': pump_data.get('name', 'Unknown')
            }
        return {'symbol': '???', 'name': 'Unknown'}

    async def collect_batch(self, num_tokens: int = 10, track_minutes: int = 120, interval_sec: int = 5):
        """
        Collecte un batch de tokens recents et les track

        Args:
            num_tokens: Nombre de tokens a tracker
            track_minutes: Duree du tracking par token
        """
        print(f"\n{'='*70}")
        print(f"RUNNER TRAINING DATA COLLECTION")
        print(f"{'='*70}")
        print(f"Collecting {num_tokens} tokens, tracking each for {track_minutes} minutes")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

        # Get fresh tokens
        tokens = await self._get_new_tokens(num_tokens * 2)  # Get extra in case some fail

        collected = []
        for i, token in enumerate(tokens[:num_tokens]):
            mint = token.get('mint')
            symbol = token.get('symbol', '???')
            mcap = token.get('usd_market_cap', 0)

            print(f"\n[{i+1}/{num_tokens}] Tracking {symbol} ({mint[:8]}...) | MCap: ${mcap:,.0f}")
            print(f"    Duration: {track_minutes}min | Interval: {interval_sec}s")

            # Track token
            data = await self.track_token_over_time(mint, track_minutes, interval_seconds=interval_sec)

            if data:
                collected.append(data)
                runner_status = "RUNNER" if data.is_runner else "NORMAL"
                print(f"  [DONE] {runner_status} | Max: {data.max_multiplier}x | Peak: {data.time_to_peak_minutes}min")
            else:
                print(f"  [SKIP] Could not track token")

        # Save results
        if collected:
            self._save_training_data(collected)

        print(f"\n{'='*70}")
        print(f"COLLECTION COMPLETE!")
        print(f"{'='*70}")
        print(f"Tokens collected: {len(collected)}")
        print(f"Runners found: {sum(1 for d in collected if d.is_runner)}")
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

    async def _get_new_tokens(self, limit: int = 20) -> List[Dict]:
        """Get newest tokens from Pump.fun"""
        try:
            response = await self.client.get(
                f"{self.pump_api}/coins",
                params={"limit": limit, "sort": "created_timestamp", "order": "DESC"}
            )
            if response.status_code == 200:
                tokens = response.json()
                # Filter tokens with reasonable mcap
                return [t for t in tokens if 5000 <= t.get('usd_market_cap', 0) <= 50000]
        except Exception as e:
            print(f"[ERROR] Failed to get new tokens: {e}")
        return []

    def _save_training_data(self, data: List[RunnerTrainingData]):
        """Save training data to CSV"""
        os.makedirs("ml_module/dataset", exist_ok=True)

        # Convert to flat format for CSV
        rows = []
        for item in data:
            base_row = {
                'mint': item.mint,
                'symbol': item.symbol,
                'name': item.name,
                'is_runner': 1 if item.is_runner else 0,
                'max_multiplier': item.max_multiplier,
                'time_to_peak_minutes': item.time_to_peak_minutes,
                'phase_at_peak': item.phase_at_peak,
                'final_mcap': item.final_mcap,
                'rugged': 1 if item.rugged else 0,
                'num_snapshots': len(item.snapshots)
            }

            # Add first and last snapshot features
            if item.snapshots:
                first = item.snapshots[0]
                last = item.snapshots[-1]

                base_row.update({
                    # Initial state
                    'initial_mcap': first.market_cap,
                    'initial_holders': first.holder_count,
                    'initial_bonding': first.bonding_curve_progress,
                    'initial_momentum': first.momentum_score,
                    # Final state
                    'final_holders': last.holder_count,
                    'final_bonding': last.bonding_curve_progress,
                    'final_migrated': 1 if last.is_migrated else 0,
                    # Changes
                    'holder_growth': last.holder_count - first.holder_count,
                    'mcap_change': (last.market_cap - first.market_cap) / max(first.market_cap, 1) * 100,
                    # Social
                    'has_twitter': 1 if first.has_twitter else 0,
                    'has_telegram': 1 if first.has_telegram else 0,
                    'has_website': 1 if first.has_website else 0,
                    # Volume
                    'avg_volume_5m': sum(s.volume_5m for s in item.snapshots) / len(item.snapshots),
                    'max_buy_sell_ratio': max(s.buy_sell_ratio for s in item.snapshots),
                })

            rows.append(base_row)

        df = pd.DataFrame(rows)

        # Save
        filename = f"ml_module/dataset/runner_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        print(f"\n[SAVED] Training data saved to: {filename}")

        # Also append to master file
        master_file = "ml_module/dataset/runner_training_master.csv"
        if os.path.exists(master_file):
            existing = pd.read_csv(master_file)
            df = pd.concat([existing, df], ignore_index=True)
            df = df.drop_duplicates(subset=['mint'], keep='last')

        df.to_csv(master_file, index=False)
        print(f"[SAVED] Master file updated: {master_file} ({len(df)} total tokens)")

        # Save detailed snapshots as JSON
        json_file = f"ml_module/dataset/runner_snapshots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w') as f:
            json_data = []
            for item in data:
                json_data.append({
                    'mint': item.mint,
                    'symbol': item.symbol,
                    'is_runner': item.is_runner,
                    'max_multiplier': item.max_multiplier,
                    'snapshots': [asdict(s) for s in item.snapshots]
                })
            json.dump(json_data, f, indent=2)
        print(f"[SAVED] Detailed snapshots saved to: {json_file}")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


async def main():
    """Main collection loop"""
    print("\n" + "="*70)
    print("RUNNER TRAINING DATA COLLECTOR - REAL-TIME")
    print("="*70)
    print("\nCollecte des donnees TEMPS REEL pour entrainer l'IA")
    print("a detecter les RUNNERS (tokens qui font >3x)")
    print("\nOptions:")
    print("1. Quick test (3 tokens, 30 min, interval 10s)")
    print("2. Standard (5 tokens, 2h, interval 5s) - RECOMMANDE")
    print("3. Deep collection (10 tokens, 4h, interval 5s)")
    print("4. Marathon (5 tokens, 6h, interval 5s) - Maximum de donnees")

    choice = input("\nSelect mode (1/2/3/4): ").strip()

    collector = RunnerDataCollector()

    try:
        if choice == '1':
            await collector.collect_batch(num_tokens=3, track_minutes=30, interval_sec=10)
        elif choice == '3':
            await collector.collect_batch(num_tokens=10, track_minutes=240, interval_sec=5)
        elif choice == '4':
            await collector.collect_batch(num_tokens=5, track_minutes=360, interval_sec=5)
        else:
            await collector.collect_batch(num_tokens=5, track_minutes=120, interval_sec=5)
    finally:
        await collector.close()

    print("\n[OK] Collection complete!")
    print("[NEXT] Train the AI with the collected data:")
    print("       python train_runner_model.py")


if __name__ == "__main__":
    asyncio.run(main())

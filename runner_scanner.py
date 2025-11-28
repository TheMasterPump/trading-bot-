"""
RUNNER SCANNER - Detecte les tokens qui vont RUNNER (monter fort)
Predit:
1. Si le token va runner AVANT migration
2. Si le token va continuer APRES migration
3. Jusqu'ou il peut monter (target price)

C'est notre FORCE - detecter les runners avant tout le monde!
"""

import asyncio
import json
import httpx
import joblib
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.layout import Layout

console = Console()


class MigrationPhase(Enum):
    """Phase du token par rapport a la migration"""
    EARLY = "early"                    # < 30% bonding
    MID = "mid"                        # 30-70% bonding
    PRE_MIGRATION = "pre_migration"    # 70-100% bonding
    MIGRATING = "migrating"            # En cours de migration
    POST_MIGRATION = "post_migration"  # Apres migration sur Raydium


class RunnerType(Enum):
    """Type de runner detecte"""
    MOON = "MOON"           # >10x potentiel - RARE!
    RUNNER = "RUNNER"       # 3x-10x potentiel - BON!
    PUMPER = "PUMPER"       # 2x-3x potentiel - OK
    WEAK = "WEAK"           # <2x potentiel
    RUG = "RUG"             # Va probablement rug


@dataclass
class RunnerPrediction:
    """Prediction complete d'un token runner"""
    mint: str
    symbol: str
    name: str

    # Phase actuelle
    phase: MigrationPhase
    bonding_progress: float

    # Scores
    runner_score: float         # 0-100
    migration_probability: float  # 0-100%
    continuation_probability: float  # Prob de continuer apres migration

    # Type de runner
    runner_type: RunnerType
    confidence: str  # HIGH/MEDIUM/LOW

    # Market data
    current_mcap: float
    volume_24h: float
    holders: int

    # PREDICTIONS DE PRIX
    target_pre_migration: float    # Target avant migration
    target_post_migration: float   # Target apres migration
    target_ath: float              # Target ATH potentiel

    # Multipliers
    potential_x_pre: float         # Ex: 2.5x avant migration
    potential_x_post: float        # Ex: 5x apres migration
    potential_x_max: float         # Ex: 10x max potentiel

    # Timing
    time_to_migration: str         # "~15min", "~30min", etc.

    # Decision
    action: str                    # BUY/WAIT/SKIP
    entry_zone: Tuple[float, float]  # Range de mcap pour entrer

    # Signals
    bullish_signals: list
    bearish_signals: list


class RunnerScanner:
    """
    Scanner qui detecte les RUNNERS sur PumpFun
    Notre avantage: detecter les runners AVANT migration et APRES!
    """

    def __init__(self):
        self.pump_api = "https://frontend-api-v2.pump.fun"
        self.dex_api = "https://api.dexscreener.com/latest/dex"
        self.client = httpx.AsyncClient(timeout=30.0)

        # Stats
        self.tokens_scanned = 0
        self.runners_found = 0
        self.moon_shots_found = 0

        # Charger les modeles existants si disponibles
        self.model_10s = None
        self.model_15s = None
        try:
            self.model_10s = joblib.load('model_10s.pkl')
            self.model_15s = joblib.load('model_15s.pkl')
            console.print("[green]Modeles 10s/15s charges!")
        except:
            console.print("[yellow]Modeles 10s/15s non trouves - utilisation des heuristiques")

        # Patterns appris des runners historiques
        self.runner_patterns = {
            # Volume patterns
            'volume_threshold_early': 5000,     # $5k volume = token actif
            'volume_threshold_strong': 15000,   # $15k+ = fort momentum
            'volume_threshold_moon': 50000,     # $50k+ = moon potential

            # Holder patterns
            'holders_threshold_early': 30,
            'holders_threshold_strong': 100,
            'holders_threshold_moon': 300,

            # Transaction patterns
            'txn_velocity_threshold': 5,        # 5+ txn/min = actif
            'buy_ratio_threshold': 0.6,         # 60%+ buys = bullish

            # Migration patterns
            'bonding_hot_zone': 85,             # >85% = proche migration
            'post_migration_pump_window': 30,   # 30 min critiques apres migration
        }

        # Multipliers historiques par phase
        self.historical_targets = {
            MigrationPhase.EARLY: {'min': 2, 'avg': 5, 'max': 20},
            MigrationPhase.MID: {'min': 1.5, 'avg': 3, 'max': 10},
            MigrationPhase.PRE_MIGRATION: {'min': 1.3, 'avg': 2, 'max': 5},
            MigrationPhase.POST_MIGRATION: {'min': 1.5, 'avg': 3, 'max': 15},
        }

    async def analyze_token(self, token_data: Dict) -> Optional[RunnerPrediction]:
        """
        Analyse complete d'un token pour detecter s'il va runner

        Args:
            token_data: Donnees du token (de PumpFun API ou websocket)

        Returns:
            RunnerPrediction avec toutes les predictions
        """
        try:
            mint = token_data.get('mint', '')
            symbol = token_data.get('symbol', '???')
            name = token_data.get('name', 'Unknown')

            # Get market data
            mcap = token_data.get('usd_market_cap', token_data.get('marketCap', 0))
            volume_24h = token_data.get('volume', token_data.get('volume_24h', 0))
            holders = token_data.get('holder_count', 0)

            # Determine phase
            phase, bonding_progress = self._determine_phase(token_data)

            # Calculate scores
            runner_score = self._calculate_runner_score(token_data, phase)
            migration_prob = self._calculate_migration_probability(token_data, phase, bonding_progress)
            continuation_prob = self._calculate_continuation_probability(token_data, runner_score)

            # Determine runner type
            runner_type = self._determine_runner_type(runner_score, migration_prob)

            # Calculate price targets
            targets = self._calculate_price_targets(mcap, phase, runner_score, migration_prob)

            # Generate signals
            bullish, bearish = self._generate_signals(token_data, phase, runner_score)

            # Determine action
            action, entry_zone = self._determine_action(mcap, phase, runner_score, runner_type)

            # Estimate time to migration
            time_to_migration = self._estimate_migration_time(bonding_progress, token_data)

            self.tokens_scanned += 1
            if runner_type in [RunnerType.MOON, RunnerType.RUNNER]:
                self.runners_found += 1
            if runner_type == RunnerType.MOON:
                self.moon_shots_found += 1

            return RunnerPrediction(
                mint=mint,
                symbol=symbol,
                name=name,
                phase=phase,
                bonding_progress=bonding_progress,
                runner_score=runner_score,
                migration_probability=migration_prob,
                continuation_probability=continuation_prob,
                runner_type=runner_type,
                confidence=self._get_confidence(runner_score),
                current_mcap=mcap,
                volume_24h=volume_24h,
                holders=holders,
                target_pre_migration=targets['pre_migration'],
                target_post_migration=targets['post_migration'],
                target_ath=targets['ath'],
                potential_x_pre=targets['x_pre'],
                potential_x_post=targets['x_post'],
                potential_x_max=targets['x_max'],
                time_to_migration=time_to_migration,
                action=action,
                entry_zone=entry_zone,
                bullish_signals=bullish,
                bearish_signals=bearish
            )

        except Exception as e:
            console.print(f"[red]Erreur analyse: {e}")
            return None

    def _determine_phase(self, token_data: Dict) -> Tuple[MigrationPhase, float]:
        """Determine la phase du token"""

        # Check si migre
        if token_data.get('raydium_pool') or token_data.get('complete'):
            return MigrationPhase.POST_MIGRATION, 100.0

        # Estimer bonding curve progress via market cap
        mcap = token_data.get('usd_market_cap', token_data.get('marketCap', 0))

        # PumpFun migre autour de $69k mcap
        bonding = min(100, (mcap / 69000) * 100)

        if bonding >= 95:
            return MigrationPhase.MIGRATING, bonding
        elif bonding >= 70:
            return MigrationPhase.PRE_MIGRATION, bonding
        elif bonding >= 30:
            return MigrationPhase.MID, bonding
        else:
            return MigrationPhase.EARLY, bonding

    def _calculate_runner_score(self, token_data: Dict, phase: MigrationPhase) -> float:
        """Calcule le score runner (0-100)"""
        score = 0

        # Volume score (max 30)
        volume = token_data.get('volume', token_data.get('volume_24h', 0))
        if volume >= 50000:
            score += 30
        elif volume >= 20000:
            score += 25
        elif volume >= 10000:
            score += 20
        elif volume >= 5000:
            score += 15
        elif volume >= 2000:
            score += 10

        # Holder score (max 25)
        holders = token_data.get('holder_count', 0)
        if holders >= 300:
            score += 25
        elif holders >= 150:
            score += 20
        elif holders >= 100:
            score += 15
        elif holders >= 50:
            score += 10
        elif holders >= 30:
            score += 5

        # Transaction velocity (max 20)
        txns = token_data.get('txnCount', token_data.get('txns', 0))
        if txns >= 100:
            score += 20
        elif txns >= 50:
            score += 15
        elif txns >= 20:
            score += 10
        elif txns >= 10:
            score += 5

        # Social presence (max 15)
        if token_data.get('twitter'):
            score += 5
        if token_data.get('telegram'):
            score += 5
        if token_data.get('website'):
            score += 5

        # Phase bonus (max 10)
        if phase == MigrationPhase.PRE_MIGRATION:
            score += 10  # Proche de migration = momentum
        elif phase == MigrationPhase.POST_MIGRATION:
            # Check si volume continue apres migration
            if volume >= 30000:
                score += 10
        elif phase == MigrationPhase.EARLY:
            # Early with good metrics = potential
            if holders >= 50 and volume >= 5000:
                score += 5

        return min(100, score)

    def _calculate_migration_probability(self, token_data: Dict,
                                          phase: MigrationPhase,
                                          bonding: float) -> float:
        """Calcule la probabilite de migration"""

        if phase == MigrationPhase.POST_MIGRATION:
            return 100.0  # Deja migre

        if phase == MigrationPhase.MIGRATING:
            return 95.0  # En cours

        prob = bonding  # Base = progress bonding curve

        # Ajustements
        volume = token_data.get('volume', 0)
        holders = token_data.get('holder_count', 0)

        if volume >= 20000:
            prob += 10
        if holders >= 100:
            prob += 5
        if token_data.get('twitter'):
            prob += 3
        if token_data.get('telegram'):
            prob += 2

        return min(100, prob)

    def _calculate_continuation_probability(self, token_data: Dict,
                                             runner_score: float) -> float:
        """Calcule la prob de continuer apres migration"""

        # Base sur le runner score
        base = runner_score * 0.7

        # Bonus si fort volume
        volume = token_data.get('volume', 0)
        if volume >= 30000:
            base += 15
        elif volume >= 15000:
            base += 10

        # Bonus si beaucoup de holders (distribution)
        holders = token_data.get('holder_count', 0)
        if holders >= 200:
            base += 10
        elif holders >= 100:
            base += 5

        return min(100, base)

    def _determine_runner_type(self, runner_score: float,
                                migration_prob: float) -> RunnerType:
        """Determine le type de runner"""

        combined_score = (runner_score * 0.7) + (migration_prob * 0.3)

        if combined_score >= 85:
            return RunnerType.MOON
        elif combined_score >= 70:
            return RunnerType.RUNNER
        elif combined_score >= 55:
            return RunnerType.PUMPER
        elif combined_score >= 40:
            return RunnerType.WEAK
        else:
            return RunnerType.RUG

    def _calculate_price_targets(self, current_mcap: float,
                                  phase: MigrationPhase,
                                  runner_score: float,
                                  migration_prob: float) -> Dict:
        """
        Calcule les targets de prix
        C'est la ou on predit JUSQU'OU le token peut monter!
        """

        # Get historical multipliers for this phase
        hist = self.historical_targets.get(phase, {'min': 1.2, 'avg': 2, 'max': 5})

        # Adjust based on runner score
        score_factor = runner_score / 60  # Normalize

        # Calculate multipliers
        x_pre = round(hist['avg'] * score_factor, 1)
        x_post = round(hist['max'] * score_factor * 0.8, 1)
        x_max = round(hist['max'] * score_factor, 1)

        # Ensure minimums
        x_pre = max(1.2, x_pre)
        x_post = max(1.5, x_post)
        x_max = max(2, x_max)

        # Calculate targets
        # Migration target (autour de $69k pour PumpFun)
        migration_mcap = 69000

        return {
            'pre_migration': migration_mcap if current_mcap < migration_mcap else current_mcap * x_pre,
            'post_migration': migration_mcap * x_post,
            'ath': current_mcap * x_max,
            'x_pre': x_pre,
            'x_post': x_post,
            'x_max': x_max
        }

    def _generate_signals(self, token_data: Dict,
                          phase: MigrationPhase,
                          runner_score: float) -> Tuple[list, list]:
        """Genere les signaux bullish et bearish"""

        bullish = []
        bearish = []

        # Check volume
        volume = token_data.get('volume', 0)
        if volume >= 30000:
            bullish.append(f"Fort volume: ${volume:,.0f}")
        elif volume < 5000:
            bearish.append("Volume faible")

        # Check holders
        holders = token_data.get('holder_count', 0)
        if holders >= 150:
            bullish.append(f"Bonne distribution: {holders} holders")
        elif holders < 30:
            bearish.append("Peu de holders")

        # Check phase
        if phase == MigrationPhase.PRE_MIGRATION:
            bullish.append("PROCHE MIGRATION!")
        elif phase == MigrationPhase.POST_MIGRATION:
            bullish.append("A MIGRE - Watch for pump!")

        # Check social
        if token_data.get('twitter') and token_data.get('telegram'):
            bullish.append("Social complet")
        elif not token_data.get('twitter') and not token_data.get('telegram'):
            bearish.append("Pas de social")

        # Runner score
        if runner_score >= 70:
            bullish.append(f"RUNNER SCORE: {runner_score}/100")
        elif runner_score < 40:
            bearish.append(f"Score faible: {runner_score}/100")

        return bullish, bearish

    def _determine_action(self, mcap: float, phase: MigrationPhase,
                          runner_score: float,
                          runner_type: RunnerType) -> Tuple[str, Tuple[float, float]]:
        """Determine l'action recommandee"""

        # Entry zones by phase
        if phase == MigrationPhase.EARLY:
            entry_zone = (mcap * 0.9, mcap * 1.2)
        elif phase == MigrationPhase.MID:
            entry_zone = (mcap * 0.95, mcap * 1.1)
        elif phase == MigrationPhase.PRE_MIGRATION:
            entry_zone = (mcap * 0.98, mcap * 1.05)  # Tight zone
        else:
            entry_zone = (mcap * 0.85, mcap * 1.0)  # Buy dips post-migration

        # Determine action
        if runner_type == RunnerType.RUG:
            action = "SKIP"
        elif runner_type == RunnerType.WEAK:
            action = "WAIT"
        elif runner_type == RunnerType.MOON:
            action = "BUY NOW!"
        elif runner_type == RunnerType.RUNNER:
            action = "BUY"
        else:
            action = "CONSIDER"

        return action, entry_zone

    def _estimate_migration_time(self, bonding: float, token_data: Dict) -> str:
        """Estime le temps avant migration"""

        if bonding >= 100:
            return "MIGRE"

        # Estimate based on current velocity
        volume = token_data.get('volume', 0)

        remaining = 100 - bonding

        if volume >= 30000:
            # Fast pace
            if remaining < 10:
                return "~5-10 min"
            elif remaining < 20:
                return "~10-20 min"
            else:
                return "~30-60 min"
        elif volume >= 10000:
            # Medium pace
            if remaining < 10:
                return "~10-20 min"
            elif remaining < 20:
                return "~30-60 min"
            else:
                return "~1-2h"
        else:
            # Slow pace
            return "~2h+" if remaining > 30 else "~30min-1h"

    def _get_confidence(self, runner_score: float) -> str:
        """Retourne le niveau de confiance"""
        if runner_score >= 75:
            return "HIGH"
        elif runner_score >= 55:
            return "MEDIUM"
        else:
            return "LOW"

    def display_prediction(self, pred: RunnerPrediction):
        """Affiche une prediction avec style"""

        # Couleur selon type
        type_colors = {
            RunnerType.MOON: "bold magenta",
            RunnerType.RUNNER: "bold green",
            RunnerType.PUMPER: "bold yellow",
            RunnerType.WEAK: "dim white",
            RunnerType.RUG: "bold red"
        }
        color = type_colors.get(pred.runner_type, "white")

        # Header
        console.print(f"\n[{color}]{'='*70}")
        console.print(f"[{color}]{pred.runner_type.value} DETECTED: {pred.symbol} ({pred.name[:30]})")
        console.print(f"[{color}]{'='*70}")

        # Table principale
        table = Table(show_header=False, box=None)
        table.add_column("", style="cyan", width=25)
        table.add_column("", style="green")

        table.add_row("Mint", f"{pred.mint[:32]}...")
        table.add_row("Phase", f"{pred.phase.value.upper()} ({pred.bonding_progress:.1f}% bonding)")
        table.add_row("Market Cap", f"${pred.current_mcap:,.0f}")
        table.add_row("Volume 24h", f"${pred.volume_24h:,.0f}")
        table.add_row("Holders", str(pred.holders))
        table.add_row("", "")
        table.add_row("RUNNER SCORE", f"{pred.runner_score:.0f}/100 ({pred.confidence})")
        table.add_row("Migration Prob", f"{pred.migration_probability:.0f}%")
        table.add_row("Continuation Prob", f"{pred.continuation_probability:.0f}%")

        console.print(table)

        # Price targets panel
        targets_text = Text()
        targets_text.append(f"\n  Current: ${pred.current_mcap:,.0f}\n\n", style="white")
        targets_text.append(f"  Pre-Migration: ${pred.target_pre_migration:,.0f} ({pred.potential_x_pre}x)\n", style="yellow")
        targets_text.append(f"  Post-Migration: ${pred.target_post_migration:,.0f} ({pred.potential_x_post}x)\n", style="green")
        targets_text.append(f"  ATH Potential: ${pred.target_ath:,.0f} ({pred.potential_x_max}x)\n", style="magenta")
        targets_text.append(f"\n  Time to Migration: {pred.time_to_migration}\n", style="cyan")

        console.print(Panel(targets_text, title="PRICE TARGETS", border_style="green"))

        # Signals
        if pred.bullish_signals:
            signals = Text()
            for s in pred.bullish_signals:
                signals.append(f"  + {s}\n", style="green")
            console.print(Panel(signals, title="BULLISH SIGNALS", border_style="green"))

        if pred.bearish_signals:
            signals = Text()
            for s in pred.bearish_signals:
                signals.append(f"  - {s}\n", style="red")
            console.print(Panel(signals, title="BEARISH SIGNALS", border_style="red"))

        # Action
        action_color = "green" if "BUY" in pred.action else "yellow" if pred.action == "CONSIDER" else "red"
        console.print(f"\n[{action_color}]>>> ACTION: {pred.action} <<<")
        console.print(f"[cyan]Entry Zone: ${pred.entry_zone[0]:,.0f} - ${pred.entry_zone[1]:,.0f}")
        console.print(f"[{color}]{'='*70}\n")

    async def scan_new_tokens(self, limit: int = 20):
        """Scan les tokens recents"""

        console.print(f"\n[bold cyan]Scanning {limit} recent tokens...")

        try:
            response = await self.client.get(
                f"{self.pump_api}/coins",
                params={"limit": limit, "sort": "created_timestamp", "order": "DESC"}
            )

            if response.status_code != 200:
                console.print(f"[red]API Error: {response.status_code}")
                return []

            tokens = response.json()
            runners = []

            for token in tokens:
                pred = await self.analyze_token(token)

                if pred and pred.runner_type in [RunnerType.MOON, RunnerType.RUNNER, RunnerType.PUMPER]:
                    runners.append(pred)
                    self.display_prediction(pred)

            return runners

        except Exception as e:
            console.print(f"[red]Scan error: {e}")
            return []

    async def live_scan(self):
        """Scan en temps reel via WebSocket"""

        console.print(f"\n[bold green]{'='*70}")
        console.print(f"[bold green]RUNNER SCANNER - LIVE MODE")
        console.print(f"[bold green]Detection des RUNNERS en temps reel!")
        console.print(f"[bold green]{'='*70}\n")

        # Import PumpFun monitor
        try:
            from pumpfun_monitor import PumpFunMonitor
            monitor = PumpFunMonitor()
        except ImportError:
            console.print("[red]PumpFunMonitor non disponible - utilisant polling")
            # Fallback to polling
            while True:
                await self.scan_new_tokens(20)
                await asyncio.sleep(30)
            return

        async def on_new_token(token_data):
            """Callback pour nouveau token"""
            pred = await self.analyze_token(token_data)

            if pred:
                if pred.runner_type in [RunnerType.MOON, RunnerType.RUNNER]:
                    # Alert!
                    console.print(f"\n[bold blink red]*** ALERT: {pred.runner_type.value} DETECTED! ***")
                    self.display_prediction(pred)
                elif pred.runner_type == RunnerType.PUMPER:
                    self.display_prediction(pred)

        # Subscribe
        await monitor.subscribe_new_tokens(callback=on_new_token)

    def display_stats(self):
        """Affiche les stats"""
        console.print(f"\n[cyan]{'='*50}")
        console.print(f"[cyan]SCANNER STATS")
        console.print(f"[cyan]{'='*50}")
        console.print(f"[green]Tokens Scanned: {self.tokens_scanned}")
        console.print(f"[green]Runners Found: {self.runners_found}")
        console.print(f"[magenta]Moon Shots: {self.moon_shots_found}")
        if self.tokens_scanned > 0:
            rate = (self.runners_found / self.tokens_scanned) * 100
            console.print(f"[yellow]Runner Rate: {rate:.1f}%")
        console.print(f"[cyan]{'='*50}\n")

    async def close(self):
        """Cleanup"""
        await self.client.aclose()


async def main():
    """Main"""
    console.print(f"\n[bold cyan]{'='*70}")
    console.print(f"[bold cyan]RUNNER SCANNER")
    console.print(f"[bold cyan]Detection des tokens qui vont RUNNER!")
    console.print(f"[bold cyan]{'='*70}\n")

    console.print("Options:")
    console.print("1. Scan tokens recents")
    console.print("2. Live scan (temps reel)")
    console.print("3. Analyser un token specifique")

    choice = input("\nChoix (1/2/3): ").strip()

    scanner = RunnerScanner()

    try:
        if choice == '1':
            limit = int(input("Nombre de tokens a scanner (defaut 20): ") or "20")
            await scanner.scan_new_tokens(limit)
        elif choice == '2':
            await scanner.live_scan()
        elif choice == '3':
            mint = input("Mint address: ").strip()
            # Fetch token data
            response = await scanner.client.get(f"{scanner.pump_api}/coins/{mint}")
            if response.status_code == 200:
                token = response.json()
                pred = await scanner.analyze_token(token)
                if pred:
                    scanner.display_prediction(pred)
            else:
                console.print("[red]Token non trouve")

        scanner.display_stats()

    except KeyboardInterrupt:
        console.print("\n[yellow]Scanner arrete")
        scanner.display_stats()
    finally:
        await scanner.close()


if __name__ == "__main__":
    asyncio.run(main())

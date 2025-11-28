"""
RUNNER DETECTOR - Detecte les tokens qui vont "run" (monter fort)
Analyse avant et apres migration PumpFun -> Raydium
Predit le potentiel de hausse (target price)
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import Enum


class RunnerPhase(Enum):
    """Phase du token dans son cycle de vie"""
    EARLY_PUMP = "early_pump"           # Debut sur PumpFun (0-30% bonding)
    MID_PUMP = "mid_pump"               # Milieu PumpFun (30-70% bonding)
    PRE_MIGRATION = "pre_migration"     # Proche migration (70-100% bonding)
    MIGRATING = "migrating"             # En cours de migration
    POST_MIGRATION = "post_migration"   # Apres migration sur Raydium


class RunnerPotential(Enum):
    """Potentiel de hausse du token"""
    MOON = "moon"           # >1000% potentiel (10x+)
    RUNNER = "runner"       # 300-1000% potentiel (3x-10x)
    PUMPER = "pumper"       # 100-300% potentiel (2x-3x)
    WEAK = "weak"           # <100% potentiel
    DUMP = "dump"           # Va probablement dump


@dataclass
class RunnerAnalysis:
    """Resultat de l'analyse runner"""
    token_mint: str
    phase: RunnerPhase
    potential: RunnerPotential

    # Scores (0-100)
    momentum_score: float       # Vitesse de croissance
    accumulation_score: float   # Whales/smart money accumulent
    hype_score: float          # Buzz social
    organic_score: float       # Croissance organique vs manipulation
    migration_score: float     # Probabilite de migration reussie

    # Predictions
    runner_score: float        # Score global (0-100)
    confidence: str            # HIGH/MEDIUM/LOW

    # Price targets
    current_mcap: float
    target_mcap_conservative: float   # Target pessimiste
    target_mcap_moderate: float       # Target modere
    target_mcap_optimistic: float     # Target optimiste

    # Multipliers
    potential_x_low: float
    potential_x_mid: float
    potential_x_high: float

    # Timing
    estimated_time_to_target: str     # "15min", "1h", "4h", etc.
    best_entry_zone: Tuple[float, float]  # (min_mcap, max_mcap)

    # Signals
    signals: List[str]         # Liste des signaux detectes
    warnings: List[str]        # Liste des warnings


class RunnerDetector:
    """Detecteur de tokens runners"""

    def __init__(self, rpc_url: str = None):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.rpc_url = rpc_url

        # Patterns appris des runners historiques
        self.runner_patterns = {
            # Momentum patterns
            'volume_velocity_threshold': 2.0,      # Volume doit doubler en 5min
            'holder_velocity_threshold': 1.5,      # Holders doivent augmenter 50% en 5min
            'mcap_velocity_threshold': 1.3,        # MCap doit augmenter 30% en 5min

            # Accumulation patterns
            'whale_buy_threshold': 0.5,            # Achat > 0.5 SOL = whale
            'smart_money_threshold': 3,            # 3+ whales qui buy = signal
            'dev_holding_safe': 5.0,               # Dev doit avoir < 5%

            # Pre-migration patterns
            'bonding_curve_hot_zone': 85,          # > 85% = proche migration
            'migration_momentum_threshold': 70,    # Score > 70 = va probablement migrer

            # Post-migration patterns
            'post_migration_pump_window': 30,      # Les 30 premieres min sont critiques
            'raydium_volume_multiplier': 3,        # Volume doit x3 apres migration
        }

        # Multipliers historiques par phase
        self.historical_multipliers = {
            RunnerPhase.EARLY_PUMP: {'low': 2, 'mid': 5, 'high': 20},
            RunnerPhase.MID_PUMP: {'low': 1.5, 'mid': 3, 'high': 10},
            RunnerPhase.PRE_MIGRATION: {'low': 1.3, 'mid': 2, 'high': 5},
            RunnerPhase.POST_MIGRATION: {'low': 1.2, 'mid': 2, 'high': 8},
        }

    async def analyze_runner_potential(self, token_data: Dict) -> RunnerAnalysis:
        """
        Analyse complete du potentiel runner d'un token

        Args:
            token_data: Donnees du token (mint, mcap, volume, holders, etc.)

        Returns:
            RunnerAnalysis avec scores et predictions
        """
        mint = token_data.get('mint', '')

        # Determiner la phase
        phase = self._determine_phase(token_data)

        # Calculer les scores
        momentum_score = await self._calculate_momentum_score(token_data)
        accumulation_score = await self._calculate_accumulation_score(token_data)
        hype_score = self._calculate_hype_score(token_data)
        organic_score = self._calculate_organic_score(token_data)
        migration_score = self._calculate_migration_score(token_data)

        # Score global runner
        runner_score = self._calculate_runner_score(
            momentum_score, accumulation_score, hype_score,
            organic_score, migration_score, phase
        )

        # Determiner le potentiel
        potential = self._determine_potential(runner_score, phase)

        # Calculer les targets
        current_mcap = token_data.get('market_cap', token_data.get('usd_market_cap', 0))
        multipliers = self._calculate_target_multipliers(runner_score, phase)

        # Generer signaux et warnings
        signals, warnings = self._generate_signals(token_data, runner_score, phase)

        # Estimer le timing
        time_estimate = self._estimate_time_to_target(phase, momentum_score)
        entry_zone = self._calculate_entry_zone(current_mcap, phase)

        return RunnerAnalysis(
            token_mint=mint,
            phase=phase,
            potential=potential,
            momentum_score=momentum_score,
            accumulation_score=accumulation_score,
            hype_score=hype_score,
            organic_score=organic_score,
            migration_score=migration_score,
            runner_score=runner_score,
            confidence=self._get_confidence(runner_score),
            current_mcap=current_mcap,
            target_mcap_conservative=current_mcap * multipliers['low'],
            target_mcap_moderate=current_mcap * multipliers['mid'],
            target_mcap_optimistic=current_mcap * multipliers['high'],
            potential_x_low=multipliers['low'],
            potential_x_mid=multipliers['mid'],
            potential_x_high=multipliers['high'],
            estimated_time_to_target=time_estimate,
            best_entry_zone=entry_zone,
            signals=signals,
            warnings=warnings
        )

    def _determine_phase(self, token_data: Dict) -> RunnerPhase:
        """Determine la phase du token"""

        # Check si deja migre
        if token_data.get('raydium_pool') or token_data.get('complete'):
            return RunnerPhase.POST_MIGRATION

        # Check bonding curve progress
        bonding_progress = token_data.get('bonding_curve_progress', 0)

        # Si pas de bonding progress, estimer via market cap
        if bonding_progress == 0:
            mcap = token_data.get('market_cap', token_data.get('usd_market_cap', 0))
            # PumpFun migre autour de $69k mcap
            if mcap > 65000:
                bonding_progress = 95
            elif mcap > 50000:
                bonding_progress = 80
            elif mcap > 30000:
                bonding_progress = 50
            else:
                bonding_progress = max(0, mcap / 700)  # Rough estimate

        if bonding_progress >= 95:
            return RunnerPhase.MIGRATING
        elif bonding_progress >= 70:
            return RunnerPhase.PRE_MIGRATION
        elif bonding_progress >= 30:
            return RunnerPhase.MID_PUMP
        else:
            return RunnerPhase.EARLY_PUMP

    async def _calculate_momentum_score(self, token_data: Dict) -> float:
        """Calcule le score de momentum (vitesse de croissance)"""
        score = 0

        # Volume momentum
        volume_24h = token_data.get('volume_24h', 0)
        volume_1h = token_data.get('volume_1h', volume_24h / 24)  # Estimate if not available

        if volume_1h > 0:
            volume_velocity = (volume_1h * 24) / max(volume_24h, 1)
            if volume_velocity > 2:
                score += 30  # Volume accelere fortement
            elif volume_velocity > 1.5:
                score += 20
            elif volume_velocity > 1:
                score += 10

        # Price momentum
        price_change_5m = token_data.get('price_change_5m', 0)
        price_change_1h = token_data.get('price_change_1h', 0)

        if price_change_5m > 20:
            score += 25  # Pump rapide
        elif price_change_5m > 10:
            score += 15
        elif price_change_5m > 5:
            score += 10

        if price_change_1h > 50:
            score += 20
        elif price_change_1h > 25:
            score += 10

        # Holder momentum
        holder_count = token_data.get('holder_count', 0)
        if holder_count > 200:
            score += 15
        elif holder_count > 100:
            score += 10
        elif holder_count > 50:
            score += 5

        # Transaction frequency
        txns = token_data.get('txns_5m', token_data.get('txns', 0))
        if txns > 50:
            score += 10
        elif txns > 20:
            score += 5

        return min(score, 100)

    async def _calculate_accumulation_score(self, token_data: Dict) -> float:
        """Calcule le score d'accumulation (whales/smart money)"""
        score = 50  # Base score

        # Top holder concentration (lower is better for runners)
        top_10_pct = token_data.get('top_10_concentration', 50)
        if top_10_pct < 30:
            score += 20  # Bonne distribution
        elif top_10_pct < 50:
            score += 10
        elif top_10_pct > 70:
            score -= 20  # Trop concentre

        # Dev holding
        dev_holding = token_data.get('dev_holding', 5)
        if dev_holding < 3:
            score += 15  # Dev a peu = safe
        elif dev_holding < 5:
            score += 10
        elif dev_holding > 10:
            score -= 20  # Dev a trop

        # Whale activity (if available)
        whale_buys = token_data.get('whale_buys', 0)
        if whale_buys > 5:
            score += 15
        elif whale_buys > 2:
            score += 10

        # Fresh wallets (lower is better - less bots)
        fresh_wallet_pct = token_data.get('fresh_wallet_percentage', 30)
        if fresh_wallet_pct < 20:
            score += 10
        elif fresh_wallet_pct > 50:
            score -= 15

        return max(0, min(score, 100))

    def _calculate_hype_score(self, token_data: Dict) -> float:
        """Calcule le score de hype social"""
        score = 0

        # Social presence
        if token_data.get('twitter') or token_data.get('has_twitter'):
            score += 20
        if token_data.get('telegram') or token_data.get('has_telegram'):
            score += 15
        if token_data.get('website') or token_data.get('has_website'):
            score += 10

        # Twitter metrics (if available)
        twitter_mentions = token_data.get('twitter_mentions', 0)
        if twitter_mentions > 100:
            score += 25
        elif twitter_mentions > 50:
            score += 15
        elif twitter_mentions > 10:
            score += 5

        # Telegram activity
        telegram_members = token_data.get('telegram_members', 0)
        if telegram_members > 1000:
            score += 20
        elif telegram_members > 500:
            score += 10
        elif telegram_members > 100:
            score += 5

        # KOL involvement
        if token_data.get('kol_detected') or token_data.get('has_kol_involvement'):
            score += 10

        return min(score, 100)

    def _calculate_organic_score(self, token_data: Dict) -> float:
        """Calcule le score de croissance organique"""
        score = 50  # Base

        # Bundle detection (bundles = bad)
        bundle_pct = token_data.get('bundle_percentage', 0)
        if bundle_pct < 5:
            score += 20
        elif bundle_pct < 15:
            score += 10
        elif bundle_pct > 30:
            score -= 25

        # Sniper detection
        sniper_pct = token_data.get('sniper_holdings_percentage', 0)
        if sniper_pct < 10:
            score += 15
        elif sniper_pct > 30:
            score -= 20

        # Buy/sell ratio
        buy_ratio = token_data.get('buy_sell_ratio', 1)
        if buy_ratio > 2:
            score += 15  # Plus d'achats que de ventes
        elif buy_ratio > 1.5:
            score += 10
        elif buy_ratio < 0.5:
            score -= 20  # Beaucoup de ventes

        # Wash trading detection
        if token_data.get('wash_trading_detected') or token_data.get('is_wash_trading'):
            score -= 30

        return max(0, min(score, 100))

    def _calculate_migration_score(self, token_data: Dict) -> float:
        """Calcule la probabilite de migration reussie"""
        score = 0

        # Bonding curve progress
        bonding = token_data.get('bonding_curve_progress', 0)
        if bonding > 90:
            score += 40  # Tres proche de migration
        elif bonding > 70:
            score += 30
        elif bonding > 50:
            score += 20
        elif bonding > 30:
            score += 10

        # Volume suggests momentum
        volume = token_data.get('volume_24h', 0)
        if volume > 50000:
            score += 25
        elif volume > 20000:
            score += 15
        elif volume > 10000:
            score += 10

        # Holder count
        holders = token_data.get('holder_count', 0)
        if holders > 200:
            score += 20
        elif holders > 100:
            score += 15
        elif holders > 50:
            score += 10

        # Social presence
        if token_data.get('twitter') or token_data.get('has_twitter'):
            score += 5
        if token_data.get('telegram') or token_data.get('has_telegram'):
            score += 5

        # Market cap in sweet spot
        mcap = token_data.get('market_cap', token_data.get('usd_market_cap', 0))
        if 40000 <= mcap <= 60000:
            score += 5  # Close to migration threshold

        return min(score, 100)

    def _calculate_runner_score(self, momentum: float, accumulation: float,
                                 hype: float, organic: float, migration: float,
                                 phase: RunnerPhase) -> float:
        """Calcule le score global runner"""

        # Weights depend on phase
        if phase == RunnerPhase.EARLY_PUMP:
            weights = {'momentum': 0.25, 'accumulation': 0.20, 'hype': 0.25,
                      'organic': 0.15, 'migration': 0.15}
        elif phase == RunnerPhase.PRE_MIGRATION:
            weights = {'momentum': 0.30, 'accumulation': 0.15, 'hype': 0.20,
                      'organic': 0.10, 'migration': 0.25}
        elif phase == RunnerPhase.POST_MIGRATION:
            weights = {'momentum': 0.35, 'accumulation': 0.20, 'hype': 0.25,
                      'organic': 0.10, 'migration': 0.10}
        else:
            weights = {'momentum': 0.25, 'accumulation': 0.20, 'hype': 0.20,
                      'organic': 0.15, 'migration': 0.20}

        score = (momentum * weights['momentum'] +
                 accumulation * weights['accumulation'] +
                 hype * weights['hype'] +
                 organic * weights['organic'] +
                 migration * weights['migration'])

        return round(score, 1)

    def _determine_potential(self, runner_score: float, phase: RunnerPhase) -> RunnerPotential:
        """Determine le potentiel du token"""

        if runner_score >= 80:
            return RunnerPotential.MOON
        elif runner_score >= 65:
            return RunnerPotential.RUNNER
        elif runner_score >= 50:
            return RunnerPotential.PUMPER
        elif runner_score >= 35:
            return RunnerPotential.WEAK
        else:
            return RunnerPotential.DUMP

    def _calculate_target_multipliers(self, runner_score: float, phase: RunnerPhase) -> Dict:
        """Calcule les multipliers cibles"""

        base = self.historical_multipliers.get(phase, {'low': 1.5, 'mid': 2, 'high': 5})

        # Adjust based on runner score
        score_factor = runner_score / 70  # Normalize around 70

        return {
            'low': round(base['low'] * score_factor, 1),
            'mid': round(base['mid'] * score_factor, 1),
            'high': round(base['high'] * score_factor, 1)
        }

    def _generate_signals(self, token_data: Dict, runner_score: float,
                          phase: RunnerPhase) -> Tuple[List[str], List[str]]:
        """Genere les signaux et warnings"""
        signals = []
        warnings = []

        # Positive signals
        if runner_score >= 70:
            signals.append("STRONG RUNNER POTENTIAL")

        if token_data.get('volume_24h', 0) > 30000:
            signals.append("High volume activity")

        if token_data.get('holder_count', 0) > 150:
            signals.append("Strong holder base")

        if phase == RunnerPhase.PRE_MIGRATION:
            signals.append("APPROACHING MIGRATION - High momentum zone")

        if phase == RunnerPhase.POST_MIGRATION:
            signals.append("POST-MIGRATION - Watch for continuation")

        if token_data.get('whale_buys', 0) > 3:
            signals.append("Whale accumulation detected")

        if token_data.get('kol_detected'):
            signals.append("KOL involvement")

        # Warnings
        if token_data.get('top_10_concentration', 0) > 60:
            warnings.append("High holder concentration")

        if token_data.get('dev_holding', 0) > 8:
            warnings.append("Dev holds significant supply")

        if token_data.get('bundle_percentage', 0) > 20:
            warnings.append("Bundle activity detected")

        if token_data.get('sniper_holdings_percentage', 0) > 25:
            warnings.append("Heavy sniper presence")

        if token_data.get('buy_sell_ratio', 1) < 0.7:
            warnings.append("Sell pressure increasing")

        return signals, warnings

    def _estimate_time_to_target(self, phase: RunnerPhase, momentum: float) -> str:
        """Estime le temps pour atteindre le target"""

        if momentum >= 80:
            base_time = "5-15 min"
        elif momentum >= 60:
            base_time = "15-30 min"
        elif momentum >= 40:
            base_time = "30 min - 1h"
        else:
            base_time = "1-4h"

        if phase == RunnerPhase.PRE_MIGRATION:
            return f"Migration: ~10-30 min, Target: {base_time}"
        elif phase == RunnerPhase.POST_MIGRATION:
            return f"First pump: {base_time}"
        else:
            return base_time

    def _calculate_entry_zone(self, current_mcap: float, phase: RunnerPhase) -> Tuple[float, float]:
        """Calcule la zone d'entree optimale"""

        if phase == RunnerPhase.EARLY_PUMP:
            return (current_mcap * 0.9, current_mcap * 1.1)
        elif phase == RunnerPhase.MID_PUMP:
            return (current_mcap * 0.95, current_mcap * 1.05)
        elif phase == RunnerPhase.PRE_MIGRATION:
            return (current_mcap * 0.97, current_mcap * 1.02)  # Tight zone
        else:
            return (current_mcap * 0.85, current_mcap * 1.0)  # Buy dips post-migration

    def _get_confidence(self, runner_score: float) -> str:
        """Retourne le niveau de confiance"""
        if runner_score >= 75:
            return "HIGH"
        elif runner_score >= 55:
            return "MEDIUM"
        else:
            return "LOW"

    def format_analysis(self, analysis: RunnerAnalysis) -> str:
        """Formate l'analyse pour affichage"""

        lines = [
            f"{'='*60}",
            f"RUNNER ANALYSIS - {analysis.token_mint[:20]}...",
            f"{'='*60}",
            f"",
            f"Phase: {analysis.phase.value.upper()}",
            f"Potential: {analysis.potential.value.upper()}",
            f"Runner Score: {analysis.runner_score}/100 ({analysis.confidence})",
            f"",
            f"--- SCORES ---",
            f"Momentum:     {analysis.momentum_score}/100",
            f"Accumulation: {analysis.accumulation_score}/100",
            f"Hype:         {analysis.hype_score}/100",
            f"Organic:      {analysis.organic_score}/100",
            f"Migration:    {analysis.migration_score}/100",
            f"",
            f"--- PRICE TARGETS ---",
            f"Current MCap:  ${analysis.current_mcap:,.0f}",
            f"Conservative:  ${analysis.target_mcap_conservative:,.0f} ({analysis.potential_x_low}x)",
            f"Moderate:      ${analysis.target_mcap_moderate:,.0f} ({analysis.potential_x_mid}x)",
            f"Optimistic:    ${analysis.target_mcap_optimistic:,.0f} ({analysis.potential_x_high}x)",
            f"",
            f"Estimated Time: {analysis.estimated_time_to_target}",
            f"Entry Zone: ${analysis.best_entry_zone[0]:,.0f} - ${analysis.best_entry_zone[1]:,.0f}",
            f"",
        ]

        if analysis.signals:
            lines.append("--- SIGNALS ---")
            for s in analysis.signals:
                lines.append(f"  [+] {s}")
            lines.append("")

        if analysis.warnings:
            lines.append("--- WARNINGS ---")
            for w in analysis.warnings:
                lines.append(f"  [!] {w}")
            lines.append("")

        lines.append("="*60)

        return "\n".join(lines)

    async def close(self):
        """Ferme le client HTTP"""
        await self.client.aclose()


# Singleton instance
_runner_detector = None

def get_runner_detector(rpc_url: str = None) -> RunnerDetector:
    """Get or create runner detector singleton"""
    global _runner_detector
    if _runner_detector is None:
        _runner_detector = RunnerDetector(rpc_url)
    return _runner_detector


async def main():
    """Test runner detector"""
    detector = RunnerDetector()

    # Test avec des donnees simulees
    test_token = {
        'mint': 'TEST123456789abcdef',
        'market_cap': 35000,
        'usd_market_cap': 35000,
        'volume_24h': 25000,
        'volume_1h': 5000,
        'holder_count': 120,
        'price_change_5m': 15,
        'price_change_1h': 45,
        'top_10_concentration': 35,
        'dev_holding': 3,
        'fresh_wallet_percentage': 25,
        'bundle_percentage': 8,
        'sniper_holdings_percentage': 12,
        'buy_sell_ratio': 1.8,
        'bonding_curve_progress': 75,
        'has_twitter': True,
        'has_telegram': True,
        'twitter_mentions': 25,
        'whale_buys': 4,
    }

    analysis = await detector.analyze_runner_potential(test_token)
    print(detector.format_analysis(analysis))

    await detector.close()


if __name__ == "__main__":
    asyncio.run(main())

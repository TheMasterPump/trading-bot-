"""
Detect Pump & Dump schemes
Analyzes price action and volume patterns to detect manipulation
"""
import httpx
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class PumpDumpAnalysis:
    """Results of pump & dump analysis"""
    is_pump_dump: bool
    price_volatility: float  # Percentage volatility
    max_price_spike: float  # Maximum price increase (%)
    price_dump_after_spike: float  # Price drop after spike (%)
    rapid_price_changes: int  # Number of rapid price changes
    suspicious_volume_spikes: int  # Volume spikes during price manipulation
    time_since_ath: Optional[int]  # Minutes since all-time high
    current_vs_ath_percentage: float  # Current price vs ATH (%)
    risk_score: int
    red_flags: List[str]

    # NEW: Advanced pattern detection
    pattern_type: Optional[str]  # "fast_pump_slow_dump", "coordinated_pumps", "dead_cat_bounce", "stairs", etc.
    coordinated_pumps_count: int  # Number of coordinated pumps detected
    time_at_peak: Optional[int]  # Minutes spent at peak (if <30min = extreme red flag)
    pump_speed: float  # %/hour during pump phase
    dump_speed: float  # %/hour during dump phase
    stairs_pattern_detected: bool  # Bot trading pattern (price moves in perfect steps)
    dead_cat_bounce_detected: bool  # False recovery after dump
    manipulation_confidence: float  # 0-100% confidence this is manipulation


class PumpDumpDetector:
    """Detects pump and dump schemes by analyzing price patterns"""

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)

    def analyze_pump_dump(self, mint_address: str, token_data: Dict) -> PumpDumpAnalysis:
        """
        Analyze token for pump & dump patterns

        Pump & Dump indicators:
        1. Rapid price spike (>100% in short time)
        2. Immediate dump after spike (>50% drop)
        3. High volatility
        4. Volume spikes coordinated with price spikes
        5. Currently far below ATH (dumped)
        """
        try:
            # Get price history from DexScreener
            price_history = self._get_price_history(mint_address)

            if not price_history or len(price_history) < 10:
                # Not enough data, use basic analysis from token_data
                return self._basic_analysis(token_data)

            # Analyze price patterns
            volatility = self._calculate_volatility(price_history)
            max_spike = self._find_max_price_spike(price_history)
            dump_after_spike = self._find_dump_after_spike(price_history)
            rapid_changes = self._count_rapid_changes(price_history)
            volume_spikes = self._detect_volume_manipulation(price_history)

            # Find ATH and time since
            ath_info = self._find_ath(price_history)
            time_since_ath = ath_info.get("minutes_ago")
            current_vs_ath = ath_info.get("current_vs_ath_pct", 0)

            # Determine if pump & dump
            red_flags = []
            risk_score = 0

            # EXTREME volatility
            if volatility > 150:
                red_flags.append(f"[!!] EXTREME VOLATILITY: {volatility:.0f}% price swings")
                risk_score += 50
            elif volatility > 100:
                red_flags.append(f"[!] High volatility: {volatility:.0f}%")
                risk_score += 30

            # Price spike detection
            if max_spike > 300:
                red_flags.append(f"[!!] MASSIVE PUMP: Price spiked {max_spike:.0f}% (manipulation!)")
                risk_score += 55
            elif max_spike > 150:
                red_flags.append(f"[!!] PUMP DETECTED: Price spiked {max_spike:.0f}%")
                risk_score += 40
            elif max_spike > 100:
                red_flags.append(f"[!] Large price spike: {max_spike:.0f}%")
                risk_score += 25

            # Dump after spike
            if dump_after_spike > 70:
                red_flags.append(f"[!!] DUMPED: Price dropped {dump_after_spike:.0f}% after spike (PUMP & DUMP!)")
                risk_score += 50
            elif dump_after_spike > 50:
                red_flags.append(f"[!!] Major dump: {dump_after_spike:.0f}% drop after spike")
                risk_score += 35
            elif dump_after_spike > 30:
                red_flags.append(f"[!] Significant drop: {dump_after_spike:.0f}% after spike")
                risk_score += 20

            # Rapid price changes
            if rapid_changes > 15:
                red_flags.append(f"[!!] MANIPULATION: {rapid_changes} rapid price changes")
                risk_score += 35
            elif rapid_changes > 10:
                red_flags.append(f"[!] Many rapid price changes: {rapid_changes}")
                risk_score += 20

            # Volume manipulation
            if volume_spikes > 5:
                red_flags.append(f"[!!] Volume manipulation: {volume_spikes} suspicious volume spikes")
                risk_score += 30

            # ATH dump
            if time_since_ath and time_since_ath < 60 and current_vs_ath < 50:
                red_flags.append(f"[!!] DUMPED FROM ATH: Now {current_vs_ath:.0f}% of ATH (reached {time_since_ath}min ago)")
                risk_score += 45
            elif current_vs_ath < 30:
                red_flags.append(f"[!] Far from ATH: Only {current_vs_ath:.0f}% of all-time high")
                risk_score += 25

            # Determine if pump & dump
            is_pump_dump = (
                (max_spike > 150 and dump_after_spike > 50) or  # Clear pump & dump pattern
                (volatility > 150 and rapid_changes > 15) or  # Extreme manipulation
                risk_score >= 70  # High risk score
            )

            # NEW: Detect advanced patterns
            pattern_info = self._detect_advanced_patterns(price_history, max_spike, dump_after_spike)

            return PumpDumpAnalysis(
                is_pump_dump=is_pump_dump,
                price_volatility=volatility,
                max_price_spike=max_spike,
                price_dump_after_spike=dump_after_spike,
                rapid_price_changes=rapid_changes,
                suspicious_volume_spikes=volume_spikes,
                time_since_ath=time_since_ath,
                current_vs_ath_percentage=current_vs_ath,
                risk_score=min(risk_score, 100),
                red_flags=red_flags,
                # NEW fields
                pattern_type=pattern_info.get("pattern_type"),
                coordinated_pumps_count=pattern_info.get("coordinated_pumps", 0),
                time_at_peak=pattern_info.get("time_at_peak"),
                pump_speed=pattern_info.get("pump_speed", 0),
                dump_speed=pattern_info.get("dump_speed", 0),
                stairs_pattern_detected=pattern_info.get("stairs_pattern", False),
                dead_cat_bounce_detected=pattern_info.get("dead_cat_bounce", False),
                manipulation_confidence=pattern_info.get("manipulation_confidence", 0)
            )

        except Exception as e:
            # Return safe defaults on error
            return PumpDumpAnalysis(
                is_pump_dump=False,
                price_volatility=0,
                max_price_spike=0,
                price_dump_after_spike=0,
                rapid_price_changes=0,
                suspicious_volume_spikes=0,
                time_since_ath=None,
                current_vs_ath_percentage=100,
                risk_score=0,
                red_flags=[f"Could not analyze pump & dump: {str(e)}"],
                # NEW fields defaults
                pattern_type=None,
                coordinated_pumps_count=0,
                time_at_peak=None,
                pump_speed=0,
                dump_speed=0,
                stairs_pattern_detected=False,
                dead_cat_bounce_detected=False,
                manipulation_confidence=0
            )

    def _get_price_history(self, mint_address: str) -> Optional[List[Dict]]:
        """Get price history from DexScreener"""
        try:
            # DexScreener doesn't have historical data in free API
            # We'd need to track this ourselves or use paid services
            # For now, return None (will use basic analysis)
            return None

        except Exception:
            return None

    def _basic_analysis(self, token_data: Dict) -> PumpDumpAnalysis:
        """Basic pump & dump analysis using available price change data"""
        # Use available data to make assessment
        market_cap = token_data.get("usd_market_cap", 0)
        volume_24h = token_data.get("volume_24h", 0)

        # Get price changes if available
        price_changes = token_data.get("priceChange", {})
        change_5m = abs(float(price_changes.get('m5', 0) or 0))
        change_1h = abs(float(price_changes.get('h1', 0) or 0))
        change_6h = abs(float(price_changes.get('h6', 0) or 0))
        change_24h = float(price_changes.get('h24', 0) or 0)  # Keep sign for direction

        red_flags = []
        risk_score = 0

        # Calculate volatility from price changes (average of absolute changes)
        volatility = (change_5m + change_1h + change_6h + abs(change_24h)) / 4 if any([change_5m, change_1h, change_6h, change_24h]) else 0

        # Find max spike (highest positive change)
        max_spike = max([change_5m, change_1h, change_6h, abs(change_24h)])

        # Detect pump & dump patterns
        if max_spike > 300:
            red_flags.append(f"[!!] MASSIVE PUMP: Price spiked {max_spike:.0f}% (manipulation!)")
            risk_score += 55
        elif max_spike > 150:
            red_flags.append(f"[!!] PUMP DETECTED: Price spiked {max_spike:.0f}%")
            risk_score += 40
        elif max_spike > 100:
            red_flags.append(f"[!] Large price spike: {max_spike:.0f}%")
            risk_score += 25

        # Detect dumps (large negative 24h change)
        if change_24h < -50:
            red_flags.append(f"[!!] DUMPED: Price dropped {abs(change_24h):.0f}% in 24h")
            risk_score += 50
        elif change_24h < -30:
            red_flags.append(f"[!] Price dropped {abs(change_24h):.0f}% in 24h")
            risk_score += 30

        # High volatility
        if volatility > 150:
            red_flags.append(f"[!!] EXTREME VOLATILITY: {volatility:.0f}% average price swings")
            risk_score += 50
        elif volatility > 100:
            red_flags.append(f"[!] High volatility: {volatility:.0f}%")
            risk_score += 30

        # Very low mcap after launch = likely dumped
        if market_cap < 2000:
            red_flags.append("[!] Very low market cap - may have been dumped")
            risk_score += 20

        # No volume = dead/dumped
        if volume_24h == 0:
            red_flags.append("[!] No trading volume - token may be dead")
            risk_score += 15

        # Determine if pump & dump
        is_pump_dump = (
            (max_spike > 150 and change_24h < -30) or  # Pumped then dumped
            (volatility > 150) or  # Extreme volatility
            risk_score >= 70
        )

        # NEW: Enhanced pattern detection with available data
        pattern_info = self._detect_patterns_from_changes(change_5m, change_1h, change_6h, change_24h, max_spike)

        return PumpDumpAnalysis(
            is_pump_dump=is_pump_dump,
            price_volatility=volatility,
            max_price_spike=max_spike,
            price_dump_after_spike=abs(change_24h) if change_24h < 0 else 0,
            rapid_price_changes=sum(1 for c in [change_5m, change_1h, change_6h] if c > 20),
            suspicious_volume_spikes=0,  # Can't determine without historical data
            time_since_ath=None,
            current_vs_ath_percentage=100,
            risk_score=min(risk_score, 100),
            red_flags=red_flags,
            # NEW fields
            pattern_type=pattern_info.get("pattern_type"),
            coordinated_pumps_count=0,  # Need historical data
            time_at_peak=None,  # Need historical data
            pump_speed=pattern_info.get("pump_speed", 0),
            dump_speed=pattern_info.get("dump_speed", 0),
            stairs_pattern_detected=False,  # Need full price history
            dead_cat_bounce_detected=pattern_info.get("dead_cat_bounce", False),
            manipulation_confidence=pattern_info.get("manipulation_confidence", 0)
        )

    def _calculate_volatility(self, price_history: List[Dict]) -> float:
        """Calculate price volatility (standard deviation as % of mean)"""
        if not price_history:
            return 0

        prices = [p.get("price", 0) for p in price_history]
        prices = [p for p in prices if p > 0]

        if len(prices) < 2:
            return 0

        import statistics
        mean = statistics.mean(prices)
        if mean == 0:
            return 0

        stdev = statistics.stdev(prices)
        volatility = (stdev / mean) * 100

        return volatility

    def _find_max_price_spike(self, price_history: List[Dict]) -> float:
        """Find maximum price increase in short period"""
        if not price_history or len(price_history) < 2:
            return 0

        prices = [p.get("price", 0) for p in price_history]
        max_spike = 0

        # Check consecutive prices for spikes
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                spike = ((prices[i] - prices[i-1]) / prices[i-1]) * 100
                max_spike = max(max_spike, spike)

        return max_spike

    def _find_dump_after_spike(self, price_history: List[Dict]) -> float:
        """Find maximum price drop after a spike"""
        if not price_history or len(price_history) < 3:
            return 0

        prices = [p.get("price", 0) for p in price_history]
        max_dump = 0

        # Find peaks and subsequent drops
        for i in range(1, len(prices) - 1):
            # Is this a peak?
            if prices[i] > prices[i-1]:
                # Find drop after peak
                for j in range(i+1, min(i+10, len(prices))):  # Look 10 periods ahead
                    if prices[i] > 0:
                        drop = ((prices[i] - prices[j]) / prices[i]) * 100
                        max_dump = max(max_dump, drop)

        return max_dump

    def _count_rapid_changes(self, price_history: List[Dict]) -> int:
        """Count number of rapid price changes (>20% in one period)"""
        if not price_history or len(price_history) < 2:
            return 0

        prices = [p.get("price", 0) for p in price_history]
        rapid_count = 0

        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                change = abs((prices[i] - prices[i-1]) / prices[i-1]) * 100
                if change > 20:
                    rapid_count += 1

        return rapid_count

    def _detect_volume_manipulation(self, price_history: List[Dict]) -> int:
        """Detect suspicious volume spikes"""
        if not price_history or len(price_history) < 5:
            return 0

        volumes = [p.get("volume", 0) for p in price_history]
        volumes = [v for v in volumes if v > 0]

        if len(volumes) < 5:
            return 0

        import statistics
        mean_volume = statistics.mean(volumes)

        if mean_volume == 0:
            return 0

        # Count spikes >3x average
        spikes = sum(1 for v in volumes if v > mean_volume * 3)

        return spikes

    def _find_ath(self, price_history: List[Dict]) -> Dict:
        """Find all-time high and time since"""
        if not price_history:
            return {"minutes_ago": None, "current_vs_ath_pct": 100}

        prices_with_time = [
            (p.get("price", 0), p.get("timestamp"))
            for p in price_history
            if p.get("price", 0) > 0
        ]

        if not prices_with_time:
            return {"minutes_ago": None, "current_vs_ath_pct": 100}

        # Find ATH
        ath_price = max(p[0] for p in prices_with_time)
        current_price = prices_with_time[-1][0]

        # Find time of ATH
        ath_entry = next((p for p in prices_with_time if p[0] == ath_price), None)

        if ath_entry and ath_entry[1]:
            ath_timestamp = ath_entry[1]
            current_timestamp = prices_with_time[-1][1]

            if current_timestamp and ath_timestamp:
                minutes_ago = (current_timestamp - ath_timestamp) // 60
            else:
                minutes_ago = None
        else:
            minutes_ago = None

        # Calculate percentage
        current_vs_ath = (current_price / ath_price * 100) if ath_price > 0 else 100

        return {
            "minutes_ago": minutes_ago,
            "current_vs_ath_pct": current_vs_ath
        }

    def _detect_patterns_from_changes(self, change_5m: float, change_1h: float, change_6h: float, change_24h: float, max_spike: float) -> Dict:
        """
        Detect pump & dump patterns from price change data
        This is used when we don't have full price history
        """
        pattern_type = None
        manipulation_confidence = 0
        pump_speed = 0
        dump_speed = 0
        dead_cat_bounce = False

        # Calculate pump speed (% per hour)
        if change_5m > 50:  # Significant 5min change
            pump_speed = change_5m * 12  # Extrapolate to hourly
        elif change_1h > 100:
            pump_speed = change_1h

        # Calculate dump speed
        if change_24h < -30:
            dump_speed = abs(change_24h)

        # Pattern 1: Fast Pump Slow Dump
        # Rapid spike in 5m-1h, but slow dump over 24h
        if change_5m > 100 and change_24h < -20:
            pattern_type = "fast_pump_slow_dump"
            manipulation_confidence = min(80 + (change_5m / 10), 100)

        # Pattern 2: Massive pump still ongoing
        elif change_5m > 200 and change_1h > 300:
            pattern_type = "extreme_pump_ongoing"
            manipulation_confidence = 95

        # Pattern 3: Recent pump, starting dump
        elif change_1h > 150 and change_6h < 50:
            pattern_type = "pump_peaked_dumping"
            manipulation_confidence = min(70 + (change_1h / 10), 95)

        # Pattern 4: Dead cat bounce detection
        # Price dumped heavily but showing small recovery
        if change_24h < -50 and change_1h > 10 and change_5m > 5:
            dead_cat_bounce = True
            manipulation_confidence = max(manipulation_confidence, 60)

        # Pattern 5: Gradual pump (less suspicious but still notable)
        elif change_24h > 200 and change_1h < 150:
            pattern_type = "gradual_pump"
            manipulation_confidence = 40

        # Increase confidence based on volatility indicators
        if change_5m > 50 and abs(change_1h - change_5m * 12) > 100:
            manipulation_confidence = min(manipulation_confidence + 15, 100)

        return {
            "pattern_type": pattern_type,
            "pump_speed": pump_speed,
            "dump_speed": dump_speed,
            "dead_cat_bounce": dead_cat_bounce,
            "manipulation_confidence": manipulation_confidence
        }

    def _detect_advanced_patterns(self, price_history: List[Dict], max_spike: float, dump_after_spike: float) -> Dict:
        """
        Detect advanced pump & dump patterns with full price history
        This provides much more accurate detection when historical data is available
        """
        if not price_history or len(price_history) < 10:
            return {
                "pattern_type": None,
                "coordinated_pumps": 0,
                "time_at_peak": None,
                "pump_speed": 0,
                "dump_speed": 0,
                "stairs_pattern": False,
                "dead_cat_bounce": False,
                "manipulation_confidence": 0
            }

        # Extract prices with timestamps
        price_points = [(p.get("price", 0), p.get("timestamp", 0)) for p in price_history if p.get("price", 0) > 0]

        if len(price_points) < 10:
            return self._detect_patterns_from_changes(0, 0, 0, 0, max_spike)

        prices = [p[0] for p in price_points]
        timestamps = [p[1] for p in price_points]

        # Pattern Detection
        coordinated_pumps = self._find_coordinated_pumps(prices)
        time_at_peak = self._calculate_time_at_peak(prices, timestamps)
        stairs_pattern = self._detect_stairs_pattern(prices)
        dead_cat_bounce = self._detect_dead_cat_bounce(prices)

        # Calculate pump and dump speeds
        pump_speed, dump_speed = self._calculate_pump_dump_speeds(prices, timestamps)

        # Determine pattern type
        pattern_type = None
        manipulation_confidence = 0

        if coordinated_pumps >= 3:
            pattern_type = "coordinated_multiple_pumps"
            manipulation_confidence = 90
        elif stairs_pattern:
            pattern_type = "stairs_bot_trading"
            manipulation_confidence = 85
        elif pump_speed > 500 and dump_speed > 50:
            pattern_type = "fast_pump_slow_dump"
            manipulation_confidence = 80
        elif time_at_peak and time_at_peak < 30 and max_spike > 200:
            pattern_type = "flash_pump_dump"
            manipulation_confidence = 95
        elif dead_cat_bounce:
            pattern_type = "dead_cat_bounce"
            manipulation_confidence = max(manipulation_confidence, 70)

        # Adjust confidence based on multiple factors
        if time_at_peak and time_at_peak < 15:
            manipulation_confidence = min(manipulation_confidence + 10, 100)
        if coordinated_pumps > 0:
            manipulation_confidence = min(manipulation_confidence + (coordinated_pumps * 10), 100)

        return {
            "pattern_type": pattern_type,
            "coordinated_pumps": coordinated_pumps,
            "time_at_peak": time_at_peak,
            "pump_speed": pump_speed,
            "dump_speed": dump_speed,
            "stairs_pattern": stairs_pattern,
            "dead_cat_bounce": dead_cat_bounce,
            "manipulation_confidence": manipulation_confidence
        }

    def _find_coordinated_pumps(self, prices: List[float]) -> int:
        """Detect multiple coordinated pumps (same pattern repeated)"""
        if len(prices) < 20:
            return 0

        pumps = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                change = ((prices[i] - prices[i-1]) / prices[i-1]) * 100
                if change > 50:  # Significant pump
                    pumps.append((i, change))

        # Find similar pumps (within 20% of each other)
        coordinated_count = 0
        for i, (idx1, change1) in enumerate(pumps):
            similar = sum(1 for idx2, change2 in pumps[i+1:] if abs(change1 - change2) < change1 * 0.2)
            if similar > 0:
                coordinated_count = max(coordinated_count, similar + 1)

        return coordinated_count

    def _calculate_time_at_peak(self, prices: List[float], timestamps: List[int]) -> Optional[int]:
        """Calculate how long price stayed near peak"""
        if len(prices) < 5 or not timestamps:
            return None

        peak_price = max(prices)
        peak_threshold = peak_price * 0.95  # Within 5% of peak

        # Find all periods at peak
        peak_periods = []
        in_peak = False
        peak_start = None

        for i, price in enumerate(prices):
            if price >= peak_threshold:
                if not in_peak:
                    in_peak = True
                    peak_start = timestamps[i]
            else:
                if in_peak and peak_start:
                    peak_periods.append(timestamps[i-1] - peak_start)
                    in_peak = False

        if not peak_periods:
            return None

        # Return longest peak period in minutes
        max_peak_time = max(peak_periods)
        return max_peak_time // 60  # Convert seconds to minutes

    def _detect_stairs_pattern(self, prices: List[float]) -> bool:
        """Detect stairs pattern (bot trading - price moves in perfect steps)"""
        if len(prices) < 15:
            return False

        # Calculate price changes
        changes = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                change = ((prices[i] - prices[i-1]) / prices[i-1]) * 100
                changes.append(change)

        if len(changes) < 10:
            return False

        # Look for repeating patterns
        import statistics
        # Group changes into buckets
        positive_changes = [c for c in changes if c > 1]

        if len(positive_changes) < 5:
            return False

        # Check if changes are too similar (bot pattern)
        stdev = statistics.stdev(positive_changes) if len(positive_changes) > 1 else 100
        mean = statistics.mean(positive_changes)

        # If standard deviation is very low relative to mean, it's likely a bot
        if mean > 5 and stdev < mean * 0.15:
            return True

        return False

    def _detect_dead_cat_bounce(self, prices: List[float]) -> bool:
        """Detect dead cat bounce (small recovery after major dump)"""
        if len(prices) < 10:
            return False

        # Find the major dump
        max_price = max(prices)
        min_price = min(prices)

        if max_price == 0:
            return False

        dump_percentage = ((max_price - min_price) / max_price) * 100

        if dump_percentage < 50:  # No major dump
            return False

        # Find position of min and max
        max_idx = prices.index(max_price)
        min_idx = prices.index(min_price)

        # Dump must come after pump
        if min_idx <= max_idx:
            return False

        # Check if there's a small recovery after the dump
        if min_idx < len(prices) - 3:
            recovery_prices = prices[min_idx:min_idx+5]
            recovery = ((max(recovery_prices) - min_price) / min_price) * 100

            # Small recovery (5-30%) after major dump = dead cat bounce
            if 5 < recovery < 30:
                return True

        return False

    def _calculate_pump_dump_speeds(self, prices: List[float], timestamps: List[int]) -> tuple:
        """Calculate pump speed (%/hour) and dump speed (%/hour)"""
        if len(prices) < 5 or not timestamps:
            return (0, 0)

        # Find pump phase (rising price)
        pump_speed = 0
        max_price_idx = prices.index(max(prices))

        if max_price_idx > 0:
            # Calculate speed to peak
            time_to_peak = (timestamps[max_price_idx] - timestamps[0]) / 3600  # hours
            if time_to_peak > 0 and prices[0] > 0:
                price_increase = ((prices[max_price_idx] - prices[0]) / prices[0]) * 100
                pump_speed = price_increase / time_to_peak

        # Find dump phase (falling price)
        dump_speed = 0
        if max_price_idx < len(prices) - 1:
            time_from_peak = (timestamps[-1] - timestamps[max_price_idx]) / 3600  # hours
            if time_from_peak > 0 and prices[max_price_idx] > 0:
                price_decrease = ((prices[max_price_idx] - prices[-1]) / prices[max_price_idx]) * 100
                dump_speed = price_decrease / time_from_peak

        return (pump_speed, dump_speed)

    def close(self):
        """Close HTTP client"""
        self.client.close()

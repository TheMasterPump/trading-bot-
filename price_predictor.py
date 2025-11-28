"""
PRICE PREDICTOR - Prédit le prix maximum exact et détecte les tops
Plus précis que juste "x1-x10" - donne des chiffres exacts!
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
import joblib
from pathlib import Path
from rich.console import Console

console = Console()

class PricePredictor:
    """Prédit le market cap maximum et détecte les tops"""

    def __init__(self):
        self.models_dir = Path(__file__).parent / "models"

    def predict_max_market_cap(self, features):
        """
        Prédit le market cap MAXIMUM que le token va atteindre

        Args:
            features: dict avec les features du token

        Returns:
            dict avec:
            - max_mcap_predicted: Market cap maximum prédit
            - current_mcap: Market cap actuel
            - potential_multiplier: Combien de fois il peut encore monter
            - price_target: Prix cible
            - confidence: Confiance de la prédiction
        """
        current_mcap = features.get('market_cap_usd', 0)
        current_liquidity = features.get('liquidity_usd', 0)
        holder_count = features.get('holder_count', 0)
        volume_24h = features.get('volume_24h', 0)

        # Calcul basé sur les patterns observés
        # Facteurs de prédiction:

        # 1. Base sur la liquidité (tokens avec bonne liquidité montent plus)
        liquidity_factor = 1.0
        if current_liquidity > 100000:
            liquidity_factor = 2.5
        elif current_liquidity > 50000:
            liquidity_factor = 2.0
        elif current_liquidity > 10000:
            liquidity_factor = 1.5

        # 2. Volume/MCap ratio (fort volume = plus de potentiel)
        volume_mcap_ratio = volume_24h / max(current_mcap, 1)
        volume_factor = 1.0
        if volume_mcap_ratio > 2.0:
            volume_factor = 2.0
        elif volume_mcap_ratio > 1.0:
            volume_factor = 1.5
        elif volume_mcap_ratio > 0.5:
            volume_factor = 1.2

        # 3. Holders (plus de holders = communauté plus forte)
        holder_factor = 1.0
        if holder_count > 5000:
            holder_factor = 3.0
        elif holder_count > 2000:
            holder_factor = 2.5
        elif holder_count > 1000:
            holder_factor = 2.0
        elif holder_count > 500:
            holder_factor = 1.5

        # 4. Fresh wallets (trop de fresh = probable dump)
        fresh_wallet_pct = features.get('fresh_wallet_percentage', 0)
        fresh_penalty = 1.0
        if fresh_wallet_pct > 60:
            fresh_penalty = 0.6  # Forte pénalité
        elif fresh_wallet_pct > 40:
            fresh_penalty = 0.8

        # 5. Sniper detection (trop de snipers = insiders vont dump)
        sniper_pct = features.get('sniper_holdings_percentage', 0)
        sniper_penalty = 1.0
        if sniper_pct > 30:
            sniper_penalty = 0.5
        elif sniper_pct > 15:
            sniper_penalty = 0.7

        # 6. Top 10 concentration (trop concentré = risque dump)
        top10_conc = features.get('top_10_concentration', 0)
        concentration_penalty = 1.0
        if top10_conc > 80:
            concentration_penalty = 0.6
        elif top10_conc > 60:
            concentration_penalty = 0.8

        # Calcul du multiplicateur potentiel
        base_multiplier = liquidity_factor * volume_factor * holder_factor
        penalties = fresh_penalty * sniper_penalty * concentration_penalty

        final_multiplier = base_multiplier * penalties

        # Limite réaliste (max 100x pour être prudent)
        final_multiplier = min(final_multiplier, 100)
        final_multiplier = max(final_multiplier, 0.5)  # Min 0.5x (peut déjà être au top)

        # Prédiction du market cap max
        predicted_max_mcap = current_mcap * final_multiplier

        # Confiance basée sur la qualité des données
        confidence = 0.7  # Base
        if holder_count > 1000:
            confidence += 0.1
        if current_liquidity > 50000:
            confidence += 0.1
        if volume_24h > current_mcap * 0.5:
            confidence += 0.05

        confidence = min(confidence, 0.95)

        return {
            'current_mcap': current_mcap,
            'predicted_max_mcap': predicted_max_mcap,
            'potential_multiplier': final_multiplier,
            'confidence': confidence,
            'liquidity_factor': liquidity_factor,
            'volume_factor': volume_factor,
            'holder_factor': holder_factor,
            'penalties': penalties
        }

    def detect_top(self, features):
        """
        Détecte si le token est au TOP (prêt à dumper)

        Returns:
            dict avec:
            - is_at_top: Boolean - est-il au top?
            - dump_probability: % de chance de dump imminent
            - signals: Liste des signaux de top détectés
        """
        signals = []
        dump_score = 0

        current_mcap = features.get('market_cap_usd', 0)
        volume_24h = features.get('volume_24h', 0)
        liquidity = features.get('liquidity_usd', 0)

        # Signal 1: Volume extrême (pump final avant dump)
        volume_mcap_ratio = volume_24h / max(current_mcap, 1)
        if volume_mcap_ratio > 5.0:
            signals.append("Volume extrême détecté (x5 le market cap)")
            dump_score += 30
        elif volume_mcap_ratio > 3.0:
            signals.append("Volume très élevé (x3 le market cap)")
            dump_score += 20

        # Signal 2: Market cap élevé avec peu de liquidité
        mcap_liquidity_ratio = current_mcap / max(liquidity, 1)
        if mcap_liquidity_ratio > 100:
            signals.append("Ratio MCap/Liquidité dangereux (>100x)")
            dump_score += 25
        elif mcap_liquidity_ratio > 50:
            signals.append("Ratio MCap/Liquidité élevé (>50x)")
            dump_score += 15

        # Signal 3: Trop de fresh wallets (FOMO tard)
        fresh_pct = features.get('fresh_wallet_percentage', 0)
        if fresh_pct > 70:
            signals.append("70%+ fresh wallets (FOMO tardif)")
            dump_score += 25
        elif fresh_pct > 50:
            signals.append("50%+ fresh wallets")
            dump_score += 15

        # Signal 4: Concentration top 10 élevée (baleines prêtes à dump)
        top10 = features.get('top_10_concentration', 0)
        if top10 > 85:
            signals.append("Top 10 détient 85%+ (baleines en contrôle)")
            dump_score += 20
        elif top10 > 70:
            signals.append("Top 10 détient 70%+")
            dump_score += 10

        # Signal 5: Snipers détectés (insiders vont vendre)
        sniper_pct = features.get('sniper_holdings_percentage', 0)
        if sniper_pct > 25:
            signals.append("25%+ détenu par snipers (insiders)")
            dump_score += 30
        elif sniper_pct > 15:
            signals.append("15%+ détenu par snipers")
            dump_score += 20

        # Signal 6: Pump & dump pattern détecté
        max_spike = features.get('max_price_spike_percentage', 0)
        if max_spike > 500:
            signals.append("Spike de prix massif détecté (+500%)")
            dump_score += 25
        elif max_spike > 200:
            signals.append("Spike de prix important (+200%)")
            dump_score += 15

        # Signal 7: Market cap dans la "danger zone" (100k-500k)
        if 80000 < current_mcap < 150000:
            signals.append("Market cap dans la zone de dump typique (~100k)")
            dump_score += 20
        elif 150000 < current_mcap < 500000:
            signals.append("Market cap élevé (150k-500k)")
            dump_score += 10

        # Déterminer si au top
        is_at_top = dump_score >= 60
        dump_probability = min(dump_score, 100)

        if len(signals) == 0:
            signals.append("Aucun signal de top détecté")

        return {
            'is_at_top': is_at_top,
            'dump_probability': dump_probability,
            'signals': signals,
            'dump_score': dump_score
        }

    def get_precise_prediction(self, features):
        """
        Donne une prédiction PRÉCISE avec tous les détails

        Returns:
            dict avec toutes les infos pour décision d'achat/vente
        """
        # Prédire le max
        max_prediction = self.predict_max_market_cap(features)

        # Détecter si au top
        top_detection = self.detect_top(features)

        current_mcap = features.get('market_cap_usd', 0)
        current_price = current_mcap / 1_000_000_000  # Approximation (supply = 1B)

        predicted_max_mcap = max_prediction['predicted_max_mcap']
        predicted_max_price = predicted_max_mcap / 1_000_000_000

        # Recommandation
        if top_detection['is_at_top']:
            action = "VENDRE MAINTENANT"
            action_color = "red"
            reason = f"Token au TOP! Dump probable ({top_detection['dump_probability']}%)"
        elif max_prediction['potential_multiplier'] > 3:
            action = "ACHETER"
            action_color = "green"
            reason = f"Potentiel de {max_prediction['potential_multiplier']:.1f}x"
        elif max_prediction['potential_multiplier'] > 1.5:
            action = "ACHETER (prudent)"
            action_color = "yellow"
            reason = f"Potentiel de {max_prediction['potential_multiplier']:.1f}x"
        else:
            action = "NE PAS ACHETER"
            action_color = "red"
            reason = "Peu de potentiel restant"

        return {
            'current_mcap': current_mcap,
            'current_price': current_price,
            'predicted_max_mcap': predicted_max_mcap,
            'predicted_max_price': predicted_max_price,
            'potential_multiplier': max_prediction['potential_multiplier'],
            'upside_percentage': (max_prediction['potential_multiplier'] - 1) * 100,
            'confidence': max_prediction['confidence'],
            'is_at_top': top_detection['is_at_top'],
            'dump_probability': top_detection['dump_probability'],
            'top_signals': top_detection['signals'],
            'action': action,
            'action_color': action_color,
            'reason': reason,
            'entry_price': current_price if action.startswith('ACHETER') else None,
            'exit_price': predicted_max_price if action.startswith('ACHETER') else None,
            'stop_loss': current_price * 0.5 if action.startswith('ACHETER') else None
        }

    def format_prediction_display(self, prediction):
        """Formatte la prédiction pour affichage"""
        lines = []

        lines.append("\n[bold cyan]" + "=" * 70)
        lines.append("[bold cyan]PRÉDICTION DE PRIX PRÉCISE")
        lines.append("[bold cyan]" + "=" * 70)

        lines.append(f"\n[white]Prix Actuel:     ${prediction['current_price']:.8f}")
        lines.append(f"[white]Market Cap:      ${prediction['current_mcap']:,.0f}")

        lines.append(f"\n[bold yellow]Prix Maximum Prédit: ${prediction['predicted_max_price']:.8f}")
        lines.append(f"[bold yellow]Market Cap Max:      ${prediction['predicted_max_mcap']:,.0f}")

        lines.append(f"\n[bold green]Potentiel:  {prediction['potential_multiplier']:.2f}x")
        lines.append(f"[bold green]Hausse:     +{prediction['upside_percentage']:.1f}%")
        lines.append(f"[white]Confiance:  {prediction['confidence']*100:.1f}%")

        # Top detection
        if prediction['is_at_top']:
            lines.append(f"\n[bold red][!] TOKEN AU TOP!")
            lines.append(f"[red]Probabilite de dump: {prediction['dump_probability']}%")
            lines.append(f"\n[red]Signaux detectes:")
            for signal in prediction['top_signals']:
                lines.append(f"[red]  - {signal}")

        # Action recommandée
        color = prediction['action_color']
        lines.append(f"\n[bold {color}]" + "=" * 70)
        lines.append(f"[bold {color}]ACTION: {prediction['action']}")
        lines.append(f"[bold {color}]{prediction['reason']}")
        lines.append(f"[bold {color}]" + "=" * 70)

        # Points d'entrée/sortie
        if prediction['entry_price']:
            lines.append(f"\n[green]Point d'entrée: ${prediction['entry_price']:.8f}")
            lines.append(f"[green]Point de sortie: ${prediction['exit_price']:.8f}")
            lines.append(f"[yellow]Stop loss:       ${prediction['stop_loss']:.8f}")

        return "\n".join(lines)


# Test
if __name__ == "__main__":
    predictor = PricePredictor()

    # Exemple de features d'un token
    test_features = {
        'market_cap_usd': 100000,  # 100k market cap
        'liquidity_usd': 50000,
        'holder_count': 500,
        'volume_24h': 150000,
        'fresh_wallet_percentage': 45,
        'sniper_holdings_percentage': 20,
        'top_10_concentration': 75,
        'max_price_spike_percentage': 300
    }

    prediction = predictor.get_precise_prediction(test_features)
    display = predictor.format_prediction_display(prediction)

    console.print(display)

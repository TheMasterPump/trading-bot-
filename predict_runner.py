"""
RUNNER PREDICTOR - Utilise les modeles entraines pour predire
"Ce token a 85% de chance de faire 5x, target $350k"
"""

import json
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class RunnerPrediction:
    """Resultat de la prediction"""
    # Probabilites
    runner_probability: float      # 0-100%
    migration_probability: float   # 0-100%

    # Prix
    current_mcap: float
    predicted_price: float         # Prix final predit
    target_conservative: float     # Target pessimiste
    target_moderate: float         # Target modere
    target_optimistic: float       # Target optimiste

    # Multipliers
    potential_x: float             # Ex: 5.2x

    # Classification
    category: str                  # MOON / RUNNER / PUMPER / WEAK / RUG
    confidence: str                # HIGH / MEDIUM / LOW

    # Recommendation
    action: str                    # BUY NOW / BUY / CONSIDER / WAIT / SKIP
    reason: str


class RunnerPredictor:
    """Predictor qui utilise les modeles ML entraines"""

    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.loaded = False

        # Charger les modeles
        self._load_models()

    def _load_models(self):
        """Charge les modeles depuis le disque"""
        try:
            # Classifier
            self.classifier = joblib.load(self.models_dir / 'runner_classifier_latest.pkl')
            self.clf_scaler = joblib.load(self.models_dir / 'runner_classifier_scaler_latest.pkl')

            # Regressor
            self.regressor = joblib.load(self.models_dir / 'price_regressor_latest.pkl')
            self.reg_scaler = joblib.load(self.models_dir / 'price_regressor_scaler_latest.pkl')

            # Migration classifier
            self.migration_clf = joblib.load(self.models_dir / 'migration_classifier_latest.pkl')
            self.mig_scaler = joblib.load(self.models_dir / 'migration_classifier_scaler_latest.pkl')

            # Feature names
            with open(self.models_dir / 'runner_feature_names.json', 'r') as f:
                self.feature_names = json.load(f)

            with open(self.models_dir / 'migration_feature_names.json', 'r') as f:
                self.migration_feature_names = json.load(f)

            self.loaded = True
            print("[PREDICTOR] Modeles charges avec succes!")

        except Exception as e:
            print(f"[PREDICTOR] Erreur chargement modeles: {e}")
            print("[PREDICTOR] Lance d'abord: python train_runner_model.py")
            self.loaded = False

    def extract_features(self, token_data: Dict) -> Dict:
        """Extrait les features d'un token pour prediction"""
        features = {}

        # === SNAPSHOTS FEATURES ===
        for snap_name in ['3s', '5s', '7s', '10s', '15s', '30s', '1min', '5min', '10min']:
            snap = token_data.get(snap_name, {}) or {}

            prefix = snap_name
            features[f'{prefix}_txn'] = snap.get('txn', 0)
            features[f'{prefix}_buy_ratio'] = snap.get('buy_ratio', 0)
            features[f'{prefix}_traders'] = snap.get('traders', 0)
            features[f'{prefix}_mc'] = snap.get('mc', 0)

            if snap_name in ['10s', '15s', '30s']:
                features[f'{prefix}_buys'] = snap.get('buys', 0)
                features[f'{prefix}_sells'] = snap.get('sells', 0)
                features[f'{prefix}_big_buys_100'] = snap.get('big_buys_100', 0)
                features[f'{prefix}_big_buys_500'] = snap.get('big_buys_500', 0)
                features[f'{prefix}_total_buy_volume'] = snap.get('total_buy_volume', 0)
                features[f'{prefix}_smart_money'] = snap.get('smart_money_count', 0)
                features[f'{prefix}_whale_count'] = snap.get('whale_count', 0)

        # === VELOCITY & MOMENTUM ===
        mc_10s = features.get('10s_mc', 0)
        mc_30s = features.get('30s_mc', 0)
        mc_1min = features.get('1min_mc', 0)
        mc_5min = features.get('5min_mc', 0)

        if mc_10s > 0:
            features['mc_growth_10s_to_30s'] = (mc_30s - mc_10s) / mc_10s
            features['mc_growth_10s_to_1min'] = (mc_1min - mc_10s) / mc_10s
        else:
            features['mc_growth_10s_to_30s'] = 0
            features['mc_growth_10s_to_1min'] = 0

        if mc_30s > 0:
            features['mc_growth_30s_to_5min'] = (mc_5min - mc_30s) / mc_30s
        else:
            features['mc_growth_30s_to_5min'] = 0

        # Transaction velocity
        features['txn_velocity_10s'] = features.get('10s_txn', 0) / 10
        features['txn_velocity_30s'] = features.get('30s_txn', 0) / 30
        features['txn_velocity_1min'] = features.get('1min_txn', 0) / 60

        # Trader growth
        traders_10s = features.get('10s_traders', 0)
        if traders_10s > 0:
            features['trader_growth_10s_to_30s'] = features.get('30s_traders', 0) / traders_10s
            features['trader_growth_10s_to_1min'] = features.get('1min_traders', 0) / traders_10s
        else:
            features['trader_growth_10s_to_30s'] = 0
            features['trader_growth_10s_to_1min'] = 0

        # === WHALE METRICS ===
        features['whale_count'] = token_data.get('whale_count', 0)
        features['whale_total_volume'] = token_data.get('whale_total_volume_usd', 0)
        features['num_whale_wallets'] = len(token_data.get('whale_wallets_detected', []))

        # === ML METRICS ===
        ml = token_data.get('ml_metrics', {}) or {}
        features['peak_velocity'] = ml.get('peak_velocity', 0)
        features['avg_velocity'] = ml.get('avg_velocity', 0)
        features['acceleration'] = ml.get('acceleration', 0)
        features['gain_percent_from_start'] = ml.get('gain_percent_from_start', 0)
        features['time_to_10k'] = ml.get('time_to_10k', 1800)
        features['time_to_20k'] = ml.get('time_to_20k', 1800)
        features['time_to_40k'] = ml.get('time_to_40k', 1800)
        features['time_to_69k'] = ml.get('time_to_69k', 1800)
        features['ath_mc'] = ml.get('ath_mc', 0)
        features['ath_time'] = ml.get('ath_time', 1800)
        features['max_drawdown'] = ml.get('max_drawdown_percent', 0)
        features['volatility'] = ml.get('volatility', 0)
        features['num_pumps'] = ml.get('num_pumps', 0)
        features['num_dumps'] = ml.get('num_dumps', 0)
        features['whale_entry_before_10k'] = ml.get('whale_entry_before_10k', 0)
        features['whale_entry_10k_to_20k'] = ml.get('whale_entry_10k_to_20k', 0)
        features['whale_exit_count'] = ml.get('whale_exit_count', 0)
        features['avg_hold_time'] = ml.get('avg_hold_time', 0)
        features['paper_hands_count'] = ml.get('paper_hands_count', 0)
        features['diamond_hands_count'] = ml.get('diamond_hands_count', 0)
        features['holder_ratio'] = ml.get('holder_ratio', 0)

        # === SUPPLY DISTRIBUTION ===
        supply = token_data.get('supply_distribution', {}) or {}
        features['total_holders'] = supply.get('total_holders', 0)
        features['top_3_percent'] = supply.get('top_3_percent', 0)
        features['top_10_percent'] = supply.get('top_10_percent', 0)

        # === COMPUTED FEATURES ===
        features['early_signal_score'] = (
            features.get('10s_buy_ratio', 0) * 30 +
            min(features.get('10s_txn', 0), 100) * 0.3 +
            features.get('10s_big_buys_100', 0) * 5 +
            features.get('10s_whale_count', 0) * 10
        )

        features['momentum_score'] = (
            features.get('15s_buy_ratio', 0) * 20 +
            features.get('mc_growth_10s_to_30s', 0) * 50 +
            features.get('txn_velocity_30s', 0) * 10
        )

        features['whale_confidence'] = (
            features.get('num_whale_wallets', 0) * 20 +
            features.get('whale_entry_before_10k', 0) * 15 +
            min(features.get('whale_total_volume', 0) / 1000, 50)
        )

        return features

    def predict(self, token_data: Dict) -> Optional[RunnerPrediction]:
        """
        Predit si un token est un runner et son prix cible

        Args:
            token_data: Donnees du token avec snapshots

        Returns:
            RunnerPrediction avec toutes les predictions
        """
        if not self.loaded:
            print("[PREDICTOR] Modeles non charges!")
            return None

        try:
            # Extraire features
            features = self.extract_features(token_data)

            # Creer DataFrame
            df = pd.DataFrame([features])

            # Aligner avec les features attendues
            for col in self.feature_names:
                if col not in df.columns:
                    df[col] = 0

            df = df[self.feature_names]
            df = df.replace([np.inf, -np.inf], 0).fillna(0)

            # === PREDICTION RUNNER ===
            X_clf = self.clf_scaler.transform(df)
            runner_proba = self.classifier.predict_proba(X_clf)[0][1] * 100

            # === PREDICTION PRIX ===
            X_reg = self.reg_scaler.transform(df)
            predicted_price = max(0, self.regressor.predict(X_reg)[0])

            # === PREDICTION MIGRATION ===
            # Utiliser seulement les features early
            df_mig = pd.DataFrame([features])
            for col in self.migration_feature_names:
                if col not in df_mig.columns:
                    df_mig[col] = 0
            df_mig = df_mig[self.migration_feature_names]
            df_mig = df_mig.replace([np.inf, -np.inf], 0).fillna(0)

            X_mig = self.mig_scaler.transform(df_mig)
            migration_proba = self.migration_clf.predict_proba(X_mig)[0][1] * 100

            # === CALCUL DES TARGETS ===
            current_mcap = features.get('10s_mc', 0) or features.get('15s_mc', 0) or token_data.get('usd_market_cap', 10000)

            # Targets basees sur le prix predit et la probabilite
            confidence_factor = runner_proba / 100
            target_conservative = current_mcap * (1 + confidence_factor)
            target_moderate = predicted_price
            target_optimistic = predicted_price * (1 + confidence_factor * 0.5)

            # Multiplier potentiel
            potential_x = predicted_price / current_mcap if current_mcap > 0 else 1

            # === CLASSIFICATION ===
            if runner_proba >= 85 and potential_x >= 5:
                category = "MOON"
                confidence = "HIGH"
            elif runner_proba >= 70 and potential_x >= 3:
                category = "RUNNER"
                confidence = "HIGH"
            elif runner_proba >= 55 and potential_x >= 2:
                category = "PUMPER"
                confidence = "MEDIUM"
            elif runner_proba >= 40:
                category = "WEAK"
                confidence = "LOW"
            else:
                category = "RUG"
                confidence = "LOW"

            # === ACTION ===
            if category == "MOON":
                action = "BUY NOW!"
                reason = f"MOON SHOT! {runner_proba:.0f}% runner, target {potential_x:.1f}x"
            elif category == "RUNNER":
                action = "BUY"
                reason = f"Strong runner signal: {runner_proba:.0f}%, migration {migration_proba:.0f}%"
            elif category == "PUMPER":
                action = "CONSIDER"
                reason = f"Potential pump: {runner_proba:.0f}%, target {potential_x:.1f}x"
            elif category == "WEAK":
                action = "WAIT"
                reason = f"Weak signal: {runner_proba:.0f}%"
            else:
                action = "SKIP"
                reason = f"High rug risk: {runner_proba:.0f}%"

            return RunnerPrediction(
                runner_probability=round(runner_proba, 1),
                migration_probability=round(migration_proba, 1),
                current_mcap=current_mcap,
                predicted_price=round(predicted_price, 0),
                target_conservative=round(target_conservative, 0),
                target_moderate=round(target_moderate, 0),
                target_optimistic=round(target_optimistic, 0),
                potential_x=round(potential_x, 2),
                category=category,
                confidence=confidence,
                action=action,
                reason=reason
            )

        except Exception as e:
            print(f"[PREDICTOR] Erreur prediction: {e}")
            import traceback
            traceback.print_exc()
            return None

    def format_prediction(self, pred: RunnerPrediction) -> str:
        """Formate la prediction pour affichage"""
        lines = [
            "=" * 60,
            f"PREDICTION: {pred.category} ({pred.confidence})",
            "=" * 60,
            "",
            f"Runner Probability:    {pred.runner_probability:.1f}%",
            f"Migration Probability: {pred.migration_probability:.1f}%",
            "",
            f"Current MCap:    ${pred.current_mcap:,.0f}",
            f"Predicted Price: ${pred.predicted_price:,.0f}",
            "",
            "--- TARGETS ---",
            f"Conservative: ${pred.target_conservative:,.0f}",
            f"Moderate:     ${pred.target_moderate:,.0f}",
            f"Optimistic:   ${pred.target_optimistic:,.0f}",
            "",
            f"Potential: {pred.potential_x:.1f}x",
            "",
            f">>> {pred.action}: {pred.reason}",
            "=" * 60
        ]
        return "\n".join(lines)


# Test
if __name__ == "__main__":
    predictor = RunnerPredictor()

    if predictor.loaded:
        # Test avec des donnees simulees
        test_token = {
            '10s': {
                'txn': 45,
                'buys': 38,
                'sells': 7,
                'buy_ratio': 0.84,
                'traders': 32,
                'mc': 12000,
                'big_buys_100': 8,
                'big_buys_500': 2,
                'total_buy_volume': 3500,
                'smart_money_count': 3,
                'whale_count': 1
            },
            '15s': {
                'txn': 68,
                'buys': 55,
                'sells': 13,
                'buy_ratio': 0.81,
                'traders': 48,
                'mc': 15000,
                'big_buys_100': 12,
                'big_buys_500': 3,
                'total_buy_volume': 5200,
                'smart_money_count': 4,
                'whale_count': 2
            },
            '30s': {
                'txn': 95,
                'buy_ratio': 0.78,
                'traders': 65,
                'mc': 22000,
                'big_buys_100': 18,
                'big_buys_500': 5,
                'whale_count': 3
            },
            '1min': {
                'txn': 140,
                'buy_ratio': 0.75,
                'traders': 95,
                'mc': 35000,
                'big_buys_500': 7
            },
            'whale_count': 3,
            'whale_total_volume_usd': 8500,
            'whale_wallets_detected': ['wallet1', 'wallet2', 'wallet3']
        }

        pred = predictor.predict(test_token)
        if pred:
            print(predictor.format_prediction(pred))
    else:
        print("\nLance d'abord: python train_runner_model.py")

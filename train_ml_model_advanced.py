"""
ADVANCED ML MODEL TRAINING
Entraîne le modèle de prédiction sur le dataset réel de tokens pump.fun
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib

class TokenMLTrainer:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []

    def load_dataset(self):
        """Charge le dataset de tokens"""
        dataset_file = Path(__file__).parent / "training_dataset.json"

        if not dataset_file.exists():
            print("[!] Dataset not found! Run pumpfun_mass_scraper.py first")
            return None

        with open(dataset_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        tokens = data.get('tokens', [])
        print(f"\n[+] Loaded {len(tokens)} tokens from dataset")

        return tokens

    def prepare_features(self, tokens):
        """Prépare les features pour le ML"""
        print("\n[*] Preparing features...")

        features_list = []
        labels_list = []

        for token in tokens:
            # Ignorer les tokens sans label clair
            if token['label'] in ['unknown']:
                continue

            # Créer le vecteur de features
            features = {
                # Métriques de prix
                'price_usd': token.get('price_usd', 0),
                'price_change_24h': token.get('price_change_24h', 0),

                # Liquidité et volume
                'liquidity_usd': token.get('liquidity_usd', 0),
                'volume_24h': token.get('volume_24h', 0),
                'volume_mcap_ratio': token.get('volume_mcap_ratio', 0),

                # Capitalisation
                'market_cap': token.get('market_cap', 0),
                'fdv': token.get('fdv', 0),

                # Transactions
                'txns_24h_buys': token.get('txns_24h_buys', 0),
                'txns_24h_sells': token.get('txns_24h_sells', 0),
                'buy_sell_ratio': token.get('buy_sell_ratio', 0),

                # Features calculées
                'liquidity_per_mcap': token.get('liquidity_usd', 1) / max(token.get('market_cap', 1), 1),
                'avg_buy_size': token.get('volume_24h', 0) / max(token.get('txns_24h_buys', 1), 1),
                'avg_sell_size': token.get('volume_24h', 0) / max(token.get('txns_24h_sells', 1), 1),
            }

            # Label binaire : gem (1) vs rug (0)
            if token['label'] in ['gem', 'potential_gem']:
                label = 1  # GEM
            else:
                label = 0  # RUG

            features_list.append(features)
            labels_list.append(label)

        # Convertir en DataFrame
        df = pd.DataFrame(features_list)
        self.feature_names = df.columns.tolist()

        print(f"[+] Features prepared: {len(self.feature_names)} features")
        print(f"[+] Samples: {len(df)} (Gems: {sum(labels_list)}, Rugs: {len(labels_list) - sum(labels_list)})")

        return df.values, np.array(labels_list)

    def train_model(self, X, y):
        """Entraîne le modèle ML"""
        print("\n[*] Training ML model...")

        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        print(f"[+] Train set: {len(X_train)} samples")
        print(f"[+] Test set: {len(X_test)} samples")

        # Normaliser les features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Entraîner Gradient Boosting (meilleur que Random Forest généralement)
        print("\n[*] Training Gradient Boosting Classifier...")
        self.model = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            random_state=42,
            verbose=1
        )

        self.model.fit(X_train_scaled, y_train)

        # Évaluer
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)

        print("\n" + "=" * 70)
        print("MODEL EVALUATION")
        print("=" * 70)
        print(f"Accuracy: {accuracy * 100:.2f}%")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['RUG', 'GEM']))
        print("\nConfusion Matrix:")
        print(confusion_matrix(y_test, y_pred))
        print("=" * 70)

        # Feature importance
        print("\nTop 10 Most Important Features:")
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        print(feature_importance.head(10).to_string(index=False))

        return accuracy

    def save_model(self):
        """Sauvegarde le modèle entraîné"""
        models_dir = Path(__file__).parent / "models"
        models_dir.mkdir(exist_ok=True)

        # Sauvegarder le modèle
        model_file = models_dir / "token_predictor_model.pkl"
        joblib.dump(self.model, model_file)
        print(f"\n[+] Model saved: {model_file}")

        # Sauvegarder le scaler
        scaler_file = models_dir / "token_predictor_scaler.pkl"
        joblib.dump(self.scaler, scaler_file)
        print(f"[+] Scaler saved: {scaler_file}")

        # Sauvegarder les feature names
        features_file = models_dir / "token_predictor_features.json"
        with open(features_file, 'w') as f:
            json.dump({
                'feature_names': self.feature_names,
                'trained_at': datetime.now().isoformat()
            }, f, indent=2)
        print(f"[+] Features saved: {features_file}")

    def run(self):
        """Lance l'entraînement complet"""
        # Charger le dataset
        tokens = self.load_dataset()
        if not tokens:
            return

        # Préparer les features
        X, y = self.prepare_features(tokens)

        if len(X) < 20:
            print(f"\n[!] Not enough data to train! Need at least 20 labeled tokens, got {len(X)}")
            print("[!] Run pumpfun_mass_scraper.py or quick_dataset_builder.py to collect more data")
            return

        if len(X) < 50:
            print(f"\n[!] WARNING: Limited dataset ({len(X)} tokens). Model accuracy may be lower.")
            print("[!] For better accuracy, collect 50+ tokens with pumpfun_mass_scraper.py")

        # Entraîner le modèle
        accuracy = self.train_model(X, y)

        # Sauvegarder
        self.save_model()

        print("\n" + "=" * 70)
        print("TRAINING COMPLETE!")
        print("=" * 70)
        print(f"\nModel accuracy: {accuracy * 100:.2f}%")
        print("\nYou can now use this model to predict new tokens!")
        print("Use: price_predictor.py <token_address>")


def main():
    print("\n" + "=" * 70)
    print("ADVANCED ML MODEL TRAINING")
    print("=" * 70)

    trainer = TokenMLTrainer()
    trainer.run()


if __name__ == "__main__":
    main()

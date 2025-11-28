"""
TEST DU SYSTEME D'APPRENTISSAGE CONTINU
Version de test qui fait UN SEUL cycle pour tester le fonctionnement
"""
import asyncio
import httpx
import sqlite3
import pandas as pd
import joblib
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

# Import feature extractor
sys.path.insert(0, str(Path(__file__).parent))
from feature_extractor import TokenFeatureExtractor

console = Console()

class ContinuousLearningSystemTest:
    """Version test du systeme d'apprentissage continu"""

    def __init__(self):
        self.db_path = Path(__file__).parent / "learning_db.sqlite"
        self.models_dir = Path(__file__).parent / "models"
        self.dataset_dir = Path(__file__).parent / "rug coin" / "ml_module" / "dataset"

        # Initialiser la base de donnees
        self.init_database()

        # Charger le modele actuel
        self.load_current_model()

        # Feature extractor
        self.feature_extractor = TokenFeatureExtractor()

        # HTTP client
        self.client = httpx.AsyncClient(timeout=30.0)

    def init_database(self):
        """Initialise la base de donnees pour tracker les tokens"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitored_tokens (
                token_address TEXT PRIMARY KEY,
                discovered_at TIMESTAMP,
                prediction_made_at TIMESTAMP,
                predicted_label INTEGER,
                predicted_confidence REAL,
                initial_price REAL,
                initial_market_cap REAL,
                initial_liquidity REAL,
                features_json TEXT,
                label_confirmed INTEGER DEFAULT 0,
                actual_label INTEGER,
                max_roi REAL,
                labeling_timestamp TIMESTAMP,
                included_in_training INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT,
                timestamp TIMESTAMP,
                price REAL,
                market_cap REAL,
                liquidity REAL,
                FOREIGN KEY (token_address) REFERENCES monitored_tokens(token_address)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS retraining_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                retrained_at TIMESTAMP,
                samples_used INTEGER,
                new_accuracy REAL,
                model_path TEXT,
                notes TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def load_current_model(self):
        """Charge le modele actuel"""
        try:
            self.model = joblib.load(self.models_dir / "roi_predictor_latest.pkl")
            self.scaler = joblib.load(self.models_dir / "roi_scaler_latest.pkl")
            with open(self.models_dir / "roi_feature_names.json", "r") as f:
                self.feature_names = json.load(f)
            console.print("[green]Modele charge: XGBoost 95.61%!")
        except Exception as e:
            console.print(f"[red]Erreur chargement modele: {e}")
            self.model = None
            self.scaler = None
            self.feature_names = None

    async def discover_new_tokens(self):
        """Decouvre les nouveaux tokens sur Pump.fun"""
        console.print("\n[cyan]Recherche de nouveaux tokens sur Pump.fun...")

        try:
            response = await self.client.get(
                "https://frontend-api-v2.pump.fun/coins/latest"
            )

            if response.status_code == 200:
                tokens = response.json()[:5]  # Top 5 pour le test
                console.print(f"[green]OK - Trouve {len(tokens)} nouveaux tokens")
                return [token.get("mint") for token in tokens if token.get("mint")]
            else:
                console.print(f"[yellow]Erreur API: {response.status_code}")
                return []

        except Exception as e:
            console.print(f"[red]Erreur decouverte: {e}")
            return []

    async def make_prediction(self, token_address: str):
        """Fait une prediction pour un token"""
        try:
            console.print(f"[cyan]  Analyse du token {token_address[:8]}...")

            # Extraire les features
            features = await self.feature_extractor.extract_all_features(token_address)

            if not features:
                console.print(f"[yellow]  Impossible d'extraire les features")
                return None

            # Preparer pour prediction
            feature_dict = {}
            for fname in self.feature_names:
                feature_dict[fname] = features.get(fname, 0)

            df = pd.DataFrame([feature_dict])
            X = self.scaler.transform(df)

            # Prediction
            prediction = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]
            confidence = float(probabilities[prediction] * 100)

            # Sauvegarder dans la DB
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO monitored_tokens
                (token_address, discovered_at, prediction_made_at, predicted_label,
                 predicted_confidence, initial_price, initial_market_cap,
                 initial_liquidity, features_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                token_address,
                datetime.now(),
                datetime.now(),
                int(prediction),
                confidence,
                features.get('price', 0),
                features.get('market_cap_usd', 0),
                features.get('liquidity_usd', 0),
                json.dumps(feature_dict)
            ))

            conn.commit()
            conn.close()

            label_names = {0: "RUG", 1: "SAFE", 2: "GEM"}
            label_colors = {0: "red", 1: "yellow", 2: "green"}
            label = label_names[prediction]
            color = label_colors[prediction]

            console.print(f"[{color}]  PREDICTION: {label} ({confidence:.2f}% confiance)")
            console.print(f"[cyan]  Market Cap: ${features.get('market_cap_usd', 0):,.0f}")
            console.print(f"[cyan]  Liquidite: ${features.get('liquidity_usd', 0):,.0f}")

            return {
                'prediction': int(prediction),
                'confidence': confidence,
                'features': features
            }

        except Exception as e:
            console.print(f"[red]  Erreur prediction: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def show_stats(self):
        """Affiche les statistiques"""
        console.print("\n[bold yellow]" + "=" * 70)
        console.print("[bold yellow]STATISTIQUES DU SYSTEME")
        console.print("[bold yellow]" + "=" * 70)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM monitored_tokens')
        total_monitored = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM monitored_tokens WHERE label_confirmed = 1')
        total_labeled = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM monitored_tokens WHERE included_in_training = 1')
        total_trained = cursor.fetchone()[0]

        conn.close()

        console.print(f"[cyan]  Tokens monitores: {total_monitored}")
        console.print(f"[cyan]  Tokens labellises: {total_labeled}")
        console.print(f"[cyan]  Tokens en training: {total_trained}")
        console.print(f"[cyan]  Precision actuelle: 95.61%")

    async def run_test_cycle(self):
        """Cycle de test"""
        console.print("\n[bold green]" + "=" * 70)
        console.print("[bold green]TEST DU SYSTEME D'APPRENTISSAGE CONTINU")
        console.print("[bold green]" + "=" * 70)

        console.print(f"\n[bold cyan]Heure de debut: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 1. Decouvrir de nouveaux tokens
        new_tokens = await self.discover_new_tokens()

        # 2. Faire des predictions
        if new_tokens:
            console.print(f"\n[bold cyan]Predictions pour {len(new_tokens)} tokens:")
            console.print("[cyan]" + "-" * 70)

            for i, token in enumerate(new_tokens, 1):
                console.print(f"\n[bold white][{i}/{len(new_tokens)}] Token: {token}")
                await self.make_prediction(token)
                await asyncio.sleep(1)  # Petite pause

        # 3. Afficher les statistiques
        await self.show_stats()

        console.print("\n[bold green]" + "=" * 70)
        console.print("[bold green]TEST TERMINE!")
        console.print("[bold green]" + "=" * 70)

        console.print("\n[bold cyan]Pour lancer le systeme complet en continu:")
        console.print("[cyan]  python continuous_learning_system.py")

        console.print("\n[bold cyan]Pour voir le dashboard:")
        console.print("[cyan]  python dashboard.py")

        await self.close()

    async def close(self):
        """Ferme les connexions"""
        await self.client.aclose()
        await self.feature_extractor.close()


async def main():
    """Point d'entree principal"""
    system = ContinuousLearningSystemTest()
    await system.run_test_cycle()


if __name__ == "__main__":
    asyncio.run(main())

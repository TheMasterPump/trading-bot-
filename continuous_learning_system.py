"""
CONTINUOUS LEARNING SYSTEM
Systeme d'apprentissage continu qui:
1. Monitore les nouveaux tokens Pump.fun
2. Fait des predictions
3. Track les performances reelles
4. Labellise automatiquement les tokens
5. Reentra\u00eene le modele avec les nouvelles donnees
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
from rich.table import Table
import time

# Import feature extractor
sys.path.insert(0, str(Path(__file__).parent))
from feature_extractor import TokenFeatureExtractor

console = Console()

class ContinuousLearningSystem:
    """Systeme d'apprentissage continu"""

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

        # Table des tokens monitores
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

        # Table des prix historiques
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

        # Table des reentrainements
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
            console.print("[green]Modele charge avec succes!")
        except Exception as e:
            console.print(f"[red]Erreur chargement modele: {e}")
            self.model = None
            self.scaler = None
            self.feature_names = None

    async def discover_new_tokens(self):
        """Decouvre les nouveaux tokens sur Pump.fun"""
        console.print("\n[cyan]Recherche de nouveaux tokens...")

        try:
            # Utiliser l'API Pump.fun pour obtenir les derniers tokens
            response = await self.client.get(
                "https://frontend-api-v2.pump.fun/coins/latest"
            )

            if response.status_code == 200:
                tokens = response.json()[:20]  # Top 20 nouveaux tokens
                console.print(f"[green]OK -Trouve {len(tokens)} nouveaux tokens")
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
            # Extraire les features
            features = await self.feature_extractor.extract_all_features(token_address)

            if not features:
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
            console.print(f"[green]Prediction: {label_names[prediction]} ({confidence:.2f}%)")

            return {
                'prediction': int(prediction),
                'confidence': confidence,
                'features': features
            }

        except Exception as e:
            console.print(f"[red]Erreur prediction: {e}")
            return None

    async def track_token_performance(self, token_address: str):
        """Track la performance d'un token dans le temps"""
        try:
            # Recuperer les donnees actuelles
            response = await self.client.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            )

            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])

                if pairs:
                    pair = pairs[0]
                    current_price = float(pair.get("priceUsd", 0))
                    current_mcap = float(pair.get("marketCap", 0))
                    current_liquidity = float(pair.get("liquidity", {}).get("usd", 0))

                    # Sauvegarder dans l'historique
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()

                    cursor.execute('''
                        INSERT INTO price_history (token_address, timestamp, price, market_cap, liquidity)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (token_address, datetime.now(), current_price, current_mcap, current_liquidity))

                    conn.commit()
                    conn.close()

                    return {
                        'price': current_price,
                        'market_cap': current_mcap,
                        'liquidity': current_liquidity
                    }

        except Exception as e:
            console.print(f"[yellow]Erreur tracking {token_address[:8]}: {e}")

        return None

    async def auto_label_tokens(self):
        """Labellise automatiquement les tokens bases sur leur performance"""
        console.print("\n[cyan]Labellisation automatique des tokens...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Recuperer les tokens non labellises de plus de 24h
        cursor.execute('''
            SELECT token_address, initial_price, initial_market_cap, prediction_made_at
            FROM monitored_tokens
            WHERE label_confirmed = 0
            AND datetime(prediction_made_at) < datetime('now', '-24 hours')
        ''')

        tokens_to_label = cursor.fetchall()
        console.print(f"[cyan]Tokens a labelliser: {len(tokens_to_label)}")

        labeled_count = 0

        for token_address, initial_price, initial_mcap, prediction_time in tokens_to_label:
            # Recuperer le prix max depuis la prediction
            cursor.execute('''
                SELECT MAX(market_cap) as max_mcap
                FROM price_history
                WHERE token_address = ?
                AND datetime(timestamp) > datetime(?)
            ''', (token_address, prediction_time))

            result = cursor.fetchone()
            max_mcap = result[0] if result and result[0] else initial_mcap

            # Calculer le ROI
            if initial_mcap > 0:
                roi = (max_mcap - initial_mcap) / initial_mcap
            else:
                roi = 0

            # Determiner le label
            if roi < 0.5:  # Moins de 50% de gain
                actual_label = 0  # RUG
            elif roi < 10:  # Entre 50% et 10x
                actual_label = 1  # SAFE
            else:  # Plus de 10x
                actual_label = 2  # GEM

            # Mettre a jour le label
            cursor.execute('''
                UPDATE monitored_tokens
                SET label_confirmed = 1,
                    actual_label = ?,
                    max_roi = ?,
                    labeling_timestamp = ?
                WHERE token_address = ?
            ''', (actual_label, roi, datetime.now(), token_address))

            labeled_count += 1

        conn.commit()
        conn.close()

        console.print(f"[green]OK -{labeled_count} tokens labellises!")
        return labeled_count

    async def retrain_model(self):
        """Reentrainement du modele avec les nouvelles donnees"""
        console.print("\n[bold cyan]Reentrainement du modele...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Recuperer les tokens labellises non utilises
        cursor.execute('''
            SELECT token_address, features_json, actual_label
            FROM monitored_tokens
            WHERE label_confirmed = 1
            AND included_in_training = 0
        ''')

        new_samples = cursor.fetchall()

        if len(new_samples) < 10:
            console.print(f"[yellow]Pas assez de nouvelles donnees ({len(new_samples)} < 10)")
            conn.close()
            return False

        console.print(f"[cyan]Nouvelles donnees: {len(new_samples)} samples")

        # Charger le dataset existant
        existing_df = pd.read_csv(self.dataset_dir / "features_roi.csv")

        # Creer un dataframe avec les nouvelles donnees
        new_data = []
        for token_address, features_json, actual_label in new_samples:
            features = json.loads(features_json)
            features['roi_label'] = actual_label
            features['token_mint'] = token_address
            new_data.append(features)

        new_df = pd.DataFrame(new_data)

        # Combiner les datasets
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)

        # Sauvegarder le dataset combine
        backup_file = self.dataset_dir / f"features_roi_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        existing_df.to_csv(backup_file, index=False)
        console.print(f"[green]Backup: {backup_file.name}")

        combined_df.to_csv(self.dataset_dir / "features_roi.csv", index=False)
        console.print(f"[green]Dataset combine: {len(combined_df)} samples total")

        # Lancer le reentrainement
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "train_now.py")],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            console.print("[green]Reentrainement reussi!")

            # Marquer les samples comme utilises
            for token_address, _, _ in new_samples:
                cursor.execute('''
                    UPDATE monitored_tokens
                    SET included_in_training = 1
                    WHERE token_address = ?
                ''', (token_address,))

            # Sauvegarder dans l'historique
            cursor.execute('''
                INSERT INTO retraining_history (retrained_at, samples_used, notes)
                VALUES (?, ?, ?)
            ''', (datetime.now(), len(new_samples), f"Added {len(new_samples)} new samples"))

            conn.commit()
            conn.close()

            # Recharger le modele
            self.load_current_model()

            return True
        else:
            console.print(f"[red]Erreur reentrainement: {result.stderr}")
            conn.close()
            return False

    async def run_continuous_cycle(self, iterations=None, delay_minutes=60):
        """Cycle continu d'apprentissage"""
        console.print("\n[bold green]" + "=" * 70)
        console.print("[bold green]SYSTEME D'APPRENTISSAGE CONTINU DEMARRE")
        console.print("[bold green]" + "=" * 70)

        iteration = 0

        while iterations is None or iteration < iterations:
            iteration += 1

            console.print(f"\n[bold cyan]{'='*70}")
            console.print(f"[bold cyan]CYCLE {iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            console.print(f"[bold cyan]{'='*70}")

            # 1. Decouvrir de nouveaux tokens
            new_tokens = await self.discover_new_tokens()

            # 2. Faire des predictions
            if new_tokens:
                console.print(f"\n[cyan]Predictions pour {len(new_tokens)} tokens...")
                for i, token in enumerate(new_tokens[:10], 1):  # Max 10 par cycle
                    console.print(f"\n[cyan][{i}/10] Token: {token[:8]}...")
                    await self.make_prediction(token)
                    await asyncio.sleep(2)  # Eviter rate limiting

            # 3. Tracker la performance des tokens monitores
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT token_address FROM monitored_tokens WHERE label_confirmed = 0 LIMIT 50')
            tracked_tokens = [row[0] for row in cursor.fetchall()]
            conn.close()

            if tracked_tokens:
                console.print(f"\n[cyan]Tracking {len(tracked_tokens)} tokens...")
                for token in tracked_tokens[:20]:  # Max 20 par cycle
                    await self.track_token_performance(token)
                    await asyncio.sleep(1)

            # 4. Labelliser automatiquement
            labeled = await self.auto_label_tokens()

            # 5. Reentrainer si necessaire
            if labeled >= 10:
                retrained = await self.retrain_model()
                if retrained:
                    console.print("[bold green]Modele ameliore avec de nouvelles donnees!")

            # Statistiques
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM monitored_tokens')
            total_monitored = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM monitored_tokens WHERE label_confirmed = 1')
            total_labeled = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM monitored_tokens WHERE included_in_training = 1')
            total_trained = cursor.fetchone()[0]
            conn.close()

            console.print(f"\n[bold yellow]Statistiques:")
            console.print(f"[yellow]  Tokens monitores: {total_monitored}")
            console.print(f"[yellow]  Tokens labellises: {total_labeled}")
            console.print(f"[yellow]  Tokens en training: {total_trained}")

            if iterations is None or iteration < iterations:
                console.print(f"\n[cyan]Prochain cycle dans {delay_minutes} minutes...")
                await asyncio.sleep(delay_minutes * 60)

        await self.close()

    async def close(self):
        """Ferme les connexions"""
        await self.client.aclose()
        await self.feature_extractor.close()


async def main():
    """Point d'entree principal"""
    system = ContinuousLearningSystem()

    # Lancer le systeme en continu
    await system.run_continuous_cycle(iterations=None, delay_minutes=60)


if __name__ == "__main__":
    asyncio.run(main())

"""
AUTO-SCANNER
Analyse automatiquement chaque nouveau token detecte par PumpFun Monitor
Si score > 80% → ALERTE automatique!
INCLUT: Detection des RUNNERS (tokens qui vont monter fort avant/apres migration)
"""
import asyncio
import json
import pandas as pd
import joblib
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from pumpfun_monitor import PumpFunMonitor
from feature_extractor import TokenFeatureExtractor
from price_predictor import PricePredictor
from performance_tracker import PerformanceTracker
from smart_alerts_system import SmartAlertsSystem
from runner_detector import get_runner_detector, RunnerPotential, RunnerPhase

console = Console()

class AutoScanner:
    """Scanner automatique de nouveaux tokens"""

    def __init__(self):
        self.models_dir = Path(__file__).parent / "models"

        # Charger le modele
        try:
            self.model = joblib.load(self.models_dir / "roi_predictor_latest.pkl")
            self.scaler = joblib.load(self.models_dir / "roi_scaler_latest.pkl")
            with open(self.models_dir / "roi_feature_names.json", "r") as f:
                self.feature_names = json.load(f)
            console.print("[green]Modele charge!")
        except Exception as e:
            console.print(f"[red]Erreur chargement modele: {e}")
            self.model = None

        # Initialiser les composants
        self.pumpfun_monitor = PumpFunMonitor()
        self.feature_extractor = TokenFeatureExtractor()
        self.price_predictor = PricePredictor()
        self.performance_tracker = PerformanceTracker()
        self.alerts_system = SmartAlertsSystem()

        # Stats
        self.tokens_scanned = 0
        self.alerts_sent = 0
        self.start_time = datetime.now()

    async def analyze_token(self, token_address):
        """Analyse complete d'un token"""
        try:
            console.print(f"\n[bold cyan]{'='*70}")
            console.print(f"[bold cyan]ANALYSE AUTO: {token_address[:16]}...")
            console.print(f"[bold cyan]{'='*70}")

            # 1. Extraire features
            console.print("[cyan]Extraction des features...")
            features = await self.feature_extractor.extract_all_features(token_address)

            if not features:
                console.print("[red]Impossible d'extraire features")
                return None

            console.print(f"[green]OK - {len(features)} features extraites")

            # 2. Prediction de categorie
            if not self.model:
                console.print("[red]Modele non charge!")
                return None

            feature_dict = {fname: features.get(fname, 0) for fname in self.feature_names}
            df = pd.DataFrame([feature_dict])
            X = self.scaler.transform(df)

            prediction = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]

            label_names = {0: "RUG", 1: "SAFE", 2: "GEM"}

            category_result = {
                'label': int(prediction),
                'category': label_names[prediction],
                'confidence': float(probabilities[prediction] * 100),
                'probabilities': {
                    'RUG': float(probabilities[0] * 100),
                    'SAFE': float(probabilities[1] * 100),
                    'GEM': float(probabilities[2] * 100)
                }
            }

            console.print(f"[green]Categorie: {category_result['category']} ({category_result['confidence']:.1f}%)")

            # 3. Prediction de prix
            console.print("[cyan]Prediction de prix...")
            price_result = self.price_predictor.get_precise_prediction(features)

            console.print(f"[green]Potentiel: {price_result['potential_multiplier']:.1f}x")
            console.print(f"[green]Viral Potential: {features.get('viral_potential', 0):.0f}%")

            # 4. Construire resultat complet
            result = {
                'success': True,
                'token_address': token_address,
                'category_prediction': category_result,
                'price_prediction': price_result,
                'features': features,
                'timestamp': datetime.now().isoformat()
            }

            # 5. Sauvegarder prediction
            self.performance_tracker.save_prediction(token_address, result, features)

            # 6. Check si alerte necessaire
            console.print("\n[cyan]Check criteres d'alerte...")
            alert_sent = await self.alerts_system.process_prediction_for_alert(
                token_address,
                result
            )

            if alert_sent:
                self.alerts_sent += 1

            self.tokens_scanned += 1

            return result

        except Exception as e:
            console.print(f"[red]Erreur analyse: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def on_new_token(self, token_data):
        """Callback quand nouveau token detecte"""
        try:
            token_mint = token_data.get('mint')

            if not token_mint:
                return

            console.print(f"\n[bold yellow]NOUVEAU TOKEN DETECTE: {token_mint[:16]}...")

            # Analyser le token
            result = await self.analyze_token(token_mint)

            if result:
                # Afficher resume
                self.display_scan_summary(result)
            else:
                console.print("[red]Analyse failed")

        except Exception as e:
            console.print(f"[red]Erreur on_new_token: {e}")

    def display_scan_summary(self, result):
        """Affiche un resume de l'analyse"""
        table = Table(title="Scan Summary")

        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        category = result['category_prediction']
        price = result['price_prediction']
        features = result['features']

        table.add_row("Categorie", f"{category['category']} ({category['confidence']:.1f}%)")
        table.add_row("Potentiel", f"{price['potential_multiplier']:.1f}x")
        table.add_row("Viral Potential", f"{features.get('viral_potential', 0):.0f}%")
        table.add_row("Twitter Sentiment", f"{features.get('twitter_sentiment', 0):.0f}/100")
        table.add_row("Market Cap", f"${price['current_mcap']:,.0f}")
        table.add_row("Action", price['action'])

        console.print(table)

    def display_stats(self):
        """Affiche les stats du scanner"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        hours = int(uptime / 3600)
        minutes = int((uptime % 3600) / 60)

        console.print("\n[bold cyan]" + "=" * 70)
        console.print("[bold cyan]AUTO-SCANNER STATS")
        console.print("[bold cyan]" + "=" * 70)
        console.print(f"[green]Uptime: {hours}h {minutes}m")
        console.print(f"[green]Tokens Scanned: {self.tokens_scanned}")
        console.print(f"[green]Alerts Sent: {self.alerts_sent}")

        if self.tokens_scanned > 0:
            alert_rate = (self.alerts_sent / self.tokens_scanned) * 100
            console.print(f"[yellow]Alert Rate: {alert_rate:.1f}%")

        console.print("[bold cyan]" + "=" * 70)

    async def run(self):
        """Demarre le scanner automatique"""
        console.print("\n[bold green]" + "=" * 70)
        console.print("[bold green]AUTO-SCANNER STARTED")
        console.print("[bold green]Analyse automatique de chaque nouveau token")
        console.print("[bold green]Alertes automatiques si score > 80%")
        console.print("[bold green]" + "=" * 70)

        # Afficher stats toutes les 30 minutes
        async def stats_loop():
            while True:
                await asyncio.sleep(1800)  # 30 minutes
                self.display_stats()

        # Demarrer stats loop
        asyncio.create_task(stats_loop())

        # Subscribe aux nouveaux tokens
        await self.pumpfun_monitor.subscribe_new_tokens(callback=self.on_new_token)

    async def close(self):
        """Cleanup"""
        await self.feature_extractor.close()
        await self.performance_tracker.close()
        await self.alerts_system.close()


# Main
async def main():
    scanner = AutoScanner()

    try:
        await scanner.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping auto-scanner...")
        scanner.display_stats()
    finally:
        await scanner.close()


if __name__ == "__main__":
    asyncio.run(main())

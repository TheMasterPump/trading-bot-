"""
PERFORMANCE TRACKER - Track la précision réelle des prédictions
Mesure si les prédictions étaient correctes et améliore le modèle
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
import asyncio
import httpx

console = Console()

class PerformanceTracker:
    """Track la performance des prédictions en temps réel"""

    def __init__(self):
        self.db_path = Path(__file__).parent / "performance_tracking.db"
        self.init_database()
        self.client = httpx.AsyncClient(timeout=30.0)

    def init_database(self):
        """Initialise la base de données de tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table des prédictions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,
                predicted_at TIMESTAMP NOT NULL,

                -- Prédictions
                predicted_category INTEGER,
                predicted_category_name TEXT,
                category_confidence REAL,

                predicted_price_max REAL,
                predicted_mcap_max REAL,
                predicted_multiplier REAL,

                is_predicted_top BOOLEAN,
                dump_probability REAL,

                -- État initial
                initial_price REAL,
                initial_mcap REAL,
                initial_liquidity REAL,
                initial_holders INTEGER,

                -- Résultats réels (mis à jour après 24-48h)
                actual_max_price REAL,
                actual_max_mcap REAL,
                actual_multiplier REAL,
                actual_category INTEGER,

                dumped BOOLEAN,
                dump_time TIMESTAMP,

                -- Évaluation
                category_correct BOOLEAN,
                price_error_percentage REAL,
                top_detection_correct BOOLEAN,

                evaluated BOOLEAN DEFAULT 0,
                evaluation_time TIMESTAMP,

                -- Métadonnées
                notes TEXT
            )
        ''')

        # Table de statistiques globales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_stats (
                id INTEGER PRIMARY KEY,
                total_predictions INTEGER DEFAULT 0,
                total_evaluated INTEGER DEFAULT 0,

                category_accuracy REAL DEFAULT 0,
                price_accuracy REAL DEFAULT 0,
                top_detection_accuracy REAL DEFAULT 0,

                rug_precision REAL DEFAULT 0,
                rug_recall REAL DEFAULT 0,
                safe_precision REAL DEFAULT 0,
                safe_recall REAL DEFAULT 0,
                gem_precision REAL DEFAULT 0,
                gem_recall REAL DEFAULT 0,

                last_updated TIMESTAMP
            )
        ''')

        # Initialiser les stats si pas existantes
        cursor.execute('SELECT COUNT(*) FROM global_stats')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO global_stats (id, last_updated)
                VALUES (1, ?)
            ''', (datetime.now(),))

        conn.commit()
        conn.close()

    def save_prediction(self, token_address, prediction_data, features):
        """Sauvegarde une nouvelle prédiction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        category_pred = prediction_data['category_prediction']
        price_pred = prediction_data['price_prediction']

        cursor.execute('''
            INSERT INTO predictions (
                token_address, predicted_at,
                predicted_category, predicted_category_name, category_confidence,
                predicted_price_max, predicted_mcap_max, predicted_multiplier,
                is_predicted_top, dump_probability,
                initial_price, initial_mcap, initial_liquidity, initial_holders
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            token_address,
            datetime.now(),
            category_pred['label'],
            category_pred['category'],
            category_pred['confidence'],
            price_pred['predicted_max_price'],
            price_pred['predicted_max_mcap'],
            price_pred['potential_multiplier'],
            price_pred['is_at_top'],
            price_pred['dump_probability'],
            price_pred['current_price'],
            price_pred['current_mcap'],
            features.get('liquidity_usd', 0),
            features.get('holder_count', 0)
        ))

        conn.commit()
        conn.close()

        # Mettre à jour les stats
        self.update_global_stats()

        console.print(f"[green]Prédiction sauvegardée pour tracking: {token_address[:8]}...")

    async def evaluate_prediction(self, prediction_id):
        """Évalue une prédiction après 24-48h"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Récupérer la prédiction
        cursor.execute('''
            SELECT token_address, predicted_at, initial_price, initial_mcap,
                   predicted_category, predicted_price_max, predicted_mcap_max,
                   is_predicted_top
            FROM predictions WHERE id = ?
        ''', (prediction_id,))

        result = cursor.fetchone()
        if not result:
            conn.close()
            return

        token_address, predicted_at, initial_price, initial_mcap, \
        predicted_category, predicted_price_max, predicted_mcap_max, \
        is_predicted_top = result

        # Récupérer les données actuelles du token
        try:
            response = await self.client.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            )

            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])

                if pairs:
                    pair = pairs[0]
                    current_price = float(pair.get('priceUsd', 0))
                    current_mcap = float(pair.get('marketCap', 0))

                    # Calculer les max (simplification: on prend le max entre initial et actuel)
                    actual_max_price = max(initial_price, current_price)
                    actual_max_mcap = max(initial_mcap, current_mcap)
                    actual_multiplier = actual_max_mcap / max(initial_mcap, 1)

                    # Déterminer la catégorie réelle
                    if actual_multiplier < 0.5:
                        actual_category = 0  # RUG
                    elif actual_multiplier < 10:
                        actual_category = 1  # SAFE
                    else:
                        actual_category = 2  # GEM

                    # Détecter si a dumpé
                    dumped = current_mcap < initial_mcap * 0.7  # 30%+ de baisse = dump

                    # Évaluer la précision
                    category_correct = (predicted_category == actual_category)

                    price_error = abs(predicted_price_max - actual_max_price) / max(actual_max_price, 0.00000001)
                    price_error_pct = price_error * 100

                    top_detection_correct = (is_predicted_top == dumped)

                    # Mettre à jour la prédiction
                    cursor.execute('''
                        UPDATE predictions SET
                            actual_max_price = ?,
                            actual_max_mcap = ?,
                            actual_multiplier = ?,
                            actual_category = ?,
                            dumped = ?,
                            category_correct = ?,
                            price_error_percentage = ?,
                            top_detection_correct = ?,
                            evaluated = 1,
                            evaluation_time = ?
                        WHERE id = ?
                    ''', (
                        actual_max_price,
                        actual_max_mcap,
                        actual_multiplier,
                        actual_category,
                        dumped,
                        category_correct,
                        price_error_pct,
                        top_detection_correct,
                        datetime.now(),
                        prediction_id
                    ))

                    conn.commit()
                    console.print(f"[green]Évaluation complétée pour prédiction #{prediction_id}")

        except Exception as e:
            console.print(f"[red]Erreur évaluation: {e}")

        conn.close()

    async def evaluate_old_predictions(self, hours_old=24):
        """Évalue toutes les prédictions de plus de X heures"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_time = datetime.now() - timedelta(hours=hours_old)

        cursor.execute('''
            SELECT id FROM predictions
            WHERE evaluated = 0
            AND datetime(predicted_at) < datetime(?)
        ''', (cutoff_time,))

        predictions = cursor.fetchall()
        conn.close()

        console.print(f"\n[cyan]Évaluation de {len(predictions)} prédictions...")

        for (pred_id,) in predictions:
            await self.evaluate_prediction(pred_id)
            await asyncio.sleep(1)  # Rate limiting

        self.update_global_stats()

    def update_global_stats(self):
        """Recalcule les statistiques globales"""
        conn = sqlite3.connect(self.db_path)

        # Lire toutes les prédictions évaluées
        df = pd.read_sql('''
            SELECT * FROM predictions WHERE evaluated = 1
        ''', conn)

        if len(df) == 0:
            conn.close()
            return

        # Calculer les métriques
        total_predictions = len(pd.read_sql('SELECT * FROM predictions', conn))
        total_evaluated = len(df)

        category_accuracy = df['category_correct'].mean() * 100
        price_accuracy = 100 - df['price_error_percentage'].mean()
        top_detection_accuracy = df['top_detection_correct'].mean() * 100

        # Précision/Rappel par catégorie
        def calc_precision_recall(category_id):
            predicted_cat = df[df['predicted_category'] == category_id]
            actual_cat = df[df['actual_category'] == category_id]

            if len(predicted_cat) > 0:
                precision = (predicted_cat['category_correct'].sum() / len(predicted_cat)) * 100
            else:
                precision = 0

            if len(actual_cat) > 0:
                recall = (actual_cat['category_correct'].sum() / len(actual_cat)) * 100
            else:
                recall = 0

            return precision, recall

        rug_precision, rug_recall = calc_precision_recall(0)
        safe_precision, safe_recall = calc_precision_recall(1)
        gem_precision, gem_recall = calc_precision_recall(2)

        # Mettre à jour
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE global_stats SET
                total_predictions = ?,
                total_evaluated = ?,
                category_accuracy = ?,
                price_accuracy = ?,
                top_detection_accuracy = ?,
                rug_precision = ?,
                rug_recall = ?,
                safe_precision = ?,
                safe_recall = ?,
                gem_precision = ?,
                gem_recall = ?,
                last_updated = ?
            WHERE id = 1
        ''', (
            total_predictions,
            total_evaluated,
            category_accuracy,
            price_accuracy,
            top_detection_accuracy,
            rug_precision, rug_recall,
            safe_precision, safe_recall,
            gem_precision, gem_recall,
            datetime.now()
        ))

        conn.commit()
        conn.close()

    def get_stats(self):
        """Récupère les statistiques actuelles"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM global_stats WHERE id = 1')
        stats = cursor.fetchone()

        conn.close()

        if not stats:
            return None

        return {
            'total_predictions': stats[1],
            'total_evaluated': stats[2],
            'category_accuracy': stats[3],
            'price_accuracy': stats[4],
            'top_detection_accuracy': stats[5],
            'rug_precision': stats[6],
            'rug_recall': stats[7],
            'safe_precision': stats[8],
            'safe_recall': stats[9],
            'gem_precision': stats[10],
            'gem_recall': stats[11],
            'last_updated': stats[12]
        }

    def display_stats(self):
        """Affiche les statistiques"""
        stats = self.get_stats()

        if not stats:
            console.print("[yellow]Aucune statistique disponible")
            return

        console.print("\n[bold cyan]" + "=" * 70)
        console.print("[bold cyan]PERFORMANCE DU MODÈLE EN TEMPS RÉEL")
        console.print("[bold cyan]" + "=" * 70)

        # Stats globales
        table1 = Table(title="Statistiques Globales")
        table1.add_column("Métrique", style="cyan")
        table1.add_column("Valeur", style="green", justify="right")

        table1.add_row("Total Prédictions", str(stats['total_predictions']))
        table1.add_row("Évaluées", str(stats['total_evaluated']))
        table1.add_row("Précision Catégorie", f"{stats['category_accuracy']:.1f}%")
        table1.add_row("Précision Prix", f"{stats['price_accuracy']:.1f}%")
        table1.add_row("Détection Tops", f"{stats['top_detection_accuracy']:.1f}%")

        console.print(table1)

        # Stats par catégorie
        table2 = Table(title="Performance par Catégorie")
        table2.add_column("Catégorie", style="cyan")
        table2.add_column("Précision", style="green", justify="right")
        table2.add_column("Rappel", style="yellow", justify="right")

        table2.add_row("RUG", f"{stats['rug_precision']:.1f}%", f"{stats['rug_recall']:.1f}%")
        table2.add_row("SAFE", f"{stats['safe_precision']:.1f}%", f"{stats['safe_recall']:.1f}%")
        table2.add_row("GEM", f"{stats['gem_precision']:.1f}%", f"{stats['gem_recall']:.1f}%")

        console.print(table2)

        console.print(f"\n[cyan]Dernière mise à jour: {stats['last_updated']}")

    def get_recent_predictions(self, limit=10):
        """Récupère les dernières prédictions"""
        conn = sqlite3.connect(self.db_path)

        df = pd.read_sql(f'''
            SELECT token_address, predicted_at, predicted_category_name,
                   category_confidence, predicted_multiplier,
                   actual_multiplier, category_correct, evaluated
            FROM predictions
            ORDER BY predicted_at DESC
            LIMIT {limit}
        ''', conn)

        conn.close()
        return df

    async def close(self):
        """Ferme les connexions"""
        await self.client.aclose()


# Test
async def main():
    tracker = PerformanceTracker()

    # Afficher les stats
    tracker.display_stats()

    # Évaluer les prédictions anciennes
    console.print("\n[cyan]Évaluation des prédictions de plus de 24h...")
    await tracker.evaluate_old_predictions(hours_old=24)

    # Afficher les stats mises à jour
    tracker.display_stats()

    # Afficher les dernières prédictions
    console.print("\n[cyan]Dernières prédictions:")
    recent = tracker.get_recent_predictions(10)
    console.print(recent)

    await tracker.close()


if __name__ == "__main__":
    asyncio.run(main())

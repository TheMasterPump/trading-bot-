"""
DASHBOARD - Visualisation des statistiques du systeme d'apprentissage continu
"""
import sqlite3
import pandas as pd
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
import json

console = Console()

def load_stats():
    """Charge les statistiques depuis la base de donnees"""
    db_path = Path(__file__).parent / "learning_db.sqlite"

    if not db_path.exists():
        console.print("[yellow]Base de donnees non trouvee. Lancez d'abord le systeme d'apprentissage continu.")
        return None

    conn = sqlite3.connect(db_path)

    # Stats generales
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM monitored_tokens')
    total_monitored = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM monitored_tokens WHERE label_confirmed = 1')
    total_labeled = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM monitored_tokens WHERE included_in_training = 1')
    total_trained = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM monitored_tokens WHERE predicted_label = 0')
    predicted_rugs = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM monitored_tokens WHERE predicted_label = 1')
    predicted_safe = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM monitored_tokens WHERE predicted_label = 2')
    predicted_gems = cursor.fetchone()[0]

    # Predictions vs realite
    cursor.execute('''
        SELECT predicted_label, actual_label, COUNT(*)
        FROM monitored_tokens
        WHERE label_confirmed = 1
        GROUP BY predicted_label, actual_label
    ''')
    confusion_data = cursor.fetchall()

    # Derniers reentrainements
    cursor.execute('''
        SELECT retrained_at, samples_used, new_accuracy
        FROM retraining_history
        ORDER BY retrained_at DESC
        LIMIT 5
    ''')
    retraining_history = cursor.fetchall()

    # Top predictions recentes
    cursor.execute('''
        SELECT token_address, predicted_label, predicted_confidence, prediction_made_at
        FROM monitored_tokens
        ORDER BY prediction_made_at DESC
        LIMIT 10
    ''')
    recent_predictions = cursor.fetchall()

    conn.close()

    return {
        'total_monitored': total_monitored,
        'total_labeled': total_labeled,
        'total_trained': total_trained,
        'predicted_rugs': predicted_rugs,
        'predicted_safe': predicted_safe,
        'predicted_gems': predicted_gems,
        'confusion_data': confusion_data,
        'retraining_history': retraining_history,
        'recent_predictions': recent_predictions
    }


def load_model_accuracy():
    """Charge la precision du modele actuel"""
    models_dir = Path(__file__).parent / "models"

    # Trouver le fichier de metriques le plus recent
    metric_files = sorted(models_dir.glob("roi_metrics_*.json"), reverse=True)

    if metric_files:
        with open(metric_files[0], 'r') as f:
            metrics = json.load(f)
            return metrics.get('best_accuracy', 0) * 100
    return None


def display_dashboard():
    """Affiche le dashboard"""
    console.clear()

    console.print("\n[bold cyan]" + "=" * 80)
    console.print("[bold cyan]DASHBOARD - SYSTEME D'APPRENTISSAGE CONTINU")
    console.print("[bold cyan]" + "=" * 80 + "\n")

    stats = load_stats()
    if not stats:
        return

    model_accuracy = load_model_accuracy()

    # Section 1: Statistiques generales
    stats_table = Table(title="Statistiques Generales", show_header=True, header_style="bold magenta")
    stats_table.add_column("Metrique", style="cyan")
    stats_table.add_column("Valeur", style="green", justify="right")

    stats_table.add_row("Precision du modele actuel", f"{model_accuracy:.2f}%" if model_accuracy else "N/A")
    stats_table.add_row("Tokens monitores", str(stats['total_monitored']))
    stats_table.add_row("Tokens labellises (24h+)", str(stats['total_labeled']))
    stats_table.add_row("Tokens utilises pour training", str(stats['total_trained']))
    stats_table.add_row("Nouveaux tokens disponibles", str(stats['total_labeled'] - stats['total_trained']))

    console.print(stats_table)
    console.print()

    # Section 2: Distribution des predictions
    pred_table = Table(title="Distribution des Predictions", show_header=True, header_style="bold yellow")
    pred_table.add_column("Categorie", style="cyan")
    pred_table.add_column("Nombre", style="green", justify="right")
    pred_table.add_column("Pourcentage", style="yellow", justify="right")

    total_pred = stats['predicted_rugs'] + stats['predicted_safe'] + stats['predicted_gems']
    if total_pred > 0:
        pred_table.add_row("RUG", str(stats['predicted_rugs']),
                          f"{stats['predicted_rugs']/total_pred*100:.1f}%")
        pred_table.add_row("SAFE", str(stats['predicted_safe']),
                          f"{stats['predicted_safe']/total_pred*100:.1f}%")
        pred_table.add_row("GEM", str(stats['predicted_gems']),
                          f"{stats['predicted_gems']/total_pred*100:.1f}%")

    console.print(pred_table)
    console.print()

    # Section 3: Matrice de confusion
    if stats['confusion_data']:
        conf_table = Table(title="Matrice de Confusion (Predictions vs Realite)", show_header=True,
                          header_style="bold red")
        conf_table.add_column("Predit", style="cyan")
        conf_table.add_column("Reel", style="magenta")
        conf_table.add_column("Nombre", style="green", justify="right")

        label_names = {0: "RUG", 1: "SAFE", 2: "GEM"}

        for pred_label, actual_label, count in stats['confusion_data']:
            conf_table.add_row(
                label_names.get(pred_label, "?"),
                label_names.get(actual_label, "?"),
                str(count)
            )

        console.print(conf_table)
        console.print()

    # Section 4: Historique des reentrainements
    if stats['retraining_history']:
        retrain_table = Table(title="Historique des Reentrainements", show_header=True,
                             header_style="bold green")
        retrain_table.add_column("Date", style="cyan")
        retrain_table.add_column("Nouveaux samples", style="yellow", justify="right")
        retrain_table.add_column("Nouvelle precision", style="green", justify="right")

        for retrained_at, samples, accuracy in stats['retraining_history']:
            retrain_table.add_row(
                retrained_at[:19] if retrained_at else "N/A",
                str(samples),
                f"{accuracy:.2f}%" if accuracy else "N/A"
            )

        console.print(retrain_table)
        console.print()

    # Section 5: Predictions recentes
    if stats['recent_predictions']:
        recent_table = Table(title="Predictions Recentes (10 dernieres)", show_header=True,
                            header_style="bold blue")
        recent_table.add_column("Token", style="cyan")
        recent_table.add_column("Prediction", style="yellow")
        recent_table.add_column("Confiance", style="green", justify="right")
        recent_table.add_column("Date", style="magenta")

        label_names = {0: "RUG", 1: "SAFE", 2: "GEM"}
        label_colors = {0: "red", 1: "yellow", 2: "green"}

        for token, pred_label, confidence, pred_time in stats['recent_predictions']:
            label = label_names.get(pred_label, "?")
            color = label_colors.get(pred_label, "white")
            recent_table.add_row(
                token[:8] + "...",
                f"[{color}]{label}[/{color}]",
                f"{confidence:.1f}%",
                pred_time[:19] if pred_time else "N/A"
            )

        console.print(recent_table)
        console.print()

    # Recommendations
    recommendations = []

    if stats['total_labeled'] - stats['total_trained'] >= 10:
        recommendations.append("[green]Vous avez assez de nouvelles donnees pour reentrainer!")

    if stats['total_monitored'] < 50:
        recommendations.append("[yellow]Continuez a monitorer plus de tokens pour ameliorer la precision")

    if model_accuracy and model_accuracy < 90:
        recommendations.append("[yellow]Precision actuelle < 90%. Collectez plus de donnees!")

    if model_accuracy and model_accuracy >= 95:
        recommendations.append("[green]Excellente precision! Continuez ainsi!")

    if recommendations:
        console.print("[bold cyan]Recommendations:")
        for rec in recommendations:
            console.print(f"  {rec}")
        console.print()

    console.print("[bold cyan]" + "=" * 80)
    console.print("[cyan]Actualiser: Relancez ce script")
    console.print("[cyan]Demarrer apprentissage continu: python continuous_learning_system.py")
    console.print("[bold cyan]" + "=" * 80 + "\n")


if __name__ == "__main__":
    display_dashboard()

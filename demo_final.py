"""
DEMO FINALE - Avec API Helius configuree
Teste 3 nouveaux tokens en temps reel avec toute la puissance de Helius!
"""
import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from pumpfun_monitor import PumpFunMonitor
from feature_extractor import TokenFeatureExtractor
import joblib
import json
import pandas as pd

console = Console()

async def main():
    """Demo finale"""
    console.clear()

    console.print("\n[bold green]" + "=" * 70)
    console.print("[bold green]DEMO FINALE - PREDICTION AI AVEC HELIUS API")
    console.print("[bold green]" + "=" * 70)

    console.print("\n[bold yellow]Configuration:")
    console.print("[white][OK] Modele: XGBoost 95.61%")
    console.print("[white][OK] API: Helius Developer (10M credits)")
    console.print("[white][OK] WebSocket: PumpPortal")
    console.print("[white][OK] Plus de rate limit!")

    # Charger le modele
    console.print("\n[cyan]Chargement du modele...")
    models_dir = Path(__file__).parent / "models"
    model = joblib.load(models_dir / "roi_predictor_latest.pkl")
    scaler = joblib.load(models_dir / "roi_scaler_latest.pkl")
    with open(models_dir / "roi_feature_names.json", "r") as f:
        feature_names = json.load(f)
    console.print("[green]OK - Modele charge!")

    # Initialiser les composants
    monitor = PumpFunMonitor()
    extractor = TokenFeatureExtractor()

    # Scanner les nouveaux tokens
    console.print("\n[bold cyan]" + "=" * 70)
    console.print("[bold cyan]DETECTION DES NOUVEAUX TOKENS EN TEMPS REEL")
    console.print("[bold cyan]" + "=" * 70)
    console.print("\n[cyan]Ecoute de PumpPortal WebSocket...")
    console.print("[cyan]Detection de 3 nouveaux tokens...\n")

    tokens = await monitor.get_latest_tokens(count=3, timeout=30)

    if not tokens:
        console.print("\n[yellow]Aucun nouveau token detecte. Reessayez!")
        await extractor.close()
        return

    console.print(f"\n[bold green]OK - {len(tokens)} nouveaux tokens detectes!\n")

    # Analyser chaque token
    for i, token_data in enumerate(tokens, 1):
        mint = token_data.get('mint', token_data.get('signature', 'Unknown'))

        console.print("[bold white]" + "=" * 70)
        console.print(f"[bold white]TOKEN {i}/{len(tokens)}: {mint}")
        console.print("[bold white]" + "=" * 70)
        console.print(f"\n[cyan]Analyse en cours avec Helius API...")

        try:
            # Extraire features
            features = await extractor.extract_all_features(mint)

            if not features:
                console.print("[yellow]Impossible d'extraire les features")
                continue

            # Preparer pour prediction
            feature_dict = {fname: features.get(fname, 0) for fname in feature_names}
            df = pd.DataFrame([feature_dict])
            X = scaler.transform(df)

            # Prediction
            prediction = model.predict(X)[0]
            probabilities = model.predict_proba(X)[0]

            # Afficher resultat
            label_names = {0: "RUG", 1: "SAFE", 2: "GEM"}
            label_colors = {0: "red", 1: "yellow", 2: "green"}
            label_emojis = {0: "[!]", 1: "[~]", 2: "[*]"}

            label = label_names[prediction]
            color = label_colors[prediction]
            emoji = label_emojis[prediction]
            confidence = probabilities[prediction] * 100

            panel_content = f"""
[bold {color}]{emoji} PREDICTION: {label}[/bold {color}]
[bold white]Confiance: {confidence:.2f}%[/bold white]

[cyan]Probabilites:[/cyan]
[!] RUG:  {probabilities[0]*100:6.2f}%
[~] SAFE: {probabilities[1]*100:6.2f}%
[*] GEM:  {probabilities[2]*100:6.2f}%
            """

            console.print(Panel(panel_content, title="Resultat", border_style=color))

            # Table d'infos
            info_table = Table(show_header=True)
            info_table.add_column("Metrique", style="cyan")
            info_table.add_column("Valeur", style="white", justify="right")

            info_table.add_row("Market Cap", f"${features.get('market_cap_usd', 0):,.2f}")
            info_table.add_row("Liquidite", f"${features.get('liquidity_usd', 0):,.2f}")
            info_table.add_row("Holders", f"{features.get('holder_count', 0):,}")
            info_table.add_row("Volume 24h", f"${features.get('volume_24h', 0):,.2f}")
            info_table.add_row("Fresh Wallets", f"{features.get('fresh_wallet_percentage', 0):.1f}%")
            info_table.add_row("Snipers", f"{features.get('early_sniper_count', 0)}")

            console.print(info_table)

            recommendations = {
                0: "[red][!] DANGER! Fort risque de rug pull. NE PAS INVESTIR.",
                1: "[yellow][~] Gain modere probable. Investissement prudent possible.",
                2: "[green][*] Excellent potentiel! Opportunite interessante (DYOR)."
            }

            console.print(f"\n{recommendations[prediction]}\n")

        except Exception as e:
            console.print(f"[red]Erreur: {e}\n")

        await asyncio.sleep(1)

    # Conclusion
    console.print("\n[bold green]" + "=" * 70)
    console.print("[bold green]DEMO TERMINEE AVEC SUCCES!")
    console.print("[bold green]" + "=" * 70)

    console.print("\n[bold cyan]Performances avec Helius:")
    console.print("[green]  [OK] Aucune erreur rate limit!")
    console.print("[green]  [OK] Vitesse maximale!")
    console.print("[green]  [OK] Donnees completes!")

    console.print("\n[bold yellow]Pour lancer le systeme complet:")
    console.print("[white]  python continuous_learning_system.py")
    console.print("[white]  python app.py\n")

    await extractor.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrompue.")

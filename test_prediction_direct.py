"""
TEST DIRECT DE PREDICTION
Teste la prediction sur un token specifique
"""
import asyncio
import sys
from pathlib import Path
from rich.console import Console
import joblib
import json
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from feature_extractor import TokenFeatureExtractor

console = Console()

async def test_prediction(token_address):
    """Teste une prediction sur un token"""

    console.print("\n[bold cyan]" + "=" * 70)
    console.print("[bold cyan]TEST DE PREDICTION DIRECTE")
    console.print("[bold cyan]" + "=" * 70)

    # Charger le modele
    models_dir = Path(__file__).parent / "models"

    console.print("\n[cyan]Chargement du modele...")
    model = joblib.load(models_dir / "roi_predictor_latest.pkl")
    scaler = joblib.load(models_dir / "roi_scaler_latest.pkl")
    with open(models_dir / "roi_feature_names.json", "r") as f:
        feature_names = json.load(f)
    console.print("[green]Modele charge: XGBoost 95.61%!")

    # Extraire les features
    console.print(f"\n[cyan]Analyse du token: {token_address}")
    console.print("[cyan]Extraction des features...")

    extractor = TokenFeatureExtractor()
    features = await extractor.extract_all_features(token_address)

    if not features:
        console.print("[red]Impossible d'extraire les features")
        await extractor.close()
        return

    console.print("[green]Features extraites avec succes!")

    # Preparer pour prediction
    feature_dict = {}
    for fname in feature_names:
        feature_dict[fname] = features.get(fname, 0)

    df = pd.DataFrame([feature_dict])
    X = scaler.transform(df)

    # Prediction
    prediction = model.predict(X)[0]
    probabilities = model.predict_proba(X)[0]

    # Afficher les resultats
    console.print("\n[bold yellow]" + "=" * 70)
    console.print("[bold yellow]RESULTATS DE LA PREDICTION")
    console.print("[bold yellow]" + "=" * 70)

    label_names = {0: "RUG", 1: "SAFE", 2: "GEM"}
    label_colors = {0: "red", 1: "yellow", 2: "green"}
    label = label_names[prediction]
    color = label_colors[prediction]
    confidence = probabilities[prediction] * 100

    console.print(f"\n[bold {color}]PREDICTION: {label}")
    console.print(f"[bold {color}]CONFIANCE: {confidence:.2f}%")

    console.print("\n[cyan]Probabilites:")
    console.print(f"[red]  RUG:  {probabilities[0]*100:6.2f}%")
    console.print(f"[yellow]  SAFE: {probabilities[1]*100:6.2f}%")
    console.print(f"[green]  GEM:  {probabilities[2]*100:6.2f}%")

    console.print("\n[cyan]Informations du token:")
    console.print(f"[white]  Market Cap: ${features.get('market_cap_usd', 0):,.2f}")
    console.print(f"[white]  Liquidite:  ${features.get('liquidity_usd', 0):,.2f}")
    console.print(f"[white]  Holders:    {features.get('holder_count', 0):,}")
    console.print(f"[white]  Volume 24h: ${features.get('volume_24h', 0):,.2f}")

    console.print("\n[cyan]Features cles:")
    console.print(f"[white]  Fresh wallets: {features.get('fresh_wallet_percentage', 0):.1f}%")
    console.print(f"[white]  Bot holders:   {features.get('bot_holder_percentage', 0):.1f}%")
    console.print(f"[white]  Top 10 conc:   {features.get('top_10_concentration', 0):.1f}%")
    console.print(f"[white]  Sniper count:  {features.get('early_sniper_count', 0)}")

    recommendations = {
        0: "[red]DANGER! Fort risque de rug pull. NE PAS INVESTIR.",
        1: "[yellow]Gain modere probable. Investissement prudent possible.",
        2: "[green]Excellent potentiel! Opportunite interessante (DYOR)."
    }

    console.print(f"\n[bold white]Recommandation:")
    console.print(f"{recommendations[prediction]}")

    console.print("\n[bold cyan]" + "=" * 70)

    await extractor.close()


async def main():
    """Point d'entree"""
    # Utiliser un token Solana connu pour le test
    # USDC sur Solana (stable, devrait etre SAFE)
    test_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    console.print("\n[bold green]Test avec USDC (devrait predire SAFE):")
    await test_prediction(test_token)

    # Si l'utilisateur veut tester un autre token
    console.print("\n[cyan]Pour tester un autre token, modifiez la variable 'test_token' dans ce script.")
    console.print("[cyan]Ou lancez: python app.py pour l'interface web!")


if __name__ == "__main__":
    asyncio.run(main())

"""
TOKEN PREDICTOR - ML VERSION
Utilise le modèle ML entraîné pour prédire si un token est un RUG ou GEM
"""
import sys
import json
import httpx
import joblib
import numpy as np
from pathlib import Path

class MLTokenPredictor:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.client = httpx.Client(timeout=30.0)

    def load_model(self):
        """Charge le modèle ML entraîné"""
        models_dir = Path(__file__).parent / "models"

        model_file = models_dir / "token_predictor_model.pkl"
        scaler_file = models_dir / "token_predictor_scaler.pkl"
        features_file = models_dir / "token_predictor_features.json"

        if not model_file.exists():
            print("\n[!] Model not found! Please train the model first:")
            print("    python train_ml_model_advanced.py")
            return False

        # Charger le modèle
        self.model = joblib.load(model_file)
        self.scaler = joblib.load(scaler_file)

        with open(features_file, 'r') as f:
            data = json.load(f)
            self.feature_names = data['feature_names']

        print(f"[+] Model loaded successfully")
        print(f"[+] Features: {len(self.feature_names)}")

        return True

    def get_token_data(self, token_address):
        """Récupère les données d'un token depuis DexScreener"""
        print(f"\n[*] Fetching token data for {token_address}...")

        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            response = self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])

                if pairs:
                    # Prendre la première paire
                    pair = pairs[0]
                    print(f"[+] Found token: {pair.get('baseToken', {}).get('name', 'Unknown')}")
                    return pair

            print("[!] Token not found on DexScreener")
            return None

        except Exception as e:
            print(f"[-] Error fetching token: {e}")
            return None

    def extract_features(self, pair):
        """Extrait les features d'un token"""
        try:
            # Extraire les mêmes features que pour l'entraînement
            price_usd = float(pair.get('priceUsd', 0))
            liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0))
            volume_24h = float(pair.get('volume', {}).get('h24', 0))
            price_change_24h = float(pair.get('priceChange', {}).get('h24', 0))
            market_cap = float(pair.get('marketCap', 0))
            fdv = float(pair.get('fdv', 0))
            txns_24h_buys = pair.get('txns', {}).get('h24', {}).get('buys', 0)
            txns_24h_sells = pair.get('txns', {}).get('h24', {}).get('sells', 0)

            # Calculer les ratios
            buys = txns_24h_buys
            sells = txns_24h_sells

            buy_sell_ratio = buys / max(sells, 1)
            volume_mcap_ratio = volume_24h / max(market_cap, 1)

            # Créer le dictionnaire de features
            features = {
                'price_usd': price_usd,
                'price_change_24h': price_change_24h,
                'liquidity_usd': liquidity_usd,
                'volume_24h': volume_24h,
                'volume_mcap_ratio': volume_mcap_ratio,
                'market_cap': market_cap,
                'fdv': fdv,
                'txns_24h_buys': txns_24h_buys,
                'txns_24h_sells': txns_24h_sells,
                'buy_sell_ratio': buy_sell_ratio,
                'liquidity_per_mcap': liquidity_usd / max(market_cap, 1),
                'avg_buy_size': volume_24h / max(buys, 1),
                'avg_sell_size': volume_24h / max(sells, 1),
            }

            return features

        except Exception as e:
            print(f"[-] Error extracting features: {e}")
            return None

    def predict(self, token_address):
        """Prédit si un token est un RUG ou GEM"""

        # Charger le modèle
        if not self.load_model():
            return

        # Récupérer les données du token
        pair = self.get_token_data(token_address)
        if not pair:
            return

        # Extraire les features
        features = self.extract_features(pair)
        if not features:
            return

        # Créer le vecteur de features dans le bon ordre
        feature_vector = np.array([features[name] for name in self.feature_names]).reshape(1, -1)

        # Normaliser
        feature_vector_scaled = self.scaler.transform(feature_vector)

        # Prédire
        prediction = self.model.predict(feature_vector_scaled)[0]
        probability = self.model.predict_proba(feature_vector_scaled)[0]

        # Afficher les résultats
        print("\n" + "=" * 70)
        print("PREDICTION RESULT")
        print("=" * 70)

        token_name = pair.get('baseToken', {}).get('name', 'Unknown')
        token_symbol = pair.get('baseToken', {}).get('symbol', 'UNK')

        print(f"\nToken: {token_name} ({token_symbol})")
        print(f"Address: {token_address}")

        if prediction == 1:
            print(f"\n[GEM] This token is predicted to be a GEM!")
            print(f"Confidence: {probability[1] * 100:.2f}%")
        else:
            print(f"\n[RUG] This token is predicted to be a RUG!")
            print(f"Confidence: {probability[0] * 100:.2f}%")

        print("\n" + "-" * 70)
        print("Token Metrics:")
        print("-" * 70)
        print(f"Price: ${features['price_usd']:.8f}")
        print(f"Price Change 24h: {features['price_change_24h']:.2f}%")
        print(f"Market Cap: ${features['market_cap']:,.2f}")
        print(f"Liquidity: ${features['liquidity_usd']:,.2f}")
        print(f"Volume 24h: ${features['volume_24h']:,.2f}")
        print(f"Buy/Sell Ratio: {features['buy_sell_ratio']:.2f}")
        print("=" * 70)

        print("\n[i] Note: This model was trained on limited data.")
        print("    For best accuracy, collect 100+ tokens and retrain.")

    def close(self):
        """Ferme le client HTTP"""
        self.client.close()


def main():
    if len(sys.argv) < 2:
        print("\nUsage: python predict_token_ml.py <token_address>")
        print("\nExample:")
        print("  python predict_token_ml.py 7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr")
        return

    token_address = sys.argv[1]

    predictor = MLTokenPredictor()
    try:
        predictor.predict(token_address)
    finally:
        predictor.close()


if __name__ == "__main__":
    main()

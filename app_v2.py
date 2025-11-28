"""
PREDICTION AI V2 - Avec prédictions de prix précises!
Plus de "x1-x10" vague - prix exacts et détection de tops!
"""
from flask import Flask, render_template, request, jsonify
import joblib
import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from feature_extractor import TokenFeatureExtractor
from price_predictor import PricePredictor
from performance_tracker import PerformanceTracker

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Charger le modèle
MODEL_DIR = Path(__file__).parent / "models"

try:
    model = joblib.load(MODEL_DIR / "roi_predictor_latest.pkl")
    scaler = joblib.load(MODEL_DIR / "roi_scaler_latest.pkl")
    with open(MODEL_DIR / "roi_feature_names.json", "r") as f:
        feature_names = json.load(f)
    print("[OK] Modele charge: XGBoost 95.61%!")
    MODEL_LOADED = True
except Exception as e:
    print(f"[ERREUR] Impossible de charger le modele: {e}")
    MODEL_LOADED = False

# Price predictor
price_predictor = PricePredictor()

# Performance tracker
performance_tracker = PerformanceTracker()

@app.route('/')
def index():
    return render_template('index_v2.html', model_loaded=MODEL_LOADED)

@app.route('/predict', methods=['POST'])
def predict():
    if not MODEL_LOADED:
        return jsonify({'success': False, 'error': 'Modèle non chargé'}), 500

    data = request.get_json()
    token_address = data.get('token_address', '').strip()

    if not token_address:
        return jsonify({'success': False, 'error': 'Adresse de token requise'}), 400

    try:
        # Extraire les features
        extractor = TokenFeatureExtractor()
        features = asyncio.run(extractor.extract_all_features(token_address))
        asyncio.run(extractor.close())

        if not features:
            return jsonify({'success': False, 'error': 'Impossible d\'extraire les features'}), 400

        # Prédiction de catégorie (RUG/SAFE/GEM)
        import pandas as pd
        feature_dict = {fname: features.get(fname, 0) for fname in feature_names}
        df = pd.DataFrame([feature_dict])
        X = scaler.transform(df)

        prediction = model.predict(X)[0]
        probabilities = model.predict_proba(X)[0]

        label_names = {0: "RUG", 1: "SAFE", 2: "GEM"}

        # Prédiction de prix PRÉCISE
        price_prediction = price_predictor.get_precise_prediction(features)

        # Résultat complet
        result = {
            'success': True,
            'token_address': token_address,

            # Prédiction de catégorie
            'category_prediction': {
                'label': int(prediction),
                'category': label_names[prediction],
                'confidence': float(probabilities[prediction] * 100),
                'probabilities': {
                    'RUG': float(probabilities[0] * 100),
                    'SAFE': float(probabilities[1] * 100),
                    'GEM': float(probabilities[2] * 100)
                }
            },

            # Prédiction de prix PRÉCISE
            'price_prediction': {
                'current_price': price_prediction['current_price'],
                'current_mcap': price_prediction['current_mcap'],
                'predicted_max_price': price_prediction['predicted_max_price'],
                'predicted_max_mcap': price_prediction['predicted_max_mcap'],
                'potential_multiplier': price_prediction['potential_multiplier'],
                'upside_percentage': price_prediction['upside_percentage'],
                'confidence': price_prediction['confidence'] * 100,

                # Détection de top
                'is_at_top': price_prediction['is_at_top'],
                'dump_probability': price_prediction['dump_probability'],
                'top_signals': price_prediction['top_signals'],

                # Action recommandée
                'action': price_prediction['action'],
                'action_color': price_prediction['action_color'],
                'reason': price_prediction['reason'],

                # Points d'entrée/sortie
                'entry_price': price_prediction.get('entry_price'),
                'exit_price': price_prediction.get('exit_price'),
                'stop_loss': price_prediction.get('stop_loss')
            },

            # Features clés
            'features': {
                'liquidity_usd': features.get('liquidity_usd', 0),
                'holder_count': features.get('holder_count', 0),
                'volume_24h': features.get('volume_24h', 0),
                'fresh_wallets': features.get('fresh_wallet_percentage', 0),
                'bot_holders': features.get('bot_holder_percentage', 0),
                'top_10_concentration': features.get('top_10_concentration', 0),
                'sniper_count': features.get('early_sniper_count', 0)
            },

            'timestamp': datetime.now().isoformat()
        }

        # Save prediction for performance tracking
        performance_tracker.save_prediction(token_address, result, features)

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    return jsonify({
        'success': True,
        'model_info': {
            'type': 'XGBoost + Price Predictor',
            'category_accuracy': 95.61,
            'price_prediction': 'Enabled',
            'top_detection': 'Enabled',
            'features_count': len(feature_names) if feature_names else 0
        }
    })


@app.route('/api/performance')
def api_performance():
    """API endpoint to get real-time performance stats"""
    try:
        stats = performance_tracker.get_stats()

        if not stats:
            return jsonify({
                'success': True,
                'message': 'No performance data yet',
                'stats': {
                    'total_predictions': 0,
                    'total_evaluated': 0
                }
            })

        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/recent-predictions')
def api_recent_predictions():
    """Get recent predictions with their results"""
    try:
        limit = request.args.get('limit', 10, type=int)
        recent = performance_tracker.get_recent_predictions(limit)

        return jsonify({
            'success': True,
            'predictions': recent.to_dict('records') if not recent.empty else []
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("  PREDICTION AI V2 - Predictions de Prix Precises")
    print("=" * 70)
    print(f"\n  Modele charge: {'OUI' if MODEL_LOADED else 'NON'}")
    print(f"  Prix precis: OUI")
    print(f"  Detection tops: OUI")
    print(f"\n  URL: http://localhost:5002")
    print(f"\n  [Ctrl+C pour arreter]")
    print("=" * 70 + "\n")

    app.run(host='0.0.0.0', port=5002, debug=True)

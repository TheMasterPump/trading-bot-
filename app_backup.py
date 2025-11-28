"""
PREDICTION AI - Site Web de Prédiction ROI
Système de prédiction du potentiel ROI pour tokens Pump.fun
+ Trading Bot Automatique
"""
from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for
import joblib
import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps

# Ajouter le chemin rug coin pour importer les modules d'analyse
sys.path.insert(0, str(Path(__file__).parent / "rug coin"))

from feature_extractor import TokenFeatureExtractor
from database_bot import db
from wallet_generator import SolanaWalletManager
from trading_service_optimized import start_bot_for_user, stop_bot_for_user, get_bot_status, get_system_stats, get_active_bots_count
from payment_config import PAYMENT_WALLET_ADDRESS, SUBSCRIPTION_PRICES
from payment_verifier import verify_payment_sync
from system_limits import MAX_CONCURRENT_BOTS, get_capacity_status, ERROR_MESSAGES
from scanner_data_manager import scanner_manager
from predict_runner import RunnerPredictor

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'  # IMPORTANT: Changer en production!
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Initialiser le wallet manager
wallet_manager = SolanaWalletManager()

@app.after_request
def add_header(response):
    """Désactive le cache pour tous les fichiers"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Charger le modèle ML
MODEL_DIR = Path(__file__).parent / "models"

try:
    runner_predictor = RunnerPredictor(models_dir=str(MODEL_DIR))
    MODEL_LOADED = runner_predictor.loaded
    if MODEL_LOADED:
        print("[OK] Modele Runner charge avec succes!")
    else:
        print("[ERROR] RunnerPredictor non charge")
except Exception as e:
    print(f"[ERROR] Impossible de charger RunnerPredictor: {e}")
    runner_predictor = None
    MODEL_LOADED = False

# Mapping des labels
LABEL_NAMES = {
    0: "RUG",
    1: "SAFE",
    2: "GEM"
}

ROI_RANGES = {
    0: "Token rug pull",
    1: "ROI 1-10x (gain modéré)",
    2: "ROI >10x (excellent potentiel)"
}

ROI_COLORS = {
    0: "danger",
    1: "warning",
    2: "success"
}

RECOMMENDATIONS = {
    0: "DO NOT BUY - Fort risque de rug pull",
    1: "Gain modéré probable - Investissement prudent possible",
    2: "Potentiel élevé - Opportunité intéressante (DYOR)"
}


@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html', model_loaded=MODEL_LOADED)


@app.route('/predict', methods=['POST'])
def predict():
    """API de prédiction"""
    if not MODEL_LOADED:
        return jsonify({
            'success': False,
            'error': 'Modèle ML non chargé'
        }), 500

    # Récupérer l'adresse du token
    data = request.get_json()
    token_address = data.get('token_address', '').strip()

    if not token_address:
        return jsonify({
            'success': False,
            'error': 'Adresse de token requise'
        }), 400

    try:
        # Extraire les features
        extractor = TokenFeatureExtractor()
        features = asyncio.run(extractor.extract_all_features(token_address))

        if not features:
            return jsonify({
                'success': False,
                'error': 'Impossible d\'extraire les features du token'
            }), 400

        # Préparer pour prédiction
        import pandas as pd
        feature_dict = {}
        for fname in feature_names:
            feature_dict[fname] = features.get(fname, 0)

        df = pd.DataFrame([feature_dict])
        X = scaler.transform(df)

        # Prédiction
        prediction = model.predict(X)[0]
        probabilities = model.predict_proba(X)[0]

        # Préparer la réponse
        market_cap = features.get('market_cap_usd', 0)

        # Détection de tokens morts/dump (override le modèle si signaux négatifs forts)
        buys_24h = features.get('buys_24h', 0)
        sells_24h = features.get('sells_24h', 0)
        volume_24h = features.get('volume_24h', 0)
        holder_count = features.get('holder_count', 0)

        is_dead_token = False
        dead_reason = ""

        # Token mort si: 0 buys, ou sells >> buys, ou volume très bas
        if buys_24h == 0 and sells_24h > 0:
            is_dead_token = True
            dead_reason = "0 buys, seulement des sells - Token mort"
        elif sells_24h > buys_24h * 2 and buys_24h < 10:
            is_dead_token = True
            dead_reason = f"Ratio sells/buys mauvais ({sells_24h}/{buys_24h})"
        elif volume_24h < 100 and market_cap < 10000:
            is_dead_token = True
            dead_reason = "Volume et MC très bas - Token abandonné"

        # Override prediction si token mort
        if is_dead_token:
            prediction = 0  # Force RUG
            probabilities = [0.95, 0.04, 0.01]  # 95% RUG

        # Calculer target price et migration probability basé sur la catégorie
        if prediction == 2:  # GEM
            target_multiplier = 10.0
            migration_prob = 85.0
        elif prediction == 1:  # SAFE
            target_multiplier = 3.0
            migration_prob = 45.0
        else:  # RUG
            target_multiplier = 0.1
            migration_prob = 5.0

        target_price = market_cap * target_multiplier

        result = {
            'success': True,
            'token_address': token_address,
            'token_info': {
                'symbol': features.get('symbol', 'N/A'),
                'name': features.get('name', 'Unknown'),
            },
            'prediction': {
                'label': int(prediction),
                'category': LABEL_NAMES[prediction],
                'roi_range': ROI_RANGES[prediction],
                'confidence': float(probabilities[prediction] * 100),
                'color': ROI_COLORS[prediction],
                'recommendation': dead_reason if is_dead_token else RECOMMENDATIONS[prediction],
                'target_price': round(target_price, 2),
                'target_multiplier': f"{target_multiplier}x",
                'migration_probability': round(migration_prob, 1),
                'is_dead': is_dead_token
            },
            'probabilities': {
                'RUG': float(probabilities[0] * 100),
                'SAFE': float(probabilities[1] * 100),
                'GEM': float(probabilities[2] * 100)
            },
            'features': {
                'organic_holders': features.get('organic_holder_estimate', 0),
                'liquidity_usd': features.get('liquidity_usd', 0),
                'fresh_wallets': features.get('fresh_wallet_percentage', 0),
                'bot_holders': features.get('bot_holder_percentage', 0),
                'holder_count': features.get('holder_count', 0),
                'market_cap': market_cap,
                'volume_24h': features.get('volume_24h', 0),
                'buy_sell_ratio': features.get('buy_sell_ratio', 0),
                'buys_24h': features.get('buys_24h', 0),
                'sells_24h': features.get('sells_24h', 0),
                'total_txns_24h': features.get('total_txns_24h', 0)
            },
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/about')
def about():
    """Page à propos"""
    return render_template('about.html')


@app.route('/api/stats')
def api_stats():
    """Statistiques du modèle"""
    if not MODEL_LOADED:
        return jsonify({
            'success': False,
            'error': 'Modèle non chargé'
        }), 500

    return jsonify({
        'success': True,
        'model_info': {
            'type': 'Random Forest Classifier',
            'accuracy': 94.74,
            'features_count': len(feature_names) if feature_names else 0,
            'categories': list(LABEL_NAMES.values()),
            'training_date': '2025-11-08'
        }
    })


# ====== DECORATORS ======

def login_required(f):
    """Décorateur pour vérifier l'authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentification requise'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ====== AUTHENTICATION ROUTES ======

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Inscription d'un nouvel utilisateur"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'success': False, 'error': 'Email et password requis'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password doit faire au moins 6 caractères'}), 400

    # Créer l'utilisateur
    user_id = db.create_user(email, password)

    if user_id is None:
        return jsonify({'success': False, 'error': 'Email déjà utilisé'}), 400

    # Générer un wallet automatiquement
    wallet_info = wallet_manager.generate_wallet()
    wallet_id = db.create_wallet(user_id, wallet_info['address'], wallet_info['private_key'])

    if wallet_id is None:
        return jsonify({'success': False, 'error': 'Erreur création wallet'}), 500

    # Connecter l'utilisateur
    session['user_id'] = user_id
    session['email'] = email
    session.permanent = True

    return jsonify({
        'success': True,
        'message': 'Compte créé avec succès!',
        'user': {
            'id': user_id,
            'email': email
        },
        'wallet': {
            'address': wallet_info['address'],
            'private_key': wallet_info['private_key'],  # ⚠️ MONTRE UNE SEULE FOIS !
            'show_warning': True  # Flag pour afficher le warning
        }
    })


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Connexion d'un utilisateur"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'success': False, 'error': 'Email et password requis'}), 400

    # Authentifier
    user = db.authenticate_user(email, password)

    if user is None:
        return jsonify({'success': False, 'error': 'Email ou password incorrect'}), 401

    # Créer la session
    session['user_id'] = user['id']
    session['email'] = user['email']
    session.permanent = True

    return jsonify({
        'success': True,
        'message': 'Connexion réussie!',
        'user': user
    })


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Déconnexion"""
    session.clear()
    return jsonify({'success': True, 'message': 'Déconnecté'})


@app.route('/api/auth/me')
@login_required
def get_current_user():
    """Récupère l'utilisateur connecté"""
    user_id = session['user_id']
    user = db.get_user(user_id)

    if user is None:
        session.clear()
        return jsonify({'success': False, 'error': 'Utilisateur non trouvé'}), 404

    return jsonify({
        'success': True,
        'user': user
    })


# ====== WALLET ROUTES ======

@app.route('/api/wallet/info')
@login_required
def wallet_info():
    """Récupère les infos du wallet"""
    user_id = session['user_id']
    wallet = db.get_wallet(user_id)

    if wallet is None:
        return jsonify({'success': False, 'error': 'Wallet non trouvé'}), 404

    # Mettre à jour le solde
    balance_sol = wallet_manager.get_balance(wallet['address'])
    balance_usd = wallet_manager.get_balance_usd(balance_sol)

    db.update_wallet_balance(user_id, balance_sol, balance_usd)

    wallet['balance_sol'] = balance_sol
    wallet['balance_usd'] = balance_usd

    return jsonify({
        'success': True,
        'wallet': wallet
    })


@app.route('/api/wallet/regenerate', methods=['POST'])
@login_required
def regenerate_wallet():
    """Génère un nouveau wallet pour l'utilisateur (si perdu l'ancien)"""
    user_id = session['user_id']

    # Vérifier qu'aucun bot n'est actif
    bot_status = get_bot_status(user_id)
    if bot_status.get('is_running'):
        return jsonify({
            'success': False,
            'error': 'Arrête ton bot avant de générer un nouveau wallet'
        }), 400

    # Récupérer l'ancien wallet (pour archivage optionnel)
    old_wallet = db.get_wallet(user_id)

    # Générer nouveau wallet
    new_wallet_info = wallet_manager.generate_wallet()

    # Mettre à jour dans la BDD
    # Note: On pourrait archiver l'ancien wallet au lieu de le remplacer
    success = db.update_wallet(
        user_id=user_id,
        new_address=new_wallet_info['address'],
        new_private_key=new_wallet_info['private_key']
    )

    if not success:
        return jsonify({
            'success': False,
            'error': 'Erreur lors de la création du nouveau wallet'
        }), 500

    return jsonify({
        'success': True,
        'message': 'Nouveau wallet généré avec succès!',
        'wallet': {
            'address': new_wallet_info['address'],
            'private_key': new_wallet_info['private_key'],  # ⚠️ MONTRE UNE SEULE FOIS !
            'show_warning': True,
            'old_address': old_wallet['address'] if old_wallet else None
        }
    })


# ====== BOT ROUTES ======

@app.route('/api/bot/status')
@login_required
def bot_status():
    """Récupère le statut du bot"""
    user_id = session['user_id']
    status = db.get_bot_status(user_id)

    return jsonify({
        'success': True,
        'status': status
    })


@app.route('/api/bot/start', methods=['POST'])
@login_required
def start_bot():
    """Démarre le bot"""
    user_id = session['user_id']
    data = request.get_json() or {}

    strategy = data.get('strategy', 'AI_PREDICTIONS')
    risk_level = data.get('risk_level', 'MEDIUM')

    # ===== LIMITE DE CAPACITÉ =====
    current_bots = get_active_bots_count()
    capacity = get_capacity_status(current_bots)

    if not capacity['can_accept_new']:
        return jsonify({
            'success': False,
            'error': ERROR_MESSAGES['SERVER_FULL'].format(current=current_bots),
            'server_full': True,
            'capacity': capacity
        }), 503

    # Vérifier le wallet
    wallet = db.get_wallet(user_id)
    if wallet is None:
        return jsonify({
            'success': False,
            'error': 'Wallet non trouvé'
        }), 400

    # Note: On permet de démarrer même avec 0 SOL en mode TEST/SIMULATION
    # if wallet['balance_sol'] <= 0:
    #     return jsonify({
    #         'success': False,
    #         'error': 'Wallet vide - Déposez des SOL pour commencer'
    #     }), 400

    # Vérifier la subscription
    subscription = db.get_active_subscription(user_id)
    if subscription is None:
        return jsonify({
            'success': False,
            'error': 'Aucun abonnement actif. Activez un plan (RISQUER, SAFE ou ULTRA) pour démarrer le bot.'
        }), 400

    # Démarrer le bot VIA LE SERVICE
    config = {
        'strategy': strategy,
        'risk_level': risk_level
    }

    result = start_bot_for_user(user_id, config)

    if not result['success']:
        return jsonify(result), 400

    # Mettre à jour la BDD
    db.start_bot(user_id, strategy, risk_level)

    return jsonify({
        'success': True,
        'message': 'Bot démarré! (Mode simulation pour Phase 1)',
        'strategy': strategy,
        'note': 'Le bot génère des trades de simulation. Phase 2 = trading réel avec ton bot existant.'
    })


@app.route('/api/bot/stop', methods=['POST'])
@login_required
def stop_bot():
    """Arrête le bot"""
    user_id = session['user_id']

    # Arrêter le bot VIA LE SERVICE
    result = stop_bot_for_user(user_id)

    # Mettre à jour la BDD
    db.stop_bot(user_id)

    return jsonify({
        'success': True,
        'message': 'Bot arrêté'
    })


@app.route('/api/bot/stats')
@login_required
def bot_stats():
    """Récupère les statistiques du bot"""
    user_id = session['user_id']

    # Mettre à jour les stats
    db.update_bot_stats(user_id)

    # Récupérer les stats
    stats = db.get_bot_stats(user_id)

    return jsonify({
        'success': True,
        'stats': stats
    })


@app.route('/api/bot/trades')
@login_required
def bot_trades():
    """Récupère l'historique des trades"""
    user_id = session['user_id']
    limit = request.args.get('limit', 50, type=int)

    trades = db.get_user_trades(user_id, limit)

    return jsonify({
        'success': True,
        'trades': trades
    })


@app.route('/api/subscription/upgrade', methods=['POST'])
@login_required
def upgrade_subscription():
    """Upgrade la subscription"""
    user_id = session['user_id']
    data = request.get_json()

    boost_level = data.get('boost_level', 'RISQUER')
    payment_tx = data.get('payment_tx')

    # Prix des boosts (en SOL)
    BOOST_PRICES = {
        'RISQUER': 0.15,  # Plan agressif
        'SAFE': 0.2,      # Plan conservateur
        'ULTRA': 0.5      # Plan premium (bientôt disponible)
    }

    price_sol = BOOST_PRICES.get(boost_level, 0.15)

    # Vérifier que ULTRA n'est pas encore disponible
    if boost_level == 'ULTRA':
        return jsonify({
            'success': False,
            'error': 'Le plan ULTRA sera bientôt disponible!'
        }), 400

    # Tous les plans nécessitent un paiement
    if not payment_tx:
        return jsonify({
            'success': False,
            'error': 'Transaction de paiement requise'
        }), 400

    # Créer la subscription
    db.create_subscription(user_id, boost_level, price_sol, duration_days=30, payment_tx=payment_tx)

    return jsonify({
        'success': True,
        'message': f'Subscription {boost_level} activée!',
        'expires_in_days': 30
    })


# ====== PAYMENT ROUTES ======

@app.route('/api/payment/create', methods=['POST'])
@login_required
def create_payment_request():
    """Crée une demande de paiement"""
    user_id = session['user_id']
    data = request.get_json()

    boost_level = data.get('boost_level', 'RISQUER')

    # Vérifier que ULTRA n'est pas disponible
    if boost_level == 'ULTRA':
        return jsonify({
            'success': False,
            'error': 'Le plan ULTRA sera bientôt disponible!'
        }), 400

    # Récupérer le prix
    price_sol = SUBSCRIPTION_PRICES.get(boost_level)
    if not price_sol:
        return jsonify({
            'success': False,
            'error': 'Plan invalide'
        }), 400

    # Créer la demande de paiement (expire dans 30 minutes)
    expires_at = datetime.now() + timedelta(minutes=30)

    payment_id = db.create_payment_request(
        user_id=user_id,
        boost_level=boost_level,
        amount_sol=price_sol,
        payment_address=PAYMENT_WALLET_ADDRESS,
        expires_at=expires_at.isoformat()
    )

    return jsonify({
        'success': True,
        'payment_id': payment_id,
        'amount_sol': price_sol,
        'payment_address': PAYMENT_WALLET_ADDRESS,
        'boost_level': boost_level,
        'expires_at': expires_at.isoformat(),
        'expires_in_minutes': 30
    })


@app.route('/api/payment/verify/<int:payment_id>', methods=['POST'])
@login_required
def verify_payment(payment_id):
    """Vérifie si un paiement a été effectué"""
    user_id = session['user_id']

    # Vérifier que le paiement appartient à l'utilisateur
    payment = db.get_pending_payment(payment_id)
    if not payment or payment['user_id'] != user_id:
        return jsonify({
            'success': False,
            'error': 'Paiement non trouvé'
        }), 404

    # Vérifier le paiement sur la blockchain
    result = verify_payment_sync(payment_id)

    if result['verified']:
        return jsonify({
            'success': True,
            'verified': True,
            'message': 'Paiement vérifié! Abonnement activé.',
            'signature': result['signature']
        })
    else:
        return jsonify({
            'success': False,
            'verified': False,
            'message': result.get('error', 'Transaction non trouvée. Veuillez réessayer.')
        })


@app.route('/api/payment/status/<int:payment_id>')
@login_required
def payment_status(payment_id):
    """Récupère le statut d'un paiement"""
    user_id = session['user_id']

    payment = db.get_pending_payment(payment_id)
    if not payment or payment['user_id'] != user_id:
        return jsonify({
            'success': False,
            'error': 'Paiement non trouvé'
        }), 404

    # Vérifier si expiré
    expires_at = datetime.fromisoformat(payment['expires_at'])
    is_expired = datetime.now() > expires_at

    return jsonify({
        'success': True,
        'payment': {
            'id': payment['id'],
            'boost_level': payment['boost_level'],
            'amount_sol': payment['amount_sol'],
            'status': payment['status'],
            'payment_address': payment['payment_address'],
            'expires_at': payment['expires_at'],
            'is_expired': is_expired
        }
    })


@app.route('/api/payment/history')
@login_required
def payment_history():
    """Récupère l'historique des paiements"""
    user_id = session['user_id']
    payments = db.get_user_payments(user_id)

    return jsonify({
        'success': True,
        'payments': payments
    })


# ====== MONITORING ROUTES ======

@app.route('/api/admin/stats')
def admin_stats():
    """
    Stats du système en temps réel (Optimized Architecture)
    Disponible pour monitoring sans auth (à protéger en production!)
    """
    try:
        stats = get_system_stats()
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/health')
def health_check():
    """Health check pour monitoring externe"""
    current_bots = get_active_bots_count()
    capacity = get_capacity_status(current_bots)

    return jsonify({
        'success': True,
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'active_bots': current_bots,
        'model_loaded': MODEL_LOADED,
        'capacity': capacity
    })


@app.route('/api/admin/capacity')
def admin_capacity():
    """Statut de capacité du serveur"""
    current_bots = get_active_bots_count()
    capacity = get_capacity_status(current_bots)

    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'capacity': capacity,
        'limits': {
            'max_concurrent_bots': MAX_CONCURRENT_BOTS,
            'max_bots_per_user': 1,
            'max_trades_per_day': 500
        }
    })


# ====== SCANNER ROUTES ======

@app.route('/api/scanner/stats')
def scanner_stats():
    """
    Scanner aggregated stats (PUBLIC - for homepage)
    Shows overall performance without revealing live data
    """
    try:
        stats = scanner_manager.get_aggregated_stats()
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/scanner/recent-wins')
def scanner_recent_wins():
    """
    Recent wins with 2-hour delay (PUBLIC - for homepage)
    Prevents front-running while showing proof of performance
    """
    try:
        # Get delay parameter (default 2 hours)
        delay_hours = request.args.get('delay', 2, type=int)
        limit = request.args.get('limit', 10, type=int)

        wins = scanner_manager.get_recent_wins_delayed(delay_hours, limit)

        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'delay_hours': delay_hours,
            'wins': wins
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/scanner/live-feed')
@login_required
def scanner_live_feed():
    """
    Live scanner feed (PRIVATE - subscribers only)
    Real-time token analysis results
    """
    try:
        user_id = session['user_id']

        # Check if user is subscribed (has active boost)
        # For now, just check if user exists (can add subscription check later)

        limit = request.args.get('limit', 50, type=int)
        feed = scanner_manager.get_live_scanner_feed(limit)

        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'feed': feed
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/scanner/live-gems')
@login_required
def scanner_live_gems():
    """
    Live GEM detections (PRIVATE - subscribers only)
    Shows tokens the AI identified as potential GEMs
    """
    try:
        user_id = session['user_id']

        # Check if user is subscribed (can add subscription check later)

        limit = request.args.get('limit', 20, type=int)
        gems = scanner_manager.get_live_gems(limit)

        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'gems': gems
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ====== BOT PAGE ======

@app.route('/bot')
def bot_page():
    """Page du bot de trading"""
    return render_template('bot.html')


@app.route('/admin')
def admin_page():
    """Page d'administration et monitoring"""
    return render_template('admin.html')


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("  PREDICTION AI - Site Web de Prediction ROI")
    print("=" * 70)
    print(f"\n  Modele charge: {'OUI' if MODEL_LOADED else 'NON'}")
    print(f"\n  URL: http://localhost:5001")
    print(f"  API: http://localhost:5001/predict")
    print(f"\n  [Ctrl+C pour arreter]")
    print("=" * 70 + "\n")

    app.run(host='0.0.0.0', port=5001, debug=True)

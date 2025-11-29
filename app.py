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
import random
import time
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
print(f"[PAYMENT CONFIG] Wallet address loaded: {PAYMENT_WALLET_ADDRESS}")
from payment_verifier import verify_payment_sync
from system_limits import MAX_CONCURRENT_BOTS, get_capacity_status, ERROR_MESSAGES
from scanner_data_manager import scanner_manager
from predict_runner import RunnerPredictor
from console_logger import get_console_logger
from demo_data_generator import demo_generator
import threading

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

        # Utiliser RunnerPredictor pour la prédiction
        pred_result = runner_predictor.predict(features)

        # Extraire les résultats
        market_cap = features.get('market_cap_usd', 0)
        buys_24h = features.get('buys_24h', 0)
        sells_24h = features.get('sells_24h', 0)
        volume_24h = features.get('volume_24h', 0)

        is_dead_token = False
        dead_reason = ""

        # Détection de tokens morts (override le modèle)
        if buys_24h == 0 and sells_24h > 0:
            is_dead_token = True
            dead_reason = "0 buys, seulement des sells - Token mort"
        elif sells_24h > buys_24h * 2 and buys_24h < 10:
            is_dead_token = True
            dead_reason = f"Ratio sells/buys mauvais ({sells_24h}/{buys_24h})"
        elif volume_24h < 100 and market_cap < 10000:
            is_dead_token = True
            dead_reason = "Volume et MC très bas - Token abandonné"

        # Convertir la prédiction runner en catégories RUG/SAFE/GEM
        runner_prob = pred_result.runner_probability
        target_price = pred_result.predicted_price
        migration_prob = pred_result.migration_probability

        # Calculer le multiplier
        target_multiplier = target_price / market_cap if market_cap > 0 else 1.0

        if is_dead_token:
            prediction = 0  # RUG
            probabilities = [0.95, 0.04, 0.01]
            target_price = market_cap * 0.1
            target_multiplier = 0.1
        elif target_multiplier < 1.2:  # Si target < 1.2x, c'est pas intéressant même si runner_prob élevé
            # Token déjà trop haut ou va baisser
            prediction = 0  # RUG/DUMP
            probabilities = [0.70, 0.25, 0.05]
            target_multiplier = max(0.5, target_multiplier)
        elif runner_prob >= 70 and target_multiplier >= 3.0:  # Runner avec bon upside = GEM
            prediction = 2
            probabilities = [0.05, 0.15, runner_prob / 100]
        elif runner_prob >= 40 and target_multiplier >= 1.5:  # Runner possible = SAFE
            prediction = 1
            probabilities = [0.10, runner_prob / 100, 0.10]
        else:  # Pas runner ou pas assez d'upside = RUG
            prediction = 0
            probabilities = [1 - runner_prob / 100, runner_prob / 100, 0.05]
            target_multiplier = max(0.5, target_multiplier)

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
            'type': 'Runner Classifier (Random Forest)',
            'accuracy': 99.50,
            'features_count': 91,
            'categories': list(LABEL_NAMES.values()),
            'training_date': '2025-11-24',
            'total_tokens_trained': 2228,
            'runners': 125,
            'win_rate': '5.6%'
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
        'message': '✅ Account created successfully!',
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
    """Récupère les infos du wallet (réel ou virtuel si en simulation)"""
    user_id = session['user_id']
    wallet = db.get_wallet(user_id)

    if wallet is None:
        return jsonify({'success': False, 'error': 'Wallet non trouvé'}), 404

    # Vérifier si en mode simulation
    simulation_session = db.get_simulation_session(user_id)
    is_simulation = simulation_session and simulation_session['is_active']

    if is_simulation:
        # Retourner le solde virtuel
        wallet['balance_sol'] = simulation_session['final_balance']
        wallet['balance_usd'] = wallet_manager.get_balance_usd(simulation_session['final_balance'])
        wallet['is_simulation'] = True
    else:
        # Mettre à jour le solde réel
        balance_sol = wallet_manager.get_balance(wallet['address'])
        balance_usd = wallet_manager.get_balance_usd(balance_sol)

        db.update_wallet_balance(user_id, balance_sol, balance_usd)

        wallet['balance_sol'] = balance_sol
        wallet['balance_usd'] = balance_usd
        wallet['is_simulation'] = False

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
            'error': '⚠️ Stop your bot before generating a new wallet'
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
        'message': '✅ New wallet generated successfully!',
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
    """Démarre le bot en mode SIMULATION ou RÉEL"""
    user_id = session['user_id']
    data = request.get_json() or {}

    strategy = data.get('strategy', 'AI_PREDICTIONS')
    risk_level = data.get('risk_level', 'MEDIUM')
    real_mode = data.get('real_mode', False)  # NOUVEAU: Mode réel activé?

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

    # ===== VÉRIFICATION MODE RÉEL (PREMIUM UNIQUEMENT) =====
    if real_mode:
        # Vérifier l'abonnement
        subscription = db.get_active_subscription(user_id)

        if not subscription:
            return jsonify({
                'success': False,
                'error': 'Mode réel réservé aux abonnés RISKY ou SAFE',
                'require_subscription': True
            }), 403

        boost_level = subscription['boost_level']
        if boost_level not in ['RISKY', 'SAFE']:
            return jsonify({
                'success': False,
                'error': f'Abonnement {boost_level} insuffisant. Mode réel nécessite RISKY ou SAFE.',
                'require_subscription': True
            }), 403

        # Vérifier le solde du wallet
        wallet_balance = wallet_manager.get_balance(wallet['address'])
        if wallet_balance < 0.01:  # Minimum 0.01 SOL requis (MODE TEST)
            return jsonify({
                'success': False,
                'error': f'Solde insuffisant: {wallet_balance:.4f} SOL. Minimum 0.01 SOL requis.',
                'insufficient_balance': True,
                'current_balance': wallet_balance
            }), 400

        print(f"[APP] 💰 MODE RÉEL activé pour user {user_id} | Abonnement: {boost_level} | Balance: {wallet_balance} SOL")

        # Configuration pour MODE RÉEL
        config = {
            'strategy': strategy,
            'risk_level': risk_level,
            'stop_loss': 25,
            'tp_strategy': 'PROGRESSIVE_AFTER_MIGRATION',
            'tp_config': {
                'initial_percent': 50,    # Vendre 50% à x2
                'step_percent': 5,         # Vendre 5% du reste
                'step_interval': 20        # Toutes les 20 secondes
            },
            'trailing_stop_enabled': True,
            'trailing_stop_activation_percent': 50,
            'trailing_stop_distance_percent': 20,
            'simulation_mode': False  # MODE RÉEL!
        }

        result = start_bot_for_user(user_id, config, simulation_mode=False)

        if not result['success']:
            return jsonify(result), 400

        # Mettre à jour la BDD
        db.start_bot(user_id, strategy, risk_level)

        return jsonify({
            'success': True,
            'message': '🚀 Bot started in REAL MODE!',
            'mode': 'REAL',
            'strategy': strategy,
            'wallet_balance': wallet_balance,
            'warning': '⚠️ You are trading with real SOL!'
        })

    # ===== MODE SIMULATION (GRATUIT POUR TOUS) =====
    # Vérifier si l'utilisateur a déjà une session de simulation
    simulation_session = db.get_simulation_session(user_id)

    # Si pas de session active, en créer une automatiquement
    if not simulation_session or not simulation_session['is_active']:
        # Terminer ancienne session si existe
        if simulation_session:
            db.end_simulation(simulation_session['id'])

        # Créer nouvelle session avec 10 SOL
        simulation_session_id = db.start_simulation(user_id)
        print(f"[APP] Session de simulation créée automatiquement: ID={simulation_session_id}")
    else:
        simulation_session_id = simulation_session['id']
        print(f"[APP] Utilisation session simulation existante: ID={simulation_session_id}")

    # Démarrer le bot VIA LE SERVICE EN MODE SIMULATION
    config = {
        'strategy': strategy,
        'risk_level': risk_level,
        'stop_loss': 25,
        'tp_strategy': 'PROGRESSIVE_AFTER_MIGRATION',
        'tp_config': {
            'initial_percent': 50,    # Vendre 50% à x2
            'step_percent': 5,         # Vendre 5% du reste
            'step_interval': 20        # Toutes les 20 secondes
        },
        'trailing_stop_enabled': True,
        'trailing_stop_activation_percent': 50,  # Active à +50%
        'trailing_stop_distance_percent': 20,    # Distance 20% du peak
        'simulation_mode': True,
        'simulation_session_id': simulation_session_id,
        'virtual_balance': 10.0
    }

    result = start_bot_for_user(user_id, config, simulation_mode=True)

    if not result['success']:
        return jsonify(result), 400

    # Mettre à jour la BDD
    db.start_bot(user_id, strategy, risk_level)

    return jsonify({
        'success': True,
        'message': '🎮 Bot started in SIMULATION MODE',
        'mode': 'SIMULATION',
        'strategy': strategy,
        'virtual_balance': 10.0
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


@app.route('/api/bot/sell', methods=['POST'])
@login_required
def manual_sell():
    """Vente manuelle d'une position (partielle ou totale)"""
    user_id = session['user_id']
    data = request.get_json() or {}

    token_address = data.get('token_address')
    percentage = data.get('percentage', 100)  # Par défaut 100%

    if not token_address:
        return jsonify({'success': False, 'error': 'Token address requis'}), 400

    if percentage <= 0 or percentage > 100:
        return jsonify({'success': False, 'error': 'Pourcentage invalide (1-100)'}), 400

    print(f"[MANUAL SELL] User {user_id} - Token {token_address} - {percentage}%")

    try:
        # Récupérer la position depuis la DB
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM open_positions
            WHERE user_id = ? AND token_address = ?
        """, (user_id, token_address))

        position_row = cursor.fetchone()

        if not position_row:
            return jsonify({'success': False, 'error': 'Position non trouvée'}), 404

        # Convertir en dict pour utiliser .get()
        position = dict(position_row)

        # Calculer le montant à vendre
        total_amount = position['amount_sol']
        sell_amount = total_amount * (percentage / 100.0)
        remaining_amount = total_amount - sell_amount

        print(f"[MANUAL SELL] Amount: {sell_amount:.4f} SOL ({percentage}% de {total_amount:.4f} SOL)")

        # Vérifier si c'est une simulation ou du réel
        bot_status = db.get_bot_status(user_id)
        is_simulation = True  # Par défaut simulation

        if bot_status:
            # Vérifier s'il y a une session de simulation active
            sim_session = db.get_simulation_session(user_id)
            is_simulation = sim_session and sim_session.get('is_active', False)

        # Exécuter la vente
        if is_simulation:
            # SIMULATION: Générer une TX fictive
            tx_signature = f"sim_manual_{secrets.token_urlsafe(8)}"
            print(f"[MANUAL SELL] Mode SIMULATION - TX: {tx_signature}")

            # Enregistrer le trade
            db.create_trade(
                user_id=user_id,
                token_address=token_address,
                trade_type='SELL',
                amount_sol=sell_amount,
                token_name=position['token_name'],
                price_usd=position.get('current_mc', 0),
                status='SIMULATED',
                tx_signature=tx_signature
            )

        else:
            # MODE RÉEL: Exécuter la vraie transaction
            print(f"[MANUAL SELL] Mode RÉEL - Exécution de la vente...")

            # Importer le trader
            from solana_trader_instance import create_trader_for_wallet

            # Récupérer wallet et clé privée
            wallet = db.get_wallet(user_id)
            private_key = db.get_wallet_private_key(user_id)

            if not wallet or not private_key:
                return jsonify({'success': False, 'error': 'Wallet ou clé privée introuvable'}), 400

            # Créer le trader
            trader = create_trader_for_wallet(wallet['address'], private_key)

            if not trader:
                return jsonify({'success': False, 'error': 'Impossible de créer le trader'}), 500

            # Exécuter la vente via PumpPortal
            print(f"[MANUAL SELL] Vente de {percentage}% via PumpPortal...")
            result = trader.sell_token(
                mint=token_address,
                amount_percent=percentage,
                slippage=25,
                priority_fee=0.001
            )

            if not result['success']:
                error_msg = result.get('error', 'Échec de la transaction de vente')
                print(f"[MANUAL SELL] ❌ Erreur: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 500

            tx_signature = result['signature']
            print(f"[MANUAL SELL] ✅ Vente réussie - TX: {tx_signature}")

            # Enregistrer le trade
            db.create_trade(
                user_id=user_id,
                token_address=token_address,
                trade_type='SELL',
                amount_sol=sell_amount,
                token_name=position['token_name'],
                price_usd=position.get('current_mc', 0),
                status='EXECUTED',
                tx_signature=tx_signature
            )

        # Mettre à jour ou fermer la position
        if percentage >= 100:
            # Fermer complètement la position
            cursor.execute("""
                DELETE FROM open_positions
                WHERE user_id = ? AND token_address = ?
            """, (user_id, token_address))
            print(f"[MANUAL SELL] Position fermée (100%)")
        else:
            # Mettre à jour le montant restant
            cursor.execute("""
                UPDATE open_positions
                SET amount_sol = ?
                WHERE user_id = ? AND token_address = ?
            """, (remaining_amount, user_id, token_address))
            print(f"[MANUAL SELL] Position mise à jour - Restant: {remaining_amount:.4f} SOL")

        conn.commit()

        return jsonify({
            'success': True,
            'message': f'Vente de {percentage}% réussie',
            'tx_signature': tx_signature,
            'amount_sol': sell_amount,
            'remaining_amount': remaining_amount if percentage < 100 else 0,
            'mode': 'SIMULATION' if is_simulation else 'REAL'
        })

    except Exception as e:
        print(f"[MANUAL SELL ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user/info')
@login_required
def get_user_info():
    """Récupère les informations de l'utilisateur (abonnement, wallet, permissions)"""
    user_id = session['user_id']

    # Récupérer l'utilisateur
    user = db.get_user(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'Utilisateur non trouvé'}), 404

    # Récupérer l'abonnement actif
    subscription = db.get_active_subscription(user_id)
    has_subscription = subscription is not None
    boost_level = subscription['boost_level'] if subscription else 'BASIC'

    # Vérifier si peut utiliser le mode réel
    can_use_real_mode = boost_level in ['RISKY', 'SAFE']

    # Récupérer le wallet
    wallet = db.get_wallet(user_id)
    wallet_address = wallet['address'] if wallet else None

    # Récupérer le solde réel (depuis la blockchain)
    wallet_balance = 0.0
    if wallet_address:
        try:
            wallet_balance = wallet_manager.get_balance(wallet_address)
            # Mettre à jour la BDD
            db.update_wallet_balance(user_id, wallet_balance, wallet_balance * wallet_manager.get_sol_price())
        except Exception as e:
            print(f"[ERROR] Impossible de récupérer le solde: {e}")

    # Vérifier si session de simulation active
    simulation_session = db.get_simulation_session(user_id)
    has_simulation = simulation_session and simulation_session['is_active']
    virtual_balance = simulation_session['final_balance'] if has_simulation else 0.0

    return jsonify({
        'success': True,
        'user': {
            'id': user_id,
            'email': user['email']
        },
        'subscription': {
            'active': has_subscription,
            'level': boost_level,
            'expires_at': subscription['expires_at'] if subscription else None
        },
        'wallet': {
            'address': wallet_address,
            'balance_sol': wallet_balance,
            'balance_usd': wallet_balance * wallet_manager.get_sol_price()
        },
        'simulation': {
            'active': has_simulation,
            'balance_sol': virtual_balance
        },
        'permissions': {
            'can_use_real_mode': can_use_real_mode,
            'can_use_simulation': True
        }
    })


@app.route('/api/bot/stats')
@login_required
def bot_stats():
    """Récupère les statistiques du bot (réel ou simulation)"""
    user_id = session['user_id']

    # Vérifier si en mode simulation
    simulation_session = db.get_simulation_session(user_id)
    is_simulation = simulation_session and simulation_session['is_active']

    if is_simulation:
        # Retourner les stats de simulation
        total_trades = simulation_session['total_trades']
        winning_trades = simulation_session['winning_trades']
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        stats = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'total_profit_usd': 0,  # TODO: calculer depuis les trades simulés
            'best_trade_profit': 0,
            'worst_trade_loss': 0,
            'is_simulation': True
        }
    else:
        # Mettre à jour les stats réelles
        db.update_bot_stats(user_id)

        # Récupérer les stats
        stats = db.get_bot_stats(user_id)
        stats['is_simulation'] = False

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


@app.route('/api/bot/positions')
@login_required
def bot_positions():
    """Récupère les positions actives du bot - HYBRID: Mémoire du bot OU base de données"""
    try:
        user_id = session['user_id']

        from trading_service_optimized import active_bots
        from ai_trading_engine import get_last_known_price

        positions = []

        # METHODE 1: Si bot actif, lire depuis la mémoire (TEMPS RÉEL!)
        if user_id in active_bots:
            print(f"[API] Reading positions from BOT MEMORY for user {user_id}")
            bot = active_bots[user_id]

            for mint, position in bot.active_positions.items():
                try:
                    symbol = position.get('token_name', f'Token_{mint[:6]}')
                    entry_mc = position.get('entry_mc', 0)

                    # Récupérer le prix LIVE depuis le WebSocket
                    live_price = get_last_known_price(mint)

                    if live_price['success'] and live_price['mc_usd'] > 0:
                        current_mc = live_price['mc_usd']
                    else:
                        current_mc = entry_mc

                    profit_ratio = current_mc / entry_mc if entry_mc > 0 else 1.0
                    profit_pct = (profit_ratio - 1) * 100

                    positions.append({
                        'mint': mint,
                        'token_address': mint,  # AJOUT: pour compatibilité avec boutons SELL
                        'token_name': symbol,
                        'entry_mc': entry_mc,
                        'current_mc': current_mc,
                        'amount_sol': position.get('amount', 0),
                        'profit_percent': profit_pct,
                        'profit_multiplier': profit_ratio,
                        'partial_sold': position.get('partial_sold', False),  # Flag vente partielle
                        'migration_reached': position.get('migration_reached', False),  # Flag migration
                        'distance_to_migration': 53000 - current_mc,
                        'migration_percent': (current_mc / 53000) * 100,
                        'entry_time': position.get('entry_time').isoformat() if position.get('entry_time') else None
                    })
                except Exception as e:
                    print(f"[ERROR] Failed to process position {mint[:8]}: {e}")
                    continue

        # METHODE 2: Si bot pas actif, lire depuis la BDD
        else:
            print(f"[API] Bot not active for user {user_id}, reading from DATABASE")
            db_positions = db.get_open_positions(user_id)

            for pos in db_positions:
                try:
                    mint = pos['token_address']
                    live_price = get_last_known_price(mint)

                    if live_price['success'] and live_price['mc_usd'] > 0:
                        current_mc = live_price['mc_usd']
                    else:
                        current_mc = pos['entry_mc']

                    profit_ratio = current_mc / pos['entry_mc'] if pos['entry_mc'] > 0 else 1.0
                    profit_pct = (profit_ratio - 1) * 100

                    positions.append({
                        'mint': mint,
                        'token_address': mint,  # AJOUT: pour compatibilité avec boutons SELL
                        'token_name': pos['token_name'],
                        'entry_mc': pos['entry_mc'],
                        'current_mc': current_mc,
                        'amount_sol': pos['amount_sol'],
                        'profit_percent': profit_pct,
                        'profit_multiplier': profit_ratio,
                        'partial_sold': False,  # Pas d'info en BDD, on assume false
                        'migration_reached': False,  # Pas d'info en BDD, on assume false
                        'distance_to_migration': 53000 - current_mc,
                        'migration_percent': (current_mc / 53000) * 100,
                        'entry_time': pos['entry_time']
                    })
                except Exception as e:
                    print(f"[ERROR] Failed to process position {mint[:8]}: {e}")
                    continue

        print(f"[API] Returning {len(positions)} positions for user {user_id}")
        return jsonify({
            'success': True,
            'positions': positions
        })

    except Exception as e:
        print(f"[ERROR] /api/bot/positions failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'positions': [],
            'error': str(e)
        })


@app.route('/api/bot/console-logs')
def console_logs():
    """Récupère les logs de la console (AI Engine + Bots)"""
    try:
        # Récupérer l'utilisateur connecté
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Not authenticated'
            }), 401

        logger = get_console_logger()
        limit = request.args.get('limit', 100, type=int)

        # Récupérer les logs GLOBAUX (user_id=0) + logs de l'utilisateur
        global_logs = logger.get_logs(user_id=0, limit=limit)  # Logs globaux (NEW TOKEN, SKIP, etc.)
        user_logs = logger.get_logs(user_id=user_id, limit=limit)  # Logs du bot de l'utilisateur

        # Merger et trier par timestamp
        all_logs = global_logs + user_logs
        # Trier par timestamp (format HH:MM:SS)
        all_logs.sort(key=lambda x: x['timestamp'])

        # Limiter au nombre demandé
        logs = all_logs[-limit:] if len(all_logs) > limit else all_logs

        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/subscription/upgrade', methods=['POST'])
@login_required
def upgrade_subscription():
    """Upgrade la subscription"""
    user_id = session['user_id']
    data = request.get_json()

    boost_level = data.get('boost_level', 'RISKY')
    payment_tx = data.get('payment_tx')

    # Prix des boosts (en SOL)
    BOOST_PRICES = {
        'RISKY': 1.5,     # Plan agressif
        'SAFE': 2.0,      # Plan conservateur
        'ULTRA': 3.0      # Plan premium (bientôt disponible)
    }

    price_sol = BOOST_PRICES.get(boost_level, 1.5)

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
        'message': f'✅ Subscription {boost_level} activated!',
        'expires_in_days': 30
    })


# ====== PAYMENT ROUTES ======

@app.route('/api/payment/create', methods=['POST'])
@login_required
def create_payment_request():
    """Crée une demande de paiement"""
    user_id = session['user_id']
    data = request.get_json()

    boost_level = data.get('boost_level', 'RISKY')

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
            'message': '✅ Payment verified! Subscription activated.',
            'signature': result['signature']
        })
    else:
        return jsonify({
            'success': False,
            'verified': False,
            'message': result.get('error', '❌ Transaction not found. Please try again.')
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


# ====== SIMULATION MODE API ======

@app.route('/api/simulation/start', methods=['POST'])
def start_simulation():
    """Démarre une session de simulation de 2h"""
    try:
        # Récupérer l'utilisateur depuis la session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Non authentifié'
            }), 401

        # Démarrer la simulation
        session_id = db.start_simulation(user_id)

        if session_id is None:
            return jsonify({
                'success': False,
                'error': '⚠️ You have already used your free 2-hour simulation period.'
            }), 400

        # Récupérer les détails de la session
        sim_session = db.get_simulation_session(user_id)

        return jsonify({
            'success': True,
            'session': sim_session,
            'message': '🎮 Simulation mode activated! You have 2 hours.'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/simulation/status')
def get_simulation_status():
    """Récupère le statut de la simulation en cours"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Non authentifié'
            }), 401

        # Récupérer la session de simulation
        sim_session = db.get_simulation_session(user_id)

        if not sim_session:
            return jsonify({
                'success': True,
                'has_simulation': False
            })

        # Vérifier si la simulation a expiré
        end_time = datetime.fromisoformat(sim_session['end_time'])
        now = datetime.now()

        if now > end_time and sim_session['is_active']:
            # Expirer la simulation
            db.end_simulation(sim_session['id'])
            sim_session['is_active'] = False
            sim_session['is_expired'] = True

        return jsonify({
            'success': True,
            'has_simulation': True,
            'session': sim_session,
            'time_remaining_seconds': max(0, (end_time - now).total_seconds()) if now <= end_time else 0
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/simulation/end', methods=['POST'])
def end_simulation_route():
    """Termine manuellement une session de simulation"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Non authentifié'
            }), 401

        # Récupérer la session
        sim_session = db.get_simulation_session(user_id)

        if not sim_session:
            return jsonify({
                'success': False,
                'error': 'Aucune simulation en cours'
            }), 400

        # Terminer la simulation
        db.end_simulation(sim_session['id'])

        return jsonify({
            'success': True,
            'message': '✅ Simulation completed',
            'final_stats': {
                'total_trades': sim_session['total_trades'],
                'winning_trades': sim_session['winning_trades'],
                'final_balance': sim_session['final_balance']
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ====== DEMO MODE API ======

# Variables globales pour le mode démo
demo_active = False
demo_thread = None
demo_logs = []
demo_max_logs = 200

def run_demo_simulation():
    """Thread qui exécute la simulation en arrière-plan"""
    global demo_active, demo_logs

    print("[DEMO] Starting demo simulation thread...")

    try:
        # Réinitialiser le générateur
        demo_generator.active_positions = []
        demo_generator.completed_trades = []
        demo_generator.total_profit_sol = 0.0
        demo_generator.virtual_balance = 10.0

        while demo_active:
            # Vérifier si on peut acheter un nouveau token
            if len(demo_generator.active_positions) < 3:  # Max 3 positions en même temps
                # Générer un nouveau token runner toutes les 10-20 secondes
                if random.random() < 0.3:  # 30% de chance à chaque tick
                    token = demo_generator.generate_runner_token()
                    demo_generator.active_positions.append(token)

                    # Logs pour le nouveau token
                    demo_logs.append(demo_generator.generate_log('NEW_TOKEN', token))
                    time.sleep(0.5)
                    demo_logs.append(demo_generator.generate_log('AI_ANALYSIS', token))
                    time.sleep(0.5)
                    demo_logs.append(demo_generator.generate_log('BUY_SIGNAL', token))

                    # Limiter la taille des logs
                    if len(demo_logs) > demo_max_logs:
                        demo_logs = demo_logs[-demo_max_logs:]

            # Mettre à jour les prix des positions actives
            positions_to_remove = []

            for i, token in enumerate(demo_generator.active_positions):
                # Simuler le mouvement de prix
                demo_generator.simulate_price_movement(token)

                # Log de mise à jour de prix toutes les quelques updates
                if random.random() < 0.4:  # 40% de chance
                    demo_logs.append(demo_generator.generate_log('PRICE_UPDATE', token))

                # Log de migration si atteinte
                if token['migration_reached'] and token.get('migration_logged') is None:
                    demo_logs.append(demo_generator.generate_log('MIGRATION', token))
                    token['migration_logged'] = True

                # Vérifier si on doit vendre
                if demo_generator.should_sell(token):
                    # Exécuter la vente
                    trade = demo_generator.execute_sell(token)
                    demo_logs.append(demo_generator.generate_log('SELL_EXECUTED', trade))

                    # Marquer pour suppression
                    positions_to_remove.append(i)

                    # Log de stats
                    stats = demo_generator.get_current_stats()
                    demo_logs.append(demo_generator.generate_log('STATS_UPDATE', stats))

                # Limiter la taille des logs
                if len(demo_logs) > demo_max_logs:
                    demo_logs = demo_logs[-demo_max_logs:]

            # Supprimer les positions vendues
            for i in reversed(positions_to_remove):
                demo_generator.active_positions.pop(i)

            # Pause entre les ticks (2-4 secondes)
            time.sleep(random.uniform(2, 4))

    except Exception as e:
        print(f"[DEMO ERROR] {e}")
        import traceback
        traceback.print_exc()

    print("[DEMO] Demo simulation thread stopped")


@app.route('/api/demo/start', methods=['POST'])
@login_required
def start_demo():
    """Démarre le mode démo"""
    global demo_active, demo_thread, demo_logs

    if demo_active:
        return jsonify({
            'success': False,
            'error': 'Demo already running'
        }), 400

    # Réinitialiser les logs
    demo_logs = []

    # Démarrer le thread de simulation
    demo_active = True
    demo_thread = threading.Thread(target=run_demo_simulation, daemon=True)
    demo_thread.start()

    return jsonify({
        'success': True,
        'message': '🎮 Demo mode started!'
    })


@app.route('/api/demo/stop', methods=['POST'])
@login_required
def stop_demo():
    """Arrête le mode démo"""
    global demo_active

    demo_active = False

    return jsonify({
        'success': True,
        'message': 'Demo stopped',
        'final_stats': demo_generator.get_current_stats()
    })


@app.route('/api/demo/status')
@login_required
def demo_status():
    """Récupère le statut du mode démo"""
    return jsonify({
        'success': True,
        'active': demo_active,
        'stats': demo_generator.get_current_stats()
    })


@app.route('/api/demo/logs')
@login_required
def demo_logs_api():
    """Récupère les derniers logs de la démo"""
    global demo_logs

    # Récupérer les N derniers logs
    limit = request.args.get('limit', 50, type=int)
    logs = demo_logs[-limit:] if len(demo_logs) > limit else demo_logs

    return jsonify({
        'success': True,
        'logs': logs,
        'count': len(logs),
        'active': demo_active
    })


# ====== BOT PAGE ======

@app.route('/bot')
def bot_page():
    """Page du bot de trading"""
    return render_template('bot.html')


@app.route('/admin')
def admin_page():
    """Page d'administration et monitoring"""
    return render_template('admin.html')


@app.route('/api/test/positions')
def test_positions():
    """Route de test pour debugger les positions"""
    try:
        # Test sans auth pour debug
        user_id = 4  # Hardcoded pour test
        positions = db.get_open_positions(user_id)

        # Ajouter les champs nécessaires
        from pumpfun_price_fetcher import get_token_price_live
        for pos in positions:
            try:
                result = get_token_price_live(pos['token_address'])
                if result and result.get('success') and result.get('mc_usd', 0) > 0:
                    pos['current_mc'] = result['mc_usd']
                    pos['profit_percent'] = (result['mc_usd'] - pos['entry_mc']) / pos['entry_mc']
                    pos['profit_multiplier'] = 1.0 + pos['profit_percent']
                else:
                    pos['current_mc'] = pos['entry_mc']
                    pos['profit_percent'] = 0.0
                    pos['profit_multiplier'] = 1.0
            except:
                pos['current_mc'] = pos['entry_mc']
                pos['profit_percent'] = 0.0
                pos['profit_multiplier'] = 1.0

        return jsonify({
            'success': True,
            'count': len(positions),
            'positions': positions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


# Global error handler pour logger toutes les exceptions
@app.errorhandler(500)
def internal_error(error):
    import traceback
    print("\n" + "="*80)
    print("[ERROR 500] Internal Server Error:")
    print("="*80)
    traceback.print_exc()
    print("="*80 + "\n")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


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


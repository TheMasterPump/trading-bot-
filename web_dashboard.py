"""
WEB DASHBOARD - Interface locale pour pattern_discovery_bot
Lance un serveur web local pour visualiser les données en temps réel
"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import threading
import time

app = Flask(__name__)
CORS(app)

# Fichier de données partagé avec le bot
DATA_FILE = 'bot_data.json'

def read_bot_data():
    """Lire les données du bot"""
    if not os.path.exists(DATA_FILE):
        return {
            'tokens': [],
            'completed': [],
            'runners': [],
            'flops': [],
            'alerts': [],
            'stats': {
                'total_tokens': 0,
                'total_runners': 0,
                'total_flops': 0,
                'win_rate': 0
            }
        }

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Lecture bot_data.json: {e}")
        return {
            'tokens': [],
            'completed': [],
            'runners': [],
            'flops': [],
            'alerts': [],
            'stats': {
                'total_tokens': 0,
                'total_runners': 0,
                'total_flops': 0,
                'win_rate': 0
            }
        }

@app.route('/')
def index():
    """Page principale"""
    return render_template('dashboard.html')

@app.route('/api/data')
def get_data():
    """API pour récupérer les données"""
    data = read_bot_data()
    return jsonify(data)

@app.route('/api/stats')
def get_stats():
    """API pour les statistiques"""
    data = read_bot_data()
    return jsonify(data.get('stats', {}))

@app.route('/api/alerts')
def get_alerts():
    """API pour les alertes récentes"""
    data = read_bot_data()
    # Retourner les 20 dernières alertes
    alerts = data.get('alerts', [])
    return jsonify(alerts[-20:])

@app.route('/api/tokens/active')
def get_active_tokens():
    """API pour les tokens actifs (en cours d'analyse)"""
    data = read_bot_data()
    return jsonify(data.get('tokens', []))

@app.route('/api/tokens/completed')
def get_completed_tokens():
    """API pour les tokens complétés"""
    data = read_bot_data()
    return jsonify(data.get('completed', []))

@app.route('/api/runners')
def get_runners():
    """API pour les runners uniquement"""
    data = read_bot_data()
    return jsonify(data.get('runners', []))

@app.route('/api/flops')
def get_flops():
    """API pour les flops uniquement"""
    data = read_bot_data()
    return jsonify(data.get('flops', []))

@app.route('/api/mark_migration', methods=['POST'])
def mark_migration():
    """Marquer si un RUNNER a migré ou non"""
    from flask import request
    import json

    req_data = request.json
    mint = req_data.get('mint')
    migrated = req_data.get('migrated')  # True ou False

    if mint is None or migrated is None:
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400

    # Lire les données
    bot_data = read_bot_data()

    # Trouver et mettre à jour l'alerte correspondante
    updated = False
    for alert in bot_data.get('alerts', []):
        if alert.get('type') == 'runner' and alert.get('mint') == mint:
            alert['migrated'] = migrated
            updated = True

    if updated:
        # Sauvegarder
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(bot_data, f, indent=2)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'Alert not found'}), 404

if __name__ == '__main__':
    print("\n" + "="*80)
    print("WEB DASHBOARD - Pattern Discovery Bot")
    print("="*80)
    print("\nOuvre ton navigateur a l'adresse:")
    print("\n  ->  http://localhost:5000\n")
    print("Pour arreter: Ctrl+C")
    print("="*80 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False)

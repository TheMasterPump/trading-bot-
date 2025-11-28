"""
SYSTEM LIMITS & CAPACITY CONFIGURATION
Configuration centralisée des limites du système
"""
import os

# ============================================================================
# CAPACITÉ SERVEUR
# ============================================================================

# Nombre maximum de bots actifs simultanément
# IMPORTANT: Ajuster selon ton VPS !
MAX_CONCURRENT_BOTS = int(os.environ.get('MAX_CONCURRENT_BOTS', 200))

# Mapping VPS → Limite recommandée
VPS_RECOMMENDATIONS = {
    '2GB': 50,
    '4GB': 150,
    '8GB': 300,
    '16GB': 500
}

# ============================================================================
# LIMITES PAR UTILISATEUR
# ============================================================================

# Maximum de bots qu'un seul utilisateur peut lancer (normalement 1)
MAX_BOTS_PER_USER = 1

# Maximum de trades par jour par utilisateur (anti-spam)
MAX_TRADES_PER_DAY = 500

# Maximum de tentatives de démarrage de bot par heure
MAX_BOT_START_ATTEMPTS_PER_HOUR = 10

# ============================================================================
# LIMITES WEBSOCKET & RÉSEAU
# ============================================================================

# Timeout pour reconnexion WebSocket (secondes)
WEBSOCKET_RECONNECT_DELAY = 5

# Maximum de reconnexions avant arrêt
WEBSOCKET_MAX_RECONNECTS = 10

# Timeout pour réponse API (secondes)
API_TIMEOUT = 30

# ============================================================================
# LIMITES TRADING ENGINE
# ============================================================================

# Maximum de tokens à analyser par minute (protection CPU)
MAX_TOKENS_PER_MINUTE = 1000

# Maximum de signaux à envoyer par minute (éviter spam)
MAX_SIGNALS_PER_MINUTE = 100

# ============================================================================
# LIMITES BASE DE DONNÉES
# ============================================================================

# Maximum de trades gardés en mémoire par bot
MAX_TRADES_IN_MEMORY = 100

# Intervalle de nettoyage de la DB (secondes)
DB_CLEANUP_INTERVAL = 3600  # 1 heure

# ============================================================================
# ALERTES & MONITORING
# ============================================================================

# Seuil d'alerte (% de capacité)
ALERT_THRESHOLD_PERCENT = 80  # Alerte à 80% de capacité

# Calculer le seuil d'alerte absolu
ALERT_THRESHOLD_BOTS = int(MAX_CONCURRENT_BOTS * ALERT_THRESHOLD_PERCENT / 100)

# ============================================================================
# MESSAGES UTILISATEUR
# ============================================================================

ERROR_MESSAGES = {
    'SERVER_FULL': f'Serveur complet ({{current}}/{MAX_CONCURRENT_BOTS} bots actifs). Réessaie dans quelques minutes.',
    'BOT_ALREADY_RUNNING': 'Ton bot est déjà actif. Arrête-le avant d\'en démarrer un nouveau.',
    'MAX_TRADES_REACHED': f'Limite de {MAX_TRADES_PER_DAY} trades/jour atteinte. Réessaie demain.',
    'TOO_MANY_ATTEMPTS': f'Trop de tentatives. Attends {60} minutes avant de réessayer.',
    'SYSTEM_OVERLOAD': 'Système surchargé. Réessaie dans quelques minutes.',
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_capacity_status(current_bots: int) -> dict:
    """
    Retourne le statut de capacité du serveur
    """
    percent_used = (current_bots / MAX_CONCURRENT_BOTS) * 100 if MAX_CONCURRENT_BOTS > 0 else 0

    if percent_used >= 100:
        status = 'FULL'
    elif percent_used >= ALERT_THRESHOLD_PERCENT:
        status = 'WARNING'
    elif percent_used >= 50:
        status = 'HEALTHY'
    else:
        status = 'LOW'

    return {
        'current_bots': current_bots,
        'max_bots': MAX_CONCURRENT_BOTS,
        'percent_used': round(percent_used, 1),
        'available_slots': MAX_CONCURRENT_BOTS - current_bots,
        'status': status,
        'can_accept_new': current_bots < MAX_CONCURRENT_BOTS
    }


def should_alert(current_bots: int) -> bool:
    """
    Détermine si une alerte doit être envoyée
    """
    return current_bots >= ALERT_THRESHOLD_BOTS


def get_recommended_limit_for_vps(ram_gb: int) -> int:
    """
    Retourne la limite recommandée pour un VPS donné
    """
    if ram_gb <= 2:
        return 50
    elif ram_gb <= 4:
        return 150
    elif ram_gb <= 8:
        return 300
    else:
        return 500


# ============================================================================
# CONFIGURATION DISPLAY
# ============================================================================

def print_config():
    """Affiche la configuration actuelle"""
    print("\n" + "="*70)
    print("SYSTEM LIMITS CONFIGURATION")
    print("="*70)
    print(f"Max Concurrent Bots    : {MAX_CONCURRENT_BOTS}")
    print(f"Max Bots per User      : {MAX_BOTS_PER_USER}")
    print(f"Max Trades per Day     : {MAX_TRADES_PER_DAY}")
    print(f"Alert Threshold        : {ALERT_THRESHOLD_BOTS} bots ({ALERT_THRESHOLD_PERCENT}%)")
    print(f"WebSocket Reconnect    : {WEBSOCKET_RECONNECT_DELAY}s")
    print(f"Max Tokens per Minute  : {MAX_TOKENS_PER_MINUTE}")
    print(f"Max Signals per Minute : {MAX_SIGNALS_PER_MINUTE}")
    print("="*70)
    print("\nVPS RECOMMENDATIONS:")
    for vps, limit in VPS_RECOMMENDATIONS.items():
        print(f"  {vps:6s} RAM -> {limit:3d} bots max")
    print("="*70 + "\n")


if __name__ == "__main__":
    print_config()

    # Test capacity status
    print("\nTEST CAPACITY STATUS:\n")
    for test_bots in [10, 100, 160, 200, 250]:
        status = get_capacity_status(test_bots)
        print(f"{test_bots:3d} bots -> {status['status']:8s} ({status['percent_used']:5.1f}% used, {status['available_slots']:3d} slots free)")

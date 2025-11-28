"""
CONSOLE LOGGER
Système de logs centralisé pour le terminal web
Collecte les logs de l'AI Engine et des bots
"""
from datetime import datetime
from collections import deque
from threading import Lock


class ConsoleLogger:
    """
    Logger centralisé avec buffer circulaire
    Thread-safe pour multi-threading
    Supporte l'isolation par user_id
    """

    def __init__(self, max_logs=200):
        self.logs = {}  # {user_id: deque([...])}
        self.max_logs = max_logs
        self.lock = Lock()

    def log(self, message: str, log_type: str = 'INFO', user_id: int = None):
        """
        Ajoute un log au buffer d'un utilisateur

        Args:
            message: Message à logger
            log_type: Type de log (INFO, BUY, SKIP, NEW_TOKEN, SELL, ERROR)
            user_id: ID de l'utilisateur (None = log global partagé, utilise user_id=0)
        """
        with self.lock:
            # Si pas de user_id, utiliser 0 pour les logs globaux (engine, etc.)
            uid = user_id if user_id is not None else 0

            # Créer le deque pour cet utilisateur si nécessaire
            if uid not in self.logs:
                self.logs[uid] = deque(maxlen=self.max_logs)

            timestamp = datetime.now().strftime('%H:%M:%S')
            self.logs[uid].append({
                'timestamp': timestamp,
                'message': message,
                'type': log_type
            })

    def get_logs(self, user_id: int = None, limit: int = None) -> list:
        """
        Récupère les N derniers logs d'un utilisateur

        Args:
            user_id: ID de l'utilisateur (None = logs globaux avec user_id=0)
            limit: Nombre de logs à retourner (None = tous)

        Returns:
            Liste des logs
        """
        with self.lock:
            uid = user_id if user_id is not None else 0

            # Si l'utilisateur n'a pas de logs, retourner liste vide
            if uid not in self.logs:
                return []

            user_logs = list(self.logs[uid])

            if limit:
                return user_logs[-limit:]
            return user_logs

    def clear(self, user_id: int = None):
        """
        Vide le buffer de logs d'un utilisateur

        Args:
            user_id: ID de l'utilisateur (None = logs globaux avec user_id=0)
        """
        with self.lock:
            uid = user_id if user_id is not None else 0

            if uid in self.logs:
                self.logs[uid].clear()
                self.log('Console cleared', 'INFO', user_id=uid)


# Instance globale
_console_logger = ConsoleLogger()


def get_console_logger() -> ConsoleLogger:
    """Récupère l'instance globale du logger"""
    return _console_logger

"""
Scanner Data Manager
Tracks and stores all scanner activity for public/private display
"""

import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class ScannerDataManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = 'trading_bot.db'
            self.initialized = True
            self._init_database()

    def _init_database(self):
        """Initialize scanner_activity table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scanner_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_address TEXT NOT NULL,
                token_name TEXT,
                token_symbol TEXT,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ai_prediction TEXT,
                confidence REAL,
                is_gem INTEGER DEFAULT 0,
                was_bought INTEGER DEFAULT 0,
                buy_price REAL,
                current_price REAL,
                performance_percent REAL,
                status TEXT DEFAULT 'scanned',
                metadata TEXT
            )
        """)

        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scanner_scanned_at
            ON scanner_activity(scanned_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scanner_is_gem
            ON scanner_activity(is_gem, scanned_at DESC)
        """)

        conn.commit()
        conn.close()

    def log_token_scanned(self, token_data: dict, ai_prediction: dict):
        """Log a token that was scanned by the AI"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO scanner_activity
            (token_address, token_name, token_symbol, ai_prediction, confidence, is_gem, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            token_data.get('mint'),
            token_data.get('name'),
            token_data.get('symbol'),
            ai_prediction.get('action'),
            ai_prediction.get('confidence', 0),
            1 if ai_prediction.get('action') == 'BUY' else 0,
            json.dumps(token_data)
        ))

        conn.commit()
        conn.close()

    def log_token_bought(self, token_address: str, buy_price: float):
        """Update when a token is actually bought"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE scanner_activity
            SET was_bought = 1, buy_price = ?, status = 'bought'
            WHERE token_address = ?
        """, (buy_price, token_address))

        conn.commit()
        conn.close()

    def update_token_performance(self, token_address: str, current_price: float, status: str = 'holding'):
        """Update token performance (for tracking wins/losses)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get buy price
        cursor.execute("SELECT buy_price FROM scanner_activity WHERE token_address = ?", (token_address,))
        result = cursor.fetchone()

        if result and result[0]:
            buy_price = result[0]
            performance_percent = ((current_price - buy_price) / buy_price) * 100

            cursor.execute("""
                UPDATE scanner_activity
                SET current_price = ?, performance_percent = ?, status = ?
                WHERE token_address = ?
            """, (current_price, performance_percent, status, token_address))

            conn.commit()

        conn.close()

    def get_aggregated_stats(self) -> dict:
        """Get aggregated stats for public display"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total tokens scanned
        cursor.execute("SELECT COUNT(*) FROM scanner_activity")
        total_scanned = cursor.fetchone()[0]

        # Total GEMs identified
        cursor.execute("SELECT COUNT(*) FROM scanner_activity WHERE is_gem = 1")
        total_gems = cursor.fetchone()[0]

        # Total bought
        cursor.execute("SELECT COUNT(*) FROM scanner_activity WHERE was_bought = 1")
        total_bought = cursor.fetchone()[0]

        # Win rate (profitable trades)
        cursor.execute("""
            SELECT COUNT(*)
            FROM scanner_activity
            WHERE was_bought = 1 AND performance_percent > 0 AND status IN ('sold', 'closed')
        """)
        wins = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM scanner_activity
            WHERE was_bought = 1 AND status IN ('sold', 'closed')
        """)
        total_closed = cursor.fetchone()[0]

        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

        # Average performance
        cursor.execute("""
            SELECT AVG(performance_percent)
            FROM scanner_activity
            WHERE was_bought = 1 AND status IN ('sold', 'closed')
        """)
        avg_performance = cursor.fetchone()[0] or 0

        # Best performer
        cursor.execute("""
            SELECT token_symbol, performance_percent
            FROM scanner_activity
            WHERE was_bought = 1
            ORDER BY performance_percent DESC
            LIMIT 1
        """)
        best = cursor.fetchone()
        best_performer = {
            'symbol': best[0] if best else 'N/A',
            'performance': best[1] if best else 0
        }

        conn.close()

        return {
            'total_scanned': total_scanned,
            'total_gems_identified': total_gems,
            'total_bought': total_bought,
            'win_rate': round(win_rate, 1),
            'avg_performance': round(avg_performance, 1),
            'best_performer': best_performer
        }

    def get_recent_wins_delayed(self, delay_hours: int = 2, limit: int = 10) -> List[dict]:
        """Get recent wins with delay (for public display)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Calculate cutoff time (now - delay)
        cutoff_time = datetime.now() - timedelta(hours=delay_hours)

        cursor.execute("""
            SELECT
                token_symbol,
                token_name,
                scanned_at,
                buy_price,
                current_price,
                performance_percent,
                status
            FROM scanner_activity
            WHERE was_bought = 1
                AND performance_percent > 0
                AND scanned_at <= ?
            ORDER BY performance_percent DESC
            LIMIT ?
        """, (cutoff_time, limit))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_live_scanner_feed(self, limit: int = 50) -> List[dict]:
        """Get live scanner feed (for subscribers only)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                token_address,
                token_symbol,
                token_name,
                scanned_at,
                ai_prediction,
                confidence,
                is_gem,
                was_bought,
                status
            FROM scanner_activity
            ORDER BY scanned_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_live_gems(self, limit: int = 20) -> List[dict]:
        """Get live GEM detections (for subscribers only)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                token_address,
                token_symbol,
                token_name,
                scanned_at,
                confidence,
                was_bought,
                buy_price,
                current_price,
                performance_percent,
                status
            FROM scanner_activity
            WHERE is_gem = 1
            ORDER BY scanned_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

# Global instance
scanner_manager = ScannerDataManager()

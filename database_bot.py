"""
TRADING BOT DATABASE
Gestion de la base de données pour le système de bot de trading
Supporte SQLite (dev local) et PostgreSQL (production)
"""
import sqlite3
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
import os

# Charger les variables d'environnement depuis .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[WARNING] python-dotenv not installed. Install with: pip install python-dotenv")

# Clé de chiffrement pour les wallets (PERMANENTE depuis .env)
ENCRYPTION_KEY = os.environ.get('WALLET_ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    print("[WARNING] WALLET_ENCRYPTION_KEY not found - generating temporary key")
    ENCRYPTION_KEY = Fernet.generate_key()
else:
    # La clé depuis .env est en string, on doit l'encoder en bytes
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()

cipher_suite = Fernet(ENCRYPTION_KEY)

# Configuration base de données
DATABASE_URL = os.environ.get('DATABASE_URL')
DB_PATH = Path(__file__).parent / "trading_bot.db"

# Détecter si PostgreSQL ou SQLite
USE_POSTGRES = DATABASE_URL is not None and DATABASE_URL.startswith('postgres')

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("[DATABASE] Using PostgreSQL (production mode)")
else:
    print("[DATABASE] Using SQLite (local development mode)")


class BotDatabase:
    def __init__(self):
        self.conn = None
        self.use_postgres = USE_POSTGRES
        # Placeholder SQL selon la base de données
        self.ph = '%s' if USE_POSTGRES else '?'
        self.init_database()

    def get_connection(self):
        """Connexion à la base de données (SQLite ou PostgreSQL)"""
        if self.conn is None:
            if self.use_postgres:
                # PostgreSQL connection
                self.conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
                # Auto-commit mode OFF pour gérer les transactions manuellement
                self.conn.autocommit = False
            else:
                # SQLite connection
                self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
        return self.conn

    def safe_execute(self, cursor, query, params=None):
        """
        Exécute une requête SQL de manière sécurisée avec gestion automatique des erreurs
        et rollback en cas d'échec (important pour PostgreSQL)
        """
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return True
        except Exception as e:
            # Rollback automatique en cas d'erreur
            if self.conn:
                self.conn.rollback()
            print(f"[DATABASE ERROR] Query failed: {e}")
            raise

    def safe_commit(self):
        """Commit avec gestion d'erreur et rollback automatique"""
        try:
            if self.conn:
                self.conn.commit()
            return True
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            print(f"[DATABASE ERROR] Commit failed: {e}")
            raise

    def get_cursor(self):
        """
        Retourne un cursor avec wrapper automatique pour:
        - Convertir les placeholders PostgreSQL (%s) en SQLite (?) si nécessaire
        - Gérer automatiquement les rollback en cas d'erreur
        """
        conn = self.get_connection()
        cursor = conn.cursor()  # Utiliser conn.cursor() ici pour éviter la récursion

        original_execute = cursor.execute

        def execute_wrapper(query, params=None):
            try:
                # Si SQLite, convertir %s en ?
                if not self.use_postgres:
                    query = query.replace('%s', '?')

                return original_execute(query, params) if params else original_execute(query)
            except Exception as e:
                # Rollback automatique en cas d'erreur (SQLite et PostgreSQL)
                try:
                    conn.rollback()
                    print(f"[DATABASE] Auto-rollback after error: {str(e)[:100]}")
                except:
                    pass
                raise

        cursor.execute = execute_wrapper
        return cursor

    def init_database(self):
        """Initialise les tables de la base de données"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        # Adapter le type AUTO INCREMENT selon la BDD
        if self.use_postgres:
            id_type = "SERIAL PRIMARY KEY"
        else:
            id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"

        # Table Users
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                id {id_type},
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)

        # Table Wallets
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS wallets (
                id {id_type},
                user_id INTEGER NOT NULL,
                address TEXT UNIQUE NOT NULL,
                private_key_encrypted TEXT NOT NULL,
                balance_sol REAL DEFAULT 0.0,
                balance_usd REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Table Subscriptions (Boosts)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id {id_type},
                user_id INTEGER NOT NULL,
                boost_level TEXT DEFAULT 'BASIC',
                price_paid REAL DEFAULT 0.0,
                starts_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                payment_tx TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Table Bot Status
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS bot_status (
                id {id_type},
                user_id INTEGER NOT NULL,
                is_running BOOLEAN DEFAULT FALSE,
                strategy TEXT DEFAULT 'AI_PREDICTIONS',
                risk_level TEXT DEFAULT 'MEDIUM',
                take_profit REAL DEFAULT 2.0,
                stop_loss REAL DEFAULT 0.5,
                max_position_size REAL DEFAULT 0.1,
                tp_strategy TEXT DEFAULT 'SIMPLE_MULTIPLIER',
                tp_config TEXT,
                started_at TIMESTAMP,
                stopped_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Table Trades History
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS trades (
                id {id_type},
                user_id INTEGER NOT NULL,
                token_address TEXT NOT NULL,
                token_name TEXT,
                trade_type TEXT NOT NULL,
                amount_sol REAL NOT NULL,
                price_usd REAL,
                tokens_bought REAL,
                profit_loss REAL DEFAULT 0.0,
                profit_loss_percentage REAL DEFAULT 0.0,
                prediction_category TEXT,
                prediction_confidence REAL,
                status TEXT DEFAULT 'PENDING',
                tx_signature TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Table Bot Stats
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS bot_stats (
                id {id_type},
                user_id INTEGER NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                total_profit_usd REAL DEFAULT 0.0,
                win_rate REAL DEFAULT 0.0,
                best_trade_profit REAL DEFAULT 0.0,
                worst_trade_loss REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Table Payments (pour tracker les paiements d'abonnement)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS payments (
                id {id_type},
                user_id INTEGER NOT NULL,
                boost_level TEXT NOT NULL,
                amount_sol REAL NOT NULL,
                payment_address TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                tx_signature TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Table Simulation Sessions (Mode simulation 2h)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS simulation_sessions (
                id {id_type},
                user_id INTEGER NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                duration_minutes INTEGER DEFAULT 120,
                virtual_balance_sol REAL DEFAULT 10.0,
                final_balance_sol REAL DEFAULT 10.0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                is_expired BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Table Open Positions (pour persister les positions actives)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS open_positions (
                id {id_type},
                user_id INTEGER NOT NULL,
                token_address TEXT NOT NULL,
                token_name TEXT NOT NULL,
                entry_mc REAL NOT NULL,
                entry_time TIMESTAMP NOT NULL,
                amount_sol REAL NOT NULL,
                tokens REAL NOT NULL,
                simulation_session_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (simulation_session_id) REFERENCES simulation_sessions(id)
            )
        """)

        conn.commit()
        print("[OK] Base de données initialisée!")

    # ====== USER MANAGEMENT ======

    def create_user(self, email, password):
        """Crée un nouvel utilisateur"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor()

            # Hash du password
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            if USE_POSTGRES:
                cursor.execute("""
                    INSERT INTO users (email, password_hash)
                    VALUES (%s, %s)
                    RETURNING id
                """, (email, password_hash))
                user_id = cursor.fetchone()['id']
            else:
                cursor.execute("""
                    INSERT INTO users (email, password_hash)
                    VALUES (%s, %s)
                """, (email, password_hash))
                user_id = cursor.lastrowid

            conn.commit()

            # Initialiser les stats du bot
            self._init_bot_stats(user_id)

            return user_id
        except (sqlite3.IntegrityError, Exception) as e:
            # Rollback en cas d'erreur (important pour PostgreSQL)
            conn.rollback()
            # Si c'est une erreur d'unicité (email déjà existant), retourner None
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                return None
            # Sinon, relancer l'exception
            raise

    def authenticate_user(self, email, password):
        """Authentifie un utilisateur"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        cursor.execute("""
            SELECT id, email, created_at
            FROM users
            WHERE email = %s AND password_hash = %s AND is_active = TRUE
        """, (email, password_hash))

        user = cursor.fetchone()

        if user:
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (user['id'],))
            conn.commit()

            return dict(user)
        return None

    def get_user(self, user_id):
        """Récupère les infos d'un utilisateur"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            SELECT id, email, created_at, last_login
            FROM users
            WHERE id = %s
        """, (user_id,))

        user = cursor.fetchone()
        return dict(user) if user else None

    # ====== WALLET MANAGEMENT ======

    def create_wallet(self, user_id, address, private_key):
        """Crée un wallet pour un utilisateur"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor()

            # Chiffrer la clé privée
            encrypted_key = cipher_suite.encrypt(private_key.encode()).decode()

            if USE_POSTGRES:
                cursor.execute("""
                    INSERT INTO wallets (user_id, address, private_key_encrypted)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (user_id, address, encrypted_key))
                wallet_id = cursor.fetchone()['id']
            else:
                cursor.execute("""
                    INSERT INTO wallets (user_id, address, private_key_encrypted)
                    VALUES (%s, %s, %s)
                """, (user_id, address, encrypted_key))
                wallet_id = cursor.lastrowid

            conn.commit()

            return wallet_id
        except Exception as e:
            print(f"[ERROR] Création wallet: {e}")
            return None

    def get_wallet(self, user_id):
        """Récupère le wallet d'un utilisateur"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            SELECT id, address, balance_sol, balance_usd, created_at, last_updated
            FROM wallets
            WHERE user_id = %s
        """, (user_id,))

        wallet = cursor.fetchone()
        return dict(wallet) if wallet else None

    def get_wallet_private_key(self, user_id):
        """Récupère la clé privée déchiffrée (USE WITH CAUTION)"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            SELECT private_key_encrypted
            FROM wallets
            WHERE user_id = %s
        """, (user_id,))

        result = cursor.fetchone()
        if result:
            encrypted_key = result['private_key_encrypted']
            return cipher_suite.decrypt(encrypted_key.encode()).decode()
        return None

    def update_wallet_balance(self, user_id, balance_sol, balance_usd):
        """Met à jour le solde du wallet"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            UPDATE wallets
            SET balance_sol = %s, balance_usd = %s, last_updated = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (balance_sol, balance_usd, user_id))

        conn.commit()

    def update_wallet(self, user_id, new_address, new_private_key):
        """
        Met à jour le wallet de l'utilisateur (génère nouveau wallet si perdu)
        ATTENTION: Remplace complètement l'ancien wallet!
        """
        conn = self.get_connection()
        cursor = self.get_cursor()

        # Chiffrer la nouvelle clé privée
        encrypted_key = cipher_suite.encrypt(new_private_key.encode()).decode()

        try:
            cursor.execute("""
                UPDATE wallets
                SET address = %s,
                    private_key_encrypted = %s,
                    balance_sol = 0.0,
                    balance_usd = 0.0,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (new_address, encrypted_key, user_id))

            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] Failed to update wallet: {e}")
            conn.rollback()
            return False

    # ====== SUBSCRIPTION MANAGEMENT ======

    def create_subscription(self, user_id, boost_level, price_paid, duration_days=30, payment_tx=None):
        """Crée une nouvelle subscription"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        expires_at = datetime.now() + timedelta(days=duration_days)

        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO subscriptions (user_id, boost_level, price_paid, expires_at, payment_tx)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, boost_level, price_paid, expires_at, payment_tx))
            sub_id = cursor.fetchone()['id']
        else:
            cursor.execute("""
                INSERT INTO subscriptions (user_id, boost_level, price_paid, expires_at, payment_tx)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, boost_level, price_paid, expires_at, payment_tx))
            sub_id = cursor.lastrowid

        conn.commit()
        return sub_id

    def get_active_subscription(self, user_id):
        """Récupère la subscription active d'un utilisateur"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            SELECT * FROM subscriptions
            WHERE user_id = %s AND is_active = TRUE AND expires_at > CURRENT_TIMESTAMP
            ORDER BY expires_at DESC
            LIMIT 1
        """, (user_id,))

        sub = cursor.fetchone()
        return dict(sub) if sub else None

    # ====== BOT STATUS ======

    def get_bot_status(self, user_id):
        """Récupère le statut du bot"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            SELECT * FROM bot_status WHERE user_id = %s
        """, (user_id,))

        status = cursor.fetchone()
        if status:
            return dict(status)
        else:
            # Créer un statut par défaut
            cursor.execute("""
                INSERT INTO bot_status (user_id) VALUES (%s)
            """, (user_id,))
            conn.commit()
            return self.get_bot_status(user_id)

    def start_bot(self, user_id, strategy='AI_PREDICTIONS', risk_level='MEDIUM'):
        """Démarre le bot"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            UPDATE bot_status
            SET is_running = TRUE, strategy = %s, risk_level = %s, started_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (strategy, risk_level, user_id))

        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO bot_status (user_id, is_running, strategy, risk_level, started_at)
                VALUES (%s, TRUE, %s, %s, CURRENT_TIMESTAMP)
            """, (user_id, strategy, risk_level))

        conn.commit()

    def stop_bot(self, user_id):
        """Arrête le bot"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            UPDATE bot_status
            SET is_running = FALSE, stopped_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (user_id,))

        conn.commit()

    # ====== TRADES ======

    def create_trade(self, user_id, token_address, trade_type, amount_sol, **kwargs):
        """Enregistre un nouveau trade"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO trades
                (user_id, token_address, token_name, trade_type, amount_sol,
                 price_usd, tokens_bought, prediction_category, prediction_confidence, tx_signature, status, profit_loss, profit_loss_percentage)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                token_address,
                kwargs.get('token_name'),
                trade_type,
                amount_sol,
                kwargs.get('price_usd'),
                kwargs.get('tokens_bought'),
                kwargs.get('prediction_category'),
                kwargs.get('prediction_confidence'),
                kwargs.get('tx_signature'),
                kwargs.get('status', 'PENDING'),
                kwargs.get('profit_loss', 0.0),
                kwargs.get('profit_loss_percentage', 0.0)
            ))
            trade_id = cursor.fetchone()['id']
        else:
            cursor.execute("""
                INSERT INTO trades
                (user_id, token_address, token_name, trade_type, amount_sol,
                 price_usd, tokens_bought, prediction_category, prediction_confidence, tx_signature, status, profit_loss, profit_loss_percentage)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                token_address,
                kwargs.get('token_name'),
                trade_type,
                amount_sol,
                kwargs.get('price_usd'),
                kwargs.get('tokens_bought'),
                kwargs.get('prediction_category'),
                kwargs.get('prediction_confidence'),
                kwargs.get('tx_signature'),
                kwargs.get('status', 'PENDING'),
                kwargs.get('profit_loss', 0.0),
                kwargs.get('profit_loss_percentage', 0.0)
            ))
            trade_id = cursor.lastrowid

        conn.commit()
        return trade_id

    def get_user_trades(self, user_id, limit=50):
        """Récupère l'historique des trades"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            SELECT * FROM trades
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, limit))

        trades = cursor.fetchall()
        return [dict(trade) for trade in trades]

    # ====== STATS ======

    def _init_bot_stats(self, user_id):
        """Initialise les stats pour un utilisateur"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            INSERT INTO bot_stats (user_id) VALUES (%s)
        """, (user_id,))

        conn.commit()

    def get_bot_stats(self, user_id):
        """Récupère les statistiques du bot"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            SELECT * FROM bot_stats WHERE user_id = %s
        """, (user_id,))

        stats = cursor.fetchone()
        return dict(stats) if stats else None

    def update_bot_stats(self, user_id):
        """Recalcule les stats basées sur les trades"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        # Calculer les stats depuis les trades
        cursor.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(profit_loss) as total_profit,
                MAX(profit_loss) as best_trade,
                MIN(profit_loss) as worst_trade
            FROM trades
            WHERE user_id = %s AND status = 'EXECUTED'
        """, (user_id,))

        result = cursor.fetchone()

        if result and result['total_trades'] > 0:
            win_rate = (result['winning_trades'] / result['total_trades']) * 100
        else:
            win_rate = 0.0

        # Update bot_stats
        cursor.execute("""
            UPDATE bot_stats
            SET
                total_trades = %s,
                winning_trades = %s,
                losing_trades = %s,
                total_profit_usd = %s,
                win_rate = %s,
                best_trade_profit = %s,
                worst_trade_loss = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (
            result['total_trades'] or 0,
            result['winning_trades'] or 0,
            result['losing_trades'] or 0,
            result['total_profit'] or 0.0,
            win_rate,
            result['best_trade'] or 0.0,
            result['worst_trade'] or 0.0,
            user_id
        ))

        conn.commit()

    # ====== PAYMENT METHODS ======

    def create_payment_request(self, user_id, boost_level, amount_sol, payment_address, expires_at):
        """Crée une demande de paiement"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO payments (user_id, boost_level, amount_sol, payment_address, status, expires_at)
                VALUES (%s, %s, %s, %s, 'PENDING', %s)
                RETURNING id
            """, (user_id, boost_level, amount_sol, payment_address, expires_at))
            payment_id = cursor.fetchone()['id']
        else:
            cursor.execute("""
                INSERT INTO payments (user_id, boost_level, amount_sol, payment_address, status, expires_at)
                VALUES (%s, %s, %s, %s, 'PENDING', %s)
            """, (user_id, boost_level, amount_sol, payment_address, expires_at))
            payment_id = cursor.lastrowid

        conn.commit()

        return payment_id

    def get_pending_payment(self, payment_id):
        """Récupère un paiement en attente"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            SELECT id, user_id, boost_level, amount_sol, payment_address, status,
                   created_at, expires_at, tx_signature
            FROM payments
            WHERE id = %s AND status = 'PENDING'
        """, (payment_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'id': row['id'],
            'user_id': row['user_id'],
            'boost_level': row['boost_level'],
            'amount_sol': row['amount_sol'],
            'payment_address': row['payment_address'],
            'status': row['status'],
            'created_at': row['created_at'],
            'expires_at': row['expires_at'],
            'tx_signature': row['tx_signature']
        }

    def verify_payment(self, payment_id, tx_signature):
        """Marque un paiement comme vérifié et active l'abonnement"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        # Récupérer les infos du paiement
        payment = self.get_pending_payment(payment_id)
        if not payment:
            return False

        # Mettre à jour le paiement
        cursor.execute("""
            UPDATE payments
            SET status = 'VERIFIED', tx_signature = %s, verified_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (tx_signature, payment_id))

        # Activer l'abonnement
        self.create_subscription(
            payment['user_id'],
            payment['boost_level'],
            payment['amount_sol'],
            duration_days=30,
            payment_tx=tx_signature
        )

        conn.commit()
        return True

    def expire_payment(self, payment_id):
        """Marque un paiement comme expiré"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            UPDATE payments
            SET status = 'EXPIRED'
            WHERE id = %s AND status = 'PENDING'
        """, (payment_id,))

        conn.commit()

    def get_user_payments(self, user_id, limit=20):
        """Récupère l'historique des paiements d'un utilisateur"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            SELECT id, boost_level, amount_sol, status, created_at, verified_at, tx_signature
            FROM payments
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, limit))

        payments = []
        for row in cursor.fetchall():
            payments.append({
                'id': row['id'],
                'boost_level': row['boost_level'],
                'amount_sol': row['amount_sol'],
                'status': row['status'],
                'created_at': row['created_at'],
                'verified_at': row['verified_at'],
                'tx_signature': row['tx_signature']
            })

        return payments

    # ====== SIMULATION MODE ======

    def start_simulation(self, user_id):
        """Démarre une session de simulation pour un utilisateur"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor()

            # Vérifier si l'utilisateur a déjà fait une simulation
            cursor.execute("""
                SELECT id, is_expired FROM simulation_sessions
                WHERE user_id = %s
                ORDER BY start_time DESC
                LIMIT 1
            """, (user_id,))

            existing = cursor.fetchone()
            if existing and not existing[1]:  # Si une simulation existe et n'est pas expirée
                return None  # Déjà une simulation en cours ou terminée

            # Créer une nouvelle session de simulation
            end_time = datetime.now() + timedelta(hours=2)

            if USE_POSTGRES:
                cursor.execute("""
                    INSERT INTO simulation_sessions
                    (user_id, end_time, duration_minutes, virtual_balance_sol, final_balance_sol, is_active)
                    VALUES (%s, %s, 120, 10.0, 10.0, TRUE)
                    RETURNING id
                """, (user_id, end_time))
                session_id = cursor.fetchone()['id']
            else:
                cursor.execute("""
                    INSERT INTO simulation_sessions
                    (user_id, end_time, duration_minutes, virtual_balance_sol, final_balance_sol, is_active)
                    VALUES (%s, %s, 120, 10.0, 10.0, 1)
                """, (user_id, end_time))
                session_id = cursor.lastrowid

            conn.commit()

            return session_id
        except Exception as e:
            print(f"[ERROR] Erreur start_simulation: {e}")
            return None

    def get_simulation_session(self, user_id):
        """Récupère la session de simulation active d'un utilisateur"""
        conn = self.get_connection()
        cursor = self.get_cursor()

        cursor.execute("""
            SELECT id, start_time, end_time, virtual_balance_sol, final_balance_sol,
                   total_trades, winning_trades, is_active, is_expired
            FROM simulation_sessions
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY start_time DESC
            LIMIT 1
        """, (user_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'id': row['id'],
            'start_time': row['start_time'],
            'end_time': row['end_time'],
            'virtual_balance': row['virtual_balance_sol'],
            'final_balance': row['final_balance_sol'],
            'total_trades': row['total_trades'],
            'winning_trades': row['winning_trades'],
            'is_active': row['is_active'],
            'is_expired': row['is_expired']
        }

    def update_simulation_balance(self, session_id, new_balance):
        """Met à jour le solde virtuel de la simulation"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor()

            cursor.execute("""
                UPDATE simulation_sessions
                SET final_balance_sol = %s
                WHERE id = %s
            """, (new_balance, session_id))

            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] Erreur update_simulation_balance: {e}")
            return False

    def increment_simulation_trades(self, session_id, is_win=False):
        """Incrémente le compteur de trades simulés"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor()

            if is_win:
                cursor.execute("""
                    UPDATE simulation_sessions
                    SET total_trades = total_trades + 1,
                        winning_trades = winning_trades + 1
                    WHERE id = %s
                """, (session_id,))
            else:
                cursor.execute("""
                    UPDATE simulation_sessions
                    SET total_trades = total_trades + 1
                    WHERE id = %s
                """, (session_id,))

            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] Erreur increment_simulation_trades: {e}")
            return False

    def end_simulation(self, session_id):
        """Termine une session de simulation"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor()

            cursor.execute("""
                UPDATE simulation_sessions
                SET is_active = FALSE, is_expired = TRUE
                WHERE id = %s
            """, (session_id,))

            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] Erreur end_simulation: {e}")
            return False

    # ====== OPEN POSITIONS MANAGEMENT ======

    def create_open_position(self, user_id, token_address, token_name, entry_mc, entry_time, amount_sol, tokens, simulation_session_id=None):
        """Crée une position ouverte en BDD"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor()

            if USE_POSTGRES:
                cursor.execute("""
                    INSERT INTO open_positions (user_id, token_address, token_name, entry_mc, entry_time, amount_sol, tokens, simulation_session_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, token_address, token_name, entry_mc, entry_time, amount_sol, tokens, simulation_session_id))
                position_id = cursor.fetchone()['id']
            else:
                cursor.execute("""
                    INSERT INTO open_positions (user_id, token_address, token_name, entry_mc, entry_time, amount_sol, tokens, simulation_session_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, token_address, token_name, entry_mc, entry_time, amount_sol, tokens, simulation_session_id))
                position_id = cursor.lastrowid

            conn.commit()
            return position_id
        except Exception as e:
            print(f"[ERROR] Erreur create_open_position: {e}")
            return None

    def get_open_positions(self, user_id):
        """Récupère toutes les positions ouvertes d'un utilisateur"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor()

            cursor.execute("""
                SELECT * FROM open_positions
                WHERE user_id = %s
            """, (user_id,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[ERROR] Erreur get_open_positions: {e}")
            return []

    def delete_open_position(self, user_id, token_address):
        """Supprime une position ouverte (quand elle est fermée)"""
        try:
            conn = self.get_connection()
            cursor = self.get_cursor()

            cursor.execute("""
                DELETE FROM open_positions
                WHERE user_id = %s AND token_address = %s
            """, (user_id, token_address))

            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] Erreur delete_open_position: {e}")
            return False

    def close(self):
        """Ferme la connexion"""
        if self.conn:
            self.conn.close()
            self.conn = None


# Instance globale
db = BotDatabase()


if __name__ == "__main__":
    print("Initialisation de la base de données...")
    db = BotDatabase()
    print("Base de données prête!")

"""
DEMO DATA GENERATOR
Génère des données fictives pour le mode démo (RUNNERS uniquement)
"""
import random
import time
from datetime import datetime
import secrets

class DemoDataGenerator:
    """Générateur de données pour le mode démonstration"""

    # Liste de noms de tokens sympas pour la démo
    TOKEN_NAMES = [
        "MoonShot", "DiamondHands", "RocketFuel", "GemHunter",
        "PumpMaster", "LamboToken", "ToTheMoon", "GigaChad",
        "ApeStonk", "DegenKing", "MegaPump", "SafeMoon2",
        "ElonDoge", "ShibaKiller", "PepeGold", "WojakWin"
    ]

    def __init__(self):
        self.active_positions = []
        self.completed_trades = []
        self.total_profit_sol = 0.0
        self.virtual_balance = 10.0

    def generate_token_address(self):
        """Génère une fausse adresse de token Solana"""
        return secrets.token_urlsafe(32)[:44]

    def generate_runner_token(self):
        """Génère un token RUNNER avec bon potentiel"""
        token_name = random.choice(self.TOKEN_NAMES)
        token_address = self.generate_token_address()

        # Market cap initial entre 5k et 30k (avant migration à 53k)
        entry_mc = random.randint(5000, 30000)

        # Target MC entre 80k et 500k (tous sont des runners!)
        target_mc = random.randint(80000, 500000)

        # Runner probability élevée (70-95%)
        runner_prob = random.randint(70, 95)

        # Multiplier cible
        target_multiplier = round(target_mc / entry_mc, 2)

        return {
            'token_address': token_address,
            'token_name': token_name,
            'symbol': token_name.upper()[:4],
            'entry_mc': entry_mc,
            'current_mc': entry_mc,
            'target_mc': target_mc,
            'target_multiplier': target_multiplier,
            'runner_probability': runner_prob,
            'prediction': 'GEM',
            'signal': 'BUY',
            'amount_sol': round(random.uniform(0.5, 2.0), 2),
            'entry_time': datetime.now().isoformat(),
            'migration_reached': False,
            'highest_mc': entry_mc
        }

    def simulate_price_movement(self, token):
        """Simule le mouvement de prix d'un token (TOUJOURS À LA HAUSSE pour démo!)"""
        # Augmentation progressive vers le target
        current_mc = token['current_mc']
        target_mc = token['target_mc']

        # Augmenter de 5% à 20% à chaque tick
        increase_percent = random.uniform(0.05, 0.20)
        new_mc = current_mc * (1 + increase_percent)

        # Ne pas dépasser le target
        if new_mc > target_mc:
            new_mc = target_mc

        # Mettre à jour
        token['current_mc'] = round(new_mc, 2)

        # Vérifier si migration atteinte (53k)
        if new_mc >= 53000 and not token['migration_reached']:
            token['migration_reached'] = True

        # Mettre à jour le plus haut
        if new_mc > token['highest_mc']:
            token['highest_mc'] = new_mc

        # Calculer le profit actuel
        profit_ratio = new_mc / token['entry_mc']
        token['profit_percent'] = round((profit_ratio - 1) * 100, 2)
        token['profit_multiplier'] = round(profit_ratio, 2)

        return token

    def should_sell(self, token):
        """Décide si on doit vendre le token"""
        current_mc = token['current_mc']
        target_mc = token['target_mc']

        # Vendre si :
        # 1. On a atteint 95% du target
        # 2. Ou on a au moins 2x et 30% de chance aléatoire

        if current_mc >= target_mc * 0.95:
            return True

        if token['profit_multiplier'] >= 2.0 and random.random() < 0.3:
            return True

        return False

    def execute_sell(self, token):
        """Simule la vente d'un token"""
        # Calculer le profit
        entry_value = token['amount_sol']
        exit_value = entry_value * token['profit_multiplier']
        profit_sol = exit_value - entry_value

        # Mettre à jour le solde virtuel
        self.virtual_balance += profit_sol
        self.total_profit_sol += profit_sol

        # Créer le trade complété
        trade = {
            'token_name': token['token_name'],
            'token_address': token['token_address'],
            'entry_mc': token['entry_mc'],
            'exit_mc': token['current_mc'],
            'profit_multiplier': token['profit_multiplier'],
            'profit_percent': token['profit_percent'],
            'profit_sol': round(profit_sol, 4),
            'amount_sol': token['amount_sol'],
            'entry_time': token['entry_time'],
            'exit_time': datetime.now().isoformat(),
            'migration_reached': token['migration_reached']
        }

        self.completed_trades.append(trade)

        return trade

    def generate_log(self, log_type, data):
        """Génère un log formaté pour la console"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        logs = {
            'NEW_TOKEN': f"[{timestamp}] 🔍 NEW TOKEN DETECTED | {data['token_name']} | MC: ${data['entry_mc']:,}",

            'AI_ANALYSIS': f"[{timestamp}] 🤖 AI PREDICTION | {data['token_name']} | {data['prediction']} ({data['runner_probability']}%) | Target: ${data['target_mc']:,} ({data['target_multiplier']}x)",

            'BUY_SIGNAL': f"[{timestamp}] 🟢 BUY SIGNAL | {data['token_name']} | Amount: {data['amount_sol']} SOL | Entry MC: ${data['entry_mc']:,}",

            'PRICE_UPDATE': f"[{timestamp}] 📈 PRICE UPDATE | {data['token_name']} | MC: ${data['current_mc']:,} | Profit: +{data['profit_percent']}% ({data['profit_multiplier']}x)",

            'MIGRATION': f"[{timestamp}] 🚀 MIGRATION REACHED | {data['token_name']} | MC: ${data['current_mc']:,} | Listing on Raydium!",

            'SELL_EXECUTED': f"[{timestamp}] 💰 SELL EXECUTED | {data['token_name']} | Exit MC: ${data['exit_mc']:,} | Profit: +{data['profit_sol']:.4f} SOL (+{data['profit_percent']}%)",

            'STATS_UPDATE': f"[{timestamp}] 📊 STATS | Balance: {data['balance']:.2f} SOL | Total Profit: +{data['total_profit']:.4f} SOL | Win Rate: {data['win_rate']}%"
        }

        return {
            'timestamp': timestamp,
            'type': log_type,
            'message': logs.get(log_type, ''),
            'data': data
        }

    def get_current_stats(self):
        """Retourne les stats actuelles"""
        total_trades = len(self.completed_trades)
        winning_trades = len([t for t in self.completed_trades if t['profit_sol'] > 0])
        win_rate = round((winning_trades / total_trades * 100) if total_trades > 0 else 100, 1)

        return {
            'balance': round(self.virtual_balance, 2),
            'total_profit': round(self.total_profit_sol, 4),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'active_positions': len(self.active_positions),
            'completed_trades': self.completed_trades[-10:]  # 10 derniers trades
        }


# Instance globale pour la démo
demo_generator = DemoDataGenerator()

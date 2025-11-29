"""
VISION AI BOT - DEMO TERMINAL
Script de démonstration standalone pour vidéo
Affiche la simulation du bot en temps réel dans le terminal
"""
import time
import random
from datetime import datetime
from demo_data_generator import DemoDataGenerator
import os
import sys

# Codes couleur ANSI pour Windows/Linux
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # Couleurs de base
    BLACK = '\033[30m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    # Couleurs custom
    ORANGE = '\033[38;5;208m'
    PURPLE = '\033[38;5;141m'
    PINK = '\033[38;5;213m'

def clear_screen():
    """Efface l'écran"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Affiche l'en-tête du bot"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'VISION AI TRADING BOT - LIVE DEMO':^80}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}\n")

def print_stats(generator):
    """Affiche les statistiques en temps réel"""
    stats = generator.get_current_stats()

    print(f"\n{Colors.YELLOW}{Colors.BOLD}{'─'*80}{Colors.RESET}")
    print(f"{Colors.YELLOW}{Colors.BOLD}STATS:{Colors.RESET} ", end="")
    print(f"Balance: {Colors.GREEN}{Colors.BOLD}{stats['balance']:.2f} SOL{Colors.RESET} | ", end="")
    print(f"Profit: {Colors.GREEN}{Colors.BOLD}+{stats['total_profit']:.4f} SOL{Colors.RESET} | ", end="")
    print(f"Trades: {Colors.WHITE}{Colors.BOLD}{stats['total_trades']}{Colors.RESET} | ", end="")
    print(f"Win Rate: {Colors.GREEN}{Colors.BOLD}{stats['win_rate']}%{Colors.RESET} | ", end="")
    print(f"Positions: {Colors.ORANGE}{Colors.BOLD}{stats['active_positions']}{Colors.RESET}")
    print(f"{Colors.YELLOW}{Colors.BOLD}{'─'*80}{Colors.RESET}\n")

def print_log(log_type, message):
    """Affiche un log avec la couleur appropriée"""
    timestamp = datetime.now().strftime("%H:%M:%S")

    colors = {
        'NEW_TOKEN': Colors.CYAN,
        'AI_ANALYSIS': Colors.PURPLE,
        'BUY_SIGNAL': Colors.GREEN,
        'PRICE_UPDATE': Colors.ORANGE,
        'MIGRATION': Colors.YELLOW,
        'SELL_EXECUTED': Colors.GREEN + Colors.BOLD,
        'STATS_UPDATE': Colors.CYAN
    }

    icons = {
        'NEW_TOKEN': '🔍',
        'AI_ANALYSIS': '🤖',
        'BUY_SIGNAL': '🟢',
        'PRICE_UPDATE': '📈',
        'MIGRATION': '🚀',
        'SELL_EXECUTED': '💰',
        'STATS_UPDATE': '📊'
    }

    color = colors.get(log_type, Colors.WHITE)
    icon = icons.get(log_type, '•')

    print(f"{Colors.BOLD}[{timestamp}]{Colors.RESET} {color}{icon} {message}{Colors.RESET}")

def run_demo(duration_minutes=5, speed_multiplier=1.0):
    """
    Lance la démo

    Args:
        duration_minutes: Durée de la démo en minutes (par défaut 5 min)
        speed_multiplier: Multiplicateur de vitesse (1.0 = normal, 2.0 = 2x plus rapide)
    """
    clear_screen()
    print_header()

    print(f"{Colors.MAGENTA}{Colors.BOLD}🎬 DEMO MODE STARTED{Colors.RESET}")
    print(f"{Colors.WHITE}Duration: {duration_minutes} minutes | Speed: {speed_multiplier}x{Colors.RESET}")
    print(f"{Colors.WHITE}Only trading RUNNER tokens (high profit potential){Colors.RESET}\n")

    generator = DemoDataGenerator()
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)

    last_stats_update = time.time()

    try:
        while time.time() < end_time:
            # Vérifier si on peut acheter un nouveau token
            if len(generator.active_positions) < 3:
                # 40% de chance de générer un nouveau token
                if random.random() < 0.4:
                    token = generator.generate_runner_token()
                    generator.active_positions.append(token)

                    # Logs d'achat
                    print_log('NEW_TOKEN', f"NEW TOKEN DETECTED | {token['token_name']} | MC: ${token['entry_mc']:,}")
                    time.sleep(0.3 / speed_multiplier)

                    print_log('AI_ANALYSIS', f"AI PREDICTION | {token['token_name']} | {token['prediction']} ({token['runner_probability']}%) | Target: ${token['target_mc']:,} ({token['target_multiplier']}x)")
                    time.sleep(0.3 / speed_multiplier)

                    print_log('BUY_SIGNAL', f"BUY SIGNAL | {token['token_name']} | Amount: {token['amount_sol']} SOL | Entry MC: ${token['entry_mc']:,}")
                    time.sleep(0.5 / speed_multiplier)

            # Mettre à jour les prix des positions actives
            positions_to_remove = []

            for i, token in enumerate(generator.active_positions):
                # Simuler le mouvement de prix
                generator.simulate_price_movement(token)

                # Log de mise à jour de prix (30% de chance)
                if random.random() < 0.3:
                    print_log('PRICE_UPDATE', f"PRICE UPDATE | {token['token_name']} | MC: ${token['current_mc']:,} | Profit: +{token['profit_percent']:.1f}% ({token['profit_multiplier']:.2f}x)")

                # Log de migration si atteinte
                if token['migration_reached'] and token.get('migration_logged') is None:
                    print_log('MIGRATION', f"MIGRATION REACHED | {token['token_name']} | MC: ${token['current_mc']:,} | Listing on Raydium!")
                    token['migration_logged'] = True
                    time.sleep(0.3 / speed_multiplier)

                # Vérifier si on doit vendre
                if generator.should_sell(token):
                    trade = generator.execute_sell(token)
                    print_log('SELL_EXECUTED', f"SELL EXECUTED | {trade['token_name']} | Exit MC: ${trade['exit_mc']:,} | Profit: +{trade['profit_sol']:.4f} SOL (+{trade['profit_percent']:.1f}%)")

                    positions_to_remove.append(i)
                    time.sleep(0.5 / speed_multiplier)

            # Supprimer les positions vendues
            for i in reversed(positions_to_remove):
                generator.active_positions.pop(i)

            # Afficher les stats toutes les 10 secondes
            if time.time() - last_stats_update > (10 / speed_multiplier):
                print_stats(generator)
                last_stats_update = time.time()

            # Pause entre les ticks (2-4 secondes selon speed_multiplier)
            time.sleep(random.uniform(2, 4) / speed_multiplier)

        # Afficher les stats finales
        print(f"\n{Colors.MAGENTA}{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}🎬 DEMO COMPLETED{Colors.RESET}\n")
        print_stats(generator)

        stats = generator.get_current_stats()
        print(f"{Colors.GREEN}{Colors.BOLD}FINAL RESULTS:{Colors.RESET}")
        print(f"  💰 Starting Balance: 10.00 SOL")
        print(f"  💵 Final Balance: {Colors.GREEN}{Colors.BOLD}{stats['balance']:.2f} SOL{Colors.RESET}")
        print(f"  📈 Total Profit: {Colors.GREEN}{Colors.BOLD}+{stats['total_profit']:.4f} SOL (+{(stats['total_profit']/10*100):.1f}%){Colors.RESET}")
        print(f"  🏆 Win Rate: {Colors.GREEN}{Colors.BOLD}{stats['win_rate']}%{Colors.RESET}")
        print(f"  📊 Total Trades: {stats['total_trades']}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}{'='*80}{Colors.RESET}\n")

        # Afficher les derniers trades
        if stats['completed_trades']:
            print(f"{Colors.CYAN}{Colors.BOLD}LAST TRADES:{Colors.RESET}")
            for trade in stats['completed_trades'][-5:]:
                profit_color = Colors.GREEN if trade['profit_sol'] > 0 else Colors.RED
                print(f"  • {trade['token_name']}: {profit_color}+{trade['profit_sol']:.4f} SOL (+{trade['profit_percent']:.1f}%){Colors.RESET}")
            print()

    except KeyboardInterrupt:
        print(f"\n\n{Colors.RED}{Colors.BOLD}⚠️  DEMO STOPPED BY USER{Colors.RESET}\n")
        print_stats(generator)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='VISION AI BOT - Terminal Demo')
    parser.add_argument('--duration', type=int, default=5, help='Duration in minutes (default: 5)')
    parser.add_argument('--speed', type=float, default=1.5, help='Speed multiplier (default: 1.5)')
    parser.add_argument('--mode', type=str, choices=['quick', 'standard', 'long'], default='standard',
                        help='Preset mode: quick (2min, 2x), standard (5min, 1.5x), long (10min, 1x)')

    args = parser.parse_args()

    # Appliquer le preset si spécifié
    if args.mode == 'quick':
        duration = 2
        speed = 2.0
    elif args.mode == 'standard':
        duration = 5
        speed = 1.5
    elif args.mode == 'long':
        duration = 10
        speed = 1.0
    else:
        duration = args.duration
        speed = args.speed

    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("=" * 72)
    print("          VISION AI BOT - TERMINAL DEMO                            ")
    print("                                                                    ")
    print("  This demo simulates the bot trading RUNNER tokens automatically  ")
    print("  Perfect for recording demonstration videos!                      ")
    print("=" * 72)
    print(f"{Colors.RESET}\n")

    print(f"{Colors.YELLOW}Configuration:{Colors.RESET}")
    print(f"  Duration: {duration} minutes")
    print(f"  Speed: {speed}x")
    print(f"  Mode: {args.mode}\n")

    print(f"{Colors.GREEN}Starting demo in 3 seconds... (Press Ctrl+C to stop){Colors.RESET}")
    time.sleep(3)

    run_demo(duration_minutes=duration, speed_multiplier=speed)

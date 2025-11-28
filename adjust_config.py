"""
ADJUST CONFIG - Ajuste manuellement la configuration du bot
"""
from adaptive_config import adaptive_config
from learning_engine import learning_engine
import sys

def main():
    print('='*80)
    print('AJUSTEMENT MANUEL DE LA CONFIGURATION')
    print('='*80)

    # Afficher la config actuelle
    adaptive_config.print_current_config()

    # Menu
    print('\n[OPTIONS]')
    print('  1. Forcer l\'analyse et l\'ajustement automatique')
    print('  2. Passer en mode ULTRA_CONSERVATIVE (win rate < 30%)')
    print('  3. Passer en mode CONSERVATIVE (win rate 30-50%)')
    print('  4. Passer en mode BALANCED (win rate 50-60%)')
    print('  5. Réinitialiser aux valeurs par défaut')
    print('  6. Quitter')

    try:
        choice = input('\nChoix (1-6): ').strip()

        if choice == '1':
            # Forcer l'analyse
            if len(learning_engine.trades) < 10:
                print('\n❌ Pas assez de trades (min 10)')
                return

            total_trades = len(learning_engine.trades)
            wins = len([t for t in learning_engine.trades if t['is_win']])
            win_rate = (wins / total_trades * 100)

            print(f'\nWin Rate actuel: {win_rate:.1f}% ({total_trades} trades)')
            print('Lancement de l\'ajustement automatique...')

            adaptive_config.adjust_based_on_performance(
                win_rate,
                total_trades,
                learning_engine
            )

            print('\n✅ Ajustement terminé!')

        elif choice == '2':
            # Mode ULTRA_CONSERVATIVE
            print('\n⚠️ Passage en mode ULTRA_CONSERVATIVE')
            adaptive_config.params['TRADING_MODE'] = 'ULTRA_CONSERVATIVE'
            adaptive_config.params['MAX_PRICE_8S'] = 8000
            adaptive_config.params['ELITE_WALLET_MAX_MC'] = 6000
            adaptive_config.params['ELITE_MIN_BUY_RATIO'] = 0.85
            adaptive_config.params['ELITE_MIN_WHALE_COUNT'] = 4
            adaptive_config.save_params()
            print('✅ Paramètres ultra-conservateurs appliqués!')
            adaptive_config.print_current_config()

        elif choice == '3':
            # Mode CONSERVATIVE
            print('\n⚠️ Passage en mode CONSERVATIVE')
            adaptive_config.params['TRADING_MODE'] = 'CONSERVATIVE'
            adaptive_config.params['MAX_PRICE_8S'] = 10000
            adaptive_config.params['ELITE_WALLET_MAX_MC'] = 8000
            adaptive_config.params['ELITE_MIN_BUY_RATIO'] = 0.80
            adaptive_config.params['ELITE_MIN_WHALE_COUNT'] = 3
            adaptive_config.save_params()
            print('✅ Paramètres conservateurs appliqués!')
            adaptive_config.print_current_config()

        elif choice == '4':
            # Mode BALANCED
            print('\n🟡 Passage en mode BALANCED')
            adaptive_config.params['TRADING_MODE'] = 'BALANCED'
            adaptive_config.params['MAX_PRICE_8S'] = 12000
            adaptive_config.params['ELITE_WALLET_MAX_MC'] = 10000
            adaptive_config.params['ELITE_MIN_BUY_RATIO'] = 0.75
            adaptive_config.params['ELITE_MIN_WHALE_COUNT'] = 3
            adaptive_config.save_params()
            print('✅ Paramètres équilibrés appliqués!')
            adaptive_config.print_current_config()

        elif choice == '5':
            # Reset
            confirm = input('\n⚠️ Réinitialiser aux valeurs par défaut? (o/n): ')
            if confirm.lower() == 'o':
                adaptive_config.params = {
                    'MAX_PRICE_8S': 10000,
                    'MAX_PRICE_15S': 20000,
                    'ELITE_WALLET_MAX_MC': 8000,
                    'ELITE_MIN_BUY_RATIO': 0.80,
                    'ELITE_MIN_WHALE_COUNT': 3,
                    'AUTO_BUY_MAX_MC': 12000,
                    'AUTO_BUY_MIN_TXN': 25,
                    'AUTO_BUY_MIN_TRADERS': 20,
                    'AUTO_BUY_MIN_BUY_RATIO': 0.70,
                    'THRESHOLD_8S': 0.60,
                    'THRESHOLD_15S': 0.70,
                    'AI_MIN_TXN': 15,
                    'AI_MIN_TRADERS': 12,
                    'AI_MIN_BUY_RATIO': 0.60,
                    'PRICE_JUMP_TOLERANCE': 0.20,
                    'TRADING_MODE': 'CONSERVATIVE'
                }
                adaptive_config.save_params()
                print('✅ Paramètres réinitialisés!')
                adaptive_config.print_current_config()

        elif choice == '6':
            print('\nAu revoir!')
            return

        else:
            print('\n❌ Choix invalide')

    except KeyboardInterrupt:
        print('\n\nAnnulé.')
        return

if __name__ == '__main__':
    main()

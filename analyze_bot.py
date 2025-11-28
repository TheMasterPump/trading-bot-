"""
ANALYZE BOT - Script d'analyse manuel
Lance un diagnostic complet du bot à tout moment
"""
import sys
import os

# Fix encoding pour Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from learning_engine import learning_engine
from trade_analyzer import TradeAnalyzer
from adaptive_config import adaptive_config

def main():
    print('='*80)
    print('ANALYSE COMPLETE DU BOT DE TRADING')
    print('='*80)

    # Vérifier qu'il y a des données
    if len(learning_engine.trades) == 0:
        print('\n❌ Aucun trade dans l\'historique!')
        print('   Le bot n\'a pas encore tradé ou trading_history.json est vide.')
        print('\n   Lance d\'abord le bot pour collecter des données.')
        return

    # Stats de base
    total_trades = len(learning_engine.trades)
    wins = len([t for t in learning_engine.trades if t['is_win']])
    losses = total_trades - wins
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    print(f'\n[STATISTIQUES GLOBALES]')
    print(f'  Total trades: {total_trades}')
    print(f'  Wins: {wins} ({win_rate:.1f}%)')
    print(f'  Losses: {losses} ({100-win_rate:.1f}%)')

    # Statut
    if win_rate < 30:
        status = '❌ CRITIQUE'
        color = 'rouge'
    elif win_rate < 50:
        status = '⚠️ FAIBLE'
        color = 'orange'
    elif win_rate < 60:
        status = '🟡 CORRECT'
        color = 'jaune'
    else:
        status = '✅ EXCELLENT'
        color = 'vert'

    print(f'\n  Statut: {status}')

    # Configuration actuelle
    print(f'\n[CONFIGURATION ACTUELLE]')
    print(f'  Mode: {adaptive_config.params["TRADING_MODE"]}')
    print(f'  MAX_PRICE_8S: ${adaptive_config.params["MAX_PRICE_8S"]:,}')
    print(f'  ELITE_WALLET_MAX_MC: ${adaptive_config.params["ELITE_WALLET_MAX_MC"]:,}')
    print(f'  ELITE_MIN_BUY_RATIO: {adaptive_config.params["ELITE_MIN_BUY_RATIO"]*100:.0f}%')
    print(f'  ELITE_MIN_WHALE_COUNT: {adaptive_config.params["ELITE_MIN_WHALE_COUNT"]}')
    print(f'  PRICE_JUMP_TOLERANCE: +{adaptive_config.params["PRICE_JUMP_TOLERANCE"]*100:.0f}%')

    # Lancer l'analyseur complet
    analyzer = TradeAnalyzer(learning_engine)
    analyzer.full_diagnostic()

    # Recommandations
    print(f'\n{"="*80}')
    print(f'[RECOMMANDATIONS]')
    print(f'{"="*80}')

    if win_rate < 30:
        print(f'\n❌ ACTION URGENTE REQUISE!')
        print(f'')
        print(f'Le bot perd trop souvent. Voici ce qu\'il faut faire:')
        print(f'')
        print(f'1. ARRETER le bot immédiatement')
        print(f'2. Lancer un ajustement manuel:')
        print(f'   python adjust_config.py --mode ULTRA_CONSERVATIVE')
        print(f'')
        print(f'3. Le bot va ajuster automatiquement:')
        print(f'   - MAX_PRICE_8S → $8,000 (au lieu de ${adaptive_config.params["MAX_PRICE_8S"]:,})')
        print(f'   - ELITE_WALLET_MAX_MC → $6,000')
        print(f'   - ELITE_MIN_BUY_RATIO → 85%')
        print(f'   - ELITE_MIN_WHALE_COUNT → 4')
        print(f'')
        print(f'4. Relancer le bot en mode CONSERVATEUR')

    elif win_rate < 50:
        print(f'\n⚠️ AJUSTEMENTS NECESSAIRES')
        print(f'')
        print(f'Performance en dessous de 50%. Suggestions:')
        print(f'')
        print(f'1. Le bot va s\'auto-ajuster au prochain trade milestone (50 trades)')
        print(f'2. OU tu peux forcer l\'ajustement maintenant:')
        print(f'   python adjust_config.py --analyze')

    elif win_rate < 60:
        print(f'\n🟡 BON DEBUT')
        print(f'')
        print(f'Win rate {win_rate:.1f}% est correct mais peut être amélioré.')
        print(f'')
        print(f'Le bot continue d\'apprendre et va optimiser automatiquement.')
        print(f'Objectif: 60%+ win rate.')

    else:
        print(f'\n✅ PERFORMANCE EXCELLENTE!')
        print(f'')
        print(f'Win rate {win_rate:.1f}% est excellent!')
        print(f'Les paramètres actuels fonctionnent très bien.')
        print(f'')
        print(f'Continue comme ça et le bot va maintenir cette performance.')

    # Historique des ajustements
    if adaptive_config.adjustment_history:
        print(f'\n{"="*80}')
        print(f'[HISTORIQUE DES AJUSTEMENTS - {len(adaptive_config.adjustment_history)} AJUSTEMENTS]')
        print(f'{"="*80}')

        for i, adj in enumerate(adaptive_config.adjustment_history[-5:], 1):  # 5 derniers
            print(f'\n{i}. {adj["timestamp"][:19]}')
            print(f'   Win Rate: {adj["win_rate"]:.1f}% ({adj["total_trades"]} trades)')
            for change in adj["adjustments"]:
                print(f'   • {change}')

    print(f'\n{"="*80}')
    print(f'[FIN DE L\'ANALYSE]')
    print(f'{"="*80}')
    print(f'')
    print(f'Pour ajuster manuellement les paramètres:')
    print(f'  python adjust_config.py')
    print(f'')
    print(f'Pour voir l\'historique complet:')
    print(f'  python view_history.py')
    print(f'')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\nAnalyse interrompue.')
        sys.exit(0)
    except Exception as e:
        print(f'\n\n❌ Erreur: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

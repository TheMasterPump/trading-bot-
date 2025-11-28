"""
TRADE ANALYZER - Analyseur avancé de patterns
Détecte les patterns gagnants et perdants avec précision
"""
import json
import statistics
from collections import defaultdict, Counter

class TradeAnalyzer:
    def __init__(self, learning_engine):
        self.engine = learning_engine

    def analyze_elite_wallet_performance(self):
        """Analyse la performance de chaque elite wallet"""
        print(f'\n{"="*80}')
        print(f'[ANALYSE ELITE WALLETS]')
        print(f'{"="*80}')

        # Parser les wallets depuis les raisons
        wallet_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'trades': []})

        for trade in self.engine.trades:
            reason = trade.get('reason', '')

            # Si c'est un trade elite wallet
            if 'ELITE WALLET' in reason or '2 BALEINES CONSECUTIVES' in reason:
                # Pour l'instant on groupe tous les elite trades ensemble
                # On pourrait parser les addresses spécifiques plus tard
                is_elite = True

                if trade['is_win']:
                    wallet_stats['ELITE_TRADES']['wins'] += 1
                else:
                    wallet_stats['ELITE_TRADES']['losses'] += 1

                wallet_stats['ELITE_TRADES']['trades'].append(trade)

        # Afficher les stats
        for wallet_type, stats in wallet_stats.items():
            total = stats['wins'] + stats['losses']
            if total > 0:
                wr = (stats['wins'] / total * 100)
                emoji = '✅' if wr >= 50 else '⚠️' if wr >= 30 else '❌'

                avg_profit = statistics.mean([t['profit_ratio'] for t in stats['trades']])

                print(f'{emoji} {wallet_type}:')
                print(f'   Trades: {total} ({stats["wins"]}W / {stats["losses"]}L)')
                print(f'   Win Rate: {wr:.1f}%')
                print(f'   Avg Profit: {avg_profit:.2f}x')

                if wr < 30:
                    print(f'   ❌ RECOMMANDATION: Performance mauvaise, revoir stratégie!')

    def analyze_timing_performance(self):
        """Analyse la performance selon le timing d'entrée (8s vs 15s)"""
        print(f'\n{"="*80}')
        print(f'[ANALYSE TIMING D\'ENTREE]')
        print(f'{"="*80}')

        timing_stats = defaultdict(lambda: {'wins': 0, 'total': 0, 'profits': []})

        for trade in self.engine.trades:
            entry_time = trade.get('entry_time', 'unknown')
            timing_stats[entry_time]['total'] += 1
            if trade['is_win']:
                timing_stats[entry_time]['wins'] += 1
            timing_stats[entry_time]['profits'].append(trade['profit_ratio'])

        for timing, stats in timing_stats.items():
            if stats['total'] > 0:
                wr = (stats['wins'] / stats['total'] * 100)
                avg_profit = statistics.mean(stats['profits'])
                emoji = '✅' if wr >= 50 else '⚠️' if wr >= 30 else '❌'

                print(f'{emoji} Entry @ {timing}:')
                print(f'   {stats["wins"]}/{stats["total"]} ({wr:.1f}% WR)')
                print(f'   Avg: {avg_profit:.2f}x')

    def detect_losing_patterns(self):
        """Détecte les patterns qui font perdre de l'argent"""
        print(f'\n{"="*80}')
        print(f'[DETECTION PATTERNS PERDANTS]')
        print(f'{"="*80}')

        losses = [t for t in self.engine.trades if not t['is_win']]

        if len(losses) < 5:
            print('Pas assez de pertes pour analyse (bon signe!)')
            return

        # Pattern 1: MC trop élevé
        high_mc_losses = [l for l in losses if l['entry_mc'] > 15000]
        if high_mc_losses:
            pct = len(high_mc_losses) / len(losses) * 100
            print(f'❌ PATTERN 1: MC > 15K')
            print(f'   {len(high_mc_losses)} pertes ({pct:.0f}% des pertes)')
            print(f'   MC moyen: ${statistics.mean([l["entry_mc"] for l in high_mc_losses]):,.0f}')
            print(f'   → RECOMMANDATION: Baisser MAX_MC à 12K ou 10K')

        # Pattern 2: Entrées tardives (15s)
        late_entries = [l for l in losses if l.get('entry_time') == '15s']
        if late_entries:
            pct = len(late_entries) / len(losses) * 100
            print(f'\n❌ PATTERN 2: Entrées tardives @ 15s')
            print(f'   {len(late_entries)} pertes ({pct:.0f}% des pertes)')
            print(f'   → RECOMMANDATION: Focus sur entrées @ 8s uniquement')

        # Pattern 3: Stop Loss fréquent
        stop_losses = [l for l in losses if 'STOP LOSS' in l.get('exit_reason', '')]
        if stop_losses:
            pct = len(stop_losses) / len(losses) * 100
            print(f'\n❌ PATTERN 3: Stop Loss déclenché')
            print(f'   {len(stop_losses)} pertes ({pct:.0f}% des pertes)')
            avg_drop = statistics.mean([abs(l['profit_percent']) for l in stop_losses])
            print(f'   Drop moyen: -{avg_drop:.1f}%')

        # Pattern 4: Stratégie spécifique
        strategy_losses = defaultdict(int)
        for loss in losses:
            strategy = loss.get('strategy', 'UNKNOWN')
            strategy_losses[strategy] += 1

        print(f'\n[PERTES PAR STRATEGIE]')
        for strategy, count in strategy_losses.items():
            pct = count / len(losses) * 100
            print(f'   {strategy}: {count} ({pct:.0f}%)')

    def detect_winning_patterns(self):
        """Détecte les patterns qui font gagner de l'argent"""
        print(f'\n{"="*80}')
        print(f'[DETECTION PATTERNS GAGNANTS]')
        print(f'{"="*80}')

        wins = [t for t in self.engine.trades if t['is_win']]

        if len(wins) < 5:
            print('Pas assez de wins pour analyse')
            return

        # Analyser les features des wins
        win_mcs = [w['entry_mc'] for w in wins]
        avg_win_mc = statistics.mean(win_mcs)
        median_win_mc = statistics.median(win_mcs)

        print(f'✅ MC OPTIMAL DES WINS')
        print(f'   Moyenne: ${avg_win_mc:,.0f}')
        print(f'   Médiane: ${median_win_mc:,.0f}')
        print(f'   Range: ${min(win_mcs):,.0f} - ${max(win_mcs):,.0f}')
        print(f'   → RECOMMANDATION: Viser MC autour ${median_win_mc:,.0f}')

        # Analyser les stratégies gagnantes
        strategy_wins = Counter([w.get('strategy', 'UNKNOWN') for w in wins])

        print(f'\n✅ STRATEGIES GAGNANTES')
        for strategy, count in strategy_wins.most_common():
            pct = count / len(wins) * 100
            # Calculer le win rate de cette stratégie
            strategy_trades = [t for t in self.engine.trades if t.get('strategy') == strategy]
            strategy_wr = len([t for t in strategy_trades if t['is_win']]) / len(strategy_trades) * 100 if strategy_trades else 0

            print(f'   {strategy}: {count} wins ({pct:.0f}% des wins, {strategy_wr:.0f}% WR)')

        # Analyser le timing des wins
        timing_wins = Counter([w.get('entry_time', 'unknown') for w in wins])

        print(f'\n✅ TIMING GAGNANT')
        for timing, count in timing_wins.most_common():
            pct = count / len(wins) * 100
            print(f'   @ {timing}: {count} wins ({pct:.0f}%)')

    def analyze_latency_issue(self):
        """Analyse le problème de latence (whale @ 10K, bot @ 17K)"""
        print(f'\n{"="*80}')
        print(f'[ANALYSE LATENCE]')
        print(f'{"="*80}')

        # On ne peut pas savoir exactement le prix de la whale
        # Mais on peut voir si nos entrées sont trop élevées
        avg_entry_mc = statistics.mean([t['entry_mc'] for t in self.engine.trades])

        wins = [t for t in self.engine.trades if t['is_win']]
        losses = [t for t in self.engine.trades if not t['is_win']]

        if wins and losses:
            avg_win_entry = statistics.mean([w['entry_mc'] for w in wins])
            avg_loss_entry = statistics.mean([l['entry_mc'] for l in losses])

            print(f'MC MOYEN D\'ENTREE:')
            print(f'   Global: ${avg_entry_mc:,.0f}')
            print(f'   Wins: ${avg_win_entry:,.0f}')
            print(f'   Losses: ${avg_loss_entry:,.0f}')
            print(f'   Différence: ${avg_loss_entry - avg_win_entry:,.0f}')

            if avg_loss_entry > avg_win_entry + 3000:
                print(f'\n❌ LATENCE DETECTEE!')
                print(f'   Les pertes entrent ${avg_loss_entry - avg_win_entry:,.0f} plus tard que les wins')
                print(f'   → SOLUTION: Vérifier prix en temps réel avant achat')
                print(f'   → Si MC actuel > MC décision + 20% → SKIP')

    def calculate_optimal_thresholds(self):
        """Calcule les seuils optimaux basés sur l'historique"""
        print(f'\n{"="*80}')
        print(f'[CALCUL SEUILS OPTIMAUX]')
        print(f'{"="*80}')

        if len(self.engine.trades) < 20:
            print('Pas assez de données (min 20 trades)')
            return None

        wins = [t for t in self.engine.trades if t['is_win']]
        losses = [t for t in self.engine.trades if not t['is_win']]

        if not wins:
            print('Aucun win, impossible de calculer')
            return None

        # Calculer MC optimal
        win_mcs = [w['entry_mc'] for w in wins]
        optimal_max_mc = statistics.median(win_mcs) * 1.2  # +20% marge

        print(f'SEUILS OPTIMAUX CALCULES:')
        print(f'   MAX_MC: ${optimal_max_mc:,.0f} (médiane wins × 1.2)')

        # Pour les autres seuils, on aurait besoin des features au moment de l'entrée
        # C'est stocké dans 'features' de chaque trade

        return {
            'max_mc': optimal_max_mc
        }

    def full_diagnostic(self):
        """Diagnostic complet du bot"""
        print(f'\n')
        print(f'{"#"*80}')
        print(f'#{"DIAGNOSTIC COMPLET - TRADE ANALYZER":^78}#')
        print(f'{"#"*80}')

        if len(self.engine.trades) < 10:
            print(f'\n⚠️ Pas assez de trades pour diagnostic complet (min 10)')
            print(f'   Trades actuels: {len(self.engine.trades)}')
            return

        # Toutes les analyses
        self.analyze_elite_wallet_performance()
        self.analyze_timing_performance()
        self.detect_losing_patterns()
        self.detect_winning_patterns()
        self.analyze_latency_issue()
        self.calculate_optimal_thresholds()

        print(f'\n{"#"*80}')
        print(f'#{"FIN DU DIAGNOSTIC":^78}#')
        print(f'{"#"*80}\n')

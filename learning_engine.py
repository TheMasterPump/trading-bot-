"""
LEARNING ENGINE - MOTEUR D'APPRENTISSAGE INTELLIGENT
Le bot apprend de ses erreurs et s'améliore automatiquement
"""
import json
import os
from datetime import datetime
from collections import defaultdict
import statistics

class LearningEngine:
    def __init__(self, history_file='trading_history.json'):
        self.history_file = history_file
        self.trades = []
        self.blacklist = {
            'elite_wallets': set(),  # Wallets qui font perdre
            'tokens': set()           # Tokens pump-dump
        }
        self.performance_metrics = {}
        self.load_history()

    def load_history(self):
        """Charge l'historique des trades"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.trades = data.get('trades', [])
                    blacklist_data = data.get('blacklist', {})
                    self.blacklist['elite_wallets'] = set(blacklist_data.get('elite_wallets', []))
                    self.blacklist['tokens'] = set(blacklist_data.get('tokens', []))
                    self.performance_metrics = data.get('metrics', {})
                    print(f'[LEARNING ENGINE] {len(self.trades)} trades chargés depuis historique')
            except Exception as e:
                print(f'[LEARNING ENGINE] Erreur chargement: {e}')
                self.trades = []
        else:
            print('[LEARNING ENGINE] Nouveau historique créé')
            self.trades = []

    def save_history(self):
        """Sauvegarde l'historique"""
        data = {
            'trades': self.trades,
            'blacklist': {
                'elite_wallets': list(self.blacklist['elite_wallets']),
                'tokens': list(self.blacklist['tokens'])
            },
            'metrics': self.performance_metrics,
            'last_updated': datetime.now().isoformat()
        }

        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def record_trade(self, position):
        """Enregistre un trade fermé pour apprentissage"""

        # Convertir les types numpy en types Python pour JSON
        def convert_to_python(obj):
            """Convertit les types numpy en types Python standards"""
            import numpy as np
            if isinstance(obj, (np.integer, np.int32, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float32, np.float64)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_to_python(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_python(item) for item in obj]
            return obj

        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': position['symbol'],
            'mint': position['mint'],

            # Entry details
            'entry_mc': float(position['entry_mc']),
            'entry_time': position['entry_time'],
            'strategy': position.get('strategy', 'UNKNOWN'),
            'entry_reason': position.get('entry_reason', position.get('reason', 'N/A')),  # RAISON D'ENTRÉE (AUTO-BUY, IA, etc.)
            'confidence': float(position['confidence']),

            # Exit details
            'exit_mc': float(position['exit_mc']),
            'exit_reason': position.get('exit_reason', position.get('reason', 'N/A')),  # RAISON DE SORTIE (STOP LOSS, TIMEOUT, etc.)

            # Performance
            'profit_ratio': float(position['profit_ratio']),
            'profit_percent': float(position['profit_percent']),
            'is_win': position['profit_percent'] > 0,

            # Features at entry (for learning) - convertir numpy types
            'features': convert_to_python(position.get('entry_features', {})),

            # NOUVELLES DONNEES: Plus de détails pour analyse
            'partial_sold': position.get('partial_sold', False),  # Si partial profit atteint
            'is_elite_trade': position.get('is_elite_trade', False),  # Si trade elite wallet/baleines
            'timeout_minutes': position.get('timeout_minutes', 0),  # Durée avant fermeture
        }

        self.trades.append(trade_record)
        self.save_history()

        # Analyser après chaque trade
        self.analyze_after_trade(trade_record)

        # Analyse complète tous les 10 trades
        if len(self.trades) % 10 == 0:
            print(f'\n{"="*80}')
            print(f'[LEARNING ENGINE] ANALYSE AUTOMATIQUE - {len(self.trades)} TRADES')
            print(f'{"="*80}')
            self.full_analysis()

    def analyze_after_trade(self, trade):
        """Analyse rapide après chaque trade"""
        is_win = trade['is_win']

        # Si c'est un ELITE WALLET trade qui a perdu
        if not is_win and 'ELITE WALLET' in trade.get('reason', ''):
            # Extraire les wallets de la raison
            # Format: "ELITE WALLET: 1 VIP (87rRdssF...), 3 whales, 85% buy"
            reason = trade.get('reason', '')
            # TODO: Parser les wallets et ajouter à blacklist si trop de pertes
            self.check_elite_wallet_performance(trade)

        # Si entrée trop tardive (MC trop élevé au entry)
        if not is_win and trade['entry_mc'] > 15000:
            print(f'[LEARNING] ❌ Perte avec MC élevé (${trade["entry_mc"]:,.0f}) - {trade["symbol"]}')

    def check_elite_wallet_performance(self, trade):
        """Vérifie la performance d'un elite wallet"""
        # Compter les pertes de ce wallet
        reason = trade.get('reason', '')

        # Pour l'instant, on log juste
        # On pourrait parser le wallet address et tracker ses perfs
        if not trade['is_win']:
            print(f'[LEARNING] ⚠️ Elite wallet trade perdu: {trade["symbol"]} ({trade["profit_percent"]:.1f}%)')

    def full_analysis(self):
        """Analyse complète de tous les trades"""
        if len(self.trades) < 10:
            print('[LEARNING] Pas assez de trades pour analyse (min 10)')
            return

        total = len(self.trades)
        wins = len([t for t in self.trades if t['is_win']])
        losses = total - wins
        win_rate = (wins / total * 100) if total > 0 else 0

        print(f'\n[STATISTIQUES GLOBALES]')
        print(f'  Total trades: {total}')
        print(f'  Wins: {wins} ({win_rate:.1f}%)')
        print(f'  Losses: {losses} ({100-win_rate:.1f}%)')

        # Analyser par stratégie
        self.analyze_by_strategy()

        # Analyser par plage de MC
        self.analyze_by_mc_range()

        # Analyser les raisons de pertes
        self.analyze_loss_reasons()

        # Recommandations
        self.generate_recommendations(win_rate)

    def analyze_by_strategy(self):
        """Analyse par type de stratégie"""
        strategies = defaultdict(lambda: {'wins': 0, 'total': 0, 'profits': []})

        for trade in self.trades:
            strategy = trade.get('strategy', 'UNKNOWN')
            strategies[strategy]['total'] += 1
            if trade['is_win']:
                strategies[strategy]['wins'] += 1
            strategies[strategy]['profits'].append(trade['profit_ratio'])

        print(f'\n[ANALYSE PAR STRATEGIE]')
        for strategy, data in strategies.items():
            wr = (data['wins'] / data['total'] * 100) if data['total'] > 0 else 0
            avg_profit = statistics.mean(data['profits']) if data['profits'] else 0
            emoji = '✅' if wr >= 50 else '⚠️' if wr >= 30 else '❌'
            print(f'  {emoji} {strategy}: {data["wins"]}/{data["total"]} ({wr:.1f}% WR) - Avg: {avg_profit:.2f}x')

    def analyze_by_mc_range(self):
        """Analyse par plage de Market Cap d'entrée"""
        ranges = {
            '< 8K': (0, 8000),
            '8K-12K': (8000, 12000),
            '12K-15K': (12000, 15000),
            '> 15K': (15000, float('inf'))
        }

        results = defaultdict(lambda: {'wins': 0, 'total': 0})

        for trade in self.trades:
            entry_mc = trade['entry_mc']
            for range_name, (min_mc, max_mc) in ranges.items():
                if min_mc <= entry_mc < max_mc:
                    results[range_name]['total'] += 1
                    if trade['is_win']:
                        results[range_name]['wins'] += 1
                    break

        print(f'\n[ANALYSE PAR MC ENTREE]')
        for range_name in ['< 8K', '8K-12K', '12K-15K', '> 15K']:
            data = results[range_name]
            if data['total'] > 0:
                wr = (data['wins'] / data['total'] * 100)
                emoji = '✅' if wr >= 50 else '⚠️' if wr >= 30 else '❌'
                print(f'  {emoji} {range_name:10}: {data["wins"]}/{data["total"]} ({wr:.1f}% WR)')

    def analyze_loss_reasons(self):
        """Analyse les raisons de pertes"""
        losses = [t for t in self.trades if not t['is_win']]

        if not losses:
            print(f'\n[ANALYSE DES PERTES] Aucune perte (parfait!)')
            return

        # Analyser pourquoi on perd
        loss_mc_high = len([l for l in losses if l['entry_mc'] > 15000])
        loss_stop_loss = len([l for l in losses if 'STOP LOSS' in l.get('exit_reason', '')])
        loss_elite = len([l for l in losses if 'ELITE WALLET' in l.get('reason', '')])

        print(f'\n[ANALYSE DES PERTES - {len(losses)} TRADES]')
        print(f'  MC > 15K au entry: {loss_mc_high} ({loss_mc_high/len(losses)*100:.0f}%)')
        print(f'  Stop Loss déclenché: {loss_stop_loss} ({loss_stop_loss/len(losses)*100:.0f}%)')
        print(f'  Elite wallet trades: {loss_elite} ({loss_elite/len(losses)*100:.0f}%)')

        # Trouver le MC moyen des pertes vs gains
        loss_avg_mc = statistics.mean([l['entry_mc'] for l in losses])
        wins = [t for t in self.trades if t['is_win']]
        if wins:
            win_avg_mc = statistics.mean([w['entry_mc'] for w in wins])
            print(f'\n[MC MOYEN]')
            print(f'  Losses: ${loss_avg_mc:,.0f}')
            print(f'  Wins: ${win_avg_mc:,.0f}')
            print(f'  Différence: ${loss_avg_mc - win_avg_mc:,.0f} (losses entrent plus tard!)')

    def generate_recommendations(self, current_wr):
        """Génère des recommandations basées sur l'analyse"""
        print(f'\n{"="*80}')
        print(f'[RECOMMANDATIONS AUTO]')
        print(f'{"="*80}')

        if current_wr < 30:
            print(f'❌ WIN RATE CRITIQUE ({current_wr:.1f}%)')
            print(f'')
            print(f'ACTIONS IMMEDIATES:')
            print(f'  1. BAISSER le prix max d\'entrée à 10K (actuellement trop tard)')
            print(f'  2. AUGMENTER buy_ratio minimum à 85%')
            print(f'  3. EXIGER 4+ whales minimum (au lieu de 3)')
            print(f'  4. MODE CONSERVATEUR: Moins de trades, qualité max')
            print(f'')
            print(f'⚠️ RECOMMANDATION: Arrêter le bot et ajuster les paramètres!')

        elif current_wr < 50:
            print(f'⚠️ WIN RATE FAIBLE ({current_wr:.1f}%)')
            print(f'')
            print(f'AJUSTEMENTS SUGGERES:')
            print(f'  1. Réduire prix max d\'entrée à 12K')
            print(f'  2. Augmenter seuil buy_ratio à 80%')
            print(f'  3. Vérifier prix AVANT achat (anti-latence)')
            print(f'  4. Analyser les elite wallets perdants')

        elif current_wr < 60:
            print(f'🟡 WIN RATE CORRECT ({current_wr:.1f}%)')
            print(f'')
            print(f'OPTIMISATIONS POSSIBLES:')
            print(f'  1. Affiner les seuils progressivement')
            print(f'  2. Continuer à monitorer')
            print(f'  3. Objectif: 60%+ win rate')

        else:
            print(f'✅ EXCELLENT WIN RATE ({current_wr:.1f}%)')
            print(f'')
            print(f'CONTINUER:')
            print(f'  Les paramètres actuels fonctionnent bien!')
            print(f'  Maintenir la stratégie et monitorer.')

        print(f'{"="*80}')

    def get_recommended_params(self):
        """Retourne les paramètres recommandés basés sur l'apprentissage"""
        if len(self.trades) < 20:
            # Pas assez de données, utiliser valeurs par défaut conservatrices
            return {
                'max_mc': 10000,
                'min_buy_ratio': 0.80,
                'min_whale_count': 3,
                'threshold': 0.60
            }

        # Analyser les trades gagnants
        wins = [t for t in self.trades if t['is_win']]

        if wins:
            # MC moyen des wins
            win_avg_mc = statistics.mean([w['entry_mc'] for w in wins])
            recommended_max_mc = min(15000, win_avg_mc * 1.3)  # +30% marge

            return {
                'max_mc': recommended_max_mc,
                'min_buy_ratio': 0.80,  # Sera ajusté avec plus de données
                'min_whale_count': 3,
                'threshold': 0.60
            }

        # Par défaut
        return {
            'max_mc': 10000,
            'min_buy_ratio': 0.80,
            'min_whale_count': 3,
            'threshold': 0.60
        }

    def is_wallet_blacklisted(self, wallet_address):
        """Vérifie si un wallet est blacklisté"""
        return wallet_address in self.blacklist['elite_wallets']

    def should_skip_based_on_history(self, features):
        """Détermine si on devrait skip basé sur l'historique"""
        # Si MC trop élevé historiquement perdant
        mc = features.get('mc', 0)

        # Analyser les trades passés avec MC similaire
        similar_trades = [
            t for t in self.trades[-50:]  # 50 derniers trades
            if abs(t['entry_mc'] - mc) < 2000  # +/- 2K
        ]

        if len(similar_trades) >= 5:
            wins = len([t for t in similar_trades if t['is_win']])
            wr = wins / len(similar_trades)

            if wr < 0.3:  # Moins de 30% win rate
                return True, f'MC ${mc:,.0f} historiquement perdant ({wr*100:.0f}% WR sur {len(similar_trades)} trades)'

        return False, None

# Instance globale
learning_engine = LearningEngine()

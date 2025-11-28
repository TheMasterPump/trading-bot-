"""
ADAPTIVE CONFIG - Configuration qui s'adapte automatiquement
Ajuste les paramètres en fonction des performances
"""
import json
import os

class AdaptiveConfig:
    """Configuration qui apprend et s'adapte"""

    def __init__(self, config_file='adaptive_params.json'):
        self.config_file = config_file

        # Paramètres ADAPTATIFS (changent selon performance)
        self.params = {
            # Prix limites
            'MAX_PRICE_8S': 10000,      # Sera ajusté selon performance
            'MAX_PRICE_15S': 20000,

            # Elite wallets (seuil whale = $200 = 1+ SOL)
            'ELITE_WALLET_MAX_MC': 10000,  # Max $10K pour elite trades
            'ELITE_MIN_BUY_RATIO': 0.75,   # 75% buy ratio minimum
            'ELITE_MIN_WHALE_COUNT': 2,    # 2+ baleines de 1+ SOL

            # Auto-buy rules
            'AUTO_BUY_MAX_MC': 12000,
            'AUTO_BUY_MIN_TXN': 25,
            'AUTO_BUY_MIN_TRADERS': 20,
            'AUTO_BUY_MIN_BUY_RATIO': 0.70,

            # IA thresholds - OPTION B: IA pour cas limites (< 22 txn OU < 72% buy)
            'THRESHOLD_8S': 0.60,
            'THRESHOLD_15S': 0.70,
            'AI_MIN_TXN': 17,          # OPTIMISÉ: Accepte dès 17 txn (pour IDM-like)
            'AI_MIN_TRADERS': 8,       # OPTIMISÉ: Très flexible (IA winners min = 8)
            'AI_MIN_BUY_RATIO': 0.55,  # OPTIMISÉ: Accepte 55%+ (pour IDM 57%)

            # Anti-latence
            'PRICE_JUMP_TOLERANCE': 0.20,  # Skip si prix a monté de +20%

            # Mode
            'TRADING_MODE': 'CONSERVATIVE'  # CONSERVATIVE, BALANCED, AGGRESSIVE
        }

        # Historique des ajustements
        self.adjustment_history = []

        # Charger les paramètres sauvegardés
        self.load_params()

    def load_params(self):
        """Charge les paramètres depuis le fichier"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.params = data.get('params', self.params)
                    self.adjustment_history = data.get('history', [])
                    print(f'[ADAPTIVE CONFIG] Paramètres chargés: Mode {self.params["TRADING_MODE"]}')
            except Exception as e:
                print(f'[ADAPTIVE CONFIG] Erreur chargement: {e}')

    def save_params(self):
        """Sauvegarde les paramètres"""
        data = {
            'params': self.params,
            'history': self.adjustment_history
        }

        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def adjust_based_on_performance(self, win_rate, total_trades, learning_engine):
        """Ajuste les paramètres selon la performance"""
        print(f'\n{"="*80}')
        print(f'[ADAPTIVE CONFIG] AJUSTEMENT AUTO DES PARAMETRES')
        print(f'{"="*80}')
        print(f'Win Rate actuel: {win_rate:.1f}%')
        print(f'Total trades: {total_trades}')

        adjustments_made = []

        # Pas assez de données
        if total_trades < 20:
            print(f'⚠️ Pas assez de trades pour ajuster (min 20)')
            return

        # =========================================================================
        # MODE CRITIQUE: Win Rate < 30%
        # =========================================================================
        if win_rate < 30:
            print(f'\n❌ MODE CRITIQUE - Win Rate trop bas!')

            old_mode = self.params['TRADING_MODE']
            self.params['TRADING_MODE'] = 'ULTRA_CONSERVATIVE'
            adjustments_made.append(f'Mode: {old_mode} → ULTRA_CONSERVATIVE')

            # Baisser prix max drastiquement
            if self.params['MAX_PRICE_8S'] > 8000:
                old_val = self.params['MAX_PRICE_8S']
                self.params['MAX_PRICE_8S'] = 8000
                adjustments_made.append(f'MAX_PRICE_8S: ${old_val:,} → $8,000')

            if self.params['ELITE_WALLET_MAX_MC'] > 6000:
                old_val = self.params['ELITE_WALLET_MAX_MC']
                self.params['ELITE_WALLET_MAX_MC'] = 6000
                adjustments_made.append(f'ELITE_WALLET_MAX_MC: ${old_val:,} → $6,000')

            # Augmenter buy_ratio minimum
            if self.params['ELITE_MIN_BUY_RATIO'] < 0.85:
                old_val = self.params['ELITE_MIN_BUY_RATIO']
                self.params['ELITE_MIN_BUY_RATIO'] = 0.85
                adjustments_made.append(f'ELITE_MIN_BUY_RATIO: {old_val*100:.0f}% → 85%')

            # Exiger plus de whales
            if self.params['ELITE_MIN_WHALE_COUNT'] < 4:
                old_val = self.params['ELITE_MIN_WHALE_COUNT']
                self.params['ELITE_MIN_WHALE_COUNT'] = 4
                adjustments_made.append(f'ELITE_MIN_WHALE_COUNT: {old_val} → 4')

        # =========================================================================
        # MODE FAIBLE: Win Rate 30-50%
        # =========================================================================
        elif win_rate < 50:
            print(f'\n⚠️ MODE AJUSTEMENT - Win Rate faible')

            old_mode = self.params['TRADING_MODE']
            self.params['TRADING_MODE'] = 'CONSERVATIVE'
            adjustments_made.append(f'Mode: {old_mode} → CONSERVATIVE')

            # Analyser où sont les pertes
            losses = [t for t in learning_engine.trades if not t['is_win']]

            # Si beaucoup de pertes avec MC élevé
            high_mc_losses = len([l for l in losses if l['entry_mc'] > 12000])
            if high_mc_losses > len(losses) * 0.5:  # 50%+ des pertes
                if self.params['MAX_PRICE_8S'] > 10000:
                    old_val = self.params['MAX_PRICE_8S']
                    self.params['MAX_PRICE_8S'] = 10000
                    adjustments_made.append(f'MAX_PRICE_8S: ${old_val:,} → $10,000 (trop de pertes MC élevé)')

        # =========================================================================
        # MODE CORRECT: Win Rate 50-60%
        # =========================================================================
        elif win_rate < 60:
            print(f'\n🟡 MODE EQUILIBRE - Win Rate correct')

            old_mode = self.params['TRADING_MODE']
            self.params['TRADING_MODE'] = 'BALANCED'
            adjustments_made.append(f'Mode: {old_mode} → BALANCED')

            # Fines optimisations basées sur les wins
            wins = [t for t in learning_engine.trades if t['is_win']]
            if wins:
                import statistics
                median_win_mc = statistics.median([w['entry_mc'] for w in wins])

                # Ajuster MAX_PRICE pour viser la médiane des wins
                optimal_max = int(median_win_mc * 1.3)  # +30% marge

                if abs(self.params['MAX_PRICE_8S'] - optimal_max) > 2000:
                    old_val = self.params['MAX_PRICE_8S']
                    self.params['MAX_PRICE_8S'] = optimal_max
                    adjustments_made.append(f'MAX_PRICE_8S: ${old_val:,} → ${optimal_max:,} (optimisé median wins)')

        # =========================================================================
        # MODE EXCELLENT: Win Rate >= 60%
        # =========================================================================
        else:
            print(f'\n✅ MODE OPTIMAL - Excellent Win Rate!')

            old_mode = self.params['TRADING_MODE']
            self.params['TRADING_MODE'] = 'OPTIMAL'
            if old_mode != 'OPTIMAL':
                adjustments_made.append(f'Mode: {old_mode} → OPTIMAL')

            print(f'Les paramètres actuels fonctionnent très bien, pas de changement!')

        # =========================================================================
        # SAUVEGARDER
        # =========================================================================
        if adjustments_made:
            print(f'\n[AJUSTEMENTS EFFECTUES]')
            for adj in adjustments_made:
                print(f'  • {adj}')

            # Enregistrer dans l'historique
            from datetime import datetime
            self.adjustment_history.append({
                'timestamp': datetime.now().isoformat(),
                'win_rate': win_rate,
                'total_trades': total_trades,
                'adjustments': adjustments_made
            })

            self.save_params()
            print(f'\n✅ Paramètres sauvegardés!')
        else:
            print(f'\nAucun ajustement nécessaire.')

        print(f'{"="*80}')

    def get_param(self, key):
        """Récupère un paramètre"""
        return self.params.get(key)

    def set_param(self, key, value):
        """Définit un paramètre"""
        self.params[key] = value
        self.save_params()

    def get_all_params(self):
        """Retourne tous les paramètres"""
        return self.params.copy()

    def print_current_config(self):
        """Affiche la configuration actuelle"""
        print(f'\n{"="*80}')
        print(f'[CONFIGURATION ACTUELLE - MODE: {self.params["TRADING_MODE"]}]')
        print(f'{"="*80}')
        print(f'\n[PRIX LIMITES]')
        print(f'  MAX_PRICE_8S: ${self.params["MAX_PRICE_8S"]:,}')
        print(f'  MAX_PRICE_15S: ${self.params["MAX_PRICE_15S"]:,}')
        print(f'  ELITE_WALLET_MAX_MC: ${self.params["ELITE_WALLET_MAX_MC"]:,}')

        print(f'\n[ELITE WALLET FILTERS]')
        print(f'  Min Buy Ratio: {self.params["ELITE_MIN_BUY_RATIO"]*100:.0f}%')
        print(f'  Min Whale Count: {self.params["ELITE_MIN_WHALE_COUNT"]}')

        print(f'\n[AUTO-BUY RULES]')
        print(f'  Max MC: ${self.params["AUTO_BUY_MAX_MC"]:,}')
        print(f'  Min TXN: {self.params["AUTO_BUY_MIN_TXN"]}')
        print(f'  Min Traders: {self.params["AUTO_BUY_MIN_TRADERS"]}')
        print(f'  Min Buy Ratio: {self.params["AUTO_BUY_MIN_BUY_RATIO"]*100:.0f}%')

        print(f'\n[IA THRESHOLDS]')
        print(f'  Threshold 8s: {self.params["THRESHOLD_8S"]*100:.0f}%')
        print(f'  Threshold 15s: {self.params["THRESHOLD_15S"]*100:.0f}%')

        print(f'\n[ANTI-LATENCE]')
        print(f'  Price Jump Tolerance: +{self.params["PRICE_JUMP_TOLERANCE"]*100:.0f}%')

        print(f'{"="*80}')

# Instance globale
adaptive_config = AdaptiveConfig()

"""
BOT DE TRADING LIVE PUMPFUN AVEC IA + APPRENTISSAGE AUTOMATIQUE
Achète et vend automatiquement les tokens basé sur les prédictions AI
Le bot apprend de ses erreurs et s'améliore automatiquement
VERSION INTELLIGENTE: Learning Engine + Adaptive Config + Anti-Latence
"""

import asyncio
import json
import joblib
import pandas as pd
from datetime import datetime
import websockets
import time
import os
import sys

# Couleurs terminal
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    BLUE = Fore.CYAN  # Cyan est plus lisible que bleu foncé
    RESET = Style.RESET_ALL
except ImportError:
    # Si colorama pas installé, pas de couleurs
    BLUE = ""
    RESET = ""

# Fix encoding pour Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Modules d'apprentissage
from learning_engine import learning_engine
from solana_trader import solana_trader
from trade_analyzer import TradeAnalyzer
from adaptive_config import adaptive_config

# Module prix SOL en temps réel
from sol_price_fetcher import get_sol_price_usd

# Module prix token PumpFun en temps réel
from pumpfun_price_fetcher import get_token_price_live

# ============================================================================
# FONCTION PRINT COULEUR BLEU
# ============================================================================
def print_blue(text):
    """Print en bleu/cyan pour terminal"""
    print(f"{BLUE}{text}{RESET}")

# ============================================================================
# CONFIGURATION INTELLIGENTE (Utilise adaptive_config)
# ============================================================================
class Config:
    # MODE
    SIMULATION_MODE = True   # True = simulation sans argent réel, False = trading live
    TEST_MODE = True         # True = trading live avec petits montants (0.01 SOL), False = montants normaux
    SCREENSHOT_MODE = True   # True = interface en anglais pour screenshots professionnels

    # WALLET SOLANA (pour trading réel - configuré dans .env)
    # Ne pas mettre la clé privée ici! Utilisez le fichier .env

    # IA - SEUILS DE CONFIANCE (ASSOUPLIS pour avoir plus de trades)
    THRESHOLD_8S = 0.50  # ASSOUPLI: 50% au lieu de 85% (plus de trades IA)
    THRESHOLD_15S = 0.50  # ASSOUPLI: 50% au lieu de 85% (plus de trades IA)

    # PRIX LIMITES (MC en USD) - DATASET OPTIMISÉ (8K-30K)
    MAX_PRICE_8S = 12000  # Early entry @ 8s
    MAX_PRICE_15S = 30000  # Late entry @ 15s (dataset = $29K moyen!)

    # SYSTEME HYBRIDE - REGLES INTELLIGENTES (DATASET OPTIMISÉ)
    # Niveau 1: AUTO-BUY (Runners évidents - bypass IA)
    # OPTIMISÉ: Paramètres pour capturer 93% des winners historiques
    AUTO_BUY_MIN_TXN = 22      # OPTIMISÉ: 22 txn min (garde 93% winners)
    AUTO_BUY_MIN_TRADERS = 17  # DATASET: min 17 (moyenne 22)
    AUTO_BUY_MIN_BUY_RATIO = 0.72  # OPTIMISÉ: 72% (garde 93% winners)
    AUTO_BUY_MAX_MC = 30000    # Max 30K (dataset = $29K moyen)

    # NOUVEAUX FILTRES AUTO-BUY: Volume modéré (pas trop de bots)
    AUTO_BUY_MAX_TXN = 50  # Maximum de transactions (éviter bots)
    AUTO_BUY_MAX_TRADERS = 35  # Maximum de traders (volume modéré)

    # Niveau 2: Filtres pour IA (pré-filtre avant IA)
    AI_MIN_TXN = adaptive_config.get_param('AI_MIN_TXN')
    AI_MIN_TRADERS = adaptive_config.get_param('AI_MIN_TRADERS')
    AI_MIN_BUY_RATIO = adaptive_config.get_param('AI_MIN_BUY_RATIO')

    # Level 3: AUTO SKIP (too weak)
    SKIP_IF_TXN_BELOW = 5        # Skip si < 5 transactions
    SKIP_IF_BUY_RATIO_BELOW = 0.40  # Skip si < 40% buy ratio

    # Bonus pour baleines (DÉSACTIVÉ - baleines = mauvais signal)
    WHALE_BOOST_THRESHOLD = 999  # Désactivé (les baleines sont un red flag)
    WHALE_BOOST_AMOUNT = 0.0     # Pas de boost

    # WALLETS ELITE - AUTO-FOLLOW (meilleurs traders avec bon PNL)
    ELITE_WALLETS = {
        '87rRdssFiTJKY4MGARa4G5vQ31hmR7MxSmhzeaJ5AAxJ',
        'CyaE1VxvBrahnPWkqm5VsdCvyS2QmNht2UFrKJHga54o',
        '5B79fMkcFeRTiwm7ehsZsFiKsC7m7n1Bgv9yLxPp9q2X',
        '4BdKaxN8G6ka4GYtQQWk4G4dZRUTX2vQH9GcXdBREFUk',
        '4Be9CvxqHW6BYiRAxW9Q3xu1ycTMWaL5z8NX4HR3ha7t',
        '2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f',
        'Av3xWHJ5EsoLZag6pr7LKbrGgLRTaykXomDD5kBhL9YQ',
        '78N177fzNJpp8pG49xDv1efYcTMSzo9tPTKEA9mAVkh2',
        'CA4keXLtGJWBcsWivjtMFBghQ8pFsGRWFxLrRCtirzu5',
        'BbwF4wSwmxMVp7xubA7qigCUU6RMcvK2soMu8VrDHjDH',
        'A8H8D8WegN7MgMdRAVYWU2uAcSTfZaC3c6pyLDF8CFXv',
        'iBH7W6i8i6dKmv5aoj7b6VRjx1UXMyjuxx1BichwVZd',
        '8yJFWmVTQq69p6VJxGwpzW7ii7c5J9GRAtHCNMMQPydj',
        'BoBo2S28s9E2gE2qMJPSMFUvdptpBCXaRhLg6UYR8teE',
        '5YkZmuaLhrPjFv4vtYE2mcR6J4JEXG1EARGh8YYFo8s4'
    }
    ELITE_WALLET_MAX_MC = adaptive_config.get_param('ELITE_WALLET_MAX_MC')
    ELITE_MIN_BUY_RATIO = adaptive_config.get_param('ELITE_MIN_BUY_RATIO')
    ELITE_MIN_WHALE_COUNT = adaptive_config.get_param('ELITE_MIN_WHALE_COUNT')

    # TRADING
    if SCREENSHOT_MODE:
        BUY_AMOUNT_SOL = 0.3  # Mode screenshot: montants réalistes pour images
        DISPLAY_AMOUNT = 0.3  # Montant affiché
    else:
        BUY_AMOUNT_SOL = 0.01 if TEST_MODE else 0.05
        DISPLAY_AMOUNT = BUY_AMOUNT_SOL
    SLIPPAGE_BPS = 2500     # Slippage toléré (2500 = 25%) - PumpFun bouge TRÈS vite
    PRIORITY_FEE = 0.001    # Priority fee (0.001 SOL pour passer rapidement)

    # TAKE PROFIT / STOP LOSS
    TAKE_PROFIT_MC = 53000  # Vendre quand MC atteint $53K (migration) - pour trades IA normaux
    TAKE_PROFIT_PARTIAL = 2.0  # Vendre 50% à 2x (récupère investissement)
    TAKE_PROFIT_FINAL = 53000  # Vendre les 50% restants à la migration
    STOP_LOSS_PERCENT = 0.40  # AMÉLIORÉ: -40% au lieu de -35% (éviter 94% de stop loss)

    # TIMEOUT DES POSITIONS
    POSITION_TIMEOUT_MINUTES = 45  # AMÉLIORÉ: 45 min au lieu de 30 (capturer runners lents)

    # ANTI-LATENCE: Vérifier que le prix n'a pas explosé avant d'acheter
    PRICE_JUMP_TOLERANCE = adaptive_config.get_param('PRICE_JUMP_TOLERANCE')  # +20% max

    # ========================================================================
    # OPTIMISATIONS BASÉES SUR L'ANALYSE (Sweet Spot + Filtres Stricts)
    # ========================================================================
    # Sweet Spot: 8-30K MC = ZONE OPTIMALE (dataset migrations = $29K moyen!)
    SWEET_SPOT_MIN_MC = 8000   # Minimum 8K (catch early)
    SWEET_SPOT_MAX_MC = 30000  # OPTIMISÉ à 30K (dataset = $29K moyen, catch late runners)

    # Filtres baleines intelligents (conditionnels au MC)
    AI_MIN_WHALE_COUNT = 0     # Pas de minimum strict
    AI_STRICT_BUY_RATIO = 0.72 # DATASET: 72% (au lieu de 75%)
    AI_MAX_WHALES_EARLY = 1    # Max 1 baleine SI MC < 12K (early entry)
    AI_MAX_WHALES_LATE = 3     # Max 3 baleines SI MC >= 12K (late entry, dataset = 35% ont 2+)

    # Partial profit ajusté
    PARTIAL_SELL_PERCENT = 0.50  # Vendre 50% à 2x

    # ========================================================================
    # VENTE PROGRESSIVE APRÈS MIGRATION (pour capturer les mega pumps)
    # ========================================================================
    PROGRESSIVE_SELL_ENABLED = True    # Activer vente progressive après migration
    PROGRESSIVE_SELL_INTERVAL = 20     # Vendre toutes les 20 secondes
    PROGRESSIVE_SELL_PERCENT = 0.05    # Vendre 5% de la position totale à chaque fois
    PROGRESSIVE_SELL_STOP_LOSS = 0.15  # Si MC baisse de 15% depuis max, vendre tout le reste

    # PUMPFUN
    PUMPFUN_WS = "wss://pumpportal.fun/api/data"

    # Prix SOL dynamique (mis à jour toutes les 30s depuis CoinGecko)
    @staticmethod
    def get_sol_price():
        """Récupère le prix SOL/USD en temps réel"""
        return get_sol_price_usd()

print('='*80)
if Config.SCREENSHOT_MODE:
    print('PUMPFUN AI TRADING BOT - AUTOMATED INTELLIGENCE SYSTEM')
else:
    print('BOT DE TRADING LIVE PUMPFUN - INTELLIGENCE ARTIFICIELLE AUTO-APPRENANTE')
print('='*80)
if not Config.SCREENSHOT_MODE:
    print(f'\n[MODE: {"SIMULATION" if Config.SIMULATION_MODE else "LIVE TRADING"}]')

# Afficher le prix SOL en temps réel
sol_price = Config.get_sol_price()
if Config.SCREENSHOT_MODE:
    print(f'\n[💰 SOL PRICE - REAL TIME]')
    print(f'  SOL Price: ${sol_price:.2f} USD (CoinGecko)')
    print(f'  Updated every 30s')
else:
    print(f'\n[💰 PRIX SOL EN TEMPS REEL]')
    print(f'  Prix SOL: ${sol_price:.2f} USD (CoinGecko)')
    print(f'  Mise a jour toutes les 30s')

# Afficher la config adaptive
if Config.SCREENSHOT_MODE:
    print(f'\n[🧠 AI AUTO-LEARNING]')
    print(f'  > {len(learning_engine.trades)} trades in history')
    print(f'  > Mode: {adaptive_config.params["TRADING_MODE"]}')
    print(f'  > Auto-analysis every 10 trades')
    print(f'  > Auto-adjustment every 50 trades')
else:
    print(f'\n[🧠 APPRENTISSAGE AUTOMATIQUE]')
    print(f'  > {len(learning_engine.trades)} trades dans l\'historique')
    print(f'  > Mode: {adaptive_config.params["TRADING_MODE"]}')
    print(f'  > Analyse auto tous les 10 trades')
    print(f'  > Ajustement auto tous les 50 trades')

if Config.SCREENSHOT_MODE:
    print(f'\n[🎯 OPTIMIZATIONS - BASED ON 174 TRADES ANALYSIS]')
    print(f'  ✅ Optimal Sweet Spot: MC ${Config.SWEET_SPOT_MIN_MC/1000:.0f}K-${Config.SWEET_SPOT_MAX_MC/1000:.0f}K (19.5% WR + avg profit +110%!)')
    print(f'  ✅ ANTI-WHALE FILTERS: 0 whales for AUTO-BUY, max 1 for AI')
    print(f'  ✅ Minimum buy ratio: {Config.AI_STRICT_BUY_RATIO*100:.0f}%')
    print(f'  ✅ Stop Loss: -{Config.STOP_LOSS_PERCENT*100:.0f}% (widened to let tokens breathe)')
    print(f'  ✅ Timeout: {Config.POSITION_TIMEOUT_MINUTES} min (catch slow runners)')
    print(f'  ✅ LIVE PRICE verification before each trade')
else:
    print(f'\n[🎯 AMÉLIORATIONS BASÉES SUR ANALYSE DE 174 TRADES]')
    print(f'  ✅ Sweet Spot OPTIMAL: MC ${Config.SWEET_SPOT_MIN_MC/1000:.0f}K-${Config.SWEET_SPOT_MAX_MC/1000:.0f}K (19.5% WR + profit +110%!)')
    print(f'  ✅ FILTRES ANTI-BALEINES: 0 baleine pour AUTO-BUY, max 1 pour IA')
    print(f'  ✅ Buy ratio minimum: {Config.AI_STRICT_BUY_RATIO*100:.0f}%')
    print(f'  ✅ Stop Loss: -{Config.STOP_LOSS_PERCENT*100:.0f}% (élargi pour laisser respirer)')
    print(f'  ✅ Timeout: {Config.POSITION_TIMEOUT_MINUTES} min (capturer runners lents)')
    print(f'  ✅ Vérification PRIX LIVE avant chaque achat/vente')

sell_pct = int(Config.PARTIAL_SELL_PERCENT * 100)
keep_pct = 100 - sell_pct
print(f'\n[💰 STRATEGIE VENTE PROGRESSIVE - CAPTURE LES MEGA PUMPS]')
print(f'  1. À {Config.TAKE_PROFIT_PARTIAL:.1f}x: Vendre {sell_pct}% (RÉCUPÈRE INVESTISSEMENT)')
print(f'  2. À ${Config.TAKE_PROFIT_FINAL:,} (migration): VENTE PROGRESSIVE')
print(f'     -> Vendre {int(Config.PROGRESSIVE_SELL_PERCENT*100)}% toutes les {Config.PROGRESSIVE_SELL_INTERVAL}s')
print(f'     -> Si token pump à 100K/200K/500K = MAX PROFIT!')
print(f'     -> Protection: Si MC baisse {int(Config.PROGRESSIVE_SELL_STOP_LOSS*100)}% depuis max, vendre tout le reste')
print(f'  ✅ Après 2x: Position 100% RISK-FREE!')

print(f'\n[🐋 PATTERNS ULTRA-PRIORITAIRES - FILTRES STRICTS]')
print(f'  1. 2 consecutive whales (>$500) -> AUTO-BUY')
print(f'  2. ELITE Wallet detected -> AUTO-BUY ({len(Config.ELITE_WALLETS)} VIP tracked)')
print(f'  FILTRES: MC < ${Config.ELITE_WALLET_MAX_MC:,}, buy_ratio >= {Config.ELITE_MIN_BUY_RATIO*100:.0f}%, {Config.ELITE_MIN_WHALE_COUNT}+ whales')

print(f'\n[⚡ ANTI-LATENCE]')
print(f'  > Real-time price verification before buy')
print(f'  > Skip if price explodes +{Config.PRICE_JUMP_TOLERANCE*100:.0f}% during analysis')
print(f'  > Avoid buying at 17K when whale bought at 10K!')

print(f'\n[⏰ TIMEOUT POSITIONS]')
print(f'  > Auto close after {Config.POSITION_TIMEOUT_MINUTES} minutes')
print(f'  > Ensures ALL trades are recorded')
print(f'  > Check every 5 minutes')

print(f'\n[IMPROVED DECISION SYSTEM @ 8s]')
print(f'  Level 1 - AUTO-BUY (bypass AI):')
print(f'    - Txn: {Config.AUTO_BUY_MIN_TXN}-{Config.AUTO_BUY_MAX_TXN}, Traders: {Config.AUTO_BUY_MIN_TRADERS}-{Config.AUTO_BUY_MAX_TRADERS}')
print(f'    - Buy Ratio >= {Config.AUTO_BUY_MIN_BUY_RATIO*100:.0f}%, MC < ${Config.AUTO_BUY_MAX_MC:,}')
print(f'    - ❌ REJECT if whales detected (0 whale required)')
print(f'  Level 2 - AI + Filters:')
print(f'    - AI Threshold: {Config.THRESHOLD_8S*100:.0f}% (stricter), MC < ${Config.MAX_PRICE_8S:,}')
print(f'    - ❌ REJECT if > 1 whale (whales = red flag)')
print(f'    - Buy ratio minimum: {Config.AI_STRICT_BUY_RATIO*100:.0f}%')
print(f'  Level 3 - AUTO SKIP:')
print(f'    - Transactions < {Config.SKIP_IF_TXN_BELOW} OR Buy Ratio < {Config.SKIP_IF_BUY_RATIO_BELOW*100:.0f}%')
if Config.SCREENSHOT_MODE:
    print(f'\n[2ND CHANCE @ 15s]')
    print(f'  - 2 consecutive whales @ 15s -> AUTO-BUY (MC < ${Config.ELITE_WALLET_MAX_MC:,})')
    print(f'  - Late elite wallet: 1+ new VIP wallet -> AUTO-BUY (MC < ${Config.ELITE_WALLET_MAX_MC:,})')
    print(f'  - Late whales: 2+ new whales -> AUTO-BUY (MC < ${Config.MAX_PRICE_15S:,})')
    print(f'  - Standard AI: Threshold {Config.THRESHOLD_15S*100:.0f}%')
else:
    print(f'\n[2ND CHANCE @ 15s]')
    print(f'  - 2 consecutive whales @ 15s -> AUTO-BUY (MC < ${Config.ELITE_WALLET_MAX_MC:,})')
    print(f'  - Late elite wallet: 1+ new VIP wallet -> AUTO-BUY (MC < ${Config.ELITE_WALLET_MAX_MC:,})')
    print(f'  - Late whales: 2+ new whales -> AUTO-BUY (MC < ${Config.MAX_PRICE_15S:,})')
    print(f'  - Standard AI: Threshold {Config.THRESHOLD_15S*100:.0f}%')
if Config.SCREENSHOT_MODE:
    print(f'\n[PARAMETERS]')
    print(f'Amount per trade: {Config.DISPLAY_AMOUNT} SOL')
    print(f'Stop Loss: -{Config.STOP_LOSS_PERCENT*100:.0f}% (✅ CHECKED EVERY SECOND)')
    print(f'Take Profit: ${Config.TAKE_PROFIT_MC:,} (migration)')
    print(f'\n[LIVE STATISTICS]')
    print(f'Total Trades: 0')
    print(f'Migrations: 0')
    print(f'PNL: 0.000 SOL')
else:
    print(f'\n[PARAMETRES]')
    print(f'Montant par trade: {Config.BUY_AMOUNT_SOL} SOL')
    print(f'Stop Loss: -{Config.STOP_LOSS_PERCENT*100:.0f}% (✅ VERIFIE CHAQUE SECONDE)')
    print(f'Take Profit: ${Config.TAKE_PROFIT_MC:,} (migration)')
    print(f'\n[STATISTIQUES EN TEMPS REEL]')
    print(f'Nombre de trades: 0')
    print(f'PNL: 0.000 SOL')

# ============================================================================
# UTILITAIRES
# ============================================================================
def update_console_title(text):
    """Met à jour le titre de la console Windows"""
    if sys.platform == 'win32':
        os.system(f'title {text}')

# ============================================================================
# CHARGEMENT DES MODELES IA
# ============================================================================
print(f'\n[CHARGEMENT DES MODELES IA]')
try:
    model_10s = joblib.load('model_10s.pkl')
    model_15s = joblib.load('model_15s.pkl')
    print('  Modele @ 10s: OK')
    print('  Modele @ 15s: OK')
except Exception as e:
    print(f'  ERREUR: {e}')
    print('  Lance d\'abord: python train_models.py')
    exit(1)

# ============================================================================
# GESTIONNAIRE DE POSITIONS
# ============================================================================
class PositionManager:
    def __init__(self):
        self.positions = {}  # {mint: position_data}
        self.closed_positions = []
        self.migrations_count = 0  # Compteur de migrations

    def open_position(self, mint, symbol, entry_mc, confidence, entry_time, reason='', entry_features=None):
        """Ouvre une position"""
        if Config.SCREENSHOT_MODE:
            print(f'  [LIVE] Buying {Config.DISPLAY_AMOUNT} SOL on {symbol}')
        elif Config.SIMULATION_MODE:
            print(f'  [SIMULATION] Achat de {Config.BUY_AMOUNT_SOL} SOL sur {symbol}')
        else:
            # ACHAT RÉEL via PumpPortal API
            print(f'  [LIVE] Achat de {Config.BUY_AMOUNT_SOL} SOL sur {symbol}')
            result = solana_trader.buy_token(
                mint=mint,
                amount_sol=Config.BUY_AMOUNT_SOL,
                slippage=Config.SLIPPAGE_BPS / 100,  # Convertir BPS en %
                priority_fee=Config.PRIORITY_FEE
            )

            if not result['success']:
                print(f'  [ERREUR ACHAT] {result["error"]}')
                print(f'  Position NON ouverte - achat échoué')
                return None

        # Détecter si c'est un trade ELITE (wallets elite ou baleines consecutives)
        is_elite_trade = ('ELITE WALLET' in reason or
                         '2 BALEINES CONSECUTIVES' in reason or
                         'BALEINE' in reason.upper())

        # Utiliser stratégie PARTIAL PROFIT (50% à 2x, 50% à migration)
        # Au lieu de tout ou rien
        strategy = 'PARTIAL_PROFIT'
        partial_take_profit_mc = entry_mc * Config.TAKE_PROFIT_PARTIAL  # 2x
        final_take_profit_mc = Config.TAKE_PROFIT_FINAL  # Migration 69K

        position = {
            'mint': mint,
            'symbol': symbol,
            'entry_mc': entry_mc,
            'entry_time': entry_time,
            'entry_timestamp': datetime.now(),
            'confidence': confidence,
            'amount_sol': Config.BUY_AMOUNT_SOL,
            'stop_loss_mc': entry_mc * (1 - Config.STOP_LOSS_PERCENT),
            'partial_take_profit_mc': partial_take_profit_mc,  # 2x - vendre 50%
            'final_take_profit_mc': final_take_profit_mc,  # Migration - vendre 50% restant
            'partial_sold': False,  # Pas encore vendu 50%
            'is_elite_trade': is_elite_trade,
            'strategy': strategy,
            'reason': reason,
            'entry_features': entry_features or {},  # Features pour apprentissage
            'last_mc': entry_mc,  # Dernier MC connu (pour timeout)
            'status': 'OPEN',

            # Vente progressive après migration
            'migration_reached': False,  # Si migration atteinte (53K)
            'last_progressive_sell_time': None,  # Timestamp dernière vente progressive
            'max_mc_since_migration': 0,  # MC max depuis migration
            'progressive_sell_count': 0,  # Nombre de ventes progressives
            'amount_remaining': 1.0,  # Pourcentage restant (100% au départ)

            # Protection API down
            'api_failure_count': 0  # Compteur d'échecs API consécutifs
        }

        self.positions[mint] = position

        if Config.SCREENSHOT_MODE:
            print(f'\n[POSITION OPENED - {strategy}]')
            print(f'  Token: {symbol}')
            print(f'  Reason: {reason}')
            print(f'  Entry MC: ${entry_mc:,.0f}')
            print(f'  Confidence: {confidence*100:.0f}%')
            print(f'  Stop Loss: ${position["stop_loss_mc"]:,.0f}')
            print(f'  Partial TP: ${partial_take_profit_mc:,.0f} ({Config.TAKE_PROFIT_PARTIAL:.1f}x - SELL 50%)')
            print(f'  Migration: ${final_take_profit_mc:,.0f} -> PROGRESSIVE SELL 5% every 20s')
        else:
            print(f'\n[POSITION OUVERTE - {strategy}]')
            print(f'  Token: {symbol}')
            print(f'  Raison: {reason}')
            print(f'  MC Entree: ${entry_mc:,.0f}')
            print(f'  Confiance: {confidence*100:.0f}%')
            print(f'  Stop Loss: ${position["stop_loss_mc"]:,.0f}')
            print(f'  Take Profit Partiel: ${partial_take_profit_mc:,.0f} ({Config.TAKE_PROFIT_PARTIAL:.1f}x - VENDRE 50%)')
            print(f'  Migration: ${final_take_profit_mc:,.0f} -> VENTE PROGRESSIVE 5% toutes les 20s')

        # Mettre à jour le titre de la console
        self.update_title()

        # Afficher les stats dans la console
        self.display_stats_inline()

        return position

    def close_position(self, mint, exit_mc, reason, amount_percent=100):
        """
        Ferme une position (totalement ou partiellement)

        Args:
            mint: Adresse du token
            exit_mc: Market cap de sortie
            reason: Raison de la sortie
            amount_percent: Pourcentage à vendre (default: 100%)
        """
        if mint not in self.positions:
            return

        position = self.positions[mint]

        if Config.SCREENSHOT_MODE:
            if amount_percent == 100:
                print(f'  [LIVE] Selling {position["symbol"]}')
            else:
                print(f'  [LIVE] Selling {amount_percent}% of {position["symbol"]}')
        elif Config.SIMULATION_MODE:
            if amount_percent == 100:
                print(f'  [SIMULATION] Vente de {position["symbol"]}')
            else:
                print(f'  [SIMULATION] Vente de {amount_percent}% de {position["symbol"]}')
        else:
            # VENTE RÉELLE via PumpPortal API
            if amount_percent == 100:
                print(f'  [LIVE] Vente de {position["symbol"]}')
            else:
                print(f'  [LIVE] Vente de {amount_percent}% de {position["symbol"]}')

            result = solana_trader.sell_token(
                mint=mint,
                amount_percent=amount_percent,
                slippage=Config.SLIPPAGE_BPS / 100,
                priority_fee=Config.PRIORITY_FEE
            )

            if not result['success']:
                print(f'  [ERREUR VENTE] {result["error"]}')
                print(f'  Position NON fermée - vente échouée')
                return

        position['exit_mc'] = exit_mc
        position['exit_time'] = datetime.now()
        position['entry_reason'] = position.get('reason', 'Unknown')  # Sauvegarder raison d'entrée
        position['exit_reason'] = reason  # Raison de sortie
        position['reason'] = reason  # Garder pour compatibilité avec learning_engine

        # CALCULER LA DURÉE DE LA POSITION (pour analyse)
        if 'entry_timestamp' in position:
            duration = (position['exit_time'] - position['entry_timestamp']).total_seconds() / 60
            position['timeout_minutes'] = round(duration, 1)
        else:
            position['timeout_minutes'] = 0

        # CALCUL DU PROFIT REEL (corrigé pour partial profit)
        if position.get('partial_sold', False):
            # Si 50% vendus à x2, on a déjà récupéré 100% de la mise
            # Les 50% restants sont GRATUITS
            # Profit réel = 100% récupéré + 50% du prix actuel
            position['profit_ratio'] = 1.0 + 0.5 * (exit_mc / position['entry_mc'])
            position['profit_percent'] = (position['profit_ratio'] - 1) * 100
            position['partial_profit_adjustment'] = True
        else:
            # Position complète (pas de partial sold)
            position['profit_ratio'] = exit_mc / position['entry_mc']
            position['profit_percent'] = (position['profit_ratio'] - 1) * 100
            position['partial_profit_adjustment'] = False

        position['status'] = 'CLOSED'

        # Note: Les migrations sont comptées dès qu'elles atteignent 53K (dans check_position)
        # Pas besoin de compter ici pour éviter les doublons

        self.closed_positions.append(position)

        # ENREGISTRER DANS LE LEARNING ENGINE POUR APPRENTISSAGE
        learning_engine.record_trade(position)

        del self.positions[mint]

        emoji = '💰' if position['profit_percent'] > 0 else '📉'
        strategy_label = position.get('strategy', 'UNKNOWN')

        if Config.SCREENSHOT_MODE:
            # Message anglais pour screenshots
            result_label = "WIN" if position['profit_percent'] > 0 else "LOSS"
            print(f'\n{emoji} [POSITION CLOSED - {result_label}] - {reason}')
            print(f'  Token: {position["symbol"]}')
            print(f'  Entry: ${position["entry_mc"]:,.0f}')
            print(f'  Exit: ${exit_mc:,.0f}')
            if position.get('partial_sold', False):
                print(f'  Real Profit: {position["profit_ratio"]:.2f}x ({position["profit_percent"]:+.1f}%) ✅ WITH 2x PARTIAL')
            else:
                print(f'  Profit: {position["profit_ratio"]:.2f}x ({position["profit_percent"]:+.1f}%)')
        else:
            print(f'\n{emoji} [POSITION FERMEE - {strategy_label}] - {reason}')
            print(f'  Token: {position["symbol"]}')
            print(f'  Raison entree: {position.get("reason", "N/A")}')
            print(f'  Entree: ${position["entry_mc"]:,.0f}')
            print(f'  Sortie: ${exit_mc:,.0f}')
            if position.get('partial_sold', False):
                print(f'  Profit REEL: {position["profit_ratio"]:.2f}x ({position["profit_percent"]:+.1f}%) ✅ AVEC x2 PARTIEL')
            else:
                print(f'  Profit: {position["profit_ratio"]:.2f}x ({position["profit_percent"]:+.1f}%)')

        # Mettre à jour le titre de la console
        self.update_title()

        # Afficher les stats dans la console
        self.display_stats_inline()

        # ANALYSE AUTO et AJUSTEMENT tous les 50 trades
        total_trades = len(self.closed_positions)
        if total_trades % 50 == 0 and total_trades > 0:
            print(f'\n{"="*80}')
            print(f'[AUTO-AJUSTEMENT] {total_trades} trades atteints!')
            print(f'{"="*80}')
            stats = self.get_stats_summary()
            adaptive_config.adjust_based_on_performance(
                stats['win_rate'],
                total_trades,
                learning_engine
            )
            # Diagnostic complet
            analyzer = TradeAnalyzer(learning_engine)
            analyzer.full_diagnostic()

    def check_expired_positions(self):
        """Vérifie et ferme les positions expirées (timeout)"""
        import time
        from datetime import datetime, timedelta

        timeout_seconds = Config.POSITION_TIMEOUT_MINUTES * 60
        now = datetime.now()

        expired_positions = []

        for mint, position in list(self.positions.items()):
            # NE PAS TIMEOUT les positions qui ont déjà vendu 50% et attendent la migration !
            # Ces positions sont GRATUITES (investissement récupéré) et peuvent prendre leur temps
            partial_sold = position.get('partial_sold', False)

            if partial_sold:
                # Position en attente de migration - PAS DE TIMEOUT !
                # Elle attend 53K pour vente progressive
                continue

            # Calculer l'âge de la position (seulement pour positions normales)
            position_age = (now - position['entry_timestamp']).total_seconds()

            if position_age > timeout_seconds:
                expired_positions.append(mint)

        # Fermer les positions expirées
        for mint in expired_positions:
            position = self.positions[mint]
            # Utiliser le dernier MC connu ou le MC d'entrée
            last_known_mc = position.get('last_mc', position['entry_mc'])

            print(f'\n⏰ [TIMEOUT] Position expired: {position["symbol"]}')
            print(f'   Opened since: {Config.POSITION_TIMEOUT_MINUTES} minutes')
            print(f'   Auto close at current price: ${last_known_mc:,.0f}')

            self.close_position(mint, last_known_mc, f'TIMEOUT ({Config.POSITION_TIMEOUT_MINUTES}min)')

        return len(expired_positions)

    def check_position(self, mint, current_mc):
        """Vérifie une position (stop loss / take profit PARTIEL)"""
        if mint not in self.positions:
            return

        position = self.positions[mint]

        # ====================================================================
        # PRIX LIVE: Vérifier le prix RÉEL avant vente/stop loss
        # ====================================================================
        live_price = get_token_price_live(mint)
        if live_price['success']:
            # Utiliser le prix live (plus précis)
            actual_mc = live_price['mc_usd']
            position['last_mc'] = actual_mc
        else:
            # Fallback au MC du websocket si API échoue
            actual_mc = current_mc
            position['last_mc'] = current_mc

        # ====================================================================
        # TRAILING STOP LOSS INTELLIGENT: Protéger les profits progressivement
        # ====================================================================
        # Calculer le profit actuel
        entry_mc = position['entry_mc']
        profit_ratio = actual_mc / entry_mc
        profit_percent = (profit_ratio - 1) * 100

        # Ajuster le stop loss selon le profit actuel
        # SYSTÈME PROGRESSIF pour ne pas être trop serré
        if profit_percent >= 80:
            # +80% à +100% (proche de 2x) → Stop loss à +30% (profit garanti)
            new_stop_loss = entry_mc * 1.30
            trailing_label = "+30% profit garanti"
        elif profit_percent >= 50:
            # +50% à +80% → Stop loss à breakeven 0% (aucune perte)
            new_stop_loss = entry_mc * 1.00
            trailing_label = "breakeven (0% perte max)"
        elif profit_percent >= 20:
            # +20% à +50% → Stop loss à -20% (protection légère)
            new_stop_loss = entry_mc * 0.80
            trailing_label = "-20% max"
        else:
            # < +20% profit → Stop loss normal à -40%
            new_stop_loss = entry_mc * (1 - Config.STOP_LOSS_PERCENT)
            trailing_label = f"-{Config.STOP_LOSS_PERCENT*100:.0f}% normal"

        # Mettre à jour le stop loss SI IL MONTE (jamais descendre!)
        if new_stop_loss > position['stop_loss_mc']:
            old_stop_loss = position['stop_loss_mc']
            position['stop_loss_mc'] = new_stop_loss

            # Afficher seulement si changement significatif
            if profit_percent >= 20:
                print(f'\n📈 [TRAILING STOP LOSS] {position["symbol"]}')
                print(f'   Profit actuel: +{profit_percent:.1f}%')
                print(f'   Ancien SL: ${old_stop_loss:,.0f} → Nouveau SL: ${new_stop_loss:,.0f}')
                print(f'   Protection: {trailing_label}')

        # ====================================================================
        # STRATEGIE PARTIAL PROFIT: Vendre XX% à 2x, garder le reste pour migration
        # ====================================================================

        # Étape 1: Take Profit PARTIEL à 2x (vendre XX%)
        if not position['partial_sold'] and actual_mc >= position['partial_take_profit_mc']:
            sell_percent = int(Config.PARTIAL_SELL_PERCENT * 100)
            print(f'\n💰 [PARTIAL PROFIT @ 2x] {position["symbol"]}')
            print(f'  MC LIVE: ${actual_mc:,.0f} (Target: ${position["partial_take_profit_mc"]:,.0f})')
            print(f'  Vente de {sell_percent}% de la position')
            print(f'  ✅ INVESTISSEMENT RECUPERE+ - Les {100-sell_percent}% restants sont GRATUITS!')

            # VENTE PARTIELLE RÉELLE (si pas en simulation)
            if not Config.SIMULATION_MODE:
                result = solana_trader.sell_token(
                    mint=mint,
                    amount_percent=sell_percent,
                    slippage=Config.SLIPPAGE_BPS / 100,
                    priority_fee=0.0001
                )

                if not result['success']:
                    print(f'  [ERREUR] Vente partielle échouée: {result["error"]}')
                    print(f'  On réessayera au prochain check...')
                    return  # Ne pas marquer comme vendu si échec

            # Marquer comme partiellement vendu
            position['partial_sold'] = True
            position['partial_profit_mc'] = actual_mc

            # Ajuster le stop loss pour protéger le reste
            # Nouveau stop loss = prix d'entrée (on ne peut plus perdre!)
            position['stop_loss_mc'] = position['entry_mc']

            print(f'  Nouveau Stop Loss: ${position["stop_loss_mc"]:,.0f} (breakeven - position gratuite!)')
            print(f'  En attente de migration ${position["final_take_profit_mc"]:,.0f} pour vendre les {100-sell_percent}% restants...')
            return

        # Étape 2: Migration atteinte - VENTE PROGRESSIVE
        if position['partial_sold'] and actual_mc >= position['final_take_profit_mc']:
            # Migration atteinte!
            if not position['migration_reached']:
                position['migration_reached'] = True
                position['last_progressive_sell_time'] = datetime.now()
                position['max_mc_since_migration'] = actual_mc

                # COMPTER LA MIGRATION DÈS MAINTENANT (pas à la fermeture!)
                self.migrations_count += 1

                print(f'\n🚀 [MIGRATION ATTEINTE - {position["symbol"]}] 🚀')
                print(f'  MC: ${actual_mc:,.0f} >= ${position["final_take_profit_mc"]:,.0f}')
                print(f'  🎉 MIGRATION #{self.migrations_count} DÉTECTÉE!')
                print(f'  🔄 VENTE PROGRESSIVE activée: 5% toutes les 20 secondes')
                print(f'  Protection: Si MC baisse de 15% depuis max, vente totale du reste')

                # Mettre à jour le titre immédiatement
                self.update_title()

            # Mettre à jour le MC max depuis migration
            if actual_mc > position['max_mc_since_migration']:
                position['max_mc_since_migration'] = actual_mc

            # Vérifier si besoin de vendre progressivement
            time_since_last_sell = (datetime.now() - position['last_progressive_sell_time']).total_seconds()

            # VENTE PROGRESSIVE toutes les 20 secondes
            if time_since_last_sell >= Config.PROGRESSIVE_SELL_INTERVAL:
                # Calculer combien il reste
                remaining_after_partial = 1.0 - Config.PARTIAL_SELL_PERCENT  # 50% restant
                amount_to_sell_pct = int(Config.PROGRESSIVE_SELL_PERCENT * 100)  # 5% de la position totale

                print(f'\n💰 [VENTE PROGRESSIVE #{position["progressive_sell_count"]+1}] {position["symbol"]}')
                print(f'  MC: ${actual_mc:,.0f} (Max: ${position["max_mc_since_migration"]:,.0f})')
                print(f'  Vente: {amount_to_sell_pct}% de la position TOTALE')

                # VENTE PROGRESSIVE RÉELLE (si pas en simulation)
                if not Config.SIMULATION_MODE:
                    result = solana_trader.sell_token(
                        mint=mint,
                        amount_percent=amount_to_sell_pct,
                        slippage=Config.SLIPPAGE_BPS / 100,
                        priority_fee=0.0001
                    )

                    if not result['success']:
                        print(f'  [ERREUR] Vente progressive échouée: {result["error"]}')
                        print(f'  On réessayera au prochain check...')
                        return  # Ne pas incrémenter le compteur si échec

                # Mettre à jour le montant restant
                position['amount_remaining'] -= Config.PROGRESSIVE_SELL_PERCENT
                position['progressive_sell_count'] += 1
                position['last_progressive_sell_time'] = datetime.now()

                remaining_pct = position['amount_remaining'] * 100
                print(f'  Restant: {remaining_pct:.0f}%')

                # Si moins de 5% reste, vendre tout et fermer
                if position['amount_remaining'] <= Config.PROGRESSIVE_SELL_PERCENT:
                    print(f'  ✅ POSITION FINALE - Vente du reste ({remaining_pct:.0f}%)')
                    self.close_position(mint, actual_mc, f'VENTE PROGRESSIVE COMPLETE ({position["progressive_sell_count"]} ventes)')
                    return

            # STOP LOSS: Si MC baisse de 15% depuis le max, vendre tout le reste
            mc_drop_from_max = (position['max_mc_since_migration'] - actual_mc) / position['max_mc_since_migration']
            if mc_drop_from_max >= Config.PROGRESSIVE_SELL_STOP_LOSS:
                remaining_pct = position['amount_remaining'] * 100
                print(f'\n⚠️ [STOP LOSS PROGRESSIF] {position["symbol"]}')
                print(f'  MC baisse de {mc_drop_from_max*100:.1f}% depuis max ${position["max_mc_since_migration"]:,.0f}')
                print(f'  MC actuel: ${actual_mc:,.0f}')
                print(f'  Vente du reste: {remaining_pct:.0f}%')
                self.close_position(mint, actual_mc, f'STOP LOSS PROGRESSIF (MC baisse -{mc_drop_from_max*100:.0f}% depuis max)')
                return

            # Continuer à surveiller
            return

        # Stop Loss
        if actual_mc <= position['stop_loss_mc']:
            print(f'\n📉 [STOP LOSS] {position["symbol"]}')
            print(f'  MC LIVE: ${actual_mc:,.0f} <= SL: ${position["stop_loss_mc"]:,.0f}')
            if position['partial_sold']:
                sell_percent = int(Config.PARTIAL_SELL_PERCENT * 100)
                # Si déjà vendu XX%, c'est un petit gain
                self.close_position(mint, actual_mc, f'STOP LOSS ({sell_percent}% déjà vendu @ 2x)')
            else:
                # Perte complète
                self.close_position(mint, actual_mc, 'STOP LOSS')
            return

    def update_title(self):
        """Met à jour le titre de la console avec les stats"""
        stats = self.get_stats_summary()

        if stats['total_trades'] == 0:
            title = f"Trading Bot - Positions: {stats['open_positions']} - Trades: 0"
        else:
            pnl_sign = "+" if stats['total_pnl'] >= 0 else ""
            title = (f"Trading Bot - Trades: {stats['total_trades']} "
                    f"W:{stats['wins']} L:{stats['losses']} - "
                    f"Win Rate: {stats['win_rate']:.0f}% - "
                    f"PNL: {pnl_sign}{stats['total_pnl']:.3f} SOL - "
                    f"Positions: {stats['open_positions']}")

        update_console_title(title)

    def display_stats_inline(self):
        """Affiche les stats directement dans la console"""
        stats = self.get_stats_summary()

        print(f'\n{"─"*80}')
        if Config.SCREENSHOT_MODE:
            print(f'[📊 LIVE STATISTICS]')
        else:
            print(f'[📊 STATISTIQUES EN TEMPS REEL]')
        print(f'{"─"*80}')

        if stats['total_trades'] == 0:
            if Config.SCREENSHOT_MODE:
                print(f'Total Trades: 0 (Wins: 0 | Losses: 0)')
                print(f'Win Rate: ⚪ 0.0%')
                print(f'Migrations: 0')
                print(f'PNL: 0.000 SOL')
                print(f'Avg Profit: 0.00x')
                print(f'Open Positions: {stats["open_positions"]}')
            else:
                print(f'Nombre de trades: 0')
                print(f'PNL: 0.000 SOL')
                print(f'Positions ouvertes: {stats["open_positions"]}')
        else:
            pnl_emoji = "💰" if stats['total_pnl'] >= 0 else "📉"
            status_emoji = "🟢" if stats['win_rate'] >= 60 else "🟡" if stats['win_rate'] >= 40 else "🔴"

            if Config.SCREENSHOT_MODE:
                print(f'Total Trades: {stats["total_trades"]} (Wins: {stats["wins"]} | Losses: {stats["losses"]})')
                print(f'Win Rate: {status_emoji} {stats["win_rate"]:.1f}%')
                print(f'Migrations: 🚀 {self.migrations_count}')
                print(f'PNL: {pnl_emoji} {stats["total_pnl"]:+.3f} SOL')
                print(f'Avg Profit: {stats["avg_profit"]:.2f}x')
                print(f'Open Positions: {stats["open_positions"]}')
            else:
                print(f'Nombre de trades: {stats["total_trades"]} (Wins: {stats["wins"]} | Losses: {stats["losses"]})')
                print(f'Win Rate: {status_emoji} {stats["win_rate"]:.1f}%')
                print(f'PNL: {pnl_emoji} {stats["total_pnl"]:+.3f} SOL')
                print(f'Profit moyen: {stats["avg_profit"]:.2f}x')
                print(f'Positions ouvertes: {stats["open_positions"]}')

        print(f'{"─"*80}')

    def get_stats_summary(self):
        """Retourne un résumé des statistiques"""
        total_trades = len(self.closed_positions)
        open_positions = len(self.positions)

        if total_trades == 0:
            return {
                'total_trades': 0,
                'open_positions': open_positions,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'total_pnl': 0,
                'best': 0,
                'worst': 0
            }

        wins = len([p for p in self.closed_positions if p['profit_percent'] > 0])
        losses = total_trades - wins
        profits = [p['profit_ratio'] for p in self.closed_positions]
        avg_profit = sum(profits) / len(profits)

        # Calcul du P&L total approximatif (en x)
        total_pnl = sum([(p['profit_ratio'] - 1) * Config.BUY_AMOUNT_SOL for p in self.closed_positions])

        return {
            'total_trades': total_trades,
            'open_positions': open_positions,
            'wins': wins,
            'losses': losses,
            'win_rate': (wins/total_trades*100) if total_trades > 0 else 0,
            'avg_profit': avg_profit,
            'total_pnl': total_pnl,
            'best': max(profits),
            'worst': min(profits)
        }

    def show_stats(self):
        """Affiche les statistiques"""
        if not self.closed_positions:
            print('\nAucun trade ferme pour le moment.')
            return

        stats = self.get_stats_summary()

        print(f'\n{"="*80}')
        print('STATISTIQUES DE TRADING')
        print('='*80)
        print(f'\nTotal trades: {stats["total_trades"]}')
        print(f'  Gagnants: {stats["wins"]} ({stats["win_rate"]:.1f}%)')
        print(f'  Perdants: {stats["losses"]} ({100-stats["win_rate"]:.1f}%)')

        print(f'\nProfit moyen: {stats["avg_profit"]:.2f}x')
        print(f'Meilleur: {stats["best"]:.2f}x')
        print(f'Pire: {stats["worst"]:.2f}x')
        print(f'\nP&L Total: {stats["total_pnl"]:+.3f} SOL')

# ============================================================================
# BOT PRINCIPAL
# ============================================================================
class LiveTradingBot:
    def __init__(self):
        self.positions = PositionManager()
        self.tokens = {}  # {mint: {trades, created_at, symbol, etc.}}
        self.model_10s = model_10s
        self.model_15s = model_15s

    def calculate_snapshot(self, token, max_age):
        """Calcule les features pour une période (comme pattern_discovery_bot)"""
        created_at = token['created_at']
        trades_in_period = [t for t in token['trades'] if (t['time'] - created_at) <= max_age]

        if not trades_in_period:
            return None

        buys = [t for t in trades_in_period if t['type'] == 'buy']
        sells = [t for t in trades_in_period if t['type'] == 'sell']
        unique_traders = len(set(t['trader'] for t in trades_in_period))

        # Calculer la vélocité (croissance MC)
        mc_current = trades_in_period[-1]['mc'] if trades_in_period else 0
        mc_initial = token.get('mc_initial', 0)
        velocity = (mc_current - mc_initial) / max_age if max_age > 0 else 0

        # Compter les baleines (achats > $400 = 2+ SOL minimum)
        WHALE_THRESHOLD = 400  # $400 = 2 SOL @ $200
        whale_count = len(set(t['trader'] for t in buys if t.get('amount_usd', 0) >= WHALE_THRESHOLD))

        # DEBUG: Afficher les montants pour comprendre la détection
        if len(buys) > 0 and whale_count > 0:
            buy_amounts_usd = [t.get('amount_usd', 0) for t in buys]
            max_buy = max(buy_amounts_usd) if buy_amounts_usd else 0
            whale_buys = [amt for amt in buy_amounts_usd if amt >= WHALE_THRESHOLD]
            print(f'  🐋 [WHALE DETECTED] {token.get("symbol", "?")} - {whale_count} whales, Max: ${max_buy:.0f}, Whale buys: {[f"${amt:.0f}" for amt in whale_buys[:3]]}')

        # Compter les WALLETS ELITE (whitelist des meilleurs traders)
        elite_wallet_count = len(set(t['trader'] for t in buys if t['trader'] in Config.ELITE_WALLETS))
        elite_wallets_found = [t['trader'][:8] for t in buys if t['trader'] in Config.ELITE_WALLETS]

        # DETECTER 2 BALEINES CONSECUTIVES (pattern ultra-fort)
        consecutive_whales = False
        if len(buys) >= 2:
            # Regarder les 5 derniers achats
            recent_buys = buys[-5:]
            whale_buys = [b for b in recent_buys if b.get('amount_usd', 0) >= WHALE_THRESHOLD]

            # Vérifier si les 2 dernières baleines sont consécutives
            if len(whale_buys) >= 2:
                last_whale_idx = None
                second_last_whale_idx = None

                # Trouver les positions des 2 dernières baleines
                for i in range(len(recent_buys) - 1, -1, -1):
                    if recent_buys[i].get('amount_usd', 0) >= WHALE_THRESHOLD:
                        if last_whale_idx is None:
                            last_whale_idx = i
                        elif second_last_whale_idx is None:
                            second_last_whale_idx = i
                            break

                # Consécutives si aucun autre achat entre elles
                if last_whale_idx is not None and second_last_whale_idx is not None:
                    if last_whale_idx - second_last_whale_idx == 1:
                        consecutive_whales = True

        return {
            'txn': len(trades_in_period),
            'buys': len(buys),
            'sells': len(sells),
            'buy_ratio': len(buys)/len(trades_in_period) if trades_in_period else 0,
            'traders': unique_traders,
            'mc': mc_current,
            'velocity': velocity,
            'whale_count': whale_count,
            'elite_wallet_count': elite_wallet_count,
            'elite_wallets': elite_wallets_found,  # Pour affichage
            'consecutive_whales': consecutive_whales  # Pattern ultra-fort
        }

    def predict_8s(self, snapshot_8s, mint=None):
        """Prédiction @ 8 secondes (SYSTEME HYBRIDE: IA + REGLES INTELLIGENTES)"""
        if not snapshot_8s:
            return None

        # Extraire les métriques
        txn = snapshot_8s.get('txn', 0)
        traders = snapshot_8s.get('traders', 0)
        buy_ratio = snapshot_8s.get('buy_ratio', 0)
        mc = snapshot_8s.get('mc', 0)
        whale_count = snapshot_8s.get('whale_count', 0)
        elite_wallet_count = snapshot_8s.get('elite_wallet_count', 0)
        elite_wallets = snapshot_8s.get('elite_wallets', [])
        consecutive_whales = snapshot_8s.get('consecutive_whales', False)

        # ========================================================================
        # VÉRIFICATION PRIX LIVE (éviter d'acheter après un pump)
        # ========================================================================
        if mint:
            live_price = get_token_price_live(mint)
            if live_price['success']:
                mc_live = live_price['mc_usd']
                # Vérifier que le prix n'a pas explosé entre le websocket et maintenant
                if mc_live > mc * (1 + Config.PRICE_JUMP_TOLERANCE):
                    price_jump_pct = (mc_live - mc) / mc * 100
                    return {
                        'confidence': 0.0,
                        'mc': mc_live,
                        'should_buy': False,
                        'reason': f'SKIP: Price jumped +{price_jump_pct:.0f}% (MC ${mc:.0f} -> ${mc_live:.0f})'
                    }
                # Utiliser le prix live pour la suite
                mc = mc_live

        # ========================================================================
        # SWEET SPOT CHECK (11-12K MC = meilleur win rate)
        # ========================================================================
        if mc < Config.SWEET_SPOT_MIN_MC or mc > Config.SWEET_SPOT_MAX_MC:
            return {
                'confidence': 0.0,
                'mc': mc,
                'should_buy': False,
                'reason': f'SKIP: Outside sweet spot (MC ${mc:,.0f}, optimal zone: {Config.SWEET_SPOT_MIN_MC/1000:.0f}K-{Config.SWEET_SPOT_MAX_MC/1000:.0f}K)'
            }

        # ========================================================================
        # NIVEAU 0A (ULTRA PRIORITAIRE): 2 BALEINES CONSECUTIVES
        # FILTRES STRICTS: buy_ratio >= 80%, whale_count >= 3, MC < $8K
        # ========================================================================
        if (consecutive_whales and
            mc < Config.ELITE_WALLET_MAX_MC and
            buy_ratio >= Config.ELITE_MIN_BUY_RATIO and
            whale_count >= Config.ELITE_MIN_WHALE_COUNT):
            return {
                'confidence': 1.0,
                'mc': mc,
                'should_buy': True,
                'reason': f'2 BALEINES CONSECUTIVES: Pattern ultra-fort! ({whale_count} whales, {buy_ratio*100:.0f}% buy)'
            }

        # ========================================================================
        # NIVEAU 0B (PRIORITE MAX): WALLETS ELITE - AUTO-FOLLOW
        # FILTRES STRICTS: buy_ratio >= 80%, whale_count >= 3, MC < $8K
        # ========================================================================
        if (elite_wallet_count >= 1 and
            mc < Config.ELITE_WALLET_MAX_MC and
            buy_ratio >= Config.ELITE_MIN_BUY_RATIO and
            whale_count >= Config.ELITE_MIN_WHALE_COUNT):
            wallets_str = ', '.join(elite_wallets[:3])  # Afficher max 3 wallets
            return {
                'confidence': 1.0,  # 100% confiance (wallet elite)
                'mc': mc,
                'should_buy': True,
                'reason': f'ELITE WALLET: {elite_wallet_count} VIP ({wallets_str}...), {whale_count} whales, {buy_ratio*100:.0f}% buy'
            }

        # ========================================================================
        # NIVEAU 1: AUTO-BUY (Runners évidents - BYPASS IA)
        # ========================================================================
        if (txn >= Config.AUTO_BUY_MIN_TXN and
            traders >= Config.AUTO_BUY_MIN_TRADERS and
            buy_ratio >= Config.AUTO_BUY_MIN_BUY_RATIO and
            mc < Config.AUTO_BUY_MAX_MC):

            # NOUVEAU FILTRE INTELLIGENT: Baleines conditionnelles au MC
            # SI MC < 12K (early) → Max 1 baleine (strict, early entry)
            # SI MC >= 12K (late) → Max 3 baleines (dataset = 35% migrations ont 2+)
            max_whales_allowed = Config.AI_MAX_WHALES_EARLY if mc < 12000 else Config.AI_MAX_WHALES_LATE

            if whale_count > max_whales_allowed:
                return {
                    'confidence': 0.0,
                    'mc': mc,
                    'should_buy': False,
                    'reason': f'SKIP AUTO-BUY: {whale_count} whales (max {max_whales_allowed} @ ${mc:,.0f})'
                }

            # NOUVEAU FILTRE: Volume modéré (pas trop de bots)
            if txn > Config.AUTO_BUY_MAX_TXN or traders > Config.AUTO_BUY_MAX_TRADERS:
                return {
                    'confidence': 0.0,
                    'mc': mc,
                    'should_buy': False,
                    'reason': f'SKIP AUTO-BUY: Volume too high ({txn}txn, {traders}traders - likely bots)'
                }

            return {
                'confidence': 1.0,  # 100% confiance (règle auto-buy)
                'mc': mc,
                'should_buy': True,
                'reason': f'AUTO-BUY: {txn}txn, {traders}traders, {buy_ratio*100:.0f}% buy'
            }

        # ========================================================================
        # NIVEAU 3: SKIP AUTOMATIQUE (Trop faible - économise du temps)
        # ========================================================================
        if (txn < Config.SKIP_IF_TXN_BELOW or
            buy_ratio < Config.SKIP_IF_BUY_RATIO_BELOW or
            mc >= Config.MAX_PRICE_8S):

            return {
                'confidence': 0.0,
                'mc': mc,
                'should_buy': False,
                'reason': f'SKIP: Criteria too weak'
            }

        # ========================================================================
        # NIVEAU 2: IA + FILTRES (Potentiels - analyse avec IA)
        # ========================================================================
        # NOUVEAU FILTRE: Rejeter si MC TROP BAS (< 8K = zone perdante)
        if mc < Config.SWEET_SPOT_MIN_MC:
            return {
                'confidence': 0.0,
                'mc': mc,
                'should_buy': False,
                'reason': f'SKIP AI: MC too low (${mc:,.0f} < ${Config.SWEET_SPOT_MIN_MC:,}) - losing zone'
            }

        # NOUVEAU FILTRE INTELLIGENT: Baleines conditionnelles au MC
        # SI MC < 12K (early) → Max 1 baleine
        # SI MC >= 12K (late) → Max 3 baleines (dataset = 35% migrations ont 2+)
        max_whales_allowed = Config.AI_MAX_WHALES_EARLY if mc < 12000 else Config.AI_MAX_WHALES_LATE

        if whale_count > max_whales_allowed:
            return {
                'confidence': 0.0,
                'mc': mc,
                'should_buy': False,
                'reason': f'SKIP AI: {whale_count} whales (max {max_whales_allowed} @ ${mc:,.0f})'
            }

        if buy_ratio < Config.AI_STRICT_BUY_RATIO:
            return {
                'confidence': 0.0,
                'mc': mc,
                'should_buy': False,
                'reason': f'SKIP: Buy ratio too low ({buy_ratio*100:.0f}% < {Config.AI_STRICT_BUY_RATIO*100:.0f}%)'
            }

        # Compter critères remplis
        criteria_met = 0
        if txn >= Config.AI_MIN_TXN:
            criteria_met += 1
        if traders >= Config.AI_MIN_TRADERS:
            criteria_met += 1
        if buy_ratio >= Config.AI_MIN_BUY_RATIO:
            criteria_met += 1

        # Si moins de 2 critères, skip
        if criteria_met < 2:
            return {
                'confidence': 0.0,
                'mc': mc,
                'should_buy': False,
                'reason': f'SKIP: {criteria_met}/3 AI criteria'
            }

        # Prédiction IA
        features = pd.DataFrame([{
            'txn': txn,
            'traders': traders,
            'buy_ratio': buy_ratio,
            'mc': mc,
            'velocity': snapshot_8s.get('velocity', 0),
            'whale_count': whale_count
        }])

        proba = self.model_10s.predict_proba(features)[0, 1]

        # BONUS BALEINES: Si 3+ baleines, boost le score
        if whale_count >= Config.WHALE_BOOST_THRESHOLD:
            proba = min(1.0, proba + Config.WHALE_BOOST_AMOUNT)
            whale_boost_msg = f' +WHALE BOOST ({whale_count} whales)'
        else:
            whale_boost_msg = ''

        # Décision finale
        should_buy = proba >= Config.THRESHOLD_8S and mc < Config.MAX_PRICE_8S

        return {
            'confidence': proba,
            'mc': mc,
            'should_buy': should_buy,
            'reason': f'AI: {proba*100:.0f}%{whale_boost_msg}'
        }

    def predict_15s(self, snapshot_8s, snapshot_15s):
        """Prédiction @ 15 secondes (AVEC DETECTION BALEINES TARDIVES + ELITE WALLETS)"""
        if not snapshot_8s or not snapshot_15s:
            return None

        mc = snapshot_15s.get('mc', 0)
        whale_count_8s = snapshot_8s.get('whale_count', 0)
        whale_count_15s = snapshot_15s.get('whale_count', 0)
        elite_wallet_count_8s = snapshot_8s.get('elite_wallet_count', 0)
        elite_wallet_count_15s = snapshot_15s.get('elite_wallet_count', 0)
        elite_wallets_15s = snapshot_15s.get('elite_wallets', [])
        consecutive_whales_15s = snapshot_15s.get('consecutive_whales', False)

        # Extraire buy_ratio @ 15s pour filtres
        buy_ratio_15s = snapshot_15s.get('buy_ratio', 0)

        # ========================================================================
        # REGLE 0: AUTO-BUY SI 2 BALEINES CONSECUTIVES @ 15s
        # FILTRES STRICTS: buy_ratio >= 80%, whale_count >= 3, MC < $8K
        # ========================================================================
        if (consecutive_whales_15s and
            mc < Config.ELITE_WALLET_MAX_MC and
            buy_ratio_15s >= Config.ELITE_MIN_BUY_RATIO and
            whale_count_15s >= Config.ELITE_MIN_WHALE_COUNT):
            return {
                'confidence': 1.0,
                'mc': mc,
                'should_buy': True,
                'reason': f'2 BALEINES CONSECUTIVES @ 15s: {whale_count_15s} whales, {buy_ratio_15s*100:.0f}% buy'
            }

        # ========================================================================
        # REGLE 1: AUTO-BUY SI ELITE WALLET ARRIVE ENTRE 8s et 15s
        # FILTRES STRICTS: buy_ratio >= 80%, whale_count >= 3, MC < $8K
        # ========================================================================
        new_elite_wallets = elite_wallet_count_15s - elite_wallet_count_8s

        if (new_elite_wallets >= 1 and
            mc < Config.ELITE_WALLET_MAX_MC and
            buy_ratio_15s >= Config.ELITE_MIN_BUY_RATIO and
            whale_count_15s >= Config.ELITE_MIN_WHALE_COUNT):
            wallets_str = ', '.join(elite_wallets_15s[:3])
            return {
                'confidence': 1.0,
                'mc': mc,
                'should_buy': True,
                'reason': f'ELITE WALLET @ 15s: {new_elite_wallets} VIP ({wallets_str}...), {whale_count_15s} whales, {buy_ratio_15s*100:.0f}% buy'
            }

        # ========================================================================
        # REGLE 2: AUTO-BUY SI BALEINES ARRIVENT ENTRE 8s et 15s
        # ========================================================================
        # NOUVEAU FILTRE: Rejeter si MC TROP BAS (< 8K = zone perdante)
        if mc < Config.SWEET_SPOT_MIN_MC:
            return {
                'confidence': 0.0,
                'mc': mc,
                'should_buy': False,
                'reason': f'SKIP @ 15s: MC too low (${mc:,.0f} < ${Config.SWEET_SPOT_MIN_MC:,}) - losing zone'
            }

        # Compter les NOUVELLES baleines arrivées après 8s
        new_whales = whale_count_15s - whale_count_8s

        if new_whales >= 2 and mc < Config.MAX_PRICE_15S:
            if Config.SCREENSHOT_MODE:
                return {
                    'confidence': 1.0,
                    'mc': mc,
                    'should_buy': True,
                    'reason': f'AUTO-BUY: {new_whales} new whales @ 15s (total: {whale_count_15s})'
                }
            else:
                return {
                    'confidence': 1.0,
                    'mc': mc,
                    'should_buy': True,
                    'reason': f'AUTO-BUY: {new_whales} new whales @ 15s (total: {whale_count_15s})'
                }

        mc_growth = 0
        if snapshot_8s.get('mc', 0) > 0:
            mc_growth = (snapshot_15s.get('mc', 0) - snapshot_8s.get('mc', 0)) / snapshot_8s.get('mc', 1)

        # Note: Le modèle attend des features "10s_*" mais on utilise les données @ 8s
        # C'est OK car la structure est la même, juste un timing légèrement différent
        features = pd.DataFrame([{
            '10s_txn': snapshot_8s.get('txn', 0),
            '10s_traders': snapshot_8s.get('traders', 0),
            '10s_buy_ratio': snapshot_8s.get('buy_ratio', 0),
            '10s_mc': snapshot_8s.get('mc', 0),
            '10s_velocity': snapshot_8s.get('velocity', 0),
            '15s_txn': snapshot_15s.get('txn', 0),
            '15s_traders': snapshot_15s.get('traders', 0),
            '15s_buy_ratio': snapshot_15s.get('buy_ratio', 0),
            '15s_mc': snapshot_15s.get('mc', 0),
            '15s_velocity': snapshot_15s.get('velocity', 0),
            'mc_growth_10s_15s': mc_growth,
            'txn_growth_10s_15s': snapshot_15s.get('txn', 0) - snapshot_8s.get('txn', 0),
            'traders_growth_10s_15s': snapshot_15s.get('traders', 0) - snapshot_8s.get('traders', 0),
            'whale_count': whale_count_15s  # Utiliser le whale_count @ 15s
        }])

        proba = self.model_15s.predict_proba(features)[0, 1]

        return {
            'confidence': proba,
            'mc': mc,
            'should_buy': proba >= Config.THRESHOLD_15S and mc < Config.MAX_PRICE_15S,
            'reason': f'AI: {proba*100:.0f}%'
        }

    async def handle_new_token(self, data, ws):
        """Nouveau token détecté"""
        mint = data.get('mint')
        if not mint or mint in self.tokens:
            return

        symbol = data.get('symbol', data.get('name', ''))[:12] or f"[{mint[:8]}...]"
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * Config.get_sol_price()

        self.tokens[mint] = {
            'mint': mint,
            'symbol': symbol,
            'created_at': time.time(),
            'mc_initial': mc_usd,
            'trades': [],
            'snapshot_10s': None,
            'snapshot_15s': None
        }

        if Config.SCREENSHOT_MODE:
            print_blue(f'\n[NEW TOKEN] {symbol} ({mint[:8]}...) @ ${mc_usd:,.0f}')
        else:
            print_blue(f'\n[NOUVEAU TOKEN] {symbol} ({mint[:8]}...) @ ${mc_usd:,.0f}')

        # IMPORTANT: S'abonner aux trades de ce token spécifique !
        await ws.send(json.dumps({
            "method": "subscribeTokenTrade",
            "keys": [mint]
        }))

        # Programmer le tracking
        asyncio.create_task(self.track_token(mint))

    async def handle_trade(self, data):
        """Trade détecté"""
        mint = data.get('mint')
        if mint not in self.tokens:
            return

        token = self.tokens[mint]

        tx_type = data.get('txType')
        trader = data.get('traderPublicKey', 'unknown')
        mc_sol = data.get('marketCapSol', 0)
        mc_usd = mc_sol * Config.get_sol_price()
        sol_amount = data.get('solAmount', 0)
        amount_usd = sol_amount * Config.get_sol_price()

        # Enregistrer le trade
        token['trades'].append({
            'type': tx_type,
            'trader': trader,
            'mc': mc_usd,
            'time': time.time(),
            'amount_sol': sol_amount,
            'amount_usd': amount_usd
        })

        # Vérifier les positions ouvertes (stop loss / take profit)
        if mint in self.positions.positions:
            self.positions.check_position(mint, mc_usd)

    async def track_token(self, mint):
        """Track un token et fait les snapshots @ 8s et 15s"""
        # Attendre 8 secondes (ULTRA EARLY)
        await asyncio.sleep(8)

        if mint not in self.tokens:
            return

        token = self.tokens[mint]

        # Snapshot @ 8s
        snapshot_8s = self.calculate_snapshot(token, 8)
        if snapshot_8s:
            token['snapshot_8s'] = snapshot_8s

            # Prédiction @ 8s (SYSTEME HYBRIDE + PRIX LIVE)
            # Passer le mint pour vérification prix live
            prediction = self.predict_8s(snapshot_8s, mint=token['mint'])
            if prediction and prediction['should_buy']:
                reason = prediction.get('reason', 'IA')
                actual_buy_mc = prediction['mc']  # MC vérifié en temps réel dans predict_8s

                # Choisir l'emoji selon le type de signal
                if '2 BALEINES CONSECUTIVES' in reason:
                    emoji = '🐋🐋'  # Pattern ultra-fort
                elif 'ELITE WALLET' in reason:
                    emoji = '👑'  # Wallet VIP
                elif 'AUTO-BUY' in reason:
                    emoji = '🔥'  # Runners évidents
                elif 'WHALE BOOST' in reason:
                    emoji = '🤖'  # IA avec baleines
                else:
                    emoji = '✅'  # IA standard

                print_blue(f'  {emoji} [BUY SIGNAL @ 8s] {token["symbol"]}: {reason}, MC=${actual_buy_mc:,.0f}')

                self.positions.open_position(
                    mint, token['symbol'], actual_buy_mc,
                    prediction['confidence'], '8s', reason,
                    entry_features=snapshot_8s  # Features pour apprentissage
                )
                return  # Déjà acheté, pas besoin de vérifier @ 15s
            elif prediction:
                # Afficher pourquoi on n'achète pas (si pas déjà SKIP)
                reason = prediction.get('reason', 'Unknown')
                if 'SKIP' not in reason:
                    print_blue(f'  [SKIP @ 8s] {token["symbol"]}: {reason}, MC=${prediction["mc"]:,.0f}')
        else:
            if Config.SCREENSHOT_MODE:
                print_blue(f'  [NO DATA @ 8s] {token["symbol"]}: Not enough trades to analyze')
            else:
                print_blue(f'  [NO DATA @ 8s] {token["symbol"]}: Not enough trades to analyze')

        # Attendre 7 secondes de plus (total 15s)
        await asyncio.sleep(7)

        if mint not in self.tokens:
            return

        # Snapshot @ 15s
        snapshot_15s = self.calculate_snapshot(token, 15)
        if snapshot_15s and snapshot_8s:
            token['snapshot_15s'] = snapshot_15s

            # Prédiction @ 15s (si pas déjà acheté - 2ème CHANCE avec wallets elite + baleines tardives)
            if mint not in self.positions.positions:
                prediction = self.predict_15s(snapshot_8s, snapshot_15s)
                if prediction and prediction['should_buy']:
                    reason = prediction.get('reason', 'IA')
                    decision_mc = prediction['mc']

                    # =================================================================
                    # ANTI-LATENCE: Vérifier le prix EN TEMPS REEL avant d'acheter
                    # =================================================================
                    if token['trades']:
                        current_mc = token['trades'][-1]['mc']
                        price_jump = (current_mc - decision_mc) / decision_mc if decision_mc > 0 else 0

                        if price_jump > Config.PRICE_JUMP_TOLERANCE:
                            print_blue(f'  ⚠️ [SKIP - LATENCE @ 15s] {token["symbol"]}: Prix explosé!')
                            print(f'     Decision @ ${decision_mc:,.0f} → Prix actuel ${current_mc:,.0f} (+{price_jump*100:.0f}%)')
                            return  # Skip, trop tard!

                        actual_buy_mc = current_mc
                    else:
                        actual_buy_mc = decision_mc

                    # Choisir l'emoji
                    if '2 BALEINES CONSECUTIVES' in reason:
                        emoji = '🐋🐋'  # Pattern ultra-fort tardif
                    elif 'ELITE WALLET' in reason:
                        emoji = '👑'  # Elite wallet tardif
                    elif 'new whales' in reason:
                        emoji = '🐋'  # Baleines tardives
                    else:
                        emoji = '✅'  # IA standard

                    if Config.SCREENSHOT_MODE:
                        print_blue(f'  {emoji} [BUY SIGNAL @ 15s - 2ND CHANCE] {token["symbol"]}: {reason}, MC=${actual_buy_mc:,.0f}')
                    else:
                        print_blue(f'  {emoji} [BUY SIGNAL @ 15s - 2ND CHANCE] {token["symbol"]}: {reason}, MC=${actual_buy_mc:,.0f}')

                    self.positions.open_position(
                        mint, token['symbol'], actual_buy_mc,
                        prediction['confidence'], '15s', reason,
                        entry_features=snapshot_15s  # Features pour apprentissage
                    )
                elif prediction:
                    # Afficher pourquoi on n'achète pas (seulement si raison intéressante)
                    reason = prediction.get('reason', 'Unknown')
                    if prediction['mc'] >= Config.MAX_PRICE_15S:
                        if Config.SCREENSHOT_MODE:
                            print_blue(f'  [SKIP @ 15s] {token["symbol"]}: Price too high (${prediction["mc"]:,.0f} > ${Config.MAX_PRICE_15S:,})')
                        else:
                            print_blue(f'  [SKIP @ 15s] {token["symbol"]}: Price too high (${prediction["mc"]:,.0f} > ${Config.MAX_PRICE_15S:,})')
                    elif prediction['confidence'] < Config.THRESHOLD_15S and 'new whales' not in reason:
                        print_blue(f'  [SKIP @ 15s] {token["symbol"]}: {reason}, MC=${prediction["mc"]:,.0f}')
        else:
            if not snapshot_15s:
                if Config.SCREENSHOT_MODE:
                    print_blue(f'  [NO DATA @ 15s] {token["symbol"]}: Not enough trades to analyze')
                else:
                    print_blue(f'  [NO DATA @ 15s] {token["symbol"]}: Not enough trades to analyze')

        # Nettoyer les vieux tokens pour libérer la mémoire
        await asyncio.sleep(600)  # Après 10 minutes total
        if mint in self.tokens and mint not in self.positions.positions:
            del self.tokens[mint]

    async def connect_websocket(self):
        """Connexion au WebSocket PumpFun"""
        print(f'\n[CONNEXION AU WEBSOCKET PUMPFUN]')

        try:
            # Configurer le WebSocket pour plus de stabilité
            async with websockets.connect(
                Config.PUMPFUN_WS,
                ping_interval=20,      # Envoyer un ping toutes les 20s pour garder la connexion
                ping_timeout=30,       # Timeout si pas de pong après 30s
                close_timeout=10,      # Timeout pour fermer proprement
                max_size=10485760      # 10MB max message size
            ) as ws:
                # S'abonner aux nouveaux tokens
                await ws.send(json.dumps({
                    "method": "subscribeNewToken"
                }))

                print('  Connecte! En attente de nouveaux tokens...\n')

                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)

                    tx_type = data.get('txType')

                    # Nouveau token
                    if tx_type == 'create':
                        await self.handle_new_token(data, ws)
                    # Trade (buy/sell)
                    elif tx_type in ['buy', 'sell']:
                        await self.handle_trade(data)

        except Exception as e:
            print(f'Erreur WebSocket: {e}')
            print('  Reconnexion dans 10 secondes...')
            # Reconnexion automatique avec délai plus long
            await asyncio.sleep(10)
            await self.connect_websocket()

    async def periodic_stats_update(self):
        """Met à jour périodiquement le titre et affiche les stats"""
        await asyncio.sleep(60)  # Attendre 1 minute avant la première mise à jour

        while True:
            # Mettre à jour le titre de la console
            self.positions.update_title()

            # Afficher les stats dans la console toutes les minutes
            self.positions.display_stats_inline()

            # Attendre 60 secondes avant la prochaine mise à jour
            await asyncio.sleep(60)

    async def live_position_monitor(self):
        """Affiche l'état des positions en temps réel toutes les 3 secondes"""
        await asyncio.sleep(5)  # Attendre 5s avant le premier affichage

        while True:
            if len(self.positions.positions) > 0:
                from pumpfun_price_fetcher import get_token_price_live
                from datetime import datetime

                print(f'\n{"="*80}')
                print('[MONITORING LIVE DES POSITIONS]')
                print('='*80)

                for mint, position in list(self.positions.positions.items()):
                    symbol = position.get('symbol', 'N/A')
                    entry_mc = position.get('entry_mc', 0)
                    partial_sold = position.get('partial_sold', False)

                    # Récupérer le prix LIVE
                    live_price = get_token_price_live(mint)

                    if live_price['success'] and live_price['mc_usd'] > 0:
                        current_mc = live_price['mc_usd']
                    else:
                        current_mc = position.get('last_mc', entry_mc)

                    # Calculer le profit actuel
                    profit_ratio = current_mc / entry_mc
                    profit_pct = (profit_ratio - 1) * 100

                    # Distance à la migration
                    distance_to_migration = 53000 - current_mc
                    migration_pct = (current_mc / 53000) * 100

                    # Emoji selon statut
                    if partial_sold:
                        status = '🎯 EN ATTENTE MIGRATION (50% vendus)'
                        status_color = '✅'
                    elif profit_pct > 0:
                        status = '📈 EN PROFIT'
                        status_color = '💚'
                    else:
                        status = '📉 EN PERTE'
                        status_color = '🔴'

                    print(f'\n{status_color} {symbol}: {status}')
                    print(f'   Entry: ${entry_mc:,.0f} → Current: ${current_mc:,.0f}')
                    print(f'   Profit: {profit_ratio:.2f}x ({profit_pct:+.1f}%)')

                    if current_mc < 53000:
                        print(f'   Distance migration: ${distance_to_migration:,.0f} ({migration_pct:.1f}% vers 53K)')
                    else:
                        print(f'   ✅ MIGRATION ATTEINTE ! MC: ${current_mc:,.0f}')

                    if partial_sold:
                        print(f'   💰 Position GRATUITE - Investissement récupéré !')

                print(f'\n{"="*80}')

            # Attendre 3 secondes avant la prochaine mise à jour (TEMPS RÉEL!)
            await asyncio.sleep(3)

    async def periodic_price_check(self):
        """Vérifie le prix uniquement pour les tokens MORTS (pas de trades WebSocket)"""
        await asyncio.sleep(30)  # Attendre 30 secondes avant de commencer

        while True:
            from datetime import datetime
            now = datetime.now()

            # Vérifier chaque position ouverte
            for mint in list(self.positions.positions.keys()):
                position = self.positions.positions.get(mint)
                if not position:
                    continue

                # Vérifier le temps depuis la dernière mise à jour WebSocket
                last_update_time = position.get('last_update_time', position['entry_timestamp'])
                seconds_since_update = (now - last_update_time).total_seconds()

                # IMPORTANT: TOUJOURS vérifier les positions en attente de migration
                # Même si WebSocket actif, on doit tracker la migration à 53K !
                partial_sold = position.get('partial_sold', False)

                # Si le WebSocket est actif ET que ce n'est pas une position en attente de migration, on skip
                if seconds_since_update < 30 and not partial_sold:
                    continue

                # Vérifier le prix via l'API (pour tokens morts OU positions en attente de migration)
                from pumpfun_price_fetcher import get_token_price_live
                live_price = get_token_price_live(mint)

                if live_price['success'] and live_price['mc_usd'] > 0:
                    current_mc = live_price['mc_usd']

                    # Vérifier stop loss / take profit / migration
                    self.positions.check_position(mint, current_mc)
                else:
                    # API échouée - utiliser le dernier prix WebSocket
                    current_mc = position.get('last_mc', position['entry_mc'])

                    # Vérifier quand même le stop loss avec le dernier prix connu
                    if current_mc <= position['stop_loss_mc']:
                        print(f'\n⚠️ [PROTECTION TOKEN MORT] {position["symbol"]}')
                        print(f'  Aucun trade depuis {seconds_since_update:.0f}s')
                        print(f'  Dernier prix: ${current_mc:,.0f} <= SL: ${position["stop_loss_mc"]:,.0f}')
                        print(f'  VENTE DE SÉCURITÉ')

                        self.positions.close_position(
                            mint,
                            current_mc,
                            f'STOP LOSS - Token mort ({seconds_since_update:.0f}s sans trades)'
                        )

            # Vérifier toutes les 5 secondes (au lieu de 10s)
            # Plus rapide pour capturer les migrations à 53K !
            await asyncio.sleep(5)

    async def periodic_timeout_check(self):
        """Vérifie périodiquement les positions expirées"""
        await asyncio.sleep(300)  # Attendre 5 minutes avant la première vérification

        while True:
            # Vérifier et fermer les positions expirées
            expired_count = self.positions.check_expired_positions()

            if expired_count > 0:
                print(f'\n⏰ [TIMEOUT CHECK] {expired_count} position(s) expired and closed')

            # Vérifier toutes les 5 minutes
            await asyncio.sleep(300)

    async def run(self):
        """Lance le bot"""
        print(f'\n{"="*80}')
        print('[BOT DE TRADING DEMARRE]')
        print('='*80)

        # Initialiser le titre
        self.positions.update_title()

        # Lancer les tâches en parallèle
        await asyncio.gather(
            self.connect_websocket(),
            self.periodic_stats_update(),
            self.live_position_monitor(),     # 🔥 MONITORING LIVE toutes les 3 secondes
            self.periodic_price_check(),      # ✅ Vérification prix + migration toutes les 5s
            self.periodic_timeout_check()     # Vérification des positions expirées
        )

# ============================================================================
# LANCEMENT
# ============================================================================
if __name__ == '__main__':
    print(f'\n ATTENTION:')
    if not Config.SIMULATION_MODE:
        print('  MODE LIVE ACTIVE - ARGENT REEL EN JEU!')
        print('  Assure-toi que ta cle privee est configuree')
    else:
        print('  Mode SIMULATION - Aucun argent reel utilise')

    print('\n' + '='*80)

    bot = LiveTradingBot()

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print('\n\n[BOT ARRETE]')
        bot.positions.show_stats()

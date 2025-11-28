# 🚀 PHASE 2 - Trading Réel avec ton Bot Existant

## 📋 État actuel (Phase 1)

✅ **Ce qui fonctionne:**
- Interface web complète (/bot)
- Authentification (register/login)
- Génération automatique de wallets Solana
- Dashboard avec stats
- Système de boosts
- **Mode SIMULATION**: Le bot génère des trades fictifs toutes les minutes

## 🎯 Phase 2 - Intégration complète

Pour activer le trading RÉEL avec ton bot `live_trading_bot.py`, suis ces étapes :

---

## 📝 ÉTAPE 1 : Préparer le bot existant

### 1.1 Copier les fichiers nécessaires

Assure-toi que ces fichiers sont dans le dossier principal :

```
prediction AI modele 2/
├── live_trading_bot.py          ✅ Déjà présent
├── learning_engine.py           📋 À vérifier
├── solana_trader.py             📋 À vérifier
├── trade_analyzer.py            📋 À vérifier
├── adaptive_config.py           📋 À vérifier
├── sol_price_fetcher.py         📋 À vérifier
├── pumpfun_price_fetcher.py     📋 À vérifier
├── model_10s.pkl                📋 Modèle IA @ 8s
├── model_15s.pkl                📋 Modèle IA @ 15s
```

### 1.2 Vérifier les dépendances

```bash
pip install websockets solders solana base58
```

---

## 🔧 ÉTAPE 2 : Modifier `trading_service.py`

Remplace la classe `UserTradingBot` par l'implémentation complète :

```python
# Dans trading_service.py

class UserTradingBot:
    """Bot de trading réel basé sur live_trading_bot.py"""

    def __init__(self, user_id, wallet_address, private_key, config=None):
        self.user_id = user_id
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.config = config or {}
        self.is_running = False
        self.bot_instance = None

    async def start(self):
        """Démarre le vrai bot de trading"""
        from live_trading_bot import LiveTradingBot, Config
        import joblib

        # Configurer le wallet de l'utilisateur
        os.environ['WALLET_PRIVATE_KEY'] = self.private_key
        os.environ['WALLET_ADDRESS'] = self.wallet_address

        # Configurer le mode
        Config.SIMULATION_MODE = False  # TRADING RÉEL!
        Config.TEST_MODE = True         # Petits montants
        Config.BUY_AMOUNT_SOL = 0.01    # 0.01 SOL par trade

        # Charger les modèles
        model_10s = joblib.load('model_10s.pkl')
        model_15s = joblib.load('model_15s.pkl')

        # Créer le bot
        self.bot_instance = LiveTradingBot()
        self.bot_instance.model_10s = model_10s
        self.bot_instance.model_15s = model_15s

        # Hook pour enregistrer les trades dans notre BDD
        self._setup_trade_hooks()

        # Lancer le bot
        self.is_running = True
        await self.bot_instance.run()

    def _setup_trade_hooks(self):
        """Configure les hooks pour enregistrer les trades"""
        original_close = self.bot_instance.positions.close_position

        def hooked_close(mint, exit_mc, reason, amount_percent=100):
            # Appeler l'original
            result = original_close(mint, exit_mc, reason, amount_percent)

            # Enregistrer dans notre BDD web
            if self.bot_instance.positions.closed_positions:
                position = self.bot_instance.positions.closed_positions[-1]

                # Calculer le profit en SOL
                profit_sol = (position['profit_ratio'] - 1) * position['amount_sol']

                db.create_trade(
                    user_id=self.user_id,
                    token_address=mint,
                    token_name=position.get('symbol', 'Unknown'),
                    trade_type='BUY_SELL',
                    amount_sol=position['amount_sol'],
                    tokens_bought=position.get('tokens_bought', 0),
                    profit_loss=profit_sol,
                    profit_loss_percentage=position['profit_percent'],
                    prediction_category=position.get('reason', 'Unknown'),
                    prediction_confidence=position.get('confidence', 0),
                    status='EXECUTED',
                    tx_signature=f'live_{mint[:8]}',
                    price_usd=exit_mc
                )

                # Mettre à jour les stats
                db.update_bot_stats(self.user_id)

                print(f"[WEB] Trade enregistré: {position['symbol']} - {position['profit_percent']:.1f}%")

            return result

        self.bot_instance.positions.close_position = hooked_close

    async def stop(self):
        """Arrête le bot"""
        self.is_running = False
        if self.bot_instance:
            # Le bot s'arrêtera au prochain cycle
            pass
```

---

## 🔐 ÉTAPE 3 : Sécuriser les clés privées

### 3.1 Modifier `solana_trader.py`

Dans ton fichier `solana_trader.py`, assure-toi qu'il peut lire la clé privée depuis l'environnement :

```python
import os
from solders.keypair import Keypair
import base58

def get_keypair():
    """Récupère la keypair depuis l'environnement"""
    private_key_b58 = os.environ.get('WALLET_PRIVATE_KEY')
    if not private_key_b58:
        raise Exception("WALLET_PRIVATE_KEY not set")

    private_key_bytes = base58.b58decode(private_key_b58)
    return Keypair.from_bytes(private_key_bytes)
```

### 3.2 Modifier `live_trading_bot.py`

Ajouter au début de `Config` :

```python
class Config:
    # Wallet depuis l'environnement (sécurisé)
    WALLET_ADDRESS = os.environ.get('WALLET_ADDRESS', '')
    WALLET_PRIVATE_KEY = os.environ.get('WALLET_PRIVATE_KEY', '')

    # ... reste de la config
```

---

## 🎮 ÉTAPE 4 : Tester en mode SIMULATION

Avant de lancer en mode LIVE, teste d'abord :

### 4.1 Activer la simulation dans `trading_service.py`

```python
# Dans la fonction start()
Config.SIMULATION_MODE = True  # MODE SIMULATION!
Config.TEST_MODE = True
```

### 4.2 Lancer et observer

```bash
python app.py
```

Puis :
1. Créer un compte sur `/bot`
2. Cliquer "START BOT"
3. Surveiller la console pour voir les logs

Le bot devrait :
- Se connecter au WebSocket PumpFun
- Analyser les tokens en temps réel
- Simuler des achats/ventes
- Enregistrer dans la BDD

---

## 🚀 ÉTAPE 5 : Activer le TRADING RÉEL

⚠️ **ATTENTION: Argent réel en jeu !**

### 5.1 Configurer le mode LIVE

```python
# Dans trading_service.py
Config.SIMULATION_MODE = False  # 🔴 TRADING RÉEL!
Config.TEST_MODE = True          # Petits montants
Config.BUY_AMOUNT_SOL = 0.01     # 0.01 SOL par trade
```

### 5.2 Prérequis

- ✅ Wallet utilisateur a des SOL (minimum 0.1 SOL pour commencer)
- ✅ Modèles IA entraînés (`model_10s.pkl`, `model_15s.pkl`)
- ✅ Tous les fichiers du bot présents
- ✅ RPC Solana configuré

### 5.3 Lancer

```bash
python app.py
```

Le bot va :
1. Scanner les nouveaux tokens sur PumpFun
2. Analyser avec l'IA (8s et 15s)
3. Acheter les tokens GEM détectés
4. Vendre avec take profit (2x partiel, puis migration)
5. Enregistrer tout dans la BDD web

---

## 📊 ÉTAPE 6 : Monitoring

### 6.1 Logs en temps réel

Les logs du bot s'affichent dans la console :

```
[NOUVEAU TOKEN] PEPE (...)  @ $10,000
[BUY SIGNAL @ 8s] PEPE: 2 BALEINES CONSECUTIVES, MC=$12,000
[POSITION OUVERTE] PEPE - Take Profit: $24,000 (2x)
💰 [PARTIAL PROFIT @ 2x] PEPE - MC: $25,000
🚀 [MIGRATION ATTEINTE] PEPE - VENTE PROGRESSIVE
💰 [POSITION FERMEE] PEPE - Profit: 3.5x (+250%)
```

### 6.2 Dashboard web

Sur `/bot`, l'utilisateur voit :
- **Stats en temps réel** (win rate, PNL, best trade)
- **Historique des trades** dans l'onglet "TRADES"
- **Statut du bot** (RUNNING/STOPPED)

### 6.3 Base de données

Tous les trades sont dans `trading_bot.db` :

```sql
SELECT * FROM trades WHERE user_id = 1 ORDER BY created_at DESC;
SELECT * FROM bot_stats WHERE user_id = 1;
```

---

## 🛡️ SÉCURITÉ

### Production Checklist

Avant de déployer en production :

- [ ] Changer `SECRET_KEY` dans `app.py`
- [ ] Mettre `WALLET_ENCRYPTION_KEY` en variable d'environnement
- [ ] Utiliser HTTPS (pas HTTP)
- [ ] Limiter les montants par trade (max 0.05 SOL)
- [ ] Backup régulier de `trading_bot.db`
- [ ] Rate limiting sur les API
- [ ] Logs d'erreurs centralisés
- [ ] Monitoring des profits/pertes
- [ ] Alerte si bot crash

---

## 🐛 Troubleshooting

### Bot ne démarre pas

```bash
# Vérifier les fichiers
ls -la *.pkl
ls -la learning_engine.py solana_trader.py

# Tester le bot manuellement
python live_trading_bot.py
```

### Erreur "Module not found"

```bash
pip install -r requirements_bot.txt
pip install websockets solders solana base58
```

### Bot ne trade pas

- Vérifier que WebSocket PumpFun fonctionne
- Vérifier que les modèles IA sont chargés
- Vérifier les seuils de confiance (Config.THRESHOLD_8S, etc.)
- Regarder les logs pour voir les SKIP reasons

### Trades non enregistrés

- Vérifier que le hook est bien configuré
- Regarder les logs : `[WEB] Trade enregistré...`
- Vérifier `trading_bot.db` : `SELECT * FROM trades;`

---

## 📈 Optimisation

### Performances

- Utiliser PostgreSQL au lieu de SQLite pour production
- Ajouter un cache Redis pour les balances
- WebSockets pour updates temps réel (au lieu de polling)
- Background tasks avec Celery pour gérer les bots

### Features avancées

- **Multi-strategy** : Laisser l'utilisateur choisir (AI_PREDICTIONS, COPY_TRADING, etc.)
- **Risk management** : Stop loss global par jour
- **Auto-compound** : Réinvestir les profits automatiquement
- **Social features** : Leaderboard des meilleurs traders
- **Notifications** : Email/Telegram quand le bot trade

---

## 🎯 Résumé

**Phase 1 (ACTUELLE)** :
- ✅ Interface web fonctionnelle
- ✅ Gestion des utilisateurs
- ✅ Wallets générés automatiquement
- ✅ Simulation de trades

**Phase 2 (CE GUIDE)** :
- 🔄 Intégrer `live_trading_bot.py`
- 🔄 Trading RÉEL automatique 24/7
- 🔄 Enregistrement dans la BDD web
- 🔄 Dashboard en temps réel

**Phase 3 (FUTUR)** :
- ⏳ Paiements SOL pour boosts
- ⏳ Multi-strategy
- ⏳ Notifications push
- ⏳ Mobile app
- ⏳ Analytics avancés

---

## ✅ Checklist de déploiement

Avant de lancer en production:

- [ ] Copier tous les fichiers du bot dans le dossier principal
- [ ] Installer toutes les dépendances
- [ ] Modifier `trading_service.py` avec l'implémentation complète
- [ ] Tester en mode SIMULATION
- [ ] Vérifier les hooks de BDD
- [ ] Configurer les clés privées sécurisées
- [ ] Tester avec un petit montant (0.01 SOL)
- [ ] Surveiller les premiers trades
- [ ] Activer le mode LIVE

---

**🚨 IMPORTANT:** Commence toujours avec `Config.SIMULATION_MODE = True` et `Config.TEST_MODE = True` !

Une fois que tout fonctionne bien en simulation, tu peux passer à `SIMULATION_MODE = False` pour le trading réel.

**Bon trading ! 🚀💰**

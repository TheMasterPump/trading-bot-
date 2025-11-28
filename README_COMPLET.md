# 🤖 PREDICTION AI + TRADING BOT - Système Complet

Un système de trading automatique sur Solana alimenté par l'IA, avec interface web pour que les utilisateurs puissent créer et gérer leur propre bot de trading.

---

## 📋 Vue d'ensemble du système

### **3 Composants Principaux**

1. **🔍 Scanner AI** (`/` - index.html)
   - Scan les tokens Solana pour détecter les rugs/gems
   - Modèle ML avec 94.74% de précision
   - Prédictions ROI (RUG, SAFE, GEM)
   - Historique des 5 derniers scans

2. **🤖 Trading Bot** (`/bot` - bot.html)
   - Interface web pour créer un compte
   - Génération automatique de wallet Solana
   - Trading automatique 24/7 avec IA
   - Dashboard avec stats en temps réel
   - Système de boosts (BASIC/PRO/PREMIUM)

3. **🎓 Bot de Trading Avancé** (`live_trading_bot.py`)
   - Ton bot existant qui fonctionne déjà
   - Stratégie IA multi-niveaux (8s, 15s)
   - Détection de baleines et wallets elite
   - Vente progressive et take profit partiel
   - Apprentissage automatique

---

## 🚀 Installation rapide

### **1. Dépendances**

```bash
cd "C:\Users\user\Desktop\project\prediction AI modele 2"

# Installer les dépendances du bot
pip install -r requirements_bot.txt

# Ou manuellement:
pip install Flask Flask-Session
pip install solders solana base58
pip install cryptography
pip install joblib pandas
pip install websockets
```

### **2. Initialiser la base de données**

```bash
# Créer les tables
python database_bot.py
```

### **3. Lancer le serveur**

```bash
python app.py
```

Puis ouvrir :
- **Scanner AI** : http://localhost:5001/
- **Trading Bot** : http://localhost:5001/bot

---

## 🎯 Utilisation

### **Mode 1 : Scanner AI (Déjà fonctionnel)**

1. Aller sur http://localhost:5001/
2. Entrer une adresse de token Solana
3. Cliquer "SCAN TOKEN"
4. Voir la prédiction (GEM/SAFE/RUG)

### **Mode 2 : Trading Bot (Phase 1 - Simulation)**

1. Aller sur http://localhost:5001/bot
2. Créer un compte (email + password)
3. **Un wallet Solana est généré automatiquement !**
4. Cliquer "START BOT"
5. Le bot génère des trades de simulation
6. Voir les stats dans le dashboard

### **Mode 3 : Trading Réel (Phase 2 - Voir PHASE2_GUIDE.md)**

1. Copier les fichiers du bot existant
2. Modifier `trading_service.py`
3. Tester en simulation
4. Activer le trading réel
5. Surveiller les profits ! 💰

---

## 📁 Structure du projet

```
prediction AI modele 2/
│
├── app.py                          # Flask app principal
├── database_bot.py                 # Gestion BDD SQLite
├── wallet_generator.py             # Génération wallets Solana
├── trading_service.py              # Service de trading (gère les bots)
├── trading_bot.db                  # BDD SQLite (créée auto)
│
├── templates/
│   ├── index.html                  # Scanner AI
│   └── bot.html                    # Trading Bot interface
│
├── models/
│   ├── roi_predictor_latest.pkl    # Modèle ML pour scanner
│   ├── model_10s.pkl               # Modèle IA @ 8s (à copier)
│   └── model_15s.pkl               # Modèle IA @ 15s (à copier)
│
├── live_trading_bot.py             # Bot de trading avancé
├── learning_engine.py              # Apprentissage automatique
├── solana_trader.py                # Exécution des trades
├── adaptive_config.py              # Config adaptative
│
├── README_COMPLET.md               # Ce fichier
├── TRADING_BOT_README.md           # Doc du bot
└── PHASE2_GUIDE.md                 # Guide migration Phase 2
```

---

## 🎨 Interface Web

### **Design Cyberpunk Turquoise**

- **Matrix rain** background animé
- **Scanlines** et effets CRT
- **Néon turquoise** avec glow effects
- **Cyber Eye logo** animé avec suivi de la souris
- **Terminal style** avec police monospace
- **Responsive** et moderne

### **Fonctionnalités**

#### Scanner AI
- ✅ Input pour adresse token
- ✅ Barre de progression animée (5 étapes)
- ✅ Résultats avec effet typing
- ✅ Historique des 5 derniers scans (localStorage)
- ✅ Badges de confiance colorés

#### Trading Bot
- ✅ Authentification (register/login)
- ✅ 5 tabs : Overview, Wallet, Boosts, Trades, Settings
- ✅ Dashboard avec stats en temps réel
- ✅ Wallet display avec copy button
- ✅ Système de boosts avec 3 plans
- ✅ Tableau d'historique des trades
- ✅ Configuration du bot (strategy, risk, TP/SL)

---

## 🗄️ Base de données

### **Tables principales**

| Table | Description |
|-------|-------------|
| `users` | Comptes utilisateurs (email, password hash) |
| `wallets` | Wallets Solana (adresse, clé privée chiffrée AES-256) |
| `subscriptions` | Boosts actifs (BASIC/PRO/PREMIUM) |
| `bot_status` | État du bot (running/stopped, stratégie) |
| `trades` | Historique complet des trades |
| `bot_stats` | Statistiques (win rate, profits, best trade) |

### **Sécurité**

- **Passwords** : Hashés avec SHA-256
- **Clés privées** : Chiffrées avec AES-256 (Fernet)
- **Sessions** : JWT tokens avec expiration 7 jours
- **HTTPS** : Recommandé pour la production

---

## 🤖 Bot de Trading

### **Stratégie (de ton bot existant)**

#### **Système à 3 niveaux @ 8s**

1. **AUTO-BUY** (bypass IA)
   - Transactions >= 15
   - Traders >= 8
   - Buy ratio >= 75%
   - MC < $12K

2. **IA + Filtres**
   - Seuil IA: 70%
   - MC < $15K
   - Bonus baleines: +15% si 3+ baleines

3. **SKIP automatique**
   - Transactions < 5
   - Buy ratio < 40%

#### **Patterns Ultra-Prioritaires**

- 🐋🐋 **2 baleines consécutives** → AUTO-BUY
- 👑 **Elite wallets** → AUTO-BUY (15 VIP trackés)
- 🔥 **Runners évidents** → AUTO-BUY

#### **Take Profit Progressif**

1. **À 2x** : Vendre 50% (récupère investissement)
2. **À 53K (migration)** : Vente progressive
   - 5% toutes les 20 secondes
   - Si token pump à 100K/200K = MAX PROFIT
   - Stop loss: Si MC baisse 15% depuis max

#### **Stop Loss**

- **-25%** vérifié TOUTES LES SECONDES
- Protection tokens morts (aucun trade depuis 30s)
- Timeout: Fermeture auto après 30 minutes

---

## 📊 Stats & Monitoring

### **Métriques trackées**

- **Win Rate** : % de trades gagnants
- **Total PNL** : Profit/Loss total en SOL
- **Best Trade** : Meilleur profit
- **Worst Trade** : Pire perte
- **Avg Profit** : Profit moyen par trade
- **Total Trades** : Nombre de trades exécutés

### **Dashboard en temps réel**

- Stats rafraîchies automatiquement (30s)
- Statut du bot (RUNNING/STOPPED) avec indicateur animé
- Historique des trades avec filtres
- Graphiques (à venir en Phase 3)

---

## 💰 Système de Boosts

| Boost | Prix | Trades/heure | Features |
|-------|------|--------------|----------|
| **BASIC** | Gratuit | 1 | AI basique, Take profit 2x |
| **PRO** | 0.1 SOL/mois | 10 | AI avancée, Custom TP/SL, Analytics |
| **PREMIUM** | 0.5 SOL/mois | Illimité | Multi-strategy, Auto-compound, Support VIP |

---

## 🔐 Sécurité & Production

### **Checklist avant déploiement**

- [ ] Changer `SECRET_KEY` dans app.py
- [ ] Mettre `WALLET_ENCRYPTION_KEY` en variable d'environnement
- [ ] Activer HTTPS (pas HTTP)
- [ ] Backup régulier de `trading_bot.db`
- [ ] Rate limiting sur les API
- [ ] Logs d'erreurs (Sentry, etc.)
- [ ] Monitoring des bots (alertes si crash)
- [ ] Limiter les montants par trade
- [ ] Tests de charge

### **Variables d'environnement**

```bash
# .env
SECRET_KEY=your-super-secret-key-here
WALLET_ENCRYPTION_KEY=your-fernet-key-here
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
DATABASE_URL=sqlite:///trading_bot.db
```

---

## 🐛 Troubleshooting

### **Bot ne démarre pas**

```bash
# Vérifier les dépendances
pip list | grep -E "Flask|solana|cryptography"

# Tester la BDD
python database_bot.py

# Tester le wallet generator
python wallet_generator.py
```

### **Erreur "Module not found"**

```bash
pip install -r requirements_bot.txt
```

### **Wallet balance = 0**

- Vérifier que des SOL ont été envoyés
- Attendre 1-2 minutes (confirmation blockchain)
- Cliquer "REFRESH BALANCE"

### **Trades non visibles**

```bash
# Vérifier la BDD
sqlite3 trading_bot.db
SELECT * FROM trades WHERE user_id = 1;
SELECT * FROM bot_stats WHERE user_id = 1;
```

---

## 📈 Roadmap

### **Phase 1 (ACTUELLE)** ✅

- Interface web complète
- Authentification
- Génération de wallets
- Dashboard avec stats
- **Mode SIMULATION**

### **Phase 2 (EN COURS)** 🔄

- Intégration de `live_trading_bot.py`
- Trading RÉEL avec IA
- Enregistrement en BDD
- Monitoring en temps réel

### **Phase 3 (FUTUR)** ⏳

- Paiements SOL pour boosts (vérification TX blockchain)
- Multi-strategy (COPY_TRADING, SCALPING, DCA)
- Notifications (Email, Telegram, Discord)
- Graphiques avancés (Chart.js)
- Mobile app (React Native)
- Leaderboard des meilleurs traders
- API publique
- Auto-compound des profits
- Risk management avancé

---

## 🎓 Documentation

### **Guides disponibles**

- `README_COMPLET.md` : Ce fichier (vue d'ensemble)
- `TRADING_BOT_README.md` : Doc du système de trading bot
- `PHASE2_GUIDE.md` : Guide d'intégration du bot réel

### **Code examples**

```python
# Créer un utilisateur
from database_bot import db
user_id = db.create_user('test@example.com', 'password123')

# Générer un wallet
from wallet_generator import SolanaWalletManager
manager = SolanaWalletManager()
wallet = manager.generate_wallet()

# Démarrer le bot
from trading_service import start_bot_for_user
result = start_bot_for_user(user_id, {'strategy': 'AI_PREDICTIONS'})
```

---

## 🤝 Support

Pour toute question ou problème :

1. Lire la documentation (README, PHASE2_GUIDE)
2. Vérifier les logs dans la console
3. Tester manuellement les composants
4. Vérifier que la BDD existe et est accessible

---

## 📜 Licence

© 2025 PREDICTION AI - Tous droits réservés

**Note**: Ce projet est à usage personnel. Le trading de cryptomonnaies comporte des risques. Ne trade jamais plus que ce que tu peux te permettre de perdre.

---

## 🎉 Crédits

- **Scanner AI** : Modèle ML entraîné sur 350+ tokens
- **Bot de Trading** : Stratégie IA multi-niveaux avec apprentissage automatique
- **Interface** : Design cyberpunk turquoise avec animations
- **Backend** : Flask + SQLite + Solana SDK

---

**🚀 Bon trading ! Que les profits soient avec toi ! 💰**

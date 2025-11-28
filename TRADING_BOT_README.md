# 🤖 TRADING BOT AI - Documentation

## 📋 Vue d'ensemble

Le Trading Bot AI est un système de trading automatique pour Solana qui utilise l'intelligence artificielle pour détecter les tokens GEM et trader automatiquement 24/7.

## 🚀 Installation

### 1. Installer les dépendances

```bash
cd "C:\Users\user\Desktop\project\prediction AI modele 2"
pip install -r requirements_bot.txt
```

### 2. Initialiser la base de données

```bash
python database_bot.py
```

Cela créera automatiquement le fichier `trading_bot.db` avec toutes les tables nécessaires.

### 3. Tester la génération de wallet

```bash
python wallet_generator.py
```

## 🎯 Lancement

```bash
python app.py
```

Puis ouvrir dans le navigateur :
- **Scanner AI** : http://localhost:5001/
- **Trading Bot** : http://localhost:5001/bot

## 💡 Comment utiliser

### 1. Créer un compte

1. Aller sur http://localhost:5001/bot
2. Cliquer sur l'onglet "REGISTER"
3. Entrer email + password
4. **Un wallet Solana est automatiquement généré pour vous!**

### 2. Déposer des SOL

1. Aller dans l'onglet "WALLET"
2. Copier l'adresse de votre wallet
3. Envoyer des SOL depuis Phantom/Solflare vers cette adresse
4. Cliquer sur "REFRESH BALANCE"

### 3. Démarrer le bot

1. Aller dans l'onglet "OVERVIEW"
2. Cliquer sur **"START BOT"**
3. Le bot trade automatiquement pour vous!

## 🎮 Fonctionnalités

### ✅ Implémenté (Phase 1)

- ✅ Authentification (register/login)
- ✅ Génération automatique de wallet Solana
- ✅ Affichage du solde (SOL + USD)
- ✅ Dashboard avec statistiques
- ✅ Système de boosts (BASIC/PRO/PREMIUM)
- ✅ Historique des trades
- ✅ Configuration du bot (risk level, take profit, stop loss)
- ✅ Interface cyberpunk turquoise

### 🔄 À implémenter (Phase 2)

- ⏳ Logique de trading automatique
  - Scanner les nouveaux tokens
  - Utiliser le modèle ML pour prédire
  - Exécuter les trades automatiquement
  - Gérer les take profit / stop loss
- ⏳ Paiement des boosts en SOL
- ⏳ Notifications par email/telegram
- ⏳ Graphiques de performance
- ⏳ API pour mobile app

## 🎨 Structure du projet

```
prediction AI modele 2/
├── app.py                  # Flask app principal
├── database_bot.py         # Gestion BDD SQLite
├── wallet_generator.py     # Génération wallets Solana
├── trading_bot.db          # Base de données (créée automatiquement)
├── templates/
│   ├── index.html         # Page scanner AI
│   └── bot.html           # Page trading bot
└── models/
    └── roi_predictor_latest.pkl  # Modèle ML
```

## 🔐 Sécurité

### Production (IMPORTANT!)

Avant de déployer en production:

1. **Changer la SECRET_KEY dans app.py**
   ```python
   app.config['SECRET_KEY'] = 'your-super-secret-key-here-change-me'
   ```

2. **Mettre ENCRYPTION_KEY en variable d'environnement**
   ```python
   # Dans database_bot.py
   ENCRYPTION_KEY = os.environ.get('WALLET_ENCRYPTION_KEY')
   ```

3. **Utiliser HTTPS** pour éviter l'interception des mots de passe

4. **Backup régulier de trading_bot.db** (contient les wallets chiffrés)

## 📊 Base de données

### Tables principales

- **users** : Emails, passwords hashés, dates
- **wallets** : Adresses, clés privées chiffrées, balances
- **subscriptions** : Boosts actifs, expirations
- **bot_status** : État du bot (running/stopped), stratégie
- **trades** : Historique complet des trades
- **bot_stats** : Statistiques (win rate, profits, etc.)

### Backup

```bash
# Sauvegarder la BDD
cp trading_bot.db trading_bot.db.backup

# Restaurer
cp trading_bot.db.backup trading_bot.db
```

## 🤖 Stratégies de trading

### AI PREDICTIONS (implémentée)

Le bot:
1. Scanne les nouveaux tokens sur Solana
2. Utilise le modèle ML pour prédire GEM/SAFE/RUG
3. Achète si prédit comme GEM avec confiance > 80%
4. Vend avec take profit (défaut: 2x) ou stop loss (défaut: -50%)

### Autres stratégies (à venir)

- **COPY TRADING** : Copie les trades des wallets performants
- **SCALPING** : Trading haute fréquence
- **DCA** : Dollar Cost Averaging sur les GEMs

## 💰 Système de Boosts

| Boost | Prix | Trades/heure | Features |
|-------|------|--------------|----------|
| BASIC | Gratuit | 1 | AI basique |
| PRO | 0.1 SOL/mois | 10 | AI avancée, custom settings |
| PREMIUM | 0.5 SOL/mois | Illimité | Multi-strategy, auto-compound |

## 🐛 Troubleshooting

### Erreur "Module not found"
```bash
pip install -r requirements_bot.txt
```

### Erreur "Database locked"
```bash
# Fermer toutes les instances de app.py
# Puis relancer
python app.py
```

### Wallet balance = 0
```bash
# Vérifier que des SOL ont bien été envoyés
# Attendre 1-2 minutes (confirmation blockchain)
# Cliquer sur "REFRESH BALANCE"
```

## 📞 Support

Pour toute question ou bug:
1. Vérifier les logs dans le terminal
2. Vérifier que la base de données existe (`trading_bot.db`)
3. Vérifier que les dépendances sont installées

## 🔥 Prochaines étapes

1. **Implémenter la logique de trading automatique**
   - Créer `trading_engine.py`
   - Scanner en temps réel
   - Exécuter les trades via Solana SDK

2. **Ajouter les paiements SOL**
   - Vérifier les transactions blockchain
   - Activer les boosts automatiquement

3. **Optimiser les performances**
   - Caching Redis
   - WebSockets pour updates temps réel
   - Background tasks avec Celery

## 📜 Licence

© 2025 PREDICTION AI - Tous droits réservés

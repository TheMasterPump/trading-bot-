# 🤖 AUTO TRADER BOT

Bot de trading automatique pour tokens Solana sur PumpFun, basé sur l'analyse de 75 runners.

## 📊 Performance des Filtres

- **Capture Rate**: 60% des runners détectés
- **Précision**: 42.5% (quand signal → runner dans 43% des cas)
- **Entrée moyenne**: $11,246
- **Gain médian**: +133%
- **Meilleur gain**: +591%

---

## 🎯 Stratégie de Trading

### Entrée (à 15 secondes)
- Buy Ratio ≥ 50%
- Transactions ≥ 20
- Traders ≥ 12
- Big Buys ≥ 5

### Sortie (Targets)
- **Target 1**: $25K → Vendre 30% (+150-200%)
- **Target 2**: $50K → Vendre 40% (+300-400%)
- **Target 3**: $69K → Vendre 30% (+500-600%)

### Stop Loss
- Buy ratio < 40%
- Pas de volume pendant 3 minutes
- Perte > 30%

---

## 🚀 Installation

```bash
cd "C:\Users\user\Desktop\prediction AI\trading_bot"
pip install websockets
```

---

## ⚙️ Configuration

Éditer `config.py` :

```python
# Mode de trading
TRADING_MODE = 'PAPER'  # 'PAPER' pour simulation, 'LIVE' pour réel

# Risk Management
RISK_MANAGEMENT = {
    'max_position_size_usd': 100,  # Maximum $100 par position
    'max_concurrent_positions': 3,  # Max 3 positions simultanées
    'min_wallet_balance': 50,  # Minimum $50 dans le wallet
}

# Pour LIVE trading (après tests en PAPER)
WALLET = {
    'private_key': 'VOTRE_CLEF_PRIVEE',
    'rpc_url': 'https://api.mainnet-beta.solana.com'
}
```

---

## 🎮 Utilisation

### Mode PAPER (Simulation)

```bash
python auto_trader.py
```

Le bot va :
1. Se connecter au WebSocket PumpPortal
2. Surveiller les nouveaux tokens
3. Détecter les signaux d'achat à 15 secondes
4. Simuler les trades (pas d'argent réel)
5. Afficher les profits/pertes

### Mode LIVE (Trading Réel)

⚠️ **ATTENTION** : Mode non implémenté pour ta sécurité !

Avant de passer en LIVE :
1. Tester en PAPER pendant au moins 1 semaine
2. Vérifier les résultats
3. Implémenter les fonctions Solana pour acheter/vendre
4. Commencer avec de PETITS montants ($10-20)

---

## 📈 Exemples de Signaux

```
[SIGNAL D'ENTREE] BENJI @ $10,380
  Buy Ratio: 65.0% (>= 50%)
  Transactions: 41 (>= 20)
  Traders: 25 (>= 12)
  Big Buys: 8 (>= 5)
  Volume: $2,995

[BUY EXECUTED - PAPER] BENJI
  Entry: $10,380
  Size: $100.00
  Balance restante: $900.00

[TARGET HIT] BENJI @ $71,703
  Target: target_3 ($69,000)
  PnL: +591.0%
  Vendre: 30% de la position

[SELL EXECUTED - PAPER] BENJI
  Exit: $71,703
  Entry: $10,380
  Profit: $591.23 (+591.0%)
  Balance: $1,491.23
```

---

## 🛡️ Sécurité

### Mode PAPER (Recommandé)
- ✅ Aucun risque
- ✅ Teste la stratégie
- ✅ Affine les paramètres
- ✅ Comprend les signaux

### Mode LIVE
- ⚠️ Risque de perte totale
- ⚠️ Commencer PETIT ($10-20)
- ⚠️ Ne jamais investir plus que tu peux perdre
- ⚠️ Vérifier CHAQUE trade manuellement au début

---

## 📁 Structure du Projet

```
trading_bot/
├── config.py          # Configuration (filtres, targets, wallet)
├── auto_trader.py     # Bot de trading principal
├── README.md          # Ce fichier
└── trades.json        # Historique des trades (créé automatiquement)
```

---

## 🔧 Personnalisation

### Changer les Filtres d'Entrée

Dans `config.py` :

```python
ENTRY_FILTERS = {
    'buy_ratio_min': 55,      # Plus strict
    'transactions_min': 25,   # Plus strict
    'traders_min': 15,        # Plus strict
    'big_buys_min': 8,        # Plus strict
}
```

⚠️ Plus strict = moins de trades mais meilleure précision

### Changer les Targets

```python
TARGETS = {
    'target_1': 20000,  # Plus conservateur
    'target_2': 40000,
    'target_3': 60000,
}
```

---

## 📊 Statistiques

Le bot affiche en temps réel :
- Nombre de positions ouvertes
- Balance du wallet
- Profit/Loss par position
- Historique des trades

---

## ❓ FAQ

**Q: Combien je peux gagner ?**
R: Basé sur l'analyse : Gain médian de +133%, meilleur gain +591%. Mais ce sont des résultats passés, pas garantis.

**Q: C'est sûr ?**
R: En mode PAPER → 100% sûr, c'est de la simulation.
En mode LIVE → Risque de perte totale. Crypto = très volatile.

**Q: Je peux trader avec $10 ?**
R: Oui, mais ajuste `max_position_size_usd` dans config.py

**Q: Comment savoir si ça marche ?**
R: Lance en PAPER pendant 1 semaine, regarde le balance finale.

**Q: Pourquoi pas tous les runners détectés ?**
R: Les filtres capturent 60% des runners. C'est un compromis entre capture rate et précision.

---

## 🚨 AVERTISSEMENT

**⚠️ CE BOT EST FOURNI À TITRE ÉDUCATIF**

- Le trading de crypto-monnaies est TRÈS risqué
- Tu peux perdre TOUT ton argent
- Les performances passées ne garantissent PAS les performances futures
- NE trade JAMAIS avec de l'argent dont tu as besoin
- Commence TOUJOURS en mode PAPER
- Je ne suis PAS responsable de tes pertes

**UTILISE À TES PROPRES RISQUES !**

---

## 📞 Support

Pour questions ou bugs, vérifie :
1. Les logs du bot
2. La configuration dans `config.py`
3. Que websockets est installé
4. Que tu es en mode PAPER

# 🤖 AUTO-TRADING BOT - GUIDE COMPLET

## ⚠️ AVERTISSEMENTS IMPORTANTS

**CE BOT PEUT PERDRE VOTRE ARGENT !**

- ✅ Peut gagner de l'argent en copiant les baleines
- ❌ Peut PERDRE de l'argent sur les rugs
- ⚡ Trade automatiquement SANS votre validation
- 💰 Utilise votre SOL RÉEL

**RECOMMANDATIONS:**
1. **COMMENCEZ EN MODE SIMULATION** (gratuit, sans risque)
2. Testez pendant 24-48h
3. Si rentable, activez avec **PETIT budget** (0.1 SOL max)
4. Augmentez progressivement si profitable

---

## 📋 CONFIGURATION

### Fichier: `auto_trading_config.json`

```json
{
  "trading_enabled": false,        ← DOIT être true pour trader
  "simulation_mode": true,         ← true = simulation, false = REAL
  "max_sol_per_trade": 0.1,       ← Budget max par trade
  "stop_loss_percent": -30,        ← Vendre si -30% (protection)
  "take_profit_percent": 100,      ← Vendre si +100% (profit)
  "min_liquidity_usd": 5000,       ← Éviter tokens avec <$5k liquidity
  "min_whales_buying": 2,          ← Acheter si 2+ baleines achètent
  "max_concurrent_positions": 3    ← Max 3 tokens en même temps
}
```

### Paramètres Importants:

**`trading_enabled`**
- `false` = Bot désactivé
- `true` = Bot activé

**`simulation_mode`**
- `true` = **SIMULATION** (recommandé pour tester)
- `false` = **REAL TRADING** (utilise vrai SOL)

**`max_sol_per_trade`**
- Montant max à investir par token
- Commencez petit : 0.05 - 0.1 SOL

**`stop_loss_percent`**
- Protection contre grosses pertes
- -30 = vendre si perte de 30%
- Plus strict = -20 (vend plus tôt)
- Plus risqué = -50 (accepte plus de perte)

**`take_profit_percent`**
- Vendre quand profit atteint
- 100 = vendre à +100% (2x)
- Conservateur = 50 (+50%)
- Agressif = 200 (+200%, 3x)

---

## 🚀 UTILISATION

### ÉTAPE 1 - MODE SIMULATION (SANS RISQUE)

```bash
# 1. Vérifier la config (simulation ON)
notepad auto_trading_config.json

# Vérifier que:
# "trading_enabled": true
# "simulation_mode": true

# 2. Lancer le bot
python auto_trading_bot.py

# 3. Voir l'historique des trades
python view_trading_history.py
```

**Le bot va:**
- Détecter les achats des baleines
- "Simuler" des achats/ventes
- Logger tout dans `auto_trading_history.json`
- **NE PAS trader réellement**

### ÉTAPE 2 - ACTIVER LE VRAI TRADING (RISQUÉ)

⚠️ **SEULEMENT SI LA SIMULATION EST PROFITABLE**

```bash
# 1. Modifier la config
notepad auto_trading_config.json

# Changer:
# "simulation_mode": false  ← ATTENTION !
# "max_sol_per_trade": 0.05  ← Commencer très petit

# 2. Lancer (UTILISE VRAI SOL!)
python auto_trading_bot.py
```

---

## 📊 MONITORING

### Voir les trades en direct

```bash
# Historique des trades
python view_trading_history.py

# Alertes des baleines
python view_whale_alerts.py

# Progression du dataset ML
python check_scraper_progress.py
```

### Fichiers générés:

- `auto_trading_history.json` - Tous les trades du bot
- `whale_alerts.json` - Achats détectés des baleines
- `training_dataset.json` - Dataset ML

---

## 🎯 STRATÉGIES RECOMMANDÉES

### DÉBUTANT (Sécurisé)
```json
{
  "max_sol_per_trade": 0.05,
  "stop_loss_percent": -20,
  "take_profit_percent": 50,
  "min_liquidity_usd": 10000,
  "min_whales_buying": 3
}
```
- Petit budget
- Stop-loss strict
- Take-profit conservateur
- Haute sélectivité

### INTERMÉDIAIRE (Équilibré)
```json
{
  "max_sol_per_trade": 0.2,
  "stop_loss_percent": -30,
  "take_profit_percent": 100,
  "min_liquidity_usd": 5000,
  "min_whales_buying": 2
}
```

### AGRESSIF (Risqué)
```json
{
  "max_sol_per_trade": 0.5,
  "stop_loss_percent": -40,
  "take_profit_percent": 200,
  "min_liquidity_usd": 3000,
  "min_whales_buying": 1
}
```

---

## ⚙️ PROCESS EN COURS

Vérifier quels scripts tournent:

```bash
# Liste des process
# 1. Scraper massif (collecte 500 tokens)
# 2. Whale monitor (surveille 259 baleines)
# 3. Auto-trading bot (si lancé)
```

---

## 🆘 PROBLÈMES FRÉQUENTS

### "Trading is DISABLED"
→ Mettre `"trading_enabled": true` dans config

### "No trades yet"
→ Aucune baleine n'a acheté récemment
→ Attendre ou vérifier que whale monitor tourne

### "Low liquidity"
→ Token a <$5000 liquidity
→ Bot évite automatiquement (protection)

### Bot ne trouve pas de tokens
→ Baisser `min_whales_buying` à 1
→ Baisser `min_liquidity_usd` à 3000

---

## 📈 OPTIMISATION

### Améliorer la rentabilité:

1. **Analyser l'historique**
   ```bash
   python view_trading_history.py
   ```
   - Voir le win rate
   - Ajuster stop-loss/take-profit

2. **Tester différentes configs**
   - Essayer 24h avec config A
   - Essayer 24h avec config B
   - Garder la meilleure

3. **Suivre les meilleures baleines**
   - Identifier quelles baleines sont les plus profitables
   - Filtrer pour suivre seulement celles-là

---

## ⚠️ SÉCURITÉ

**JAMAIS:**
- ❌ Investir plus que vous pouvez perdre
- ❌ Utiliser tout votre SOL
- ❌ Laisser tourner sans surveillance au début
- ❌ Modifier le code sans comprendre

**TOUJOURS:**
- ✅ Commencer en simulation
- ✅ Tester avec petit budget
- ✅ Monitorer régulièrement
- ✅ Garder des stop-loss stricts

---

## 📞 COMMANDES UTILES

```bash
# Lancer le bot
python auto_trading_bot.py

# Voir les trades
python view_trading_history.py

# Voir les alertes baleines
python view_whale_alerts.py

# Vérifier le scraper
python check_scraper_progress.py

# Voir les process
# (vos 3 process en arrière-plan)
```

---

## 🎓 NOTES IMPORTANTES

**LE BOT N'EST PAS MAGIQUE:**
- Il copie les baleines, mais elles peuvent se tromper
- Certaines baleines achètent des rugs
- Le timing est critique (vous achetez après eux)

**POUR MAXIMISER LES PROFITS:**
1. Collecter 500+ tokens (dataset ML complet)
2. Entraîner le modèle ML
3. Utiliser ML pour filtrer les opportunités
4. Combiner: Baleine + ML = Meilleurs trades

**LE BOT ACTUEL (VERSION 1.0):**
- ✅ Détecte les achats des baleines
- ✅ Simule les trades
- ❌ N'utilise PAS encore le ML pour filtrer
- ❌ Trading réel pas implémenté (simulation seulement)

**PROCHAINES AMÉLIORATIONS:**
- Intégration avec Jupiter pour vrais swaps
- Utilisation du modèle ML pour filtrer
- Telegram notifications
- Dashboard web

---

**Bonne chance et tradez prudemment ! 🚀**

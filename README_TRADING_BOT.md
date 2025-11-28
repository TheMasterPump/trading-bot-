# 🤖 BOT DE TRADING AI PUMPFUN

Bot de trading automatique qui utilise l'Intelligence Artificielle pour détecter et trader les tokens PumpFun à fort potentiel.

## 📊 PERFORMANCES

**IA Entraînée sur 1,876 tokens** :
- ✅ Détecte 88% des runners
- ✅ Précision : 73% @ 15s
- ✅ Profit moyen : 5.34x
- ✅ Prix d'entrée médian : $12,716

---

## 🚀 INSTALLATION

### 1. Installer les dépendances

```bash
pip install pandas scikit-learn xgboost imbalanced-learn joblib
pip install websockets requests base58 solders
```

### 2. Vérifier que les modèles IA sont entraînés

```bash
python train_models.py
```

Cela va créer :
- `model_10s.pkl` (modèle @ 10 secondes)
- `model_15s.pkl` (modèle @ 15 secondes)

---

## ⚙️ CONFIGURATION

Ouvre `live_trading_bot.py` et modifie la section `Config` :

```python
class Config:
    # MODE
    SIMULATION_MODE = True  # True = simulation, False = trading réel

    # WALLET (pour trading réel seulement)
    PRIVATE_KEY = "VOTRE_CLE_PRIVEE_ICI"  # Base58 ou array

    # IA - SEUILS
    THRESHOLD_10S = 0.65  # Confiance minimum @ 10s (65%)
    THRESHOLD_15S = 0.70  # Confiance minimum @ 15s (70%)

    # PRIX LIMITES
    MAX_PRICE_10S = 15000   # Prix max pour entrer @ 10s
    MAX_PRICE_15S = 20000   # Prix max pour entrer @ 15s

    # TRADING
    BUY_AMOUNT_SOL = 0.05   # Montant par trade (0.05 SOL)
    SLIPPAGE_BPS = 500      # Slippage 5%

    # STOP LOSS / TAKE PROFIT
    TAKE_PROFIT_MC = 69000  # Vendre à $69K MC (migration)
    STOP_LOSS_PERCENT = 0.30  # Stop loss à -30%
```

---

## 🎯 UTILISATION

### MODE SIMULATION (Recommandé pour débuter)

```bash
python live_trading_bot.py
```

Le bot va :
1. Se connecter au WebSocket PumpFun
2. Détecter les nouveaux tokens
3. Analyser avec l'IA @ 10s et 15s
4. **Simuler** les achats/ventes (pas d'argent réel)
5. Afficher les statistiques

### MODE LIVE (Trading réel ⚠️)

1. **Configure ta clé privée** dans `Config.PRIVATE_KEY`
2. **Désactive le mode simulation** : `SIMULATION_MODE = False`
3. **Lance le bot** :

```bash
python live_trading_bot.py
```

⚠️ **ATTENTION** : En mode LIVE, le bot trade avec de l'argent RÉEL !

---

## 📈 STRATÉGIE DU BOT

### Pipeline de décision :

```
@ 10 SECONDES:
├─ L'IA analyse le token
├─ SI confiance ≥ 65% ET MC < $15,000
│  └─ ✅ ACHETER IMMÉDIATEMENT
└─ SINON
   └─ ⏳ SURVEILLER jusqu'à 15s

@ 15 SECONDES:
├─ L'IA réanalyse avec plus de données
├─ SI confiance ≥ 70% ET MC < $20,000
│  └─ ✅ ACHETER
└─ SINON
   └─ ❌ IGNORER le token

APRÈS ACHAT:
├─ Monitoring continu toutes les 5s
├─ SI MC atteint $69,000
│  └─ 💰 VENDRE (Take Profit)
├─ SI MC baisse de -30%
│  └─ 📉 VENDRE (Stop Loss)
```

---

## 📊 EXEMPLES DE RÉSULTATS

```
✅ [POSITION OUVERTE]
  Token: ROSIKOFI
  MC Entrée: $17,960
  Confiance IA: 85%
  Stop Loss: $12,572
  Take Profit: $69,000

💰 [POSITION FERMÉE] - TAKE PROFIT
  Token: ROSIKOFI
  Entrée: $17,960
  Sortie: $69,188
  Profit: 3.85x (+285.0%)
```

---

## 🔧 DÉPANNAGE

### Le bot ne détecte pas de tokens

- Vérifie ta connexion internet
- Le WebSocket PumpFun peut être down
- Attends quelques minutes

### Erreur "model_10s.pkl not found"

Lance d'abord :
```bash
python train_models.py
```

### Le bot ne trade pas

- Vérifie que `SIMULATION_MODE = False` (pour trading réel)
- Vérifie que ta clé privée est configurée
- Vérifie que tu as assez de SOL dans ton wallet

---

## 📝 FICHIERS IMPORTANTS

- `live_trading_bot.py` : Bot de trading LIVE
- `model_10s.pkl` : Modèle IA @ 10s
- `model_15s.pkl` : Modèle IA @ 15s
- `train_models.py` : Script d'entraînement
- `test_models.py` : Test des modèles
- `prediction_bot.py` : Bot de prédiction (sans trading)

---

## ⚠️ AVERTISSEMENTS

1. **Le trading crypto comporte des risques**
   - Investis seulement ce que tu peux perdre
   - Les performances passées ne garantissent pas les résultats futurs

2. **Teste TOUJOURS en mode simulation d'abord**
   - Comprends bien comment le bot fonctionne
   - Ajuste les paramètres selon tes besoins

3. **Surveille ton bot**
   - Ne le laisse pas tourner sans surveillance
   - Vérifie régulièrement les positions

4. **Backup ta clé privée**
   - Ne partage JAMAIS ta clé privée
   - Stocke-la en sécurité

---

## 🎓 AMÉLIORER LE BOT

### Augmenter la précision :

1. **Collecter plus de données** :
   - Laisse tourner `pattern_discovery_bot.py` plus longtemps
   - Objectif : 500+ runners

2. **Réentraîner les modèles** :
   ```bash
   python train_models.py
   ```

3. **Ajuster les seuils** :
   - Augmente `THRESHOLD_15S` à 0.75 pour plus de précision (mais moins d'entrées)
   - Diminue à 0.65 pour plus d'entrées (mais plus de risque)

### Optimiser les profits :

1. **Réduire le prix max d'entrée** :
   - `MAX_PRICE_10S = 12000` (au lieu de 15000)
   - Meilleur prix d'entrée = plus de profit

2. **Ajuster le stop loss** :
   - Plus serré (20%) = moins de perte mais sorties fréquentes
   - Plus large (40%) = plus de perte mais garde les positions

---

## 📞 SUPPORT

Si tu as des questions :
1. Lis bien ce README
2. Teste en mode SIMULATION d'abord
3. Vérifie les logs du bot

BON TRADING ! 🚀

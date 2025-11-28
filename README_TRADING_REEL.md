# Guide de configuration - Trading Réel

## ⚠️ ATTENTION
Le trading avec de l'argent réel comporte des risques. Testez toujours avec de petits montants d'abord!

## 📋 Étapes de configuration

### 1. Installer les dépendances

```bash
pip install python-dotenv solders
```

### 2. Créer le fichier .env

1. Copiez le fichier `.env.example` et renommez-le en `.env`
2. Ouvrez le fichier `.env` avec un éditeur de texte
3. Remplissez vos informations:

```env
SOLANA_PRIVATE_KEY=votre_cle_privee_base58_ici
SOLANA_PUBLIC_KEY=votre_adresse_publique_ici
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
```

**IMPORTANT:**
- NE PARTAGEZ JAMAIS votre clé privée!
- Ajoutez `.env` au `.gitignore` si vous utilisez Git
- La clé privée doit être au format Base58

### 3. Configuration des modes

Dans `live_trading_bot.py`, ligne 41-42:

#### Mode Simulation (par défaut)
```python
SIMULATION_MODE = True   # Pas d'argent réel
TEST_MODE = False        # N'a pas d'effet en simulation
```

#### Mode Test (petits montants)
```python
SIMULATION_MODE = False  # Trading réel
TEST_MODE = True         # Utilise 0.01 SOL par trade
```

#### Mode Live (montants normaux)
```python
SIMULATION_MODE = False  # Trading réel
TEST_MODE = False        # Utilise 0.05 SOL par trade
```

### 4. Vérifier votre balance

Avant de lancer le bot en mode réel, vérifiez que vous avez:
- **Mode TEST**: Minimum 0.2 SOL (pour 10-20 trades test)
- **Mode LIVE**: Minimum 1 SOL (pour 20 trades)

### 5. Lancer le bot

```bash
# Mode Simulation (recommandé pour débuter)
python live_trading_bot.py

# Mode Test (avec .env configuré et TEST_MODE=True)
python live_trading_bot.py

# Mode Live (avec .env configuré et SIMULATION_MODE=False, TEST_MODE=False)
python live_trading_bot.py
```

## 🛡️ Protections intégrées

Le bot inclut plusieurs protections:
- ✅ Vérification du wallet avant chaque trade
- ✅ Gestion d'erreurs des transactions
- ✅ Réessai automatique si la vente échoue
- ✅ Vérification du prix live avant achat
- ✅ Stop loss et take profit automatiques

## 📊 Stratégie de vente

### Vente partielle à 2x
- Vend 50% de la position
- Récupère l'investissement initial
- Le reste devient "gratuit" (risk-free)

### Vente progressive après migration (53K)
- Vend 5% toutes les 20 secondes
- Continue tant que le prix monte
- Si le prix baisse de 15% depuis le max: vend tout le reste

### Exemple:
```
Achat: 10K MC (0.01 SOL)
↓
2x (20K MC): Vend 50% ✅ (récupère 0.01 SOL)
↓
53K MC (migration): Vente progressive commence
  - 60K: vend 5% (reste 45%)
  - 80K: vend 5% (reste 40%)
  - 120K: vend 5% (reste 35%)
  - 200K: vend 5% (reste 30%)
  - Baisse à 170K (-15%): VEND TOUT (30%) ✅
```

## ⚠️ Erreurs courantes

### "Clé privée non configurée"
→ Vérifiez que le fichier `.env` existe et contient `SOLANA_PRIVATE_KEY`

### "Bibliothèque solders non installée"
→ Exécutez: `pip install solders`

### "Transaction failed"
→ Vérifiez:
  - Vous avez assez de SOL dans le wallet
  - Le RPC est accessible
  - Le slippage n'est pas trop bas (augmentez à 10-15%)

## 💡 Recommandations

1. **Commencez TOUJOURS en mode TEST** (0.01 SOL par trade)
2. Surveillez les 10-20 premiers trades de près
3. Analysez les résultats avec `analyze_real_data.py`
4. Ajustez les paramètres si nécessaire
5. Passez en mode LIVE seulement si le TEST est profitable

## 📞 Support

En cas de problème, vérifiez:
1. Le fichier `.env` est bien configuré
2. Les dépendances sont installées
3. Vous avez assez de SOL
4. Le mode est correctement configuré dans `live_trading_bot.py`

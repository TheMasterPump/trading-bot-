# 🎯 Guide des Stratégies de Take Profit

## 🚀 Système de Stratégies Personnalisables

Chaque utilisateur peut maintenant configurer son propre bot avec **5 stratégies de Take Profit différentes** !

---

## 📊 Les 5 Stratégies Disponibles

### **1. 🎲 SIMPLE MULTIPLIER** (Vendre Tout à xN)

**Concept** : Vendre 100% de la position quand un multiplier est atteint.

**Configuration** :
- `Multiplier` : x2, x3, x5, x10, etc.

**Exemple** :
- Achète à 10K MC
- Multiplier = x3
- Vend 100% à 30K MC (3x)

**Idéal pour** :
- ✓ Stratégie simple et claire
- ✓ Take profit rapide
- ✓ Pas de gestion complexe

---

### **2. 💎 PARTIAL HOLD** (Sell 50% @ x2 + Hold Reste)

**Concept** : Vendre un % à un premier TP, puis garder le reste jusqu'à un certain MC.

**Configuration** :
- `% à vendre au premier TP` : 50% (par défaut)
- `Premier TP multiplier` : x2 (par défaut)
- `Hold le reste jusqu'à (MC)` : 50K (par défaut)

**Exemple** :
- Achète à 10K MC
- Vend 50% à 20K MC (x2) → Récupère investissement initial
- Hold 50% restant jusqu'à 50K MC
- Si atteint 50K → Vend le reste (x5)
- Si n'atteint pas → Exit avant 50K

**Idéal pour** :
- ✓ Sécuriser l'investissement initial
- ✓ Garder une exposition si ça pump
- ✓ Stratégie équilibrée risque/récompense

---

### **3. 🚪 EXIT BEFORE MIGRATION** (Vendre Avant Migration)

**Concept** : Vendre 100% avant que le token atteigne la migration Raydium.

**Configuration** :
- `Exit Market Cap Target` :
  - 40K (avant migration)
  - 50K (proche migration)
  - 53K (juste avant migration)

**Exemple** :
- Achète à 10K MC
- Target = 53K
- Dès que MC atteint 53K → Vend 100%
- N'attend PAS la migration (pas de risque dump)

**Idéal pour** :
- ✓ Éviter le risque post-migration
- ✓ Exit garanti avant dump potentiel
- ✓ Pas d'exposition aux bots MEV
- ✓ Profits constants sans stress

---

### **4. 📈 PROGRESSIVE AFTER MIGRATION** (Vente Progressive)

**Concept** : Vendre une partie à x2, puis vendre progressivement après la migration en plusieurs étapes.

**Configuration** :
- `Sell initiaux @ x2` : 50% (0 = pas de sell partiel)
- `% à vendre par étape` : 5% (par défaut)
- `Délai entre chaque vente` : 20 secondes (par défaut)

**Exemple** :
- Achète à 10K MC
- Vend 50% à 20K MC (x2)
- Attend la migration (53K)
- Après migration : Vend 5% toutes les 20 secondes
- Continue jusqu'à vente complète ou stop loss

**Idéal pour** :
- ✓ Maximiser les gains si pump fort après migration
- ✓ Stratégie du bot existant (déjà prouvée)
- ✓ Sell progressif = meilleurs prix moyens
- ✓ Capture les runners (100K+, 200K+)

---

### **5. 💰 ALL-IN AFTER MIGRATION** (Vendre Tout Après Migration)

**Concept** : Vendre 100% dès que la migration Raydium est atteinte.

**Configuration** :
- Aucune config (stratégie simple)

**Exemple** :
- Achète à 10K MC
- Attend la migration (~53K)
- Dès migration atteinte → Vend 100%
- Profit: 5.3x garanti

**Idéal pour** :
- ✓ Stratégie ultra-simple
- ✓ Profit garanti à la migration
- ✓ Pas de risque de manquer la sortie
- ✓ Pas de gestion post-migration

---

## 🎮 Comment Choisir sa Stratégie ?

### **Par Profil de Trader** :

| Profil | Stratégie Recommandée | Pourquoi |
|--------|----------------------|----------|
| **Débutant** | SIMPLE MULTIPLIER ou ALL-IN AFTER MIGRATION | Simple, pas de stress |
| **Conservateur** | EXIT BEFORE MIGRATION | Sécurise les gains avant risque |
| **Équilibré** | PARTIAL HOLD | Récupère investissement + garde exposition |
| **Agressif** | PROGRESSIVE AFTER MIGRATION | Maximise les runners |
| **Pro** | PROGRESSIVE (personnalisé) | Contrôle total sur chaque paramètre |

### **Par Objectif** :

| Objectif | Stratégie |
|----------|-----------|
| Récupérer investissement rapidement | PARTIAL HOLD (50% @ x2) |
| Profits constants sans stress | EXIT BEFORE MIGRATION |
| Maximiser les gains | PROGRESSIVE AFTER MIGRATION |
| Simplifier au maximum | SIMPLE MULTIPLIER ou ALL-IN |
| Capturer les 10x-100x | PROGRESSIVE (config agressive) |

---

## 🔧 Configuration Avancée

### **SIMPLE MULTIPLIER**

```json
{
  "strategy": "SIMPLE_MULTIPLIER",
  "multiplier": 3.0
}
```
- `multiplier` : 1.5 à 20x

### **PARTIAL HOLD**

```json
{
  "strategy": "PARTIAL_HOLD",
  "first_percent": 50,
  "first_tp": 2.0,
  "hold_until_mc": 50000
}
```
- `first_percent` : 10-90% (% à vendre au 1er TP)
- `first_tp` : 1.5-10x (multiplier du 1er TP)
- `hold_until_mc` : 10K-100K (MC max avant exit)

### **EXIT BEFORE MIGRATION**

```json
{
  "strategy": "EXIT_BEFORE_MIGRATION",
  "exit_mc": 53000
}
```
- `exit_mc` : 40000, 50000, 53000 (MC target)

### **PROGRESSIVE AFTER MIGRATION**

```json
{
  "strategy": "PROGRESSIVE_AFTER_MIGRATION",
  "initial_percent": 50,
  "step_percent": 5,
  "step_interval": 20
}
```
- `initial_percent` : 0-90% (sell @ x2, 0 = pas de sell partiel)
- `step_percent` : 1-20% (% à vendre par étape)
- `step_interval` : 5-60 secondes (délai entre ventes)

### **ALL-IN AFTER MIGRATION**

```json
{
  "strategy": "ALL_IN_AFTER_MIGRATION",
  "exit_at_migration": true
}
```
Aucun paramètre à configurer.

---

## 📈 Exemples de Résultats

### **Scénario 1 : Token Pump à 100K**

| Stratégie | Entrée | Sortie | Profit |
|-----------|--------|--------|--------|
| SIMPLE x3 | 10K | 30K | 3x |
| PARTIAL HOLD | 10K | 50% @ 20K + 50% @ 50K | 3.5x |
| EXIT BEFORE | 10K | 53K | 5.3x |
| PROGRESSIVE | 10K | 50% @ 20K + progressive jusqu'à 100K | 8x+ |
| ALL-IN AFTER | 10K | 53K | 5.3x |

**Gagnant** : PROGRESSIVE (capture le runner)

### **Scénario 2 : Token Dump Après Migration**

| Stratégie | Entrée | Sortie | Profit |
|-----------|--------|--------|--------|
| SIMPLE x3 | 10K | 30K | 3x |
| PARTIAL HOLD | 10K | 50% @ 20K + 50% @ 40K (dump) | 3x |
| EXIT BEFORE | 10K | 53K | 5.3x |
| PROGRESSIVE | 10K | 50% @ 20K + dump avant ventes | 2x |
| ALL-IN AFTER | 10K | 53K | 5.3x |

**Gagnant** : EXIT BEFORE ou ALL-IN (évitent le dump)

### **Scénario 3 : Token ne Pump Pas**

| Stratégie | Entrée | Stop Loss | Perte |
|-----------|--------|-----------|-------|
| SIMPLE x3 | 10K | -25% @ 7.5K | -25% |
| PARTIAL HOLD | 10K | -25% @ 7.5K | -25% |
| EXIT BEFORE | 10K | -25% @ 7.5K | -25% |
| PROGRESSIVE | 10K | -25% @ 7.5K | -25% |
| ALL-IN AFTER | 10K | -25% @ 7.5K | -25% |

**Égalité** : Stop loss protège toutes les stratégies.

---

## 🎯 Recommandations Finales

### **Setup Recommandé pour Chaque Plan**

#### **RISQUER** (Agressif)
```
Stratégie: PROGRESSIVE_AFTER_MIGRATION
- initial_percent: 30% (garde 70% pour runners)
- step_percent: 3% (vente lente)
- step_interval: 30 secondes
Stop Loss: -30%
```

#### **SAFE** (Conservateur)
```
Stratégie: PARTIAL_HOLD
- first_percent: 60% (récupère >initial)
- first_tp: 1.8x
- hold_until_mc: 45K (exit avant migration)
Stop Loss: -15%
```

#### **ULTRA** (Pro)
```
Stratégie: Personnalisée selon le token
- Mix de toutes les stratégies
- Adaptation en temps réel
Stop Loss: Dynamique
```

---

## 🔐 Notes Importantes

⚠️ **Tous les paramètres sont stockés en base de données** (`bot_status` table)

⚠️ **Le bot applique la stratégie configurée pour TOUS les trades**

⚠️ **Tu peux changer la stratégie à tout moment** (prend effet au prochain trade)

⚠️ **Stop Loss fonctionne indépendamment** de la stratégie de TP

---

## 🚀 Pour Phase 2 (Trading Réel)

Quand tu intègres le bot réel (`live_trading_bot.py`), tu devras :

1. **Lire la configuration** depuis la BDD :
```python
bot_status = db.get_bot_status(user_id)
tp_strategy = bot_status['tp_strategy']
tp_config = json.loads(bot_status['tp_config'])
```

2. **Appliquer la stratégie** dans le bot :
```python
if tp_strategy == 'SIMPLE_MULTIPLIER':
    if current_mc >= entry_mc * tp_config['multiplier']:
        close_position(100)

elif tp_strategy == 'PROGRESSIVE_AFTER_MIGRATION':
    if current_mc >= entry_mc * 2:
        close_position(tp_config['initial_percent'])
    if current_mc >= 53000:  # Migration
        # Vente progressive
        ...
```

3. **Tester chaque stratégie** en simulation avant production

---

**🎉 SYSTÈME DE STRATÉGIES COMPLET !** 🚀

Les utilisateurs peuvent maintenant **personnaliser complètement** leur bot de trading ! 💰

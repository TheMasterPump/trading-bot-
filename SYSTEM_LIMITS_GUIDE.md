# 🔒 Guide des Limites Système

## 🎯 Vue d'Ensemble

Les limites système sont **CRITIQUES** pour éviter :
- ❌ Crash du serveur si trop de bots
- ❌ Performance dégradée pour tous
- ❌ Coûts serveur incontrôlés
- ✅ Garantir une bonne expérience utilisateur

---

## 📊 Limites Configurées

### **Par Défaut**

```
MAX_CONCURRENT_BOTS    : 200      # Total de bots simultanés
MAX_BOTS_PER_USER      : 1        # Bots par utilisateur
MAX_TRADES_PER_DAY     : 500      # Trades max par jour/user
ALERT_THRESHOLD        : 80%      # Alerte à 160 bots
WEBSOCKET_RECONNECT    : 5s       # Délai de reconnexion
MAX_TOKENS_PER_MINUTE  : 1000     # Protection CPU
MAX_SIGNALS_PER_MINUTE : 100      # Éviter spam
```

---

## 🖥️ Recommandations VPS

### **Mapping RAM → Limite**

| VPS RAM | Max Bots | Coût/Mois | Recommandé Pour |
|---------|----------|-----------|-----------------|
| **2GB** | **50** | $10 | Test, beta |
| **4GB** | **150** | $40 | **200 users** ← TOI |
| **8GB** | **300** | $80 | Scale up |
| **16GB** | **500+** | $160 | Heavy production |

### **TON CAS : 200 utilisateurs prévus**

```python
VPS recommandé : 4GB RAM ($40/mois)
Limite système : MAX_CONCURRENT_BOTS = 200
Marge sécurité : 4GB peut gérer jusqu'à 150 confortablement
                 Passe à 8GB si tu dépasses 180 régulièrement
```

---

## 🚨 Statuts de Capacité

### **Système de 4 Niveaux**

```
LOW     : 0-50%   (0-100 bots)   → Tout va bien
HEALTHY : 50-80%  (100-160 bots) → Normal
WARNING : 80-100% (160-200 bots) → Surveille de près !
FULL    : 100%+   (200+ bots)    → REFUSE nouveaux bots
```

### **Exemple Réel**

```
10 bots  → LOW      (  5.0% used, 190 slots free)  ✅
100 bots → HEALTHY  ( 50.0% used, 100 slots free)  ✅
160 bots → WARNING  ( 80.0% used,  40 slots free)  ⚠️
200 bots → FULL     (100.0% used,   0 slots free)  ❌
250 bots → FULL     (125.0% used, -50 slots free)  ❌ BLOQUÉ
```

---

## 🔧 Configuration

### **Option 1 : Modifier dans le Code**

```python
# Dans system_limits.py
MAX_CONCURRENT_BOTS = 200  # Change ici
```

### **Option 2 : Variable d'Environnement** (Recommandé en production)

```bash
# Sur ton VPS
export MAX_CONCURRENT_BOTS=200

# Ou dans .env
echo "MAX_CONCURRENT_BOTS=200" >> .env
```

### **Option 3 : Ajuster selon VPS**

```python
# Dans system_limits.py
from system_limits import get_recommended_limit_for_vps

# Si tu as 4GB de RAM
max_bots = get_recommended_limit_for_vps(4)  # Retourne 150
```

---

## 🛡️ Protection Implémentée

### **1. Vérification au Démarrage de Bot**

```python
# Dans app.py, ligne 361
if current_bots >= MAX_CONCURRENT_BOTS:
    return error 503 "Serveur complet"
```

**Résultat** :
- Utilisateur voit : "Serveur complet (200/200 bots actifs). Réessaie dans quelques minutes."
- HTTP 503 (Service Unavailable)
- Bot ne démarre PAS

### **2. API de Monitoring**

```bash
# Vérifier capacité en temps réel
curl http://localhost:5001/api/admin/capacity

# Response
{
  "success": true,
  "capacity": {
    "current_bots": 150,
    "max_bots": 200,
    "percent_used": 75.0,
    "available_slots": 50,
    "status": "HEALTHY",
    "can_accept_new": true
  }
}
```

### **3. Dashboard Visuel**

```
http://localhost:5001/admin

Affiche :
Active Bots: 150 / 200 slots (75.0%)
         ↑        ↑        ↑
    Actuel    Max    Pourcentage
```

---

## 📈 Scaling Guide

### **Scénario 1 : Tu passes de 100 → 180 bots**

**Action** :
1. Surveille CPU/RAM via `/admin`
2. Si CPU > 70% ou RAM > 80% : Scale up !
3. Passe de 4GB → 8GB VPS
4. Change `MAX_CONCURRENT_BOTS = 300`

### **Scénario 2 : Lancement Progressif**

```
Jour 1   : MAX = 50   (soft launch)
Jour 3   : MAX = 100  (monitor)
Jour 7   : MAX = 150  (stable)
Jour 14  : MAX = 200  (full launch)
```

### **Scénario 3 : Pic de Demande**

```
Heure Normale : 100 bots actifs
Heure de Pointe : 180 bots actifs

Solution :
- Garde MAX = 200 (marge de sécurité)
- Surveille via /admin pendant les pics
- Si > 160 régulièrement : scale up
```

---

## 🚨 Alertes Recommandées

### **Quand Alerter ?**

```python
if current_bots >= 160:  # 80% de capacité
    send_alert_to_admin("⚠️ Capacité à 80% !")

if current_bots >= 190:  # 95% de capacité
    send_urgent_alert("🚨 URGENT : Presque plein !")

if current_bots >= 200:  # 100% de capacité
    send_critical_alert("❌ SERVEUR PLEIN !")
```

### **Monitoring Externe**

```bash
# UptimeRobot ou autre
Check URL : http://ton-domaine.com/api/admin/health
Interval  : 5 minutes

Alerte si :
- Response != 200
- capacity.status == "FULL"
- capacity.percent_used >= 90
```

---

## 🔍 Monitoring en Temps Réel

### **Dashboard Admin**

```
http://localhost:5001/admin

Montre :
✓ Nombre de bots actifs
✓ Capacité (% utilisé)
✓ Statut (LOW/HEALTHY/WARNING/FULL)
✓ Slots disponibles
✓ Auto-refresh toutes les 5s
```

### **API Endpoints**

```bash
# Stats complètes
GET /api/admin/stats

# Capacité
GET /api/admin/capacity

# Health check
GET /api/admin/health
```

---

## 🎯 Best Practices

### **1. Commence Conservateur**

```
Premier lancement : MAX = 100
Après 1 semaine   : MAX = 150
Après 1 mois      : MAX = 200
```

### **2. Monitor AVANT d'Augmenter**

```
Ne pas augmenter si :
- CPU > 80%
- RAM > 85%
- Tokens/min < 5 (feed lag)
- Dashboard lag
```

### **3. Garde une Marge**

```
VPS 4GB = 150 bots max recommandé
Mais tu peux configurer MAX = 200

Pourquoi ?
- Pics temporaires OK
- Mais pas 200 bots 24/7 sur 4GB
```

### **4. Scale AVANT que ce soit urgent**

```
❌ Mauvais : Attendre 200/200 puis scaler
✅ Bon     : Scaler à 160/200 (80%)
```

---

## 🛠️ Troubleshooting

### **Problème : "Serveur complet" mais dashboard montre 150/200**

**Cause** : Bots zombies (crashés mais pas unregistered)
**Solution** :
```bash
# Restart le serveur pour nettoyer
python app.py
```

### **Problème : Performance dégradée à 100 bots (MAX = 200)**

**Cause** : VPS sous-dimensionné
**Solution** : Scale up ton VPS même si pas à la limite

### **Problème : Impossible de démarrer bot même à 50/200**

**Cause** : Bug ou autre limite
**Solution** : Check logs serveur pour l'erreur exacte

---

## 📝 Checklist Déploiement

### **Avant de Lancer**

- [ ] Configurer MAX_CONCURRENT_BOTS selon ton VPS
- [ ] Tester avec 10 bots
- [ ] Vérifier `/admin` affiche correctement
- [ ] Tester "serveur complet" en démarrant MAX+1 bots
- [ ] Configurer alertes externes

### **Pendant le Launch**

- [ ] Monitor `/admin` toutes les heures
- [ ] Noter les pics d'activité
- [ ] Vérifier CPU/RAM du VPS
- [ ] Ajuster MAX si nécessaire

### **Post-Launch**

- [ ] Monitor quotidien pendant 1 semaine
- [ ] Analyser patterns d'utilisation
- [ ] Scaler si > 80% régulièrement
- [ ] Documenter incidents

---

## 🎯 Résumé

### **Configuration Actuelle**

```
MAX_CONCURRENT_BOTS : 200
VPS Recommandé      : 4GB RAM ($40/mois)
Limite Confortable  : 150 bots
Alerte à            : 160 bots (80%)
Protection          : ✅ Activée
```

### **APIs Disponibles**

```
/api/admin/stats     → Stats complètes
/api/admin/capacity  → Info capacité
/api/admin/health    → Health check
/admin               → Dashboard visuel
```

### **Statuts de Capacité**

```
0-100   bots : LOW     → Tout va bien
100-160 bots : HEALTHY → Normal
160-200 bots : WARNING → Surveille !
200+    bots : FULL    → Refuse nouveaux
```

---

## ✅ Action Items

**Pour toi MAINTENANT** :

1. ✅ Limites configurées (MAX = 200)
2. ✅ Protection activée dans app.py
3. ✅ Dashboard montre capacité
4. ✅ APIs disponibles

**Avant Production** :

1. [ ] Décide ton MAX selon VPS
2. [ ] Teste le scénario "serveur plein"
3. [ ] Configure alertes externes
4. [ ] Documente ton plan de scaling

---

**🎯 Tu es maintenant protégé contre les surcharges ! 🚀**

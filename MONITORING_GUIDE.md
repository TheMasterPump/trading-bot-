# 📊 Guide de Monitoring - Architecture Optimisée

## 🎯 Vue d'Ensemble

Le système de monitoring en temps réel te permet de surveiller l'infrastructure optimisée pour 200+ utilisateurs.

---

## 🚀 Accès au Monitoring

### **Option 1 : Dashboard Web** (Recommandé)

```
URL: http://localhost:5001/admin
```

**Dashboard inclut** :
- ✅ Nombre de bots actifs
- ✅ Stats du WebSocket Feed partagé
- ✅ Stats du Trading Engine centralisé
- ✅ Liste détaillée des bots actifs
- ✅ Auto-refresh toutes les 5 secondes
- ✅ Design cyberpunk avec Matrix effect

**Captures d'écran** :
```
┌────────────────────────────────────────────┐
│  ADMIN MONITORING                           │
├────────────────────────────────────────────┤
│  Active Bots: 15     Tokens: 1,234         │
│  Signals: 89         Architecture: OPTIMIZED│
│                                             │
│  WebSocket Feed:     Trading Engine:        │
│  ✓ RUNNING          15 Active Bots         │
│  1 Subscribers      1,234 Tokens Analyzed  │
│  1,234 Tokens       89 Signals Sent        │
│  Uptime: 2h 15m     Max: 200+ users        │
└────────────────────────────────────────────┘
```

### **Option 2 : API JSON**

```bash
# Stats complètes
curl http://localhost:5001/api/admin/stats

# Health check
curl http://localhost:5001/api/admin/health
```

**Response Example** :
```json
{
  "success": true,
  "timestamp": "2025-11-20T19:45:00",
  "stats": {
    "active_bots": 15,
    "architecture": "OPTIMIZED_CENTRALIZED",
    "max_capacity": "200+ users",
    "feed_stats": {
      "is_running": true,
      "subscribers": 1,
      "tokens_received": 1234,
      "uptime_seconds": 8100,
      "tokens_per_minute": 15.2
    },
    "engine_stats": {
      "active_bots": 15,
      "tokens_analyzed": 1234,
      "signals_sent": 89,
      "bots": [
        {
          "user_id": 1,
          "signals_received": 12,
          "uptime": 7200
        }
      ]
    }
  }
}
```

---

## 📈 Métriques Disponibles

### **1. System-Level Metrics**

| Métrique | Description | Unité |
|----------|-------------|-------|
| **active_bots** | Nombre total de bots actifs | Count |
| **architecture** | Type d'architecture | String |
| **max_capacity** | Capacité maximale | String |

### **2. WebSocket Feed Metrics**

| Métrique | Description | Unité |
|----------|-------------|-------|
| **is_running** | État du feed partagé | Boolean |
| **subscribers** | Nombre de subscribers (devrait être 1 = engine) | Count |
| **tokens_received** | Tokens reçus depuis PumpFun | Count |
| **uptime_seconds** | Temps de fonctionnement | Seconds |
| **tokens_per_minute** | Débit de tokens | Rate |

### **3. Trading Engine Metrics**

| Métrique | Description | Unité |
|----------|-------------|-------|
| **active_bots** | Bots enregistrés | Count |
| **tokens_analyzed** | Tokens analysés (1x au lieu de 200x) | Count |
| **signals_sent** | Signaux de trading envoyés | Count |
| **bots[]** | Détails par bot | Array |

### **4. Per-Bot Metrics**

| Métrique | Description | Unité |
|----------|-------------|-------|
| **user_id** | ID de l'utilisateur | Integer |
| **signals_received** | Signaux reçus | Count |
| **uptime** | Durée d'activité | Seconds |

---

## 🔍 Interprétation des Métriques

### **Tout Va Bien ✅**

```
Active Bots: 15
Feed: RUNNING (1 subscriber)
Tokens/Min: 12-20
Uptime: > 1 hour
```

**Indicateurs** :
- Feed status = RUNNING
- Subscribers = 1 (le Trading Engine)
- Active bots = Nombre réel d'utilisateurs
- Tokens/min > 10 (PumpFun actif)

### **Problèmes Potentiels ⚠️**

#### **Feed Stopped**
```
Feed: STOPPED
Tokens/Min: 0
```
**Cause** : Connexion WebSocket perdue
**Solution** :
```python
# Auto-reconnect devrait gérer ça
# Si ça persiste, restart le serveur
```

#### **Subscribers = 0**
```
Feed: RUNNING
Subscribers: 0
```
**Cause** : Engine pas démarré
**Solution** : Vérifie les logs du serveur

#### **Tokens/Min = 0**
```
Feed: RUNNING
Tokens/Min: 0
```
**Cause** : PumpFun pas actif ou problème réseau
**Solution** : Attends quelques minutes

#### **Active Bots Discrepancy**
```
Feed Active Bots: 10
Engine Active Bots: 15
```
**Cause** : Désynchronisation (rare)
**Solution** : Restart les bots ou serveur

---

## 📊 Monitoring en Production

### **Setup avec Prometheus (Optionnel)**

Si tu veux exporter vers Prometheus :

```python
# Dans app.py
from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)

@app.route('/metrics')
def metrics_endpoint():
    # Expose metrics for Prometheus
    pass
```

### **Setup avec Grafana (Optionnel)**

1. Install Grafana
2. Add Prometheus as datasource
3. Create dashboard with :
   - Active Bots (gauge)
   - Tokens/Min (graph)
   - Signals/Min (graph)
   - Uptime (stat)

### **Alerting**

Configurer des alertes si :

```python
# Alert conditions
if active_bots > 180:
    alert("Approaching capacity limit (200)")

if feed_status == "STOPPED" for > 5 minutes:
    alert("Feed connection lost")

if tokens_per_minute == 0 for > 10 minutes:
    alert("No tokens received from PumpFun")
```

---

## 🐛 Troubleshooting

### **Dashboard ne charge pas**

```bash
# Vérifier que le serveur tourne
curl http://localhost:5001/api/admin/health

# Vérifier les logs
tail -f app.log
```

### **Stats = 0 partout**

**Cause** : Aucun bot démarré
**Solution** : Démarre au moins 1 bot via `/bot`

### **"Architecture optimisée not available"**

**Cause** : Import de `trading_service` au lieu de `trading_service_optimized`
**Solution** : Vérifie `app.py` ligne 21

---

## 🔐 Sécurité en Production

### **Protéger le Dashboard**

```python
# Dans app.py
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check admin token or IP whitelist
        admin_token = request.headers.get('X-Admin-Token')
        if admin_token != os.environ.get('ADMIN_TOKEN'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/admin/stats')
@admin_required
def admin_stats():
    # ...
```

### **IP Whitelist**

```python
ALLOWED_IPS = ['127.0.0.1', '10.0.0.1']  # Ton IP

@app.before_request
def limit_admin_routes():
    if request.path.startswith('/admin') or request.path.startswith('/api/admin'):
        if request.remote_addr not in ALLOWED_IPS:
            abort(403)
```

---

## 📝 Logs

### **Types de Logs**

```
[FEED] Starting...                  # Feed démarre
[FEED] Connected successfully!      # Connexion OK
[FEED] 100 tokens processed        # Checkpoint tous les 100

[ENGINE] Starting trading engine... # Engine démarre
[ENGINE] Bot registered: User 1    # Bot s'enregistre
[ENGINE] Signal BUY → User 1       # Signal envoyé

[BOT 1] Starting...                # Bot démarre
[BOT 1] Ready! Waiting...          # Bot prêt
[BOT 1] BUY signal: abc123...      # Bot reçoit signal
```

### **Rechercher dans les Logs**

```bash
# Tous les signaux BUY envoyés
grep "Signal BUY" app.log

# Stats du feed
grep "[FEED]" app.log

# Erreurs
grep "ERROR" app.log

# Bot spécifique
grep "BOT 5" app.log
```

---

## 🎯 Bonnes Pratiques

### **1. Monitor Régulièrement**

- Ouvre `/admin` tous les jours
- Vérifie que le feed tourne
- Vérifie tokens/min > 10

### **2. Garde les Logs**

```bash
# Rotation des logs tous les jours
python app.py >> logs/app_$(date +%Y%m%d).log 2>&1
```

### **3. Set des Alertes**

- Utilise un service comme UptimeRobot
- Ping `/api/admin/health` toutes les 5 minutes
- Alerte si DOWN

### **4. Backup Stats**

```python
# Script pour sauvegarder les stats
import json
from datetime import datetime

stats = requests.get('http://localhost:5001/api/admin/stats').json()

with open(f'stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
    json.dump(stats, f, indent=2)
```

---

## 📊 Exemple d'Analyse

### **Jour Typique**

```
00:00 - 06:00: 5-10 bots actifs, 8 tokens/min
06:00 - 12:00: 20-40 bots actifs, 15 tokens/min (peak morning)
12:00 - 18:00: 50-80 bots actifs, 12 tokens/min
18:00 - 00:00: 30-50 bots actifs, 10 tokens/min
```

### **Analyse de Performance**

```
Total Tokens Analyzed: 10,000
Total Signals Sent: 500
Signal Rate: 5% (1 signal tous les 20 tokens)

Avec l'ancienne archi:
- 200 bots x 10,000 analyses = 2,000,000 analyses
- CPU: 100%

Avec la nouvelle archi:
- 1 x 10,000 analyses = 10,000 analyses
- CPU: 10%
- 💰 Économie: 99.5%
```

---

## ✅ Checklist de Monitoring

### **Quotidien**
- [ ] Ouvrir `/admin` et vérifier les stats
- [ ] Feed status = RUNNING
- [ ] Tokens/min > 5
- [ ] Pas d'erreurs dans les logs

### **Hebdomadaire**
- [ ] Analyser les pics d'activité
- [ ] Vérifier les capacités (si > 150 bots, prévoir scale)
- [ ] Archiver les logs

### **Mensuel**
- [ ] Comparer les performances mois par mois
- [ ] Optimiser les filtres du trading engine si besoin
- [ ] Mettre à jour les dépendances

---

## 🚀 Résumé

**Dashboard** : `http://localhost:5001/admin`
**API** : `http://localhost:5001/api/admin/stats`
**Health** : `http://localhost:5001/api/admin/health`

**Métriques Clés** :
- Active Bots
- Feed Status (doit être RUNNING)
- Tokens/Min (doit être > 5)
- Signals Sent

**Problèmes Communs** :
- Feed stopped → Auto-reconnect ou restart
- Tokens/min = 0 → PumpFun inactif, attendre
- No bots → Démarrer des bots via `/bot`

---

**🎯 Tu as maintenant un monitoring pro pour 200+ users !**

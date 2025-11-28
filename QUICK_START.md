# 🚀 DÉPLOIEMENT RAPIDE - RÉSUMÉ

## 1️⃣ CRÉER LE SERVEUR (5 min)
- Va sur **DigitalOcean.com**
- Crée un compte (bonus $200 de crédit gratuit)
- Crée un Droplet : Ubuntu 22.04, $6/mois, 1GB RAM
- Note l'adresse IP

## 2️⃣ SE CONNECTER (1 min)
```powershell
ssh root@VOTRE_IP
```

## 3️⃣ INSTALLER TOUT (10 min)
```bash
# Mises à jour
apt update && apt upgrade -y

# Python + outils
apt install -y python3.11 python3.11-venv python3-pip git nginx supervisor

# Créer utilisateur
adduser tradingbot
usermod -aG sudo tradingbot
```

## 4️⃣ TÉLÉCHARGER VOTRE CODE (2 min)
```bash
cd /home/tradingbot
git clone VOTRE_REPO_GITHUB trading-bot
cd trading-bot
```

## 5️⃣ INSTALLER DÉPENDANCES (5 min)
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 6️⃣ CONFIGURER .ENV (2 min)
```bash
nano .env
```
Ajoutez vos clés API, puis `Ctrl+X → Y → Enter`

## 7️⃣ CRÉER LE SCRIPT DE DÉMARRAGE (2 min)
```bash
cat > start.sh << 'SCRIPT'
#!/bin/bash
cd /home/tradingbot/trading-bot
source venv/bin/activate
gunicorn --bind 0.0.0.0:5001 --workers 4 --timeout 120 app:app
SCRIPT

chmod +x start.sh
```

## 8️⃣ CONFIGURER SUPERVISOR (3 min)
```bash
cat > /etc/supervisor/conf.d/tradingbot.conf << 'CONFIG'
[program:tradingbot]
command=/home/tradingbot/trading-bot/start.sh
directory=/home/tradingbot/trading-bot
user=tradingbot
autostart=true
autorestart=true
stderr_logfile=/var/log/tradingbot.err.log
stdout_logfile=/var/log/tradingbot.out.log
CONFIG

supervisorctl reread
supervisorctl update
supervisorctl start tradingbot
```

## 9️⃣ CONFIGURER NGINX (3 min)
```bash
cat > /etc/nginx/sites-available/tradingbot << 'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
NGINX

ln -s /etc/nginx/sites-available/tradingbot /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

## 🔟 FIREWALL (1 min)
```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
```

## ✅ C'EST FINI !
Allez sur `http://VOTRE_IP` dans votre navigateur

**Votre bot est en ligne ! 🎉**

---

## 📊 COMMANDES UTILES

```bash
# Voir les logs
tail -f /var/log/tradingbot.out.log

# Redémarrer
supervisorctl restart tradingbot

# Mettre à jour le code
cd /home/tradingbot/trading-bot
git pull
supervisorctl restart tradingbot
```

---

**Total : ~30 minutes pour tout installer ! 🚀**

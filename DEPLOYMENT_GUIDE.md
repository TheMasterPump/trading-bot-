# 🚀 GUIDE DE DÉPLOIEMENT - BOT DE TRADING SUR VPS

## 📋 CE QUE VOUS ALLEZ FAIRE

1. Créer un serveur VPS sur DigitalOcean ($6/mois)
2. Configurer le serveur Ubuntu
3. Installer votre bot
4. Configurer Nginx (serveur web)
5. Installer SSL/HTTPS gratuit
6. Faire tourner le bot 24/7

**Temps estimé : 45-60 minutes**

---

## ÉTAPE 1 : CRÉER UN COMPTE DIGITALOCEAN

### 1.1 Créer le compte
1. Allez sur : https://www.digitalocean.com
2. Cliquez sur **"Sign Up"**
3. Utilisez votre email + créez un mot de passe
4. **BONUS** : Utilisez ce lien pour $200 de crédit gratuit (4 mois gratuits !) :
   https://m.do.co/c/your-referral-code

### 1.2 Ajouter un moyen de paiement
- Carte bancaire OU PayPal
- Vous ne serez facturé qu'après avoir utilisé les crédits gratuits

---

## ÉTAPE 2 : CRÉER LE SERVEUR (DROPLET)

### 2.1 Créer un nouveau Droplet
1. Cliquez sur **"Create" → "Droplets"**
2. **Région** : Choisissez le plus proche de vos utilisateurs
   - Europe : `Frankfurt` ou `Amsterdam`
   - USA : `New York` ou `San Francisco`
3. **Image** :
   - Choisissez **Ubuntu 22.04 LTS**
4. **Droplet Type** :
   - Choisissez **Basic**
5. **CPU Options** :
   - Choisissez **Regular (Disk: SSD)**
6. **Taille** :
   - **$6/mois** : 1 GB RAM, 1 CPU, 25 GB SSD ✅ RECOMMANDÉ pour commencer
   - **$12/mois** : 2 GB RAM, 1 CPU, 50 GB SSD (si > 100 utilisateurs)

### 2.2 Authentification
- Choisissez **"Password"** (plus simple pour commencer)
- Créez un **mot de passe fort** (notez-le bien !)

### 2.3 Finaliser
1. **Hostname** : `trading-bot` (ou un nom de votre choix)
2. Cliquez sur **"Create Droplet"**
3. **Attendez 1-2 minutes** que le serveur se créée

### 2.4 Récupérer l'IP
- Vous verrez une **adresse IP** (ex: `142.93.xxx.xxx`)
- **NOTEZ CETTE IP !** Vous en aurez besoin

---

## ÉTAPE 3 : SE CONNECTER AU SERVEUR

### 3.1 Depuis Windows (votre cas)

**Option A : Utiliser PowerShell** (recommandé)
```powershell
ssh root@VOTRE_IP
```
Remplacez `VOTRE_IP` par l'IP de votre serveur

**Option B : Utiliser PuTTY**
1. Téléchargez PuTTY : https://www.putty.org/
2. Lancez PuTTY
3. Entrez votre IP dans "Host Name"
4. Cliquez "Open"

### 3.2 Premier login
- Entrez le mot de passe que vous avez créé
- Vous verrez : `root@trading-bot:~#`
- **Vous êtes connecté !** ✅

---

## ÉTAPE 4 : CONFIGURER LE SERVEUR

### 4.1 Mettre à jour le système
```bash
apt update && apt upgrade -y
```

### 4.2 Installer Python 3.11
```bash
apt install -y python3.11 python3.11-venv python3-pip
```

### 4.3 Installer les dépendances système
```bash
apt install -y git nginx supervisor
```

### 4.4 Créer un utilisateur (sécurité)
```bash
adduser tradingbot
usermod -aG sudo tradingbot
```
- Créez un mot de passe
- Appuyez sur Entrée pour les autres questions

---

## ÉTAPE 5 : TRANSFÉRER VOTRE CODE

### 5.1 Option A : Via Git (RECOMMANDÉ)

**Sur votre PC local :**
1. Créez un dépôt GitHub privé
2. Uploadez votre code :
```bash
cd "C:\Users\user\Desktop\project\prediction AI modele 2"
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/VOTRE_USERNAME/VOTRE_REPO.git
git push -u origin main
```

**Sur le serveur :**
```bash
cd /home/tradingbot
git clone https://github.com/VOTRE_USERNAME/VOTRE_REPO.git trading-bot
cd trading-bot
```

### 5.2 Option B : Via SCP (si pas de Git)

**Sur votre PC local (PowerShell) :**
```powershell
scp -r "C:\Users\user\Desktop\project\prediction AI modele 2" root@VOTRE_IP:/home/tradingbot/trading-bot
```

---

## ÉTAPE 6 : INSTALLER LES DÉPENDANCES PYTHON

**Sur le serveur :**
```bash
cd /home/tradingbot/trading-bot
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Si requirements.txt n'existe pas, installez manuellement :
```bash
pip install flask requests joblib scikit-learn pandas numpy solana solders python-dotenv cryptography websockets aiohttp
```

---

## ÉTAPE 7 : CONFIGURER LES VARIABLES D'ENVIRONNEMENT

### 7.1 Créer le fichier .env
```bash
nano .env
```

### 7.2 Ajouter vos variables :
```
WALLET_ENCRYPTION_KEY=VOTRE_CLE_ICI
PUMPPORTAL_API_KEY=VOTRE_API_KEY_ICI
HELIUS_API_KEY=VOTRE_HELIUS_API_KEY
```

- Appuyez sur `Ctrl+X`, puis `Y`, puis `Entrée` pour sauvegarder

---

## ÉTAPE 8 : CONFIGURER GUNICORN (serveur de production)

### 8.1 Installer Gunicorn
```bash
pip install gunicorn
```

### 8.2 Créer le fichier de démarrage
```bash
nano start.sh
```

Ajoutez :
```bash
#!/bin/bash
cd /home/tradingbot/trading-bot
source venv/bin/activate
gunicorn --bind 0.0.0.0:5001 --workers 4 --timeout 120 app:app
```

### 8.3 Rendre exécutable
```bash
chmod +x start.sh
```

---

## ÉTAPE 9 : CONFIGURER SUPERVISOR (pour tourner 24/7)

### 9.1 Créer la configuration
```bash
nano /etc/supervisor/conf.d/tradingbot.conf
```

### 9.2 Ajouter :
```ini
[program:tradingbot]
command=/home/tradingbot/trading-bot/start.sh
directory=/home/tradingbot/trading-bot
user=tradingbot
autostart=true
autorestart=true
stderr_logfile=/var/log/tradingbot.err.log
stdout_logfile=/var/log/tradingbot.out.log
```

### 9.3 Activer
```bash
supervisorctl reread
supervisorctl update
supervisorctl start tradingbot
```

### 9.4 Vérifier que ça tourne
```bash
supervisorctl status tradingbot
```
Vous devriez voir : `tradingbot RUNNING`

---

## ÉTAPE 10 : CONFIGURER NGINX (serveur web)

### 10.1 Créer la configuration
```bash
nano /etc/nginx/sites-available/tradingbot
```

### 10.2 Ajouter :
```nginx
server {
    listen 80;
    server_name VOTRE_IP;  # Remplacez par votre IP ou domaine

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

### 10.3 Activer et redémarrer
```bash
ln -s /etc/nginx/sites-available/tradingbot /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

---

## ÉTAPE 11 : CONFIGURER LE FIREWALL

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

---

## ÉTAPE 12 : TESTER !

### 12.1 Ouvrez votre navigateur
Allez sur : `http://VOTRE_IP`

**Vous devriez voir votre site ! 🎉**

---

## ÉTAPE 13 (OPTIONNEL) : NOM DE DOMAINE + HTTPS

### 13.1 Si vous avez un nom de domaine

**Chez votre registrar (Namecheap, GoDaddy, etc.) :**
1. Ajoutez un enregistrement DNS de type **A**
2. Pointez vers l'IP de votre serveur
3. Attendez 10-30 minutes (propagation DNS)

### 13.2 Installer SSL gratuit avec Let's Encrypt
```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d votre-domaine.com
```

Suivez les instructions, et voilà ! **HTTPS activé** ✅

---

## 📊 COMMANDES UTILES

### Voir les logs
```bash
tail -f /var/log/tradingbot.out.log
tail -f /var/log/tradingbot.err.log
```

### Redémarrer le bot
```bash
supervisorctl restart tradingbot
```

### Mettre à jour le code
```bash
cd /home/tradingbot/trading-bot
git pull
supervisorctl restart tradingbot
```

### Voir l'utilisation des ressources
```bash
htop
```

---

## 🆘 DÉPANNAGE

### Le site ne s'affiche pas
```bash
supervisorctl status tradingbot
systemctl status nginx
tail -f /var/log/tradingbot.err.log
```

### Trop de RAM utilisée
```bash
free -h
# Upgrader le Droplet si nécessaire
```

---

## 💰 COÛTS MENSUELS

- **Serveur VPS** : $6/mois (1GB RAM) ou $12/mois (2GB RAM)
- **Nom de domaine** : $10-15/an (optionnel)
- **SSL** : Gratuit avec Let's Encrypt

**Total : ~$6-12/mois**

---

## ✅ FÉLICITATIONS !

Votre bot de trading est maintenant en ligne 24/7 ! 🎉

Les utilisateurs peuvent s'inscrire, trader, et utiliser toutes les fonctionnalités.

**Besoin d'aide ?** Demandez-moi !

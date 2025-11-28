# 🔄 Guide de Régénération de Wallet

## 🎯 Problème Résolu

### **Scénario : User Perd sa Clé Privée**

```
User : "J'ai perdu ma clé privée ! 😱"
User : "Je ne peux plus accéder à mon wallet..."
User : "Mes fonds sont bloqués..."
```

### **Solution Implémentée**

```
✅ Bouton "GÉNÉRER NOUVEAU WALLET" dans Settings
✅ Double confirmation de sécurité
✅ Génération d'un nouveau wallet
✅ Affichage de la nouvelle clé privée
✅ Remplacement sécurisé dans la DB
```

---

## 🔧 Fonctionnalités

### **1. Bouton de Régénération**

**Localisation** : Onglet Settings → Section "WALLET MANAGEMENT"

**Apparence** :
- 🔴 Bouton rouge (warning)
- ⚠️ Icône d'alerte
- 📝 Message d'avertissement clair

### **2. Double Confirmation**

**Confirmation 1** :
```
⚠️ ATTENTION !

Tu es sur le point de REMPLACER ton wallet actuel par un nouveau.

AVANT DE CONTINUER:
• Assure-toi d'avoir TRANSFÉRÉ tous tes fonds de l'ancien wallet
• Assure-toi d'avoir SAUVEGARDÉ ta clé privée actuelle (si tu veux la garder)

Veux-tu vraiment continuer ?
```

**Confirmation 2** :
```
🚨 DERNIÈRE CONFIRMATION

As-tu VRAIMENT transféré tous tes fonds de l'ancien wallet ?

Si non, tu vas PERDRE tes fonds !

Continuer ?
```

### **3. Génération du Nouveau Wallet**

**Backend** (`/api/wallet/regenerate`) :
1. ✅ Vérifie que le bot n'est PAS actif
2. ✅ Récupère l'ancien wallet (pour archivage)
3. ✅ Génère nouveau wallet
4. ✅ Chiffre la nouvelle clé privée (AES-256)
5. ✅ Met à jour la DB (remplace l'ancien)
6. ✅ Reset balance à 0 SOL
7. ✅ Retourne la nouvelle clé privée (UNE SEULE FOIS)

### **4. Affichage de la Nouvelle Clé**

**Même Modal que Register** :
- 🚨 Icône warning qui pulse
- 🔴 Titre rouge "SAUVEGARDE TA CLÉ PRIVÉE !"
- ⚠️ "TU NE POURRAS JAMAIS LA REVOIR !"
- 📋 Clé privée complète
- 📥 Boutons COPIER / TÉLÉCHARGER
- ✅ Checkbox obligatoire

---

## 🔐 Sécurité

### **Protections Implémentées**

1. **Bot doit être arrêté**
   ```python
   if bot_status.get('is_running'):
       return error "Arrête ton bot avant de générer un nouveau wallet"
   ```

2. **Double confirmation**
   - Confirmation générale
   - Confirmation de transfert de fonds

3. **Affichage forcé de la nouvelle clé**
   - Modal bloquant
   - Checkbox obligatoire
   - Double-check avant fermeture

4. **Archivage de l'ancien wallet**
   - Ancien wallet address retourné
   - Affiché dans le message de succès
   - User peut noter l'ancienne adresse

---

## 📋 Flow Utilisateur Complet

### **Étape 1 : Accès**

```
1. User va dans l'onglet "Settings"
2. Scroll jusqu'à "WALLET MANAGEMENT"
3. Voit le bouton rouge "GÉNÉRER NOUVEAU WALLET"
```

### **Étape 2 : Transfert des Fonds (CRITIQUE)**

```
⚠️ AVANT DE CLIQUER SUR LE BOUTON :

1. User ouvre Phantom/Solflare avec son ancien wallet
2. User TRANSFÈRE tous ses fonds vers un autre wallet
3. User VÉRIFIE que le solde = 0 SOL
4. User est maintenant prêt à générer un nouveau wallet
```

### **Étape 3 : Génération**

```
1. User clique "GÉNÉRER NOUVEAU WALLET"
   ↓
2. Popup 1 : "⚠️ ATTENTION ! ..."
   User clique "OK"
   ↓
3. Popup 2 : "🚨 DERNIÈRE CONFIRMATION ..."
   User clique "OK"
   ↓
4. API génère le nouveau wallet
   ↓
5. Success message :
   "✅ NOUVEAU WALLET GÉNÉRÉ !

   Ancien wallet: FGh8... (20 premiers caractères)
   Nouveau wallet: Xy9k... (20 premiers caractères)

   Tu vas maintenant voir ta NOUVELLE clé privée.
   SAUVEGARDE-LA IMMÉDIATEMENT !"
```

### **Étape 4 : Sauvegarde de la Nouvelle Clé**

```
🚨 MODAL APPARAÎT 🚨

1. User voit sa nouvelle clé privée complète
2. User clique "COPIER" → Colle dans password manager
   OU
   User clique "TÉLÉCHARGER" → Sauvegarde le fichier .txt
3. User coche "J'ai sauvegardé ma clé privée"
4. User clique "J'AI COMPRIS ET SAUVEGARDÉ"
   ↓
5. Modal se ferme
6. Dashboard se rafraîchit avec le nouveau wallet
```

---

## 🧪 Testing

### **Test 1 : Bot Actif (Devrait Échouer)**

```bash
1. START le bot
2. Va dans Settings
3. Clique "GÉNÉRER NOUVEAU WALLET"
4. Accepte les 2 confirmations

✅ Doit afficher :
   "Erreur: Arrête ton bot avant de générer un nouveau wallet"
```

### **Test 2 : Annulation**

```bash
1. Arrête le bot
2. Clique "GÉNÉRER NOUVEAU WALLET"
3. Clique "ANNULER" sur la première confirmation

✅ Rien ne se passe
```

### **Test 3 : Régénération Complète**

```bash
1. Arrête le bot
2. (Optionnel) Transfère les fonds
3. Clique "GÉNÉRER NOUVEAU WALLET"
4. Accepte les 2 confirmations

✅ Doit :
   - Afficher message de succès avec ancien/nouveau wallet
   - Ouvrir le modal de clé privée
   - Nouvelle clé visible
   - Boutons COPIER/TÉLÉCHARGER fonctionnent
   - Dashboard rafraîchi avec nouveau wallet
```

### **Test 4 : Vérification DB**

```bash
Avant régénération :
- Wallet address : ABC...
- Private key    : xyz... (chiffré)

Après régénération :
- Wallet address : XYZ... (nouveau)
- Private key    : pqr... (nouveau, chiffré)
- Balance        : 0 SOL (reset)
```

---

## 💡 Cas d'Utilisation

### **Cas 1 : Clé Perdue**

```
User : "J'ai perdu ma clé privée sauvegardée"

Solution :
1. Transfère tous les fonds de l'ancien wallet (via le service)
2. Régénère un nouveau wallet
3. Sauvegarde la nouvelle clé
4. Continue d'utiliser le bot avec le nouveau wallet
```

### **Cas 2 : Sécurité Compromise**

```
User : "Je pense que quelqu'un a volé ma clé"

Solution :
1. IMMÉDIATEMENT : Transfère tous les fonds vers un wallet sécurisé
2. Régénère un nouveau wallet
3. Dépose des fonds sur le NOUVEAU wallet seulement
4. Ancienne clé compromise = inutile maintenant
```

### **Cas 3 : Migration Vers Wallet Externe**

```
User : "Je veux utiliser mon propre wallet Phantom"

Solution :
1. Importe la clé privée actuelle dans Phantom
2. Utilise Phantom pour gérer le wallet
3. Le bot continue de fonctionner avec ce wallet
4. Pas besoin de régénérer (déjà possède la clé)
```

### **Cas 4 : Fresh Start**

```
User : "Je veux recommencer à zéro"

Solution :
1. Assure que solde = 0 SOL
2. Régénère nouveau wallet
3. Fresh start avec nouveau wallet
```

---

## ⚠️ Avertissements Importants

### **Pour l'Utilisateur**

1. **TOUJOURS transférer les fonds AVANT de régénérer**
   - ❌ Si tu régénères sans transférer → Fonds PERDUS
   - ✅ Transfère TOUT avant de régénérer

2. **Sauvegarder la NOUVELLE clé immédiatement**
   - La nouvelle clé ne sera JAMAIS affichée à nouveau
   - Même règles que lors du register

3. **Ancien wallet ≠ Perdu**
   - Si tu as sauvegardé l'ancienne clé, tu peux toujours l'utiliser
   - Mais le bot utilisera le NOUVEAU wallet

4. **Balance reset à 0**
   - Le nouveau wallet commence avec 0 SOL
   - Dépose des fonds pour commencer le trading

### **Pour le Développeur (Toi)**

1. **Pas de récupération de l'ancien wallet**
   - Une fois remplacé, impossible de revenir
   - Archive l'ancienne adresse mais pas la clé

2. **User responsabilité**
   - Si user perd fonds = sa responsabilité
   - Warnings suffisamment clairs

3. **Bot doit être arrêté**
   - Protection contre conflit
   - Force user à arrêter avant régénération

---

## 🔧 Implémentation Technique

### **Backend (app.py)**

**Endpoint** : `POST /api/wallet/regenerate`

```python
@app.route('/api/wallet/regenerate', methods=['POST'])
@login_required
def regenerate_wallet():
    # 1. Vérifier bot arrêté
    bot_status = get_bot_status(user_id)
    if bot_status.get('is_running'):
        return error 400

    # 2. Récupérer ancien wallet
    old_wallet = db.get_wallet(user_id)

    # 3. Générer nouveau
    new_wallet_info = wallet_manager.generate_wallet()

    # 4. Mettre à jour DB
    success = db.update_wallet(user_id, new_wallet_info['address'], new_wallet_info['private_key'])

    # 5. Retourner nouvelle clé (UNE FOIS)
    return jsonify({
        'success': True,
        'wallet': {
            'address': new_wallet_info['address'],
            'private_key': new_wallet_info['private_key'],
            'show_warning': True,
            'old_address': old_wallet['address']
        }
    })
```

### **Database (database_bot.py)**

**Fonction** : `update_wallet(user_id, new_address, new_private_key)`

```python
def update_wallet(self, user_id, new_address, new_private_key):
    # Chiffre la nouvelle clé
    encrypted_key = cipher_suite.encrypt(new_private_key.encode()).decode()

    # Met à jour
    cursor.execute("""
        UPDATE wallets
        SET address = ?,
            private_key_encrypted = ?,
            balance_sol = 0.0,
            balance_usd = 0.0,
            last_updated = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (new_address, encrypted_key, user_id))

    conn.commit()
    return True
```

### **Frontend (bot.html)**

**Section** : Settings Tab → WALLET MANAGEMENT

**Fonctions JS** :
- `confirmRegenerateWallet()` - Double confirmation
- `regenerateWallet()` - Appelle API + affiche modal

---

## ✅ Checklist de Déploiement

### **Backend**

- [x] Endpoint `/api/wallet/regenerate` créé
- [x] Fonction `db.update_wallet()` créée
- [x] Vérification bot arrêté
- [x] Génération nouveau wallet
- [x] Chiffrement de la nouvelle clé
- [x] Retour de la clé privée (une fois)

### **Frontend**

- [x] Section "WALLET MANAGEMENT" dans Settings
- [x] Bouton rouge "GÉNÉRER NOUVEAU WALLET"
- [x] Fonction `confirmRegenerateWallet()` avec double confirmation
- [x] Fonction `regenerateWallet()` pour appeler API
- [x] Réutilisation du modal de clé privée
- [x] Rafraîchissement du dashboard après régénération

### **Sécurité**

- [x] Double confirmation avant action
- [x] Warnings clairs sur transfert de fonds
- [x] Vérification bot arrêté
- [x] Affichage obligatoire de la nouvelle clé
- [x] Checkbox de sauvegarde

---

## 🎯 Résumé

**Problème** : User perd sa clé privée → Bloqué

**Solution** : Bouton de régénération de wallet

**Features** :
- ✅ Double confirmation de sécurité
- ✅ Vérification bot arrêté
- ✅ Génération sécurisée d'un nouveau wallet
- ✅ Affichage obligatoire de la nouvelle clé
- ✅ Warnings clairs sur transfert de fonds
- ✅ Update sécurisé de la DB

**Résultat** :
- 🟢 User peut toujours continuer même s'il perd sa clé
- 🟢 Processus sécurisé avec protections multiples
- 🟢 Transparence totale sur les risques
- 🟢 UX smooth avec réutilisation du modal existant

---

**🔄 Les utilisateurs peuvent maintenant régénérer leur wallet en toute sécurité ! 🚀**

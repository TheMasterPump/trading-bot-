# 🐍 VENOM Token Setup Guide

## Configuration rapide

Quand vous lancerez le token VENOM, suivez ces étapes pour activer la vérification :

### 1. Configurer l'adresse du contrat

Ouvrez le fichier `venom_config.py` et remplacez cette ligne :

```python
VENOM_TOKEN_ADDRESS = "PASTE_YOUR_VENOM_TOKEN_CONTRACT_ADDRESS_HERE"
```

Par l'adresse réelle de votre token :

```python
VENOM_TOKEN_ADDRESS = "VotreTrueAdresseDeTokenIci123..."
```

### 2. Ajuster les paramètres (optionnel)

Vous pouvez modifier ces paramètres dans `venom_config.py` :

```python
# Nombre minimum de tokens VENOM requis
REQUIRED_VENOM_BALANCE = 10_000_000  # 10 millions

# Décimales du token (standard SPL = 9)
VENOM_DECIMALS = 9

# Activer/désactiver la vérification
ENABLE_VENOM_VERIFICATION = True  # False pour désactiver temporairement
```

### 3. Redémarrer le serveur

```bash
# Arrêter le serveur actuel
Ctrl+C

# Redémarrer
python app.py
```

C'est tout ! 🎉

## Comment ça fonctionne

### Pour l'utilisateur :

1. L'utilisateur achète des tokens VENOM sur un DEX (Raydium, Jupiter, etc.)
2. Il envoie 10,000,000 tokens VENOM à son wallet Solana dans le bot
3. Il clique sur "CONNECT WALLET" dans l'onglet ACCESS
4. Le bot vérifie automatiquement son solde sur la blockchain
5. Si >= 10M tokens → Accès débloqué ✅
6. Si < 10M tokens → Accès refusé, message avec le nombre manquant ❌

### Pour le bot :

Le bot utilise l'API RPC de Solana pour :
- Interroger le solde de tokens SPL pour un wallet donné
- Vérifier que le token mint correspond à VENOM_TOKEN_ADDRESS
- Comparer le solde avec REQUIRED_VENOM_BALANCE

### Endpoints RPC utilisés :

Le bot essaie plusieurs endpoints RPC Solana pour la redondance :
- `https://api.mainnet-beta.solana.com`
- `https://solana-api.projectserum.com`

## Avantages du système

✅ **Pas d'abonnement** - Une seule fois, les users achètent et gardent les tokens
✅ **Pas de paiements récurrents** - Simplifie la gestion
✅ **Valeur du token** - Plus de demande pour le bot = plus de valeur pour VENOM
✅ **Transparence** - Tout se passe on-chain, vérifiable par tous
✅ **Flexibilité** - Les users peuvent revendre leurs tokens s'ils veulent

## Période de transition

Le code supporte actuellement DEUX systèmes en parallèle :

1. **Ancien système** : Abonnements RISKY/SAFE (pour les users existants)
2. **Nouveau système** : Tokens VENOM

Un utilisateur peut accéder au bot s'il a :
- 10M tokens VENOM **OU**
- Un abonnement RISKY/SAFE actif

Cela permet une transition en douceur sans perdre les utilisateurs existants.

### Pour désactiver l'ancien système :

Dans `app.py`, ligne ~830, changez :

```python
can_use_real_mode = can_use_real_mode_venom or (boost_level in ['RISKY', 'SAFE'])
```

En :

```python
can_use_real_mode = can_use_real_mode_venom  # VENOM tokens seulement
```

## Test sans token (dev mode)

Pour tester sans avoir lancé le token VENOM :

Dans `venom_config.py`, mettez :

```python
ENABLE_VENOM_VERIFICATION = False
```

⚠️ Cela donnera accès à TOUS les utilisateurs (mode dev uniquement !)

## Debugging

Les logs VENOM apparaissent dans la console avec le préfixe `[VENOM]` :

```
[VENOM] User 123 verification: ✅ Access granted! You have 15,000,000 VENOM tokens
[VENOM] Wallet 7x9B2... has 15,000,000 VENOM tokens
```

## Support et questions

Pour toute question sur l'intégration VENOM :
1. Vérifiez que l'adresse du contrat est correcte
2. Vérifiez les logs `[VENOM]` dans la console
3. Testez manuellement l'endpoint `/api/venom/check` avec curl ou Postman
4. Vérifiez que les RPC endpoints Solana sont accessibles

## Fichiers concernés

- `venom_config.py` - Configuration du token
- `venom_verifier.py` - Logique de vérification
- `app.py` - Intégration backend
- `bot.html` - Interface frontend
- `VENOM_SETUP.md` - Ce fichier !

---

**🐍 Bon lancement avec VENOM !**

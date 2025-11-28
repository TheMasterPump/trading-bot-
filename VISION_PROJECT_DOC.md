# VISION AI - Documentation Projet

## Qu'est-ce que VISION ?

**VISION** est une plateforme de trading automatique basee sur l'intelligence artificielle, specialisee dans la detection de tokens a fort potentiel sur la blockchain Solana.

---

## Architecture du Systeme

### 1. VISION AI - Modele de Prediction

Notre modele d'IA a ete entraine sur **des milliers de tokens** pour predire leur potentiel de ROI (Return on Investment).

**Donnees d'entrainement :**
- Analyse de milliers de tokens historiques
- Extraction de 61 features par token
- Donnees on-chain (transactions, holders, liquidite)
- Patterns de prix et volumes
- Comportement des wallets (dev, snipers, whales)

**Performance du modele :**
- Accuracy : 94.74%
- Algorithme : Random Forest Classifier
- Features : 61 indicateurs analyses

**Categories de prediction :**
| Categorie | ROI Potentiel | Recommandation |
|-----------|---------------|----------------|
| GEM | > 500% | Forte opportunite |
| POTENTIAL | 100-500% | Opportunite moderee |
| RISKY | 0-100% | Risque eleve |
| RUG | < 0% | Eviter |

---

### 2. Scanner Automatique de Tokens

Le scanner VISION analyse en temps reel tous les nouveaux tokens lances sur Solana.

**Fonctionnement :**
```
WebSocket (PumpPortal) -> Nouveaux tokens detectes
        |
        v
   VISION AI analyse le token
        |
        v
   Score de confiance calcule
        |
        v
   Signal : BUY / SKIP / WAIT
```

**Analyse effectuee :**
- Market cap initial
- Distribution des holders
- Activite des transactions
- Profil du developpeur
- Liquidite disponible
- Patterns de trading suspects

---

### 3. Bot de Trading Automatique

Le bot execute automatiquement les trades bases sur les predictions de VISION AI.

**Strategies disponibles :**

| Strategy | Description | Risque |
|----------|-------------|--------|
| RISQUER | Achats agressifs, haute frequence | Eleve |
| SAFE | Filtres stricts, moins de trades | Modere |
| ULTRA | Combinaison optimisee | Variable |

**Parametres configurables :**
- Investment par trade (en SOL)
- Take Profit (x2, x3, personnalise)
- Stop Loss (% de perte max)
- Strategies de sortie (avant/apres migration, progressif)

**Strategies de Take Profit :**
1. **Simple Multiplier** - Vend tout a x2, x3, etc.
2. **Partial Hold** - Vend une partie, garde le reste
3. **Exit Before Migration** - Sort avant le passage sur Raydium
4. **Progressive After Migration** - Vend par paliers apres migration
5. **All-in After Migration** - Attend migration puis vend tout

---

### 4. Systeme de Wallets

Chaque utilisateur possede son propre wallet Solana genere automatiquement.

**Securite :**
- Cle privee affichee UNE SEULE FOIS (a la creation)
- Stockage chiffre AES-256 dans la base de donnees
- Compatible avec Phantom, Solflare, Backpack
- Possibilite de regenerer un nouveau wallet

**Important :** L'utilisateur est responsable de sauvegarder sa cle privee. Aucune recuperation possible si perdue.

---

## Fonctionnalites Principales

### Pour les Utilisateurs

- **Dashboard** : Vue d'ensemble des performances
- **Wallet** : Gestion des fonds et adresse de depot
- **Trades** : Historique complet des transactions
- **Settings** : Configuration du bot et strategies
- **Scanner** : Vue en temps reel des detections AI (abonnes)

### Pour le Systeme

- **Architecture scalable** : Supporte 200+ utilisateurs simultanees
- **WebSocket partage** : Un seul flux pour tous les utilisateurs
- **Moteur centralise** : Analyse unique par token (pas de duplication)
- **Monitoring admin** : Dashboard de supervision en temps reel

---

## Securite et Transparence

### Approche Non-Custodial

VISION utilise une approche **hybride** :
- L'utilisateur POSSEDE sa cle privee
- Le systeme garde une copie chiffree (pour le trading auto)
- L'utilisateur peut retirer ses fonds a tout moment via un wallet externe

### Protections

- Double confirmation pour actions sensibles
- Verification du bot arrete avant regeneration wallet
- Chiffrement AES-256 pour les cles privees
- Limites de capacite serveur (max bots simultanes)

---

## Stack Technique

**Backend :**
- Python / Flask
- SQLite (base de donnees)
- WebSocket (flux temps reel)
- Asyncio (traitement concurrent)

**Frontend :**
- HTML5 / CSS3 / JavaScript
- Bootstrap 5
- Design Cyberpunk/Terminal

**Blockchain :**
- Solana (SPL tokens)
- RPC Solana mainnet
- Integration PumpPortal

**Machine Learning :**
- Scikit-learn (Random Forest)
- Feature extraction personnalisee
- 61 features par token

---

## Comment ca marche ?

### Etape 1 : Inscription
1. Creer un compte (email/password)
2. Un wallet Solana est genere automatiquement
3. SAUVEGARDER la cle privee (affichee une seule fois!)

### Etape 2 : Depot
1. Copier l'adresse du wallet
2. Envoyer des SOL depuis un exchange ou wallet externe
3. Le solde se met a jour automatiquement

### Etape 3 : Configuration
1. Choisir une strategie (RISQUER / SAFE / ULTRA)
2. Definir le montant par trade
3. Configurer le Take Profit et Stop Loss

### Etape 4 : Trading
1. Cliquer "START BOT"
2. Le bot scanne automatiquement les nouveaux tokens
3. Achete quand VISION AI detecte un GEM
4. Vend selon la strategie configuree

---

## Performances et Stats

Le scanner affiche en temps reel :
- Nombre de tokens scannes
- GEMs detectes
- Taux de reussite (win rate)
- Performance moyenne
- Meilleur trade

**Affichage public :** Stats agregees + Wins recents (delai 2h)
**Affichage prive :** Scanner live + Detections en temps reel

---

## FAQ

**Q: Est-ce que je possede vraiment mon wallet ?**
R: Oui, la cle privee vous est donnee a la creation. Vous pouvez l'importer dans Phantom/Solflare a tout moment.

**Q: Que se passe-t-il si je perds ma cle privee ?**
R: Vous pouvez regenerer un nouveau wallet dans les Settings. Assurez-vous de transferer vos fonds avant!

**Q: Combien de temps le bot trade-t-il ?**
R: 24/7 tant qu'il est actif et que vous avez des fonds.

**Q: Quelle est la performance attendue ?**
R: Les performances passees ne garantissent pas les resultats futurs. Le trading crypto est risque.

**Q: Mes fonds sont-ils en securite ?**
R: Vous controlez votre wallet. Le bot ne peut que trader, pas retirer vers d'autres adresses.

---

## Avertissement

**IMPORTANT :** Le trading de cryptomonnaies comporte des risques significatifs.

- Ne tradez qu'avec des fonds que vous pouvez vous permettre de perdre
- Les predictions AI ne sont pas des garanties de profit
- DYOR (Do Your Own Research) - Faites vos propres recherches
- Les performances passees ne predisent pas les resultats futurs

---

## Contact et Support

Pour toute question ou probleme technique, consultez la documentation ou contactez le support.

---

**VISION AI** - Trading intelligent sur Solana

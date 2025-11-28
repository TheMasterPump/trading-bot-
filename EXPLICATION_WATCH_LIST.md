# EXPLICATION - Système de Watch List

## Problème Identifié

### Ancien Système ❌
```
Token "cliguer AI" apparait à $8k
Bot vérifie: $8k < $9.5k minimum
Bot marque comme "vu" et ignore
Token monte à $9k, $10k, $21k...
Bot ne réévalue JAMAIS car déjà "vu"
```

**Résultat**: On rate des opportunités qui commencent juste en dessous de notre fenêtre !

## Nouvelle Solution ✅

### Système de Watch List

```
Token "cliguer AI" apparait à $8k
Bot vérifie: $8k < $9.5k minimum
Bot AJOUTE à la WATCH LIST (ne marque PAS comme "vu")

Toutes les 10 secondes:
  Bot vérifie tous les tokens dans la watch list
  Si token monte dans $9.5k-$13k → ACHETER
  Si token trop vieux (>30 min) → RETIRER
  Si token au dessus de $13k → RETIRER
```

### 3 Cas de Figure

**Cas 1: Token EN DESSOUS de $9.5k**
```python
if mc_usd < OPTIMAL_WINDOW['min_mc']:
    # Ajouter à watch_list
    # NE PAS marquer comme "vu"
    # Surveiller continuellement
```

**Cas 2: Token DANS la fenêtre ($9.5k-$13k)**
```python
if OPTIMAL_WINDOW['min_mc'] <= mc_usd <= OPTIMAL_WINDOW['max_mc']:
    # Évaluer le score
    # Acheter si score >= 50
    # Marquer comme "vu"
    # Retirer de watch_list si présent
```

**Cas 3: Token AU-DESSUS de $13k**
```python
if mc_usd > OPTIMAL_WINDOW['max_mc']:
    # Ignorer
    # Marquer comme "vu"
    # Retirer de watch_list si présent
```

## Exemple Concret

### "cliguer AI" Scénario

```
T+0s:  Token apparait à $8,000
       → Ajouté à watch_list
       → Pas acheté (trop bas)

T+10s: Check watch list
       → cliguer AI maintenant à $8,500
       → Toujours < $9.5k, continuer surveillance

T+20s: Check watch list
       → cliguer AI maintenant à $9,800 ✅
       → DANS la fenêtre !
       → Calculer score
       → Score = 65/100 → HIGH CONFIDENCE
       → ACHETER 2.5 SOL

T+60s: cliguer AI migre à $69,000
       → Multi-sell automatique
       → Profit: +14 SOL (+560% ROI)
```

## Avantages

1. **Capture les montées rapides**: Tokens qui commencent à $7k-$9k et explosent
2. **Pas de faux positifs**: On vérifie toujours le score avant d'acheter
3. **Nettoyage automatique**: Tokens trop vieux sont retirés
4. **Efficace**: Check toutes les 10 secondes, pas de spam

## Dashboard V2

### Nouvelle Section: WATCH LIST

```
[WATCH LIST] (Tokens below $9.5k)
  CLIGUER   $8,000 [████████░░░░░░░░░░░░] 84% - 1m
  PEPE2     $7,500 [███████░░░░░░░░░░░░░] 79% - 3m
  DOGE3     $6,200 [██████░░░░░░░░░░░░░░] 65% - 8m
```

La barre de progression montre combien le token est proche de $9.5k.

## Utilisation

### V1 (sans watch list):
```bash
python live_dashboard_bot.py
```

### V2 (AVEC watch list - RECOMMANDÉ):
```bash
python live_dashboard_bot_v2.py
```

## Conclusion

Le système de watch list résout le problème de "cliguer AI" et nous permet de capturer **tous les tokens qui montent dans notre fenêtre optimale**, même s'ils commencent en dessous !

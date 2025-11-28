#!/usr/bin/env python3
# Script to translate ALL remaining French text in bot.html to English

import re

# Read the file
with open('templates/bot.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Dictionary of French -> English translations
translations = {
    # Mode Toggle
    "Simulation/Réel": "Simulation/Real",
    "MODE RÉEL": "REAL MODE",

    # Strategy options
    "Recommandé": "Recommended",
    "STRATÉGIE DE TAKE PROFIT": "TAKE PROFIT STRATEGY",
    "Vendre Tout à xN (Simple)": "Sell All at xN (Simple)",
    "Vente Progressive Après Migration": "Progressive Sale After Migration",
    "Vendre Tout Après Migration": "Sell All After Migration",

    # Configuration labels
    "Configuration dynamique selon la stratégie": "Dynamic configuration based on strategy",
    "Multiplier (vendre à x?)": "Multiplier (sell at x?)",
    "% à vendre au premier TP": "% to sell at first TP",
    "Vendre 100% à cette market cap": "Sell 100% at this market cap",
    "% à vendre par étape après migration": "% to sell per step after migration",
    "Délai entre chaque vente (secondes)": "Delay between each sale (seconds)",
    "Vendre 100% dès migration atteinte": "Sell 100% when migration reached",
    "Vente automatique si perte dépasse ce %": "Automatic sale if loss exceeds this %",

    # Trailing Stop Loss
    "COMMENT ÇA MARCHE ?": "HOW DOES IT WORK?",
    "Si tu fais +80% de profit, SL monte à +X%": "If you make +80% profit, SL rises to +X%",
    "Si tu fais +50% de profit, SL monte à +X% (0 = breakeven)": "If you make +50% profit, SL rises to +X% (0 = breakeven)",

    # Comments and status
    "Afficher le modal de clé privée si présent": "Show private key modal if present",
    "Emoji de statut CORRECT basé sur partial_sold et migration_reached": "CORRECT status emoji based on partial_sold and migration_reached",
    "Distance à la migration": "Distance to migration",
    "Profit récupéré": "Profit recovered",
    "Déterminer la couleur selon le type": "Determine color based on type",
    "Vert par défaut": "Green by default",

    # Mode selection comments
    "Par défaut": "By default",
    "Charger les infos utilisateur au démarrage": "Load user info on startup",
    "Mettre à jour le bouton MODE RÉEL selon l'abonnement": "Update REAL MODE button based on subscription",
    "Utilisateur peut utiliser le mode réel (abonnement RISKY ou SAFE)": "User can use real mode (RISKY or SAFE subscription)",
    "Sélectionner le mode (simulation ou réel)": "Select mode (simulation or real)",
    "Vérifier si l'utilisateur peut utiliser le mode réel": "Check if user can use real mode",
    "Vérifier le solde wallet": "Check wallet balance",
    "NOUVEAU PARAMÈTRE": "NEW PARAMETER",
    "temps réel!": "real time!",

    # Payment modal
    "MONTANT À PAYER": "AMOUNT TO PAY",
    "Envoyez": "Send",
    "à l'adresse ci-dessus": "to the address above",
    "VÉRIFIER LE PAIEMENT": "VERIFY PAYMENT",

    # Private key modal
    "SAUVEGARDE TA CLÉ PRIVÉE !": "SAVE YOUR PRIVATE KEY!",
    "ATTENTION - TRÈS IMPORTANT": "WARNING - VERY IMPORTANT",
    "Cette clé = accès à ton wallet": "This key = access to your wallet",
    "TA CLÉ PRIVÉE SOLANA": "YOUR SOLANA PRIVATE KEY",
    "TÉLÉCHARGER": "DOWNLOAD",
    "J'ai sauvegardé ma clé privée en lieu sûr": "I saved my private key in a safe place",
    "J'AI COMPRIS ET SAUVEGARDÉ": "I UNDERSTOOD AND SAVED",
    "COPIÉ !": "COPIED!",
    "TÉLÉCHARGÉ !": "DOWNLOADED!",

    # Private key file content
    "SOLANA WALLET - CLÉ PRIVÉE": "SOLANA WALLET - PRIVATE KEY",
    "GARDE CE FICHIER EN SÉCURITÉ !": "KEEP THIS FILE SAFE!",
    "Clé Privée:": "Private Key:",
    "Cette clé donne accès TOTAL à ton wallet": "This key gives TOTAL access to your wallet",

    # Confirmations
    "Warning général": "General warning",
    "Vérifier qu'il a bien vidé le wallet": "Verify that they emptied the wallet",
    "Appeler l'API pour régénérer": "Call API to regenerate",
    "Afficher la nouvelle clé privée dans le modal (COMME AU REGISTER)": "Show new private key in modal (LIKE AT REGISTER)",
    "Afficher message de succès avec l'ancien wallet": "Show success message with old wallet",
    "Afficher le modal de clé privée": "Show private key modal",
    "Rafraîchir les données du dashboard": "Refresh dashboard data",

    # Payment process
    "Créer la demande de paiement": "Create payment request",
    "Générer le QR code (via API)": "Generate QR code (via API)",
    "Démarrer le timer": "Start timer",
    "Demande de paiement expirée": "Payment request expired",
    "VÉRIFICATION EN COURS...": "VERIFICATION IN PROGRESS...",
    "Paiement vérifié! Abonnement activé.": "Payment verified! Subscription activated.",
    "Rafraîchir la page": "Refresh page",
    "Transaction non trouvée. Veuillez attendre quelques secondes et réessayer.": "Transaction not found. Please wait a few seconds and try again.",

    # API comments
    "Appel API pour démarrer la simulation": "API call to start simulation",
    "Appel API pour terminer la simulation": "API call to end simulation",
    "Restaurer le mode simulation": "Restore simulation mode",
    "Calculer le temps restant": "Calculate remaining time",
    "Refresh positions uniquement si on est sur l'onglet TRADES": "Refresh positions only if on TRADES tab",

    # Security confirmation
    "Confirmation de sécurité": "Security confirmation",
    "Afficher le résultat": "Show result",
    "Rafraîchir les positions et le wallet": "Refresh positions and wallet",
}

# Apply all translations
for french, english in translations.items():
    content = content.replace(french, english)

# Write back
with open('templates/bot.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("All remaining bot.html translations completed successfully!")

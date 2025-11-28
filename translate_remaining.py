#!/usr/bin/env python3
# Script to translate all remaining French text in bot.html to English

import re

# Read the file
with open('templates/bot.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Dictionary of French -> English translations
translations = {
    # BOOSTS section - Limited spots
    "69 PLACES RESTANTES": "69 SPOTS REMAINING",
    "59 PLACES RESTANTES": "59 SPOTS REMAINING",
    "49 PLACES RESTANTES": "49 SPOTS REMAINING",

    # BOOSTS section - AI training
    "IA entraîner sur plus de 6000 tokens": "AI trained on 6000+ tokens",
    "IA entraîner sur plus de 10 000 tokens": "AI trained on 10,000+ tokens",

    # Trades section - No positions
    "Aucune position active pour le moment": "No active positions at the moment",
    "Aucun trade pour le moment. Démarrez le bot pour commencer!": "No trades yet. Start the bot to begin!",

    # Strategy options
    "Sell 50% @ x2 + Hold Reste": "Sell 50% @ x2 + Hold Rest",
    "Hold le reste jusqu'à (MC)": "Hold rest until (MC)",
    "Vendre le reste avant cette market cap": "Sell rest before this market cap",

    # Trailing Stop Loss explanation
    "Le Trailing Stop Loss monte automatiquement avec tes profits pour sécuriser tes gains :": "Trailing Stop Loss automatically rises with your profits to secure your gains:",

    # Account creation success
    "Compte créé avec succès!": "Account created successfully!",
    "Votre wallet:": "Your wallet:",

    # Position status
    "Position GRATUITE - Investissement récupéré !": "FREE Position - Investment recovered!",
    "Position fermée!": "Position closed!",
    "Position restante:": "Remaining position:",
    "vers 58K": "to 58K",

    # Sale confirmation
    "Pourcentage:": "Percentage:",
    "Cette action est IRREVERSIBLE!": "This action is IRREVERSIBLE!",

    # Payment modal
    "Expire dans": "Expires in",
    "Scannez avec votre wallet Solana": "Scan with your Solana wallet",
    "Ouvrez votre wallet Solana (Phantom, Solflare, etc.)": "Open your Solana wallet (Phantom, Solflare, etc.)",
    "Cliquez sur \"VÉRIFIER LE PAIEMENT\" une fois envoyé": "Click \"VERIFY PAYMENT\" once sent",
    "Votre abonnement sera activé automatiquement": "Your subscription will be activated automatically",
    "Transaction sécurisée sur la blockchain Solana": "Secure transaction on Solana blockchain",

    # Private key warning modal
    "TU NE POURRAS JAMAIS LA REVOIR !": "YOU WILL NEVER SEE IT AGAIN!",
    "NE LA PARTAGE JAMAIS avec personne": "NEVER SHARE IT with anyone",
    "COMPATIBLE AVEC": "COMPATIBLE WITH",
    "Tu peux importer cette clé dans :": "You can import this key into:",
    "Cette clé ne sera JAMAIS affichée à nouveau": "This key will NEVER be shown again",

    # Private key export message
    "Garde-la dans un lieu sûr (password manager, coffre, etc.)": "Keep it in a safe place (password manager, safe, etc.)",
    "Tu peux l'importer dans Phantom, Solflare, Backpack, etc.": "You can import it into Phantom, Solflare, Backpack, etc.",
    "Date de création:": "Creation date:",
}

# Apply all translations
for french, english in translations.items():
    content = content.replace(french, english)

# Write back
with open('templates/bot.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("All remaining translations completed successfully!")

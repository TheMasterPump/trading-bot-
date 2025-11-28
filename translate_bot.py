#!/usr/bin/env python3
# Script to translate all French text in bot.html to English

import re

# Read the file
with open('templates/bot.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Dictionary of French -> English translations
translations = {
    # Section How It Works
    "Le bot utilise notre modèle ML pour scanner automatiquement les nouveaux tokens sur Solana.": "The bot uses our ML model to automatically scan new tokens on Solana.",
    "Quand un token est prédit comme GEM avec haute confiance (>80%), le bot achète automatiquement.": "When a token is predicted as GEM with high confidence (>80%), the bot buys automatically.",
    "Le bot vend avec take profit (défaut: 2x) ou stop loss (défaut: -50%).": "The bot sells with take profit (default: 2x) or stop loss (default: -50%).",
    "Allez dans l'onglet WALLET et déposez des SOL sur votre wallet généré.": "Go to the WALLET tab and deposit SOL to your generated wallet.",
    "Cliquez sur START BOT en haut. Le bot trade 24/7 pour vous!": "Click START BOT at the top. The bot trades 24/7 for you!",

    # Wallet section
    "Chargement...": "Loading...",
    "Déposez des SOL sur cette adresse pour alimenter votre bot de trading!": "Deposit SOL to this address to fund your trading bot!",

    # Boosts section
    "99 PLACES RESTANTES": "99 SPOTS REMAINING",
    "IA entraîner sur plus de 4000 tokens": "AI trained on 4000+ tokens",

    # Various labels
    "VENDRE": "SELL",
}

# Apply all translations
for french, english in translations.items():
    content = content.replace(french, english)

# Write back
with open('templates/bot.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("All translations completed successfully!")

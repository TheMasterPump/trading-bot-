#!/usr/bin/env python3
# Script to translate all French text in dashboard.html to English

import re

# Read the file
with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Dictionary of French -> English translations
translations = {
    # Dashboard headers
    "Tokens Analysés": "Tokens Analyzed",
    "Runners Détectés": "Runners Detected",

    # Sections
    "RUNNER CANDIDATES - Filtres Optimisés (40-50% Win Rate Target)": "RUNNER CANDIDATES - Optimized Filters (40-50% Win Rate Target)",
    "Aucun RUNNER détecté pour le moment...": "No RUNNER detected at the moment...",
    "Alertes Récentes": "Recent Alerts",
    "Accélération": "Acceleration",
    "Tokens Complétés": "Completed Tokens",
    "Aucun token complété pour le moment...": "No completed token at the moment...",

    # Buttons and status
    "Migré": "Migrated",
    "Pas Migré": "Not Migrated",
    "N'a pas migré": "Did not migrate",

    # Comments
    "Erreur de récupération des données:": "Data retrieval error:",
    "Stocker les données des runners pour affichage des whales": "Store runner data for whale display",
    "Mise à jour des statistiques": "Updating statistics",
    "Mise à jour des RUNNER CANDIDATES": "Updating RUNNER CANDIDATES",
    "Mise à jour des alertes": "Updating alerts",
    "Mise à jour des tokens complétés": "Updating completed tokens",
    "Pas encore marqué - afficher les boutons": "Not yet marked - show buttons",
    "Marqué comme migré": "Marked as migrated",
    "Marqué comme non migré": "Marked as not migrated",
    "Chercher les données complètes du runner pour obtenir les infos whales": "Search full runner data to get whale info",
    "Rafraîchir immédiatement": "Refresh immediately",
    "Afficher les 20 dernières alertes": "Show last 20 alerts",
    "Afficher les 10 derniers tokens complétés": "Show last 10 completed tokens",
}

# Apply all translations
for french, english in translations.items():
    content = content.replace(french, english)

# Write back
with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("All dashboard.html translations completed successfully!")

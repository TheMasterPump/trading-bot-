@echo off
title Installation dependencies - Trading Reel
color 0A

echo ===============================================================================
echo         INSTALLATION DES DEPENDANCES POUR LE TRADING REEL
echo ===============================================================================
echo.

echo Installation de python-dotenv (pour lire le fichier .env)...
python -m pip install python-dotenv

echo.
echo Installation de solders (pour les transactions Solana)...
python -m pip install solders

echo.
echo ===============================================================================
echo Installation terminee!
echo ===============================================================================
echo.
echo Prochaine etape: Configurez votre fichier .env
echo.
pause

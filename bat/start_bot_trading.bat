@echo off
title Trading Bot - Demarrage...
color 0A
cd /d "C:\Users\user\Desktop\project\prediction AI modele 2"

echo ===============================================================================
echo                         BOT DE TRADING PUMPFUN - IA
echo ===============================================================================
echo.
echo   Ce bot utilise l'IA pour trader automatiquement les tokens PumpFun
echo   Les statistiques seront affichees dans le titre de cette fenetre
echo.
echo ===============================================================================
echo.

REM Verifier que Python est installe
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH
    echo.
    pause
    exit /b 1
)

echo [OK] Python detecte
echo.
echo Lancement du bot de trading...
echo.

REM Lancer le bot avec sortie non bufferisee
python -u live_trading_bot.py

REM Si le bot s'arrete, afficher un message
echo.
echo ===============================================================================
echo Le bot s'est arrete.
echo ===============================================================================
echo.
pause

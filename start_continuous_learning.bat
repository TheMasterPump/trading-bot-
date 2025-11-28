@echo off
chcp 65001 >nul
cls
echo.
echo ========================================================================
echo   SYSTEME D'APPRENTISSAGE CONTINU - PREDICTION AI
echo ========================================================================
echo.
echo   Ce systeme va:
echo   - Scanner les nouveaux tokens Pump.fun
echo   - Faire des predictions automatiquement
echo   - Tracker leur performance reelle
echo   - Reentrainer le modele avec les nouvelles donnees
echo   - S'ameliorer continuellement vers 99%% de precision!
echo.
echo   Precision actuelle: 95.61%%
echo   Objectif: 99%%+
echo.
echo ========================================================================
echo.
echo [INFO] Demarrage du systeme...
echo.

python continuous_learning_system.py

pause

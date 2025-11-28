@echo off
echo ========================================
echo LANCEMENT DU TRADING BOT SYSTEM
echo ========================================
echo.

echo [1/3] Test du systeme...
python test_system.py

if errorlevel 1 (
    echo.
    echo [ERREUR] Des dependances manquent!
    echo Lance d'abord: install_dependencies.bat
    pause
    exit /b 1
)

echo.
echo [2/3] Initialisation de la base de donnees...
python database_bot.py

echo.
echo [3/3] Demarrage du serveur Flask...
echo.
echo ========================================
echo SERVER DEMARRE!
echo ========================================
echo.
echo Ouvre ton navigateur:
echo   - Scanner AI:   http://localhost:5001/
echo   - Trading Bot:  http://localhost:5001/bot
echo.
echo [Ctrl+C pour arreter]
echo ========================================
echo.

python app.py

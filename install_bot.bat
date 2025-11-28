@echo off
echo ================================================
echo   TRADING BOT AI - Installation
echo ================================================
echo.

echo [1/3] Installation des dependances...
pip install -r requirements_bot.txt

echo.
echo [2/3] Initialisation de la base de donnees...
python database_bot.py

echo.
echo [3/3] Test de generation de wallet...
python wallet_generator.py

echo.
echo ================================================
echo   Installation terminee!
echo ================================================
echo.
echo Pour lancer le bot:
echo   python app.py
echo.
echo Puis ouvrir: http://localhost:5001/bot
echo.
pause

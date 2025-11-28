@echo off
title Test Connexion WebSocket
color 0E
cd /d "C:\Users\user\Desktop\prediction AI modele 2\bat"

echo ===============================================================================
echo                     TEST DE CONNEXION WEBSOCKET
echo ===============================================================================
echo.
echo Ce test va diagnostiquer si le probleme vient de:
echo   - Votre connexion internet
echo   - Ou du serveur PumpPortal
echo.
echo Laissez tourner 5-10 minutes pour avoir des statistiques fiables.
echo Appuyez sur Ctrl+C pour arreter.
echo.
echo ===============================================================================
echo.
pause

python test_websocket.py

pause

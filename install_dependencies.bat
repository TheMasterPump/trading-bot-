@echo off
echo ========================================
echo INSTALLATION DES DEPENDANCES
echo ========================================
echo.

echo [1/2] Installation de cryptography...
python -m pip install cryptography

echo.
echo [2/2] Installation de Flask-Session...
python -m pip install Flask-Session

echo.
echo ========================================
echo INSTALLATION TERMINEE!
echo ========================================
echo.
echo Tu peux maintenant lancer:
echo   python test_system.py
echo.
pause

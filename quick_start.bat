@echo off
echo ========================================
echo  PREDICTION AI - Quick Start
echo ========================================
echo.

echo [1/3] Installation des dependances...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERREUR: Installation echouee
    pause
    exit /b 1
)
echo.

echo [2/3] Entrainement des modeles avances...
echo (Cela peut prendre 5-10 minutes...)
python train_advanced_models.py
if %errorlevel% neq 0 (
    echo ERREUR: Entrainement echoue
    pause
    exit /b 1
)
echo.

echo [3/3] Lancement de l'application...
echo.
echo ========================================
echo  Application prete!
echo  Ouvrez: http://localhost:5001
echo ========================================
echo.
python app.py

pause

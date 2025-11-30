"""
VISION AI BOT - VIDEO DEMO AUTOMATION
Script qui automatise tout dans le navigateur pour faire une démo vidéo
Lance le serveur, ouvre le navigateur, se connecte, et démarre le mode démo
"""
import time
import subprocess
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Configuration
DEMO_EMAIL = "demo@visionai.bot"
DEMO_PASSWORD = "demo123456"
BASE_URL = "http://localhost:5001"
DEMO_DURATION_SECONDS = 300  # 5 minutes de démo

def start_flask_server():
    """Démarre le serveur Flask en arrière-plan"""
    print("🚀 Starting Flask server...")

    # Démarrer le serveur en arrière-plan
    process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )

    # Attendre que le serveur démarre
    print("⏳ Waiting for server to start (10 seconds)...")
    time.sleep(10)

    return process

def setup_browser():
    """Configure et retourne un driver Chrome"""
    print("🌐 Setting up browser...")

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Pour Windows, spécifier le chemin de chromedriver si nécessaire
    # Décommente et modifie si besoin :
    # service = Service('C:\\path\\to\\chromedriver.exe')
    # driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"❌ Chrome not found. Trying Firefox...")
        try:
            driver = webdriver.Firefox()
        except:
            print(f"❌ Error: Please install Chrome or Firefox WebDriver")
            print(f"   Chrome: https://chromedriver.chromium.org/")
            print(f"   Firefox: https://github.com/mozilla/geckodriver/releases")
            sys.exit(1)

    return driver

def register_and_login(driver):
    """Crée un compte démo et se connecte"""
    print("👤 Creating demo account...")

    # Aller sur la page d'accueil
    driver.get(BASE_URL)
    time.sleep(2)

    # Aller sur /bot
    driver.get(f"{BASE_URL}/bot")
    time.sleep(2)

    try:
        # Essayer de s'inscrire
        print("📝 Trying to register...")

        # Attendre le formulaire de connexion
        wait = WebDriverWait(driver, 10)

        # Cliquer sur l'onglet Register si visible
        try:
            register_tab = wait.until(EC.element_to_be_clickable((By.ID, "registerTab")))
            register_tab.click()
            time.sleep(1)
        except:
            print("   Register tab not found, trying direct registration...")

        # Remplir le formulaire d'inscription
        email_input = driver.find_element(By.ID, "registerEmail")
        password_input = driver.find_element(By.ID, "registerPassword")

        email_input.clear()
        email_input.send_keys(DEMO_EMAIL)

        password_input.clear()
        password_input.send_keys(DEMO_PASSWORD)

        # Cliquer sur le bouton Register
        register_btn = driver.find_element(By.ID, "registerBtn")
        register_btn.click()

        print("✅ Registration successful!")
        time.sleep(3)

    except Exception as e:
        # Si l'inscription échoue (compte existe déjà), se connecter
        print(f"   Registration failed (account may exist), trying to login...")

        try:
            # Cliquer sur l'onglet Login
            login_tab = driver.find_element(By.ID, "loginTab")
            login_tab.click()
            time.sleep(1)

            # Remplir le formulaire de connexion
            email_input = driver.find_element(By.ID, "loginEmail")
            password_input = driver.find_element(By.ID, "loginPassword")

            email_input.clear()
            email_input.send_keys(DEMO_EMAIL)

            password_input.clear()
            password_input.send_keys(DEMO_PASSWORD)

            # Cliquer sur le bouton Login
            login_btn = driver.find_element(By.ID, "loginBtn")
            login_btn.click()

            print("✅ Login successful!")
            time.sleep(3)

        except Exception as login_error:
            print(f"❌ Login failed: {login_error}")
            return False

    return True

def start_demo_mode(driver):
    """Lance le mode DÉMO"""
    print("🎮 Starting DEMO MODE...")

    try:
        wait = WebDriverWait(driver, 10)

        # Attendre que le bouton MODE DEMO soit visible
        demo_btn = wait.until(EC.element_to_be_clickable((By.ID, "startDemoBtn")))

        # Cliquer sur MODE DEMO
        demo_btn.click()
        print("✅ DEMO MODE started!")

        return True

    except Exception as e:
        print(f"❌ Failed to start demo: {e}")
        return False

def run_automated_demo():
    """Lance la démo complète automatisée"""
    print("\n" + "="*70)
    print("  VISION AI BOT - AUTOMATED VIDEO DEMO")
    print("="*70 + "\n")

    flask_process = None
    driver = None

    try:
        # 1. Démarrer le serveur Flask
        flask_process = start_flask_server()

        # 2. Configurer le navigateur
        driver = setup_browser()

        # 3. Créer un compte et se connecter
        if not register_and_login(driver):
            print("❌ Failed to login")
            return

        # 4. Lancer le mode DÉMO
        if not start_demo_mode(driver):
            print("❌ Failed to start demo mode")
            return

        # 5. Laisser tourner la démo
        print(f"\n🎬 DEMO IS RUNNING!")
        print(f"📹 Record your video now!")
        print(f"⏱️  Demo will run for {DEMO_DURATION_SECONDS} seconds ({DEMO_DURATION_SECONDS//60} minutes)")
        print(f"⚠️  Press Ctrl+C to stop early\n")

        # Attendre la durée de la démo
        time.sleep(DEMO_DURATION_SECONDS)

        print("\n✅ Demo completed!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo stopped by user")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Fermer le navigateur
        if driver:
            print("🔒 Closing browser...")
            try:
                # Arrêter la démo avant de fermer
                stop_demo_btn = driver.find_element(By.ID, "stopDemoBtn")
                stop_demo_btn.click()
                time.sleep(2)
            except:
                pass

            driver.quit()

        # Arrêter le serveur Flask
        if flask_process:
            print("🛑 Stopping Flask server...")
            flask_process.terminate()
            try:
                flask_process.wait(timeout=5)
            except:
                flask_process.kill()

        print("\n👋 Demo automation finished!\n")

if __name__ == "__main__":
    # Vérifier que selenium est installé
    try:
        import selenium
    except ImportError:
        print("❌ Selenium not installed!")
        print("📦 Install with: pip install selenium")
        print("📦 Also download ChromeDriver: https://chromedriver.chromium.org/")
        sys.exit(1)

    run_automated_demo()

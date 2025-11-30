"""
VISION AI BOT - SIMPLE VIDEO DEMO
Script simplifié qui lance le serveur et ouvre le navigateur
Tu fais le reste manuellement (login + mode démo)
"""
import subprocess
import sys
import os
import time
import webbrowser

def main():
    print("\n" + "="*70)
    print("  VISION AI BOT - SIMPLE VIDEO DEMO")
    print("="*70 + "\n")

    print("🚀 Starting Flask server...")

    # Démarrer le serveur Flask
    flask_process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )

    print("⏳ Waiting 10 seconds for server to start...")
    time.sleep(10)

    print("🌐 Opening browser at http://localhost:5001/bot")
    webbrowser.open("http://localhost:5001/bot")

    print("\n" + "="*70)
    print("✅ Server is running!")
    print("="*70)
    print("\n📋 STEPS TO RECORD YOUR VIDEO:")
    print("   1. Register/Login with any email")
    print("   2. Click the orange 'MODE DEMO' button")
    print("   3. Start recording your screen (OBS, etc.)")
    print("   4. Watch the bot trade automatically!")
    print("\n⚠️  Press Ctrl+C here when you're done to stop the server\n")

    try:
        # Attendre que l'utilisateur arrête
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping server...")
        flask_process.terminate()
        try:
            flask_process.wait(timeout=5)
        except:
            flask_process.kill()
        print("✅ Server stopped!")
        print("👋 Bye!\n")

if __name__ == "__main__":
    main()

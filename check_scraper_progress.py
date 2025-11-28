"""
CHECK SCRAPER PROGRESS
Vérifie la progression du scraper massif
"""
import json
from pathlib import Path
from datetime import datetime

def check_progress():
    dataset_file = Path(__file__).parent / "training_dataset.json"

    if not dataset_file.exists():
        print("\n[!] Dataset not found yet. Scraper just started.")
        return

    with open(dataset_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = data.get('total', 0)
    gems = data.get('gems', 0)
    rugs = data.get('rugs', 0)
    potential_gems = data.get('potential_gems', 0)
    potential_rugs = data.get('potential_rugs', 0)
    unknown = data.get('unknown', 0)
    last_updated = data.get('last_updated', 'Unknown')

    print("\n" + "=" * 70)
    print("SCRAPER PROGRESS")
    print("=" * 70)
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Last updated: {last_updated}")
    print(f"\nTotal tokens collected: {total}/500")
    print(f"Progress: {(total/500)*100:.1f}%")
    print(f"\nBreakdown:")
    print(f"  Gems (>100%):       {gems}")
    print(f"  Rugs (<-80%):       {rugs}")
    print(f"  Potential Gems:     {potential_gems}")
    print(f"  Potential Rugs:     {potential_rugs}")
    print(f"  Unknown:            {unknown}")
    print(f"\nLabeled tokens:      {gems + rugs + potential_gems + potential_rugs}")
    print("=" * 70)

    if total >= 100:
        print(f"\n[+] Good! You have {total} tokens.")
        print(f"[+] You can train the model when you have 100+ labeled tokens.")
        labeled = gems + rugs + potential_gems + potential_rugs
        if labeled >= 100:
            print(f"\n[SUCCESS] {labeled} labeled tokens! Ready to train!")
            print("Run: python train_ml_model_advanced.py")

if __name__ == "__main__":
    check_progress()

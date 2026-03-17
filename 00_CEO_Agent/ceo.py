"""
DARK FACTORY — CEO Command Center
Master orchestrator. Run this to start any factory.
Usage: python ~/Desktop/DarkFactory/00_CEO_Agent/ceo.py
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load env
env_path = Path(__file__).parent.parent / "_config" / ".env"
load_dotenv(dotenv_path=env_path)

# Paths
BASE_DIR = Path(__file__).parent.parent
LOG_DIR  = BASE_DIR / "_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "activity.log"

# Add factory paths to sys.path
sys.path.insert(0, str(BASE_DIR / "01_Digital_Products"))
sys.path.insert(0, str(BASE_DIR / "05_Web_Hunter"))
sys.path.insert(0, str(BASE_DIR / "02_Faceless_YT"))


def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def print_menu():
    print()
    print("╔══════════════════════════════════════╗")
    print("║     DARK FACTORY — COMMAND CENTER    ║")
    print("╚══════════════════════════════════════╝")
    print()
    print("  [B]  Digital Products Factory")
    print("  [A]  Web Hunter Factory")
    print("  [C]  YouTube Factory")
    print("  [Q]  Quit")
    print()


def run_factory_b():
    log("FACTORY B — Digital Products — STARTED")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "factory_b",
            str(BASE_DIR / "01_Digital_Products" / "factory.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()
        log("FACTORY B — Digital Products — COMPLETED")
    except Exception as e:
        log(f"FACTORY B — Digital Products — FAILED: {e}")
        print(f"\n❌ Factory B failed: {e}")


def run_factory_a():
    log("FACTORY A — Web Hunter — STARTED")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "factory_a",
            str(BASE_DIR / "05_Web_Hunter" / "factory.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()
        log("FACTORY A — Web Hunter — COMPLETED")
    except Exception as e:
        log(f"FACTORY A — Web Hunter — FAILED: {e}")
        print(f"\n❌ Factory A failed: {e}")


def run_factory_c():
    log("FACTORY C — YouTube — STARTED")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "factory_c",
            str(BASE_DIR / "02_Faceless_YT" / "factory.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()
        log("FACTORY C — YouTube — COMPLETED")
    except Exception as e:
        log(f"FACTORY C — YouTube — FAILED: {e}")
        print(f"\n❌ Factory C failed: {e}")


def main():
    log("CEO COMMAND CENTER — SESSION STARTED")

    while True:
        print_menu()
        choice = input("  Which factory to run? ").strip().upper()

        if choice == "B":
            print("\n🏭 Starting Digital Products Factory...\n")
            run_factory_b()
        elif choice == "A":
            print("\n🏭 Starting Web Hunter Factory...\n")
            run_factory_a()
        elif choice == "C":
            print("\n🏭 Starting YouTube Factory...\n")
            run_factory_c()
        elif choice == "Q":
            log("CEO COMMAND CENTER — SESSION ENDED")
            print("\n👋 Dark Factory offline. See you next time.\n")
            break
        else:
            print(f"\n  ❓ Unknown command '{choice}'. Use B, A, C or Q.\n")


if __name__ == "__main__":
    main()

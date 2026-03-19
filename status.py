#!/usr/bin/env python3
"""
DARK FACTORY — Live Status Monitor
Spuštění: python3 status.py
         python3 status.py --watch    # auto-refresh každé 3s
         python3 status.py --api      # dotáže se Railway API místo logu
"""
import os, sys, time, json, subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent

FACTORIES = {
    "a": {"name": "Web Hunter",       "dir": "05_Web_Hunter",      "out": "_outputs/web_hunter"},
    "b": {"name": "Digital Products", "dir": "01_Digital_Products","out": "_outputs/digital_products"},
    "c": {"name": "YouTube",          "dir": "02_Faceless_YT",     "out": "_outputs/youtube"},
    "d": {"name": "Data Products",    "dir": "04_Data_Products",   "out": "_outputs/data_products"},
    "e": {"name": "SEO Content",      "dir": "06_SEO_Content",     "out": "_outputs/seo_content"},
    "f": {"name": "Leads API",        "dir": "07_Leads_API",       "out": "_outputs/leads_api"},
}

def get_last_output(out_dir: str):
    d = BASE_DIR / out_dir
    if not d.exists():
        return None, None
    files = sorted(d.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    files = [f for f in files if f.is_file() and not f.name.startswith(".")]
    if not files:
        return None, None
    f = files[0]
    mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%d.%m %H:%M")
    return f.name, mtime

def get_log_tail(n=5):
    log_file = BASE_DIR / "_logs" / "scheduler.log"
    if not log_file.exists():
        return []
    with open(log_file) as f:
        lines = f.readlines()
    return [l.rstrip() for l in lines[-n:]]

def check_running_processes():
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        running = {}
        for key, info in FACTORIES.items():
            factory_dir = info["dir"].lower()
            for line in lines:
                if factory_dir in line.lower() and "python" in line.lower() and "grep" not in line:
                    pid = line.split()[1]
                    running[key] = pid
                    break
        # Check scheduler itself
        sched_running = any("scheduler.py" in l and "grep" not in l for l in lines if "python" in l.lower())
        return running, sched_running
    except Exception:
        return {}, False

def print_status():
    if sys.platform == "darwin":
        os.system("clear")
    else:
        print("\033[H\033[J", end="")

    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    running_factories, sched_running = check_running_processes()

    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║           DARK FACTORY — LIVE STATUS  {now}  ║")
    sched_status = "🟢 BĚŽÍ" if sched_running else "🔴 NEBĚŽÍ"
    print(f"╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Scheduler: {sched_status:<52}║")
    print(f"╠══════════════════════════════════════════════════════════════╣")
    print(f"║  {'KEY':<3} {'FACTORY':<18} {'STATUS':<12} {'POSLEDNÍ OUTPUT':<24}║")
    print(f"╠══════════════════════════════════════════════════════════════╣")

    for key, info in FACTORIES.items():
        name = info["name"]
        fname, ftime = get_last_output(info["out"])
        if key in running_factories:
            status = "⚙️  BĚŽÍ"
            pid_info = f"(PID {running_factories[key]})"
        elif fname:
            status = "✅ hotovo"
            pid_info = ""
        else:
            status = "💤 čeká"
            pid_info = ""

        out_str = f"{fname[:20]}..." if fname and len(fname) > 20 else (fname or "—")
        time_str = f" ({ftime})" if ftime else ""
        print(f"║  {key.upper():<3} {name:<18} {status:<12} {out_str+time_str:<24}║")

    print(f"╠══════════════════════════════════════════════════════════════╣")
    print(f"║  POSLEDNÍCH 5 ŘÁDKŮ LOGU:                                   ║")
    print(f"╠══════════════════════════════════════════════════════════════╣")
    for line in get_log_tail(5):
        short = line[-60:] if len(line) > 60 else line
        print(f"║  {short:<60}║")
    print(f"╚══════════════════════════════════════════════════════════════╝")

    if "--watch" in sys.argv:
        print(f"\n  Auto-refresh každé 3s | Ctrl+C pro ukončení")

def main():
    if "--watch" in sys.argv:
        try:
            while True:
                print_status()
                time.sleep(3)
        except KeyboardInterrupt:
            print("\n👋 Status monitor ukončen.")
    else:
        print_status()

if __name__ == "__main__":
    main()

"""
DARK FACTORY — Autonomous Scheduler + HTTP API

Modes (env var):
  CONTINUOUS_LOOP=true  → běží A→B→C→D→E→F→A→B→... dokola bez zastavení
                          LOOP_DELAY_MINUTES=60 (prodleva mezi cykly, default 60)
  RUN_ON_STARTUP=true   → jednorázově spustí všechny factories při startu
  (výchozí)             → klasický schedule: 06→B | 07→A | 08→C | 09→D | 10→E | 11→F

HTTP API (port 8080):
  POST /trigger/{a-f}  — spustí factory ihned
  GET  /status         — stav všech factories
  GET  /health         — healthcheck
  GET  /logs           — posledních N řádků logu
"""

import os
import sys
import time
import platform
import threading
import schedule
import logging
import subprocess
import importlib.util
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(dotenv_path=BASE_DIR / "_config" / ".env")

LOG_DIR = BASE_DIR / "_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "scheduler.log"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("DarkFactory")

GITHUB_TOKEN  = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
GITHUB_REPO   = os.getenv("GITHUB_REPO", "")
NOTIFY_PHONE  = os.getenv("NOTIFY_PHONE", os.getenv("GMAIL_ADDRESS", ""))
IS_MAC        = platform.system() == "Darwin"
PORT          = int(os.getenv("PORT", "8080"))
CONTINUOUS    = os.getenv("CONTINUOUS_LOOP", "false").lower() == "true"
LOOP_DELAY    = int(os.getenv("LOOP_DELAY_MINUTES", "60"))  # pauza mezi cykly

# Globální čítač cyklů
loop_cycle = 0

factory_status = {
    "a": {"name": "Web Hunter",       "last_run": None, "last_result": "never", "running": False},
    "b": {"name": "Digital Products", "last_run": None, "last_result": "never", "running": False},
    "c": {"name": "YouTube",          "last_run": None, "last_result": "never", "running": False},
    "d": {"name": "Data Products",    "last_run": None, "last_result": "never", "running": False},
    "e": {"name": "SEO Content",      "last_run": None, "last_result": "never", "running": False},
    "f": {"name": "Leads API",        "last_run": None, "last_result": "never", "running": False},
}


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────

def send_imessage(message: str):
    if not IS_MAC or not NOTIFY_PHONE:
        return
    try:
        script = f'tell application "Messages" to send "{message}" to participant "{NOTIFY_PHONE}" of (1st account whose service type = iMessage)'
        subprocess.run(["osascript", "-e", script], timeout=10, check=True)
        log.info("📱 iMessage sent")
    except Exception as e:
        log.warning(f"iMessage failed: {e}")


def send_email_via_resend(subject: str, body: str):
    resend_key = os.getenv("RESEND_API_KEY", "")
    if not resend_key or not NOTIFY_PHONE:
        return
    try:
        import requests
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
            json={"from": "DarkFactory <noreply@resend.dev>", "to": [NOTIFY_PHONE], "subject": subject, "text": body}
        )
        if r.status_code == 200:
            log.info("📧 Email notification sent")
    except Exception as e:
        log.warning(f"Email failed: {e}")


def notify(title: str, message: str):
    full = f"🏭 DARK FACTORY\n{title}\n{message}"
    if IS_MAC:
        send_imessage(full)
    else:
        send_email_via_resend(f"[DarkFactory] {title}", full)


# ── GIT PUSH ─────────────────────────────────────────────────────────────────

def push_outputs_to_github(factory_name: str):
    if not GITHUB_REPO or not GITHUB_TOKEN:
        return
    try:
        import git
        repo_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
        try:
            repo = git.Repo(BASE_DIR)
        except git.InvalidGitRepositoryError:
            repo = git.Repo.init(BASE_DIR)
            repo.create_remote("origin", repo_url)
        try:
            repo.remote("origin").set_url(repo_url)
        except Exception:
            repo.create_remote("origin", repo_url)
        repo.config_writer().set_value("user", "name", "DarkFactory").release()
        repo.config_writer().set_value("user", "email", "darkfactory@auto.run").release()
        repo.git.add("_outputs/")
        repo.git.add("_logs/")
        if repo.is_dirty(index=True):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            repo.index.commit(f"[{factory_name}] Auto output — {ts}")
            repo.remote("origin").push(refspec="HEAD:main", force=True)
            log.info(f"✅ Pushed to GitHub: {GITHUB_REPO}")
    except Exception as e:
        log.error(f"GitHub push failed: {e}")


# ── FACTORY RUNNER ────────────────────────────────────────────────────────────

def run_factory(key: str, factory_path: str, module_name: str):
    if factory_status[key]["running"]:
        log.warning(f"Factory {key.upper()} already running, skipping.")
        return False

    factory_status[key]["running"] = True
    factory_status[key]["last_run"] = datetime.now().isoformat()
    log.info(f"▶ STARTING Factory {key.upper()} — {factory_status[key]['name']}")

    try:
        spec = importlib.util.spec_from_file_location(module_name, factory_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()
        factory_status[key]["last_result"] = "success"
        log.info(f"✅ Factory {key.upper()} COMPLETED")
        return True
    except Exception as e:
        factory_status[key]["last_result"] = f"error: {e}"
        log.error(f"❌ Factory {key.upper()} FAILED: {e}")
        return False
    finally:
        factory_status[key]["running"] = False


# ── JOBS ──────────────────────────────────────────────────────────────────────

def job_a():
    ok = run_factory("a", str(BASE_DIR / "05_Web_Hunter" / "factory.py"), "factory_a")
    push_outputs_to_github("Factory-A")
    if ok:
        notify("Factory A hotovo ✅", "Web Hunter leady připraveny → _outputs/web_hunter/")

def job_b():
    ok = run_factory("b", str(BASE_DIR / "01_Digital_Products" / "factory.py"), "factory_b")
    push_outputs_to_github("Factory-B")
    if ok:
        product_id = os.getenv("GUMROAD_PRODUCT_ID", "").strip()
        if product_id:
            try:
                spec = importlib.util.spec_from_file_location("gumroad_pub", BASE_DIR / "publish_gumroad.py")
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                url  = mod.publish()
                notify("Factory B + Gumroad ✅", f"Produkt live: {url}")
            except Exception as e:
                log.error(f"Gumroad publish failed: {e}")
                notify("Factory B hotovo ✅", f"PDF ready, Gumroad chyba: {e}")
        else:
            pdf_dir = BASE_DIR / "_outputs" / "digital_products"
            pdfs = sorted(pdf_dir.glob("*.pdf"), key=lambda f: f.stat().st_mtime, reverse=True)
            notify("Factory B hotovo ✅", f"PDF: {pdfs[0].name if pdfs else '?'}. Nastav GUMROAD_PRODUCT_ID.")


def job_c():
    ok = run_factory("c", str(BASE_DIR / "02_Faceless_YT" / "factory.py"), "factory_c")
    push_outputs_to_github("Factory-C")
    if ok:
        notify("Factory C hotovo ✅", "YouTube skripty připraveny → _outputs/youtube/")

def job_d():
    ok = run_factory("d", str(BASE_DIR / "04_Data_Products" / "factory.py"), "factory_d")
    push_outputs_to_github("Factory-D")
    if ok:
        out_dir = BASE_DIR / "_outputs" / "data_products"
        csvs = sorted(out_dir.glob("*.csv"), key=lambda f: f.stat().st_mtime, reverse=True)
        notify("Factory D hotovo ✅", f"ARES data '{csvs[0].name if csvs else '?'}' → _outputs/data_products/")

def job_e():
    ok = run_factory("e", str(BASE_DIR / "06_SEO_Content" / "factory.py"), "factory_e")
    push_outputs_to_github("Factory-E")
    if ok:
        out_dir = BASE_DIR / "_outputs" / "seo_content"
        arts = sorted(out_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        art_name = arts[0].name if arts else "?"
        # Auto-publish na GitHub Pages
        try:
            spec = importlib.util.spec_from_file_location("publish_seo", BASE_DIR / "publish_seo.py")
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            url = mod.main()
            notify("Factory E + GitHub Pages ✅", f"Článek '{art_name}' live: {url}")
            log.info(f"🌐 SEO published: {url}")
        except Exception as e:
            log.error(f"SEO publish failed: {e}")
            notify("Factory E hotovo ✅", f"SEO článek '{art_name}' → _outputs/seo_content/ (publish selhal: {e})")

def job_f():
    ok = run_factory("f", str(BASE_DIR / "07_Leads_API" / "factory.py"), "factory_f")
    push_outputs_to_github("Factory-F")
    if ok:
        out_dir = BASE_DIR / "_outputs" / "leads_api"
        csvs = sorted(out_dir.glob("*.csv"), key=lambda f: f.stat().st_mtime, reverse=True)
        notify("Factory F hotovo ✅", f"Leads balíček '{csvs[0].name if csvs else '?'}' → _outputs/leads_api/")


# ── CONTINUOUS LOOP ───────────────────────────────────────────────────────────
# Pořadí: A → B → C → D → E → F → (pauza LOOP_DELAY_MINUTES) → A → ...

LOOP_ORDER = [
    ("a", job_a),
    ("b", job_b),
    ("c", job_c),
    ("d", job_d),
    ("e", job_e),
    ("f", job_f),
]

def run_continuous_loop():
    global loop_cycle
    log.info(f"🔄 CONTINUOUS LOOP MODE — pořadí: A→B→C→D→E→F, pauza {LOOP_DELAY}min mezi cykly")
    while True:
        loop_cycle += 1
        log.info(f"━━━━━━━━━━ CYKLUS #{loop_cycle} START ━━━━━━━━━━")
        notify(f"Cyklus #{loop_cycle} startuje 🔄", "Spouštím A→B→C→D→E→F")
        results = {}
        for key, job_fn in LOOP_ORDER:
            log.info(f"[Cyklus #{loop_cycle}] Spouštím Factory {key.upper()}...")
            try:
                job_fn()
                results[key] = "✅"
            except Exception as e:
                results[key] = f"❌ {e}"
                log.error(f"[Cyklus #{loop_cycle}] Factory {key.upper()} selhala: {e}")

        summary = " | ".join(f"{k.upper()}:{v}" for k, v in results.items())
        log.info(f"━━━━━━━━━━ CYKLUS #{loop_cycle} HOTOV ━━━━━━━━━━")
        log.info(f"Výsledky: {summary}")
        notify(f"Cyklus #{loop_cycle} hotov ✅", f"{summary}\nDalší cyklus za {LOOP_DELAY} min.")
        log.info(f"💤 Čekám {LOOP_DELAY} minut před dalším cyklem...")
        time.sleep(LOOP_DELAY * 60)


# ── HTTP API ──────────────────────────────────────────────────────────────────

def start_api_server():
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn

        api = FastAPI(title="Dark Factory API")
        api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

        job_map = {"a": job_a, "b": job_b, "c": job_c, "d": job_d, "e": job_e, "f": job_f}

        @api.get("/health")
        def health():
            return {"status": "ok", "time": datetime.now().isoformat()}

        @api.get("/status")
        def status():
            mode = "continuous_loop" if CONTINUOUS else ("run_on_startup" if os.getenv("RUN_ON_STARTUP","false").lower()=="true" else "scheduled")
            return {
                "mode": mode,
                "loop_cycle": loop_cycle,
                "loop_delay_minutes": LOOP_DELAY,
                "factories": factory_status,
                "loop_order": [k for k, _ in LOOP_ORDER],
            }

        @api.post("/trigger/{factory_key}")
        def trigger(factory_key: str):
            if factory_key not in job_map:
                return {"error": f"Unknown factory '{factory_key}'. Use: a-f"}
            if factory_status[factory_key]["running"]:
                return {"status": "already_running", "factory": factory_key}
            threading.Thread(target=job_map[factory_key], daemon=True).start()
            return {"status": "started", "factory": factory_key, "name": factory_status[factory_key]["name"]}

        @api.get("/logs")
        def logs(lines: int = 100):
            log_file = LOG_DIR / "scheduler.log"
            if not log_file.exists():
                return {"logs": []}
            with open(log_file) as f:
                all_lines = f.readlines()
            return {"logs": [l.rstrip() for l in all_lines[-lines:]]}

        log.info(f"🌐 API server starting on port {PORT}")
        uvicorn.run(api, host="0.0.0.0", port=PORT, log_level="warning")
    except Exception as e:
        log.error(f"API server failed: {e}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    log.info("╔══════════════════════════════════════════════╗")
    log.info("║     DARK FACTORY — SCHEDULER ONLINE          ║")
    log.info("║  6 Factories | Fully Autonomous | 24/7       ║")
    log.info("╚══════════════════════════════════════════════╝")
    log.info(f"Platform: {'macOS' if IS_MAC else 'Linux/Railway'} | Port: {PORT}")

    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    if CONTINUOUS:
        log.info(f"🔄 Mód: CONTINUOUS LOOP (A→B→C→D→E→F→A..., pauza {LOOP_DELAY}min)")
        run_continuous_loop()  # blokuje navždy

    elif os.getenv("RUN_ON_STARTUP", "false").lower() == "true":
        log.info("🚀 Mód: RUN_ON_STARTUP — jednorázový průchod")
        for _, job_fn in LOOP_ORDER:
            job_fn()
        log.info("✅ RUN_ON_STARTUP hotovo. Přepínám na scheduled mód.")
        _run_scheduled()

    else:
        log.info("📅 Mód: SCHEDULED (UTC): 07→A | 06→B | 08→C | 09→D | 10→E | 11→F")
        _run_scheduled()


def _run_scheduled():
    schedule.every().day.at("07:00").do(job_a)
    schedule.every().day.at("06:00").do(job_b)
    schedule.every().day.at("08:00").do(job_c)
    schedule.every().day.at("09:00").do(job_d)
    schedule.every().day.at("10:00").do(job_e)
    schedule.every().day.at("11:00").do(job_f)
    log.info("⏰ Schedule aktivní. Čekám na joby...")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()

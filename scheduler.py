"""
DARK FACTORY — Autonomous Scheduler + HTTP API
Runs factories on schedule, exposes HTTP trigger endpoints.

Schedule (UTC):
  06:00 → Factory B: Digital Products
  07:00 → Factory A: Web Hunter
  08:00 → Factory C: YouTube
  09:00 → Factory D: Data Products (ARES)
  10:00 → Factory E: SEO Content
  11:00 → Factory F: Leads API

HTTP API (port 8080):
  POST /trigger/a    — run Factory A now
  POST /trigger/b    — run Factory B now
  POST /trigger/c    — run Factory C now
  POST /trigger/d    — run Factory D now
  POST /trigger/e    — run Factory E now
  POST /trigger/f    — run Factory F now
  GET  /status       — last run info
  GET  /health       — healthcheck
  GET  /logs         — last N log lines
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

GITHUB_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "")
NOTIFY_PHONE = os.getenv("NOTIFY_PHONE", os.getenv("GMAIL_ADDRESS", ""))
IS_MAC       = platform.system() == "Darwin"
PORT         = int(os.getenv("PORT", "8080"))

# Track status of each factory
factory_status = {
    "b": {"name": "Digital Products", "last_run": None, "last_result": "never", "running": False},
    "a": {"name": "Web Hunter",       "last_run": None, "last_result": "never", "running": False},
    "c": {"name": "YouTube",          "last_run": None, "last_result": "never", "running": False},
    "d": {"name": "Data Products",    "last_run": None, "last_result": "never", "running": False},
    "e": {"name": "SEO Content",      "last_run": None, "last_result": "never", "running": False},
    "f": {"name": "Leads API",        "last_run": None, "last_result": "never", "running": False},
}


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────

def send_imessage(message: str):
    if not IS_MAC:
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

def job_b():
    ok = run_factory("b", str(BASE_DIR / "01_Digital_Products" / "factory.py"), "factory_b")
    push_outputs_to_github("Factory-B")
    if ok:
        pdf_dir = BASE_DIR / "_outputs" / "digital_products"
        pdfs = sorted(pdf_dir.glob("*.pdf"), key=lambda f: f.stat().st_mtime, reverse=True)
        pdf_name = pdfs[0].name if pdfs else "produkt"
        notify("Factory B hotovo ✅", f"'{pdf_name}' připraven k publikaci na Gumroad.")

def job_a():
    ok = run_factory("a", str(BASE_DIR / "05_Web_Hunter" / "factory.py"), "factory_a")
    push_outputs_to_github("Factory-A")
    if ok:
        notify("Factory A hotovo ✅", "Web Hunter leady připraveny → GitHub: _outputs/web_hunter/")

def job_c():
    ok = run_factory("c", str(BASE_DIR / "02_Faceless_YT" / "factory.py"), "factory_c")
    push_outputs_to_github("Factory-C")
    if ok:
        notify("Factory C hotovo ✅", "YouTube skripty připraveny → GitHub: _outputs/youtube/")

def job_d():
    ok = run_factory("d", str(BASE_DIR / "04_Data_Products" / "factory.py"), "factory_d")
    push_outputs_to_github("Factory-D")
    if ok:
        out_dir = BASE_DIR / "_outputs" / "data_products"
        csvs = sorted(out_dir.glob("*.csv"), key=lambda f: f.stat().st_mtime, reverse=True)
        csv_name = csvs[0].name if csvs else "data"
        notify("Factory D hotovo ✅", f"ARES data '{csv_name}' připravena → GitHub: _outputs/data_products/")

def job_e():
    ok = run_factory("e", str(BASE_DIR / "06_SEO_Content" / "factory.py"), "factory_e")
    push_outputs_to_github("Factory-E")
    if ok:
        out_dir = BASE_DIR / "_outputs" / "seo_content"
        articles = sorted(out_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        art_name = articles[0].name if articles else "článek"
        notify("Factory E hotovo ✅", f"SEO článek '{art_name}' připraven → GitHub: _outputs/seo_content/")

def job_f():
    ok = run_factory("f", str(BASE_DIR / "07_Leads_API" / "factory.py"), "factory_f")
    push_outputs_to_github("Factory-F")
    if ok:
        out_dir = BASE_DIR / "_outputs" / "leads_api"
        csvs = sorted(out_dir.glob("*.csv"), key=lambda f: f.stat().st_mtime, reverse=True)
        csv_name = csvs[0].name if csvs else "leads"
        notify("Factory F hotovo ✅", f"Leads balíček '{csv_name}' připraven → GitHub: _outputs/leads_api/")


# ── HTTP API ──────────────────────────────────────────────────────────────────

def start_api_server():
    """Run FastAPI in a background thread so scheduler keeps running."""
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn

        api = FastAPI(title="Dark Factory API")
        api.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        job_map = {
            "a": job_a, "b": job_b, "c": job_c,
            "d": job_d, "e": job_e, "f": job_f,
        }

        @api.get("/health")
        def health():
            return {"status": "ok", "time": datetime.now().isoformat()}

        @api.get("/status")
        def status():
            return {
                "factories": factory_status,
                "github_repo": GITHUB_REPO,
                "next_jobs": {
                    "06:00 UTC": "Factory B — Digital Products",
                    "07:00 UTC": "Factory A — Web Hunter",
                    "08:00 UTC": "Factory C — YouTube",
                    "09:00 UTC": "Factory D — Data Products (ARES)",
                    "10:00 UTC": "Factory E — SEO Content",
                    "11:00 UTC": "Factory F — Leads API",
                }
            }

        @api.post("/trigger/{factory_key}")
        def trigger(factory_key: str):
            if factory_key not in job_map:
                return {"error": f"Unknown factory '{factory_key}'. Use: a, b, c, d, e, f"}
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


# ── SCHEDULE + MAIN ───────────────────────────────────────────────────────────

def main():
    schedule.every().day.at("06:00").do(job_b)
    schedule.every().day.at("07:00").do(job_a)
    schedule.every().day.at("08:00").do(job_c)
    schedule.every().day.at("09:00").do(job_d)
    schedule.every().day.at("10:00").do(job_e)
    schedule.every().day.at("11:00").do(job_f)

    log.info("╔══════════════════════════════════════════════╗")
    log.info("║     DARK FACTORY — SCHEDULER ONLINE          ║")
    log.info("║  6 Factories | Fully Autonomous | 24/7       ║")
    log.info("╚══════════════════════════════════════════════╝")
    log.info(f"Platform: {'macOS' if IS_MAC else 'Linux/Railway'} | API port: {PORT}")
    log.info("Schedule (UTC): 06→B | 07→A | 08→C | 09→D | 10→E | 11→F")

    # Start HTTP API in background thread
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    if os.getenv("RUN_ON_STARTUP", "false").lower() == "true":
        log.info("RUN_ON_STARTUP=true — spouštím všechny factories...")
        for job in [job_b, job_a, job_c, job_d, job_e, job_f]:
            job()

    log.info("Čekám na první job...")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()

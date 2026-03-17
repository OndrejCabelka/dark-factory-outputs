"""
DARK FACTORY — Autonomous Scheduler
Runs factories on schedule, pushes results to GitHub.
Deploy on Railway for 24/7 operation.

Schedule (UTC):
  06:00 UTC (8:00 CZ) → Factory B: Digital Products
  07:00 UTC (9:00 CZ) → Factory A: Web Hunter
  08:00 UTC (10:00 CZ) → Factory C: YouTube
"""

import os
import sys
import time
import platform
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
NOTIFY_PHONE = os.getenv("NOTIFY_PHONE", "ondrej.cabelka@gmail.com")  # iMessage target

IS_MAC = platform.system() == "Darwin"


# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────

def send_imessage(message: str):
    """Send iMessage notification (macOS only)."""
    if not IS_MAC:
        return
    try:
        script = f'''
tell application "Messages"
    set targetService to 1st account whose service type = iMessage
    set targetBuddy to participant "{NOTIFY_PHONE}" of targetService
    send "{message}" to targetBuddy
end tell
'''
        subprocess.run(["osascript", "-e", script], timeout=10, check=True)
        log.info(f"📱 iMessage sent")
    except Exception as e:
        log.warning(f"iMessage failed (OK on Railway): {e}")


def send_email_via_resend(subject: str, body: str):
    """Send email via Resend.com (works on Railway too)."""
    resend_key = os.getenv("RESEND_API_KEY", "")
    if not resend_key:
        return
    try:
        import requests
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
            json={
                "from": "DarkFactory <noreply@resend.dev>",
                "to": [NOTIFY_PHONE],
                "subject": subject,
                "text": body,
            }
        )
        if r.status_code == 200:
            log.info("📧 Email notification sent")
        else:
            log.warning(f"Email failed: {r.text[:200]}")
    except Exception as e:
        log.warning(f"Email notification failed: {e}")


def notify(title: str, message: str):
    """Send notification via iMessage (Mac) or email (Railway)."""
    full_msg = f"🏭 DARK FACTORY\n{title}\n{message}"
    if IS_MAC:
        send_imessage(full_msg)
    else:
        send_email_via_resend(f"[DarkFactory] {title}", full_msg)


# ── GIT PUSH ─────────────────────────────────────────────────────────────────

def push_outputs_to_github(factory_name: str):
    """Commit and push outputs to GitHub."""
    if not GITHUB_REPO or not GITHUB_TOKEN:
        log.warning("GitHub not configured — skipping push.")
        return

    try:
        import git
        repo_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"

        try:
            repo = git.Repo(BASE_DIR)
        except git.InvalidGitRepositoryError:
            repo = git.Repo.init(BASE_DIR)
            repo.create_remote("origin", repo_url)
            log.info("Git repo initialised.")

        try:
            repo.remote("origin").set_url(repo_url)
        except Exception:
            repo.create_remote("origin", repo_url)

        repo.config_writer().set_value("user", "name", "DarkFactory").release()
        repo.config_writer().set_value("user", "email", "darkfactory@auto.run").release()

        repo.git.add("_outputs/")
        repo.git.add("_logs/")

        if repo.is_dirty(index=True):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_msg = f"[{factory_name}] Auto output — {timestamp}"
            repo.index.commit(commit_msg)
            repo.remote("origin").push(refspec="HEAD:main", force=True)
            log.info(f"✅ Pushed to GitHub: {GITHUB_REPO}")
        else:
            log.info("Nothing new to push.")

    except Exception as e:
        log.error(f"GitHub push failed: {e}")


# ── FACTORY RUNNER ────────────────────────────────────────────────────────────

def run_factory(factory_key: str, factory_path: str, module_name: str):
    """Load and run a factory module."""
    log.info(f"▶ STARTING {factory_key}")
    start = datetime.now()
    try:
        spec = importlib.util.spec_from_file_location(module_name, factory_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()
        elapsed = (datetime.now() - start).seconds
        log.info(f"✅ {factory_key} COMPLETED in {elapsed}s")
        return True
    except Exception as e:
        log.error(f"❌ {factory_key} FAILED: {e}")
        return False


def job_digital_products():
    """Run Factory B and notify when product is ready to publish."""
    ok = run_factory(
        "Factory B — Digital Products",
        str(BASE_DIR / "01_Digital_Products" / "factory.py"),
        "factory_b"
    )
    push_outputs_to_github("Factory-B")

    if ok:
        # Find the latest generated PDF
        pdf_dir = BASE_DIR / "_outputs" / "digital_products"
        pdfs = sorted(pdf_dir.glob("*.pdf"), key=lambda f: f.stat().st_mtime, reverse=True)
        pdf_name = pdfs[0].name if pdfs else "produkt vytvořen"
        github_url = f"https://github.com/{GITHUB_REPO}/tree/main/_outputs/digital_products" if GITHUB_REPO else "viz _outputs/digital_products/"

        notify(
            "Factory B hotovo ✅",
            f"Produkt '{pdf_name}' připraven.\nPublikuj na: gumroad.com/products/new\nStáhnout: {github_url}"
        )


def job_web_hunter():
    ok = run_factory(
        "Factory A — Web Hunter",
        str(BASE_DIR / "05_Web_Hunter" / "factory.py"),
        "factory_a"
    )
    push_outputs_to_github("Factory-A")
    if ok:
        notify("Factory A hotovo ✅", "Web Hunter leady připraveny.\nViz GitHub: _outputs/web_hunter/")


def job_youtube():
    ok = run_factory(
        "Factory C — YouTube",
        str(BASE_DIR / "02_Faceless_YT" / "factory.py"),
        "factory_c"
    )
    push_outputs_to_github("Factory-C")
    if ok:
        notify("Factory C hotovo ✅", "YouTube skripty připraveny.\nViz GitHub: _outputs/youtube/")


# ── SCHEDULE ─────────────────────────────────────────────────────────────────

def setup_schedule():
    schedule.every().day.at("06:00").do(job_digital_products)  # 8:00 CZ
    schedule.every().day.at("07:00").do(job_web_hunter)         # 9:00 CZ
    schedule.every().day.at("08:00").do(job_youtube)            # 10:00 CZ

    log.info("╔══════════════════════════════════════╗")
    log.info("║   DARK FACTORY — SCHEDULER ONLINE    ║")
    log.info("╚══════════════════════════════════════╝")
    log.info(f"Platform: {'macOS (iMessage notifications)' if IS_MAC else 'Linux/Railway (email notifications)'}")
    log.info("Schedule (CZ time): 08:00 → B | 09:00 → A | 10:00 → C")
    log.info("Waiting for next job...")


def main():
    setup_schedule()

    first_run = os.getenv("RUN_ON_STARTUP", "false").lower() == "true"
    if first_run:
        log.info("RUN_ON_STARTUP=true — running all factories now...")
        job_digital_products()
        job_web_hunter()
        job_youtube()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()

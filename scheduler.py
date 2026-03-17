"""
DARK FACTORY — Autonomous Scheduler
Runs factories on schedule, pushes results to GitHub.
Deploy this on Railway for 24/7 operation.

Schedule (UTC — Railway runs in UTC):
  06:00 UTC (8:00 CZ) → Factory B: Digital Products
  07:00 UTC (9:00 CZ) → Factory A: Web Hunter
  08:00 UTC (10:00 CZ) → Factory C: YouTube
"""

import os
import sys
import time
import schedule
import logging
import subprocess
import importlib.util
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ── SETUP ─────────────────────────────────────────────────────────────────────

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
GITHUB_REPO  = os.getenv("GITHUB_REPO", "")   # format: username/repo-name


# ── GIT PUSH ─────────────────────────────────────────────────────────────────

def push_outputs_to_github(factory_name: str):
    """Commit and push all new outputs to GitHub."""
    if not GITHUB_REPO or not GITHUB_TOKEN:
        log.warning("GitHub not configured — outputs saved locally only.")
        return

    try:
        import git
        repo_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"

        # Init repo if needed
        try:
            repo = git.Repo(BASE_DIR)
        except git.InvalidGitRepositoryError:
            repo = git.Repo.init(BASE_DIR)
            repo.create_remote("origin", repo_url)
            log.info("Git repo initialised.")

        # Update remote URL with token
        try:
            repo.remote("origin").set_url(repo_url)
        except Exception:
            repo.create_remote("origin", repo_url)

        # Configure git identity
        repo.config_writer().set_value("user", "name", "DarkFactory").release()
        repo.config_writer().set_value("user", "email", "darkfactory@auto.run").release()

        # Stage _outputs
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
    try:
        spec = importlib.util.spec_from_file_location(module_name, factory_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()
        log.info(f"✅ {factory_key} COMPLETED")
        push_outputs_to_github(factory_key)
    except Exception as e:
        log.error(f"❌ {factory_key} FAILED: {e}")


def job_digital_products():
    run_factory(
        "Factory B — Digital Products",
        str(BASE_DIR / "01_Digital_Products" / "factory.py"),
        "factory_b"
    )

def job_web_hunter():
    run_factory(
        "Factory A — Web Hunter",
        str(BASE_DIR / "05_Web_Hunter" / "factory.py"),
        "factory_a"
    )

def job_youtube():
    run_factory(
        "Factory C — YouTube",
        str(BASE_DIR / "02_Faceless_YT" / "factory.py"),
        "factory_c"
    )


# ── SCHEDULE ─────────────────────────────────────────────────────────────────

def setup_schedule():
    # UTC times (Czech time = UTC+1 winter, UTC+2 summer)
    schedule.every().day.at("06:00").do(job_digital_products)  # 8:00 CZ
    schedule.every().day.at("07:00").do(job_web_hunter)         # 9:00 CZ
    schedule.every().day.at("08:00").do(job_youtube)            # 10:00 CZ

    log.info("╔══════════════════════════════════════╗")
    log.info("║   DARK FACTORY — SCHEDULER ONLINE    ║")
    log.info("╚══════════════════════════════════════╝")
    log.info("Schedule (CZ time):")
    log.info("  08:00 → Factory B: Digital Products")
    log.info("  09:00 → Factory A: Web Hunter")
    log.info("  10:00 → Factory C: YouTube")
    log.info("Waiting for next job...")


def main():
    setup_schedule()

    # Run all factories immediately on first startup (optional — remove if unwanted)
    first_run = os.getenv("RUN_ON_STARTUP", "false").lower() == "true"
    if first_run:
        log.info("RUN_ON_STARTUP=true — running all factories now...")
        job_digital_products()
        job_web_hunter()
        job_youtube()

    # Main loop
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()

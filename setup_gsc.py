"""
Google Search Console — verifikace GitHub Pages + odeslání sitemap

Použití:
  python setup_gsc.py --verify-code=google1234567890abcdef.html
  python setup_gsc.py --meta-tag="google-site-verification" content="abc123"

Jak získat kód:
  1. Jdi na https://search.google.com/search-console
  2. Klikni "Add property" → URL prefix
  3. Zadej: https://ondrejcabelka.github.io/dark-factory-outputs/
  4. Vyber "HTML file" nebo "HTML tag" verifikaci
  5. Zkopíruj název souboru nebo meta tag obsah
  6. Spusť tento script s kódem
"""
import os, sys, subprocess, tempfile
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(dotenv_path=BASE_DIR / "_config" / ".env")

GITHUB_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "ondrejcabelka/dark-factory-outputs")
PAGES_BRANCH = "gh-pages"
BASE_URL     = "https://ondrejcabelka.github.io/dark-factory-outputs"


def push_verification_file(filename: str, content: str):
    """Pushne verifikační soubor na GitHub Pages."""
    owner = GITHUB_REPO.split("/")[0]
    repo_url = f"https://{owner}:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
    git_env = os.environ.copy()
    git_env["GIT_TERMINAL_PROMPT"] = "0"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        def git(*args):
            return subprocess.run(
                ["git", "-c", "credential.helper="] + list(args),
                cwd=tmp, capture_output=True, text=True, env=git_env
            )

        git("clone", "--branch", PAGES_BRANCH, "--depth=1", repo_url, str(tmp))
        (tmp / filename).write_text(content)
        git("config", "user.email", "darkfactory@auto.run")
        git("config", "user.name", "DarkFactory")
        git("add", filename)
        git("commit", "-m", f"[GSC] Add verification file: {filename}")
        push = git("push", repo_url, f"HEAD:{PAGES_BRANCH}")
        if push.returncode == 0:
            print(f"✅ Verifikační soubor publikován: {BASE_URL}/{filename}")
            print(f"\nDalší kroky v Google Search Console:")
            print(f"  1. Klikni 'Verify' v GSC")
            print(f"  2. Po verifikaci jdi do Sitemaps")
            print(f"  3. Přidej: {BASE_URL}/sitemap.xml")
        else:
            print(f"❌ Push selhal: {push.stderr[:200]}")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        print("\nSITEMAP URL pro GSC:")
        print(f"  {BASE_URL}/sitemap.xml")
        print("\nProperty URL pro GSC:")
        print(f"  {BASE_URL}/")
        return

    for arg in args:
        if arg.startswith("--verify-code="):
            filename = arg.split("=", 1)[1]
            # GSC soubor obsahuje jen "google-site-verification: {kód}"
            code = filename.replace(".html", "").replace("google", "")
            content = f"google-site-verification: {filename.replace('.html', '')}"
            push_verification_file(filename, content)

        elif arg.startswith("--meta-tag="):
            print("Meta tag verifikace: přidej tento tag do HTML šablony v publish_seo.py:")
            print(f'  <meta name="google-site-verification" content="{arg.split("=",1)[1]}">')
            print("\nPak spusť: python publish_seo.py --all")


if __name__ == "__main__":
    main()

"""
DARK FACTORY — SEO Auto-Publisher
Vezme nejnovější MD článek z _outputs/seo_content/, vygeneruje HTML stránku
a pushne ji do GitHub Pages větve dark-factory-outputs repozitáře.

Po nastavení GitHub Pages na branch `gh-pages` bude článek dostupný na:
  https://ondrejcabelka.github.io/dark-factory-outputs/seo/[slug]/

Spuštění: python3 publish_seo.py
          python3 publish_seo.py --all   (zpracuje všechny MD soubory)
"""

import os
import re
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(dotenv_path=BASE_DIR / "_config" / ".env")

GITHUB_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "ondrejcabelka/dark-factory-outputs")
GITHUB_PAGES_BRANCH = "gh-pages"
SEO_DIR = BASE_DIR / "_outputs" / "seo_content"

# ── HTML ŠABLONA ──────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="cs">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="keywords" content="{keywords}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="article">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{canonical_url}">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           line-height: 1.7; color: #1a1a2e; background: #fafafa; margin: 0; padding: 0; }}
    .container {{ max-width: 780px; margin: 0 auto; padding: 24px 20px 60px; }}
    h1 {{ font-size: 2em; line-height: 1.25; color: #0d0d1a; margin-bottom: 8px; }}
    h2 {{ font-size: 1.4em; color: #1a1a2e; border-bottom: 2px solid #e8e8e8;
          padding-bottom: 6px; margin-top: 2em; }}
    h3 {{ font-size: 1.15em; color: #333; margin-top: 1.5em; }}
    p {{ margin: 1em 0; }}
    a {{ color: #2563eb; }}
    table {{ width: 100%; border-collapse: collapse; margin: 1.5em 0; font-size: 0.95em; }}
    th {{ background: #2563eb; color: white; padding: 10px 12px; text-align: left; }}
    td {{ padding: 9px 12px; border-bottom: 1px solid #e5e7eb; }}
    tr:nth-child(even) {{ background: #f3f4f6; }}
    code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
    blockquote {{ border-left: 4px solid #2563eb; margin: 1em 0; padding: 10px 20px;
                  background: #eff6ff; border-radius: 0 8px 8px 0; }}
    ul, ol {{ padding-left: 1.5em; }}
    li {{ margin: 0.4em 0; }}
    .meta {{ color: #666; font-size: 0.9em; margin-bottom: 1.5em; }}
    .toc {{ background: #f0f4ff; border: 1px solid #d1dafe; border-radius: 8px;
            padding: 16px 24px; margin: 1.5em 0; }}
    .toc h2 {{ border: none; font-size: 1em; margin: 0 0 8px; }}
    .toc a {{ text-decoration: none; }}
    .faq-item {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px;
                 padding: 16px; margin: 12px 0; }}
    footer {{ text-align: center; color: #999; font-size: 0.8em; margin-top: 3em;
              border-top: 1px solid #e5e7eb; padding-top: 1em; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="meta">📅 {date} &nbsp;|&nbsp; ⏱ Čas čtení: ~{read_time} min</div>
    {body}
    <footer>
      <p>© {year} Dark Factory | Obsah generován AI</p>
    </footer>
  </div>
</body>
</html>"""


# ── MARKDOWN → HTML ───────────────────────────────────────────────────────────

def md_to_html(md: str) -> tuple[str, str, str]:
    """Jednoduchý MD→HTML konvertor. Vrátí (html_body, title, first_para)."""
    lines = md.split("\n")
    html_parts = []
    title = ""
    description = ""
    in_table = False
    in_faq = False
    in_code = False
    i = 0

    # Přeskoč YAML frontmatter
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            i += 1
        i += 1

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Code block
        if stripped.startswith("```"):
            if in_code:
                html_parts.append("</code></pre>")
                in_code = False
            else:
                html_parts.append("<pre><code>")
                in_code = True
            i += 1
            continue

        if in_code:
            html_parts.append(line.replace("<", "&lt;").replace(">", "&gt;"))
            i += 1
            continue

        # Table
        if "|" in stripped and stripped.startswith("|"):
            if not in_table:
                html_parts.append("<table>")
                in_table = True
                # Header
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                html_parts.append("<thead><tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr></thead><tbody>")
                i += 1
                if i < len(lines) and re.match(r"^\|[-| :]+\|", lines[i].strip()):
                    i += 1  # přeskoč separator
                continue
            else:
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                html_parts.append("<tr>" + "".join(f"<td>{inline_md(c)}</td>" for c in cells) + "</tr>")
                i += 1
                continue
        elif in_table:
            html_parts.append("</tbody></table>")
            in_table = False

        if not stripped:
            html_parts.append("")
            i += 1
            continue

        # Headings
        if stripped.startswith("# "):
            text = inline_md(re.sub(r"\{#[^}]+\}", "", stripped[2:]).strip())
            if not title:
                title = text
                html_parts.append(f"<h1>{text}</h1>")
            else:
                html_parts.append(f"<h1>{text}</h1>")
        elif stripped.startswith("## "):
            text = inline_md(re.sub(r"\{#[^}]+\}", "", stripped[3:]).strip())
            slug = re.sub(r"[^\w]+", "-", text.lower()).strip("-")
            html_parts.append(f'<h2 id="{slug}">{text}</h2>')
        elif stripped.startswith("### "):
            text = inline_md(re.sub(r"\{#[^}]+\}", "", stripped[4:]).strip())
            html_parts.append(f"<h3>{text}</h3>")
        elif stripped.startswith("#### "):
            html_parts.append(f"<h4>{inline_md(stripped[5:])}</h4>")
        elif stripped.startswith("---"):
            html_parts.append("<hr>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            # Collect list items
            items = []
            while i < len(lines) and (lines[i].strip().startswith("- ") or lines[i].strip().startswith("* ")):
                items.append(f"<li>{inline_md(lines[i].strip()[2:])}</li>")
                i += 1
            html_parts.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif re.match(r"^\d+\. ", stripped):
            items = []
            while i < len(lines) and re.match(r"^\d+\. ", lines[i].strip()):
                item_text = re.sub(r"^\d+\. ", "", lines[i].strip())
                items.append(f"<li>{inline_md(item_text)}</li>")
                i += 1
            html_parts.append("<ol>" + "".join(items) + "</ol>")
            continue
        elif stripped.startswith("> "):
            html_parts.append(f"<blockquote>{inline_md(stripped[2:])}</blockquote>")
        else:
            text = inline_md(stripped)
            html_parts.append(f"<p>{text}</p>")
            if not description and len(stripped) > 60:
                description = stripped[:200].rstrip(".,") + "..."

        i += 1

    if in_table:
        html_parts.append("</tbody></table>")

    return "\n".join(html_parts), title, description


def inline_md(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\{#[^}]+\}", "", text)
    return text


# ── SLUG ─────────────────────────────────────────────────────────────────────

def make_slug(title: str) -> str:
    replacements = {
        'á':'a','č':'c','ď':'d','é':'e','ě':'e','í':'i','ň':'n','ó':'o',
        'ř':'r','š':'s','ť':'t','ú':'u','ů':'u','ý':'y','ž':'z',
        'Á':'a','Č':'c','Ď':'d','É':'e','Ě':'e','Í':'i','Ň':'n','Ó':'o',
        'Ř':'r','Š':'s','Ť':'t','Ú':'u','Ů':'u','Ý':'y','Ž':'z',
    }
    slug = title.lower()
    for k, v in replacements.items():
        slug = slug.replace(k, v)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug[:60]


# ── PUBLISHER ─────────────────────────────────────────────────────────────────

def publish_article(md_path: Path) -> str | None:
    """Publikuje jeden MD soubor. Vrátí URL nebo None."""
    md = md_path.read_text(encoding="utf-8")

    # Extrahuj keyword z frontmatter
    keyword = ""
    niche = ""
    for line in md.split("\n")[:10]:
        if line.startswith("keyword:"):
            keyword = line.split(":", 1)[1].strip()
        elif line.startswith("niche:"):
            niche = line.split(":", 1)[1].strip()

    body, title, description = md_to_html(md)
    if not title:
        title = keyword or md_path.stem
    if not description:
        description = f"Průvodce: {title}"

    slug = make_slug(keyword or title)
    read_time = max(1, len(md.split()) // 200)
    canonical = f"https://ondrejcabelka.github.io/dark-factory-outputs/seo/{slug}/"

    html = HTML_TEMPLATE.format(
        title=title,
        description=description,
        keywords=f"{keyword}, {niche}, recenze, srovnání, návod",
        canonical_url=canonical,
        body=body,
        date=datetime.now().strftime("%-d. %-m. %Y"),
        read_time=read_time,
        year=datetime.now().year,
    )

    # Klonuj/updatuj gh-pages branch
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("⚠️  GITHUB_TOKEN nebo GITHUB_REPO chybí — pouze lokální uložení")
        local = SEO_DIR / f"{slug}.html"
        local.write_text(html, encoding="utf-8")
        print(f"✅ Lokální HTML: {local}")
        return str(local)

    with tempfile.TemporaryDirectory() as tmpdir:
        # GitHub potřebuje formát username:token (ne jen token)
        owner = GITHUB_REPO.split("/")[0]
        repo_url = f"https://{owner}:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
        tmp = Path(tmpdir)

        # Zakáž interaktivní git prompty
        git_env = os.environ.copy()
        git_env["GIT_TERMINAL_PROMPT"] = "0"
        git_env["GIT_ASKPASS"] = "/bin/echo"

        def git(*args, **kwargs):
            return subprocess.run(
                ["git", "-c", "credential.helper="] + list(args),
                cwd=tmp, capture_output=True, text=True, env=git_env, **kwargs
            )

        clone = git("clone", "--branch", GITHUB_PAGES_BRANCH, "--depth=1", repo_url, str(tmp))
        if clone.returncode != 0:
            # Branch neexistuje — klonuj main a vytvoř orphan gh-pages
            subprocess.run(
                ["git", "-c", "credential.helper=", "clone", "--depth=1", repo_url, str(tmp)],
                capture_output=True, env=git_env
            )
            git("checkout", "--orphan", GITHUB_PAGES_BRANCH)
            git("rm", "-rf", ".")
            (tmp / "index.html").write_text("<html><body><h1>Dark Factory SEO</h1></body></html>")

        # Ulož článek
        article_dir = tmp / "seo" / slug
        article_dir.mkdir(parents=True, exist_ok=True)
        (article_dir / "index.html").write_text(html, encoding="utf-8")

        # Aktualizuj sitemap
        _update_sitemap(tmp)

        # Commit + push
        git("config", "user.email", "darkfactory@auto.run")
        git("config", "user.name", "DarkFactory")
        git("add", "-A")
        commit = git("commit", "-m", f"[SEO] Publish: {title[:60]}")
        if "nothing to commit" in commit.stdout:
            print(f"ℹ️  Článek již publikován: {canonical}")
            return canonical
        push = git("push", "-f", repo_url, f"HEAD:{GITHUB_PAGES_BRANCH}")
        if push.returncode != 0:
            raise RuntimeError(f"git push failed: {push.stderr[:300]}")
        print(f"✅ Publikováno: {canonical}")
        return canonical


def _update_sitemap(repo_dir: Path):
    """Vygeneruje sitemap.xml ze všech HTML stránek."""
    urls = []
    for html_file in (repo_dir / "seo").rglob("index.html"):
        rel = html_file.parent.relative_to(repo_dir)
        url = f"https://ondrejcabelka.github.io/dark-factory-outputs/{rel}/"
        urls.append(f"  <url><loc>{url}</loc><changefreq>weekly</changefreq></url>")

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""
    (repo_dir / "sitemap.xml").write_text(sitemap)


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main(publish_all: bool = False) -> str | None:
    md_files = sorted(SEO_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    md_files = [f for f in md_files if not f.name.startswith("generated")]

    if not md_files:
        print("⚠️  Žádné MD soubory v _outputs/seo_content/")
        return None

    targets = md_files if publish_all else [md_files[0]]
    published_urls = []

    for md_path in targets:
        print(f"📝 Publikuji: {md_path.name}")
        url = publish_article(md_path)
        if url:
            published_urls.append(url)

    if published_urls:
        log = BASE_DIR / "_outputs" / "seo_content" / "published_urls.txt"
        existing = log.read_text().splitlines() if log.exists() else []
        new_entries = [u for u in published_urls if u not in existing]
        if new_entries:
            log.write_text("\n".join(existing + new_entries) + "\n")
        print(f"\n🌐 Publikováno {len(published_urls)} článků")
        for u in published_urls:
            print(f"   → {u}")

    return published_urls[0] if published_urls else None


if __name__ == "__main__":
    publish_all = "--all" in sys.argv
    main(publish_all=publish_all)

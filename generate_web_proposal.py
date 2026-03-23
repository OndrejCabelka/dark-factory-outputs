"""
WebHunter — Fáze 2: AI HTML Web Proposal Generator
====================================================
Bere lead (jméno firmy, obor, město) → Claude vygeneruje
personalizovaný HTML návrh webu → publikuje na GitHub Pages.

URL pattern: https://ondrejcabelka.github.io/dark-factory-outputs/navrhy/{slug}/

Použití:
  python3 generate_web_proposal.py --lead "Instalatér Novák" --obor instalatér --mesto Praha --tel +420777123456
  python3 generate_web_proposal.py --csv _outputs/web_hunter/leads_20260321_111443.csv --limit 5
  python3 generate_web_proposal.py --batch  # vygeneruje top 10 leadů z posledního CSV
"""

import os, re, csv, json, base64, requests, argparse, unicodedata
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import anthropic

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / "_config" / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN      = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "") or os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO       = os.getenv("GITHUB_REPO", "OndrejCabelka/dark-factory-outputs")

OUTPUT_DIR = BASE_DIR / "_outputs" / "web_navrhy"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROPOSALS_INDEX = OUTPUT_DIR / "proposals_index.json"
BASE_URL = f"https://ondrejcabelka.github.io/dark-factory-outputs/navrhy"


# ── SLUG HELPER ───────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text[:50]


# ── HTML GENERATOR (Claude) ───────────────────────────────────────────────────

OBOR_ICONS = {
    "instalatér": "🔧", "elektrikář": "⚡", "malíř natěrač": "🖌️",
    "klempíř": "🔩", "truhlář": "🪵", "zedník": "🧱", "pokrývač": "🏠",
    "tesař": "🪚", "obkladač": "🪟", "zahradník": "🌿",
    "stavební firma": "🏗️", "fasáda": "🏢",
}

OBOR_SERVICES = {
    "instalatér": ["Oprava vodovodního potrubí", "Instalace koupelen", "Výměna bojlerů", "Havárie 24/7", "Ústřední topení"],
    "elektrikář": ["Elektroinstalace", "Revize elektro", "Hromosvod", "Fotovoltaika", "Rekonstrukce rozvodů"],
    "malíř natěrač": ["Malování interiérů", "Fasádní nátěry", "Tapetování", "Zateplení fasád", "Stropy a SDK"],
    "klempíř": ["Oplechování střech", "Okapy a svody", "Vikýře", "Střešní okna", "Opravy plechových střech"],
    "truhlář": ["Kuchyňské linky na míru", "Vestavěné skříně", "Dřevěné podlahy", "Schody", "Dveře a okna"],
    "zedník": ["Zednické práce", "Rekonstrukce bytů", "Betonářské práce", "Přístavby", "Omítky"],
    "pokrývač": ["Pokládka střešní krytiny", "Opravy střech", "Tepelná izolace", "Střechy na klíč", "Vikýře"],
    "tesař": ["Krovové konstrukce", "Dřevěné altány", "Pergoly", "Opravy krovů", "Dřevostavby"],
    "obkladač": ["Pokládka obkladů a dlažby", "Koupelny na klíč", "Terasy", "Epoxidové spárování", "Hydroizolace"],
    "zahradník": ["Zakládání zahrad", "Sekání trávy", "Výsadba rostlin", "Závlahové systémy", "Zahradní úpravy"],
}


def generate_html_proposal(lead: dict) -> str:
    """Claude vygeneruje kompletní single-page HTML návrh webu pro firmu."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    nazev  = lead.get("nazev", lead.get("name", "Vaše firma"))
    obor   = lead.get("obor", "řemeslník")
    mesto  = lead.get("mesto", "Česká republika")
    tel    = lead.get("telefon", lead.get("tel", ""))
    rating = lead.get("rating", "")

    icon     = OBOR_ICONS.get(obor, "🔨")
    services = OBOR_SERVICES.get(obor, ["Profesionální práce", "Rychlý servis", "Kvalita garantována", "Přijatelná cena"])
    services_list = "\n".join(f"  - {s}" for s in services)

    stars = ""
    if rating:
        try:
            r = float(rating)
            stars = f" · ⭐ {r:.1f}/5 na Google"
        except:
            pass

    prompt = f"""Jsi expert webdesigner. Vytvoř KOMPLETNÍ, profesionální single-page HTML web pro tuto firmu.

FIRMA: {nazev}
OBOR: {obor} {icon}
MĚSTO: {mesto}
TELEFON: {tel or "neuvedeno"}{stars}

SLUŽBY FIRMY (zahrni do webu):
{services_list}

TECHNICKÉ POŽADAVKY — musíš splnit VŠECHNY:
1. Kompletní HTML5 dokument (<!DOCTYPE html> ... </html>) — vše v jednom souboru
2. Inline CSS v <style> tagu — žádné externí soubory
3. Žádný JavaScript (čistý HTML/CSS)
4. Mobile-first, responsivní design
5. Moderní, profesionální vzhled — tmavý hero, barvy dle oboru
6. Font: system-ui nebo Google Fonts (přes @import v CSS)

STRUKTURA WEBU (povinná):
1. <header> — navbar: logo (název firmy) + telefonní číslo jako CTA tlačítko
2. <section id="hero"> — velký hero s:
   - H1: "Profesionální {obor} v {mesto} a okolí"
   - Podnadpis (benefit-oriented, 1 věta)
   - 2 CTA tlačítka: "Zavolat nyní" (tel: odkaz) + "Napsat e-mail"
3. <section id="sluzby"> — grid karet služeb (min. 4 karty s ikonami)
4. <section id="proc-my"> — 3 benefity proč vybrat tuto firmu
5. <section id="reference"> — 2-3 fiktivní recenze zákazníků (jméno + text, 2-3 věty)
6. <section id="kontakt"> — kontaktní info: telefon (klikatelný), e-mail placeholder, adresa + mapa placeholder
7. <footer> — copyright, IČO placeholder

VIZUÁLNÍ STYL:
- Hero: tmavý gradient nebo silná fotka-like barva dle oboru (modrá pro instalatéra, žlutá pro elektrikáře, zelená pro zahradníka)
- Karty: lehký shadow, hover efekt (CSS :hover)
- Barvy: primární + bílá + tmavé pozadí
- Zaoblené rohy (border-radius: 12px)
- Moderní typografie, dostatek bílého prostoru

BANNER NAHOŘE (vložit JAKO PRVNÍ v <body>, před vším ostatním):
<div id="proposal-banner" style="background:linear-gradient(135deg,#FF4D00,#ff7c47);color:white;text-align:center;padding:12px 20px;font-size:13px;font-family:system-ui">
  📋 <strong>Návrh webu</strong> pro {nazev} · Připravil Ondřej Čábelka, webdesigner · 
  <a href="mailto:ondrej.cabelka@gmail.com" style="color:white;font-weight:bold">ondrej.cabelka@gmail.com</a> · 
  <a href="tel:+420XXXXXXXXX" style="color:white;font-weight:bold">Domluvit spolupráci →</a>
</div>

DŮLEŽITÉ:
- Přizpůsob design oboru (barvy, ikony, texty)
- Telefon {tel or 'XX XXX XXX XXX'} musí být klikatelný (href="tel:...")
- Vše česky, přirozený jazyk
- Výstup: POUZE čistý HTML kód, bez markdown bloků, bez vysvětlení před/po kódu
- Začni přímo s: <!DOCTYPE html>"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}]
    )

    html = msg.content[0].text.strip()

    # Pokud Claude zabalil do markdown bloku
    if html.startswith("```"):
        html = re.sub(r"^```[html]*\n?", "", html)
        html = re.sub(r"\n?```$", "", html)

    return html


# ── GITHUB PAGES PUBLISHER ────────────────────────────────────────────────────

def publish_to_github(slug: str, html: str) -> str:
    """Publikuje HTML na GitHub Pages pod /navrhy/{slug}/index.html"""
    if not GITHUB_TOKEN:
        print("  ⚠ Chybí GITHUB_TOKEN — ukládám jen lokálně")
        return f"{BASE_URL}/{slug}/"

    repo = GITHUB_REPO
    path = f"navrhy/{slug}/index.html"
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    # Zkontroluj jestli soubor existuje (pro update)
    sha = None
    r = requests.get(api_url, headers=headers)
    if r.status_code == 200:
        sha = r.json().get("sha")

    content_b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")
    payload = {
        "message": f"navrh: {slug}",
        "content": content_b64,
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha

    for attempt in range(3):
        try:
            r = requests.put(api_url, headers=headers, json=payload, timeout=15)
            if r.status_code in (200, 201):
                url = f"{BASE_URL}/{slug}/"
                print(f"  ✅ Publikováno: {url}")
                return url
            elif r.status_code == 422:
                # SHA conflict — refresh SHA a zkus znovu
                r2 = requests.get(api_url, headers=headers, timeout=10)
                if r2.status_code == 200:
                    payload["sha"] = r2.json().get("sha")
                    continue
            elif r.status_code in (429, 500, 502, 503):
                import time as _t; _t.sleep(5 * (attempt + 1))
                continue
            print(f"  ⚠ GitHub publish chyba {r.status_code}: {r.text[:100]}")
            break
        except Exception as e:
            import time as _t; _t.sleep(5 * (attempt + 1))
            if attempt == 2:
                print(f"  ⚠ GitHub publish exception: {e}")
    return f"{BASE_URL}/{slug}/"


# ── INDEX MANAGEMENT ──────────────────────────────────────────────────────────

def load_index() -> dict:
    if PROPOSALS_INDEX.exists():
        return json.loads(PROPOSALS_INDEX.read_text())
    return {}


def save_index(index: dict):
    PROPOSALS_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2))


# ── MAIN FLOW ─────────────────────────────────────────────────────────────────

def generate_for_lead(lead: dict) -> dict:
    """Vygeneruje návrh pro jeden lead. Vrátí metadata."""
    nazev = lead.get("nazev", lead.get("name", ""))
    obor  = lead.get("obor", "řemeslník")
    mesto = lead.get("mesto", "")

    slug = slugify(f"{nazev}-{obor}-{mesto}")
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n🎨 Generuji návrh: {nazev} | {obor} | {mesto}")
    print(f"  Slug: {slug}")

    # Check if already generated
    index = load_index()
    if slug in index:
        print(f"  ℹ Již existuje: {index[slug]['url']}")
        return index[slug]

    # Generate HTML
    html = generate_html_proposal(lead)
    size_kb = len(html) / 1024

    # Save locally
    local_path = OUTPUT_DIR / f"{slug}.html"
    local_path.write_text(html, encoding="utf-8")
    print(f"  💾 Uloženo: {local_path.name} ({size_kb:.1f} kB)")

    # Publish to GitHub Pages
    url = publish_to_github(slug, html)

    # Update index
    tracking_id = lead.get("tracking_id", lead.get("id", slug))
    metadata = {
        "slug":         slug,
        "lead_id":      lead.get("id", ""),
        "tracking_id":  tracking_id,
        "nazev":        nazev,
        "obor":         obor,
        "mesto":        mesto,
        "telefon":      lead.get("telefon", lead.get("tel", "")),
        "url":          url,
        "generated":    ts,
        "html_size":    round(size_kb, 1),
    }
    index[slug] = metadata
    save_index(index)

    # Ulož do Supabase web_navrhy (pro JOIN v call queue dashboardu)
    _save_proposal_to_supabase(lead.get("id", ""), html, slug, url)

    return metadata


def _save_proposal_to_supabase(lead_id: str, html: str, slug: str, url: str):
    """Upsertuje návrh do Supabase web_navrhy tabulky."""
    sb_url = os.getenv("SUPABASE_URL", "")
    sb_key = os.getenv("SUPABASE_ANON_KEY", "")
    if not sb_url or not sb_key or not lead_id:
        return
    try:
        import requests as _req
        row = {"lead_id": lead_id, "html": html[:500000], "slug": slug, "url": url}
        r = _req.post(
            f"{sb_url}/rest/v1/web_navrhy?on_conflict=slug",
            headers={
                "apikey": sb_key,
                "Authorization": f"Bearer {sb_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            json=row,
            timeout=8,
        )
        if r.ok:
            print(f"  📋 Supabase web_navrhy: uloženo ({slug})")
        else:
            print(f"  ⚠ Supabase web_navrhy chyba {r.status_code}: {r.text[:80]}")

        # Explicitní PATCH stavu leadu — záloha za DB trigger
        if lead_id:
            _req.patch(
                f"{sb_url}/rest/v1/leads?id=eq.{lead_id}",
                headers={
                    "apikey": sb_key,
                    "Authorization": f"Bearer {sb_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json={"stav": "navrh_vygenerovan"},
                timeout=5,
            )
    except Exception as e:
        print(f"  ⚠ Supabase web_navrhy exception: {e}")


def load_latest_leads(limit: int = 10) -> list[dict]:
    """Načte top leady z posledního CSV souboru."""
    csvs = sorted(
        (BASE_DIR / "_outputs" / "web_hunter").glob("leads_*.csv"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not csvs:
        print("❌ Žádný leads CSV nenalezen. Spusť nejdřív Factory A.")
        return []

    latest = csvs[0]
    print(f"📂 Načítám leady z: {latest.name}")

    leads = []
    with open(latest, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("telefon"):  # pouze leady s telefonem
                leads.append(row)
            if len(leads) >= limit:
                break

    print(f"  Nalezeno {len(leads)} leadů s telefonem (limit={limit})")
    return leads


def main():
    parser = argparse.ArgumentParser(description="WebHunter — AI HTML Web Proposal Generator")
    parser.add_argument("--lead",  help="Název firmy")
    parser.add_argument("--obor",  default="řemeslník", help="Obor firmy")
    parser.add_argument("--mesto", default="Praha",     help="Město")
    parser.add_argument("--tel",   default="",          help="Telefon")
    parser.add_argument("--csv",   help="CSV soubor s leady")
    parser.add_argument("--limit", type=int, default=5, help="Max počet leadů z CSV (default: 5)")
    parser.add_argument("--batch", action="store_true", help="Zpracuj top 10 leadů z posledního CSV")
    args = parser.parse_args()

    print("=" * 60)
    print("WebHunter — AI HTML Web Proposal Generator")
    print("=" * 60)

    if not ANTHROPIC_API_KEY:
        print("❌ Chybí ANTHROPIC_API_KEY v _config/.env")
        return

    results = []

    if args.batch:
        leads = load_latest_leads(limit=10)
        for lead in leads:
            r = generate_for_lead(lead)
            results.append(r)

    elif args.csv:
        leads = []
        with open(args.csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                leads.append(row)
                if len(leads) >= args.limit:
                    break
        for lead in leads:
            r = generate_for_lead(lead)
            results.append(r)

    elif args.lead:
        lead = {"nazev": args.lead, "obor": args.obor, "mesto": args.mesto, "telefon": args.tel}
        r = generate_for_lead(lead)
        results.append(r)

    else:
        # Demo: vygeneruj jeden testovací návrh
        print("ℹ Žádné argumenty — generuji demo návrh")
        demo = {"nazev": "Instalatér Novák", "obor": "instalatér", "mesto": "Praha", "telefon": "+420777123456"}
        r = generate_for_lead(demo)
        results.append(r)

    # Souhrn
    print(f"\n📊 SOUHRN: {len(results)} návrhů vygenerováno")
    for r in results:
        print(f"  → {r['nazev']} | {r['url']}")

    # Aktualizuj published_urls pro dashboard
    urls_file = BASE_DIR / "_outputs" / "web_navrhy" / "published_urls.txt"
    existing = set(urls_file.read_text().splitlines()) if urls_file.exists() else set()
    new_urls = {r["url"] for r in results}
    all_urls = existing | new_urls
    urls_file.write_text("\n".join(sorted(all_urls)))

    return results


if __name__ == "__main__":
    main()

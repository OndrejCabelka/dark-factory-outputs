"""
DARK FACTORY — Factory A: Web Hunter v3
Sub-agent architektura: Scout → Qualifier → EmailWriter

Sub-agent 1 (Scout): Serper Maps + Google organic → reálné firmy z CZ/SK
Sub-agent 2 (Qualifier): Filtruje kdo opravdu nemá web, deduplikuje
Sub-agent 3 (EmailWriter): Claude napíše personalizované emaily + volací skripty
"""

import os, re, csv, time, json, requests, uuid
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import anthropic

BASE_DIR = Path(__file__).parent.parent
env_path = BASE_DIR / "_config" / ".env"
load_dotenv(dotenv_path=env_path)

OUTPUT_DIR = BASE_DIR / "_outputs" / "web_hunter"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SERPER_API_KEY    = os.getenv("SERPER_API_KEY", "")
SUPABASE_URL      = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY      = os.getenv("SUPABASE_ANON_KEY", "")

# Serper endpoints
SERPER_MAPS_URL    = "https://google.serper.dev/maps"
SERPER_SEARCH_URL  = "https://google.serper.dev/search"

SERPER_HEADERS = {
    "X-API-KEY":    SERPER_API_KEY,
    "Content-Type": "application/json",
}

# ── SEARCH TARGETS ────────────────────────────────────────────────────────────
# (obor, město) — živnostníci s vysokou pravděpodobností bez webu
SEARCH_TARGETS = [
    ("instalatér",     "Praha"),
    ("elektrikář",     "Brno"),
    ("malíř natěrač",  "Ostrava"),
    ("klempíř",        "Plzeň"),
    ("truhlář",        "Liberec"),
    ("zedník",         "Olomouc"),
    ("pokrývač",       "České Budějovice"),
    ("instalatér",     "Brno"),
    ("elektrikář",     "Praha"),
    ("malíř natěrač",  "Plzeň"),
    ("klempíř",        "Brno"),
    ("tesař",          "Praha"),
    ("obkladač",       "Brno"),
    ("zahradník",      "Praha"),
]

SOCIAL_DOMAINS = {"facebook.com", "instagram.com", "linkedin.com", "youtube.com", "twitter.com", "tiktok.com"}


# ══════════════════════════════════════════════════════════════════════════════
# SUB-AGENT 1: SCOUT
# Zodpovědnost: najdi reálné firmy přes Serper Maps + Google organic
# Vstup: (obor, město) | Výstup: list[dict] surových firem
# ══════════════════════════════════════════════════════════════════════════════

def scout_maps(obor: str, mesto: str) -> list[dict]:
    """Serper Maps → Google Maps výsledky s telefonem a web statusem."""
    if not SERPER_API_KEY:
        print("  ⚠ Chybí SERPER_API_KEY")
        return []

    payload = {
        "q": f"{obor} {mesto}",
        "gl": "cz",
        "hl": "cs",
        "num": 20,
    }
    try:
        r = requests.post(SERPER_MAPS_URL, headers=SERPER_HEADERS, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ⚠ Serper Maps chyba: {e}")
        return []

    firms = []
    for place in data.get("places", []):
        # Vyčisti telefon
        phone_raw = place.get("phoneNumber", "") or place.get("phone", "") or ""
        phone = re.sub(r"[^\d+]", "", phone_raw)
        if phone.startswith("00420"):
            phone = "+" + phone[2:]
        elif phone.startswith("420") and len(phone) == 12:
            phone = "+" + phone

        firms.append({
            "nazev":     place.get("title", ""),
            "adresa":    place.get("address", mesto),
            "mesto":     mesto,
            "telefon":   phone,
            "web":       place.get("website", "") or "",
            "rating":    place.get("rating", None),
            "obor":      obor,
            "zdroj":     "serper_maps",
            "place_id":  place.get("cid", "") or place.get("placeId", ""),
        })

    print(f"  📍 Maps: {len(firms)} výsledků pro '{obor} {mesto}'")
    return firms


def scout_organic(obor: str, mesto: str) -> list[dict]:
    """Serper organic → site:firmy.cz snippety s telefonem."""
    if not SERPER_API_KEY:
        return []

    # Dvě queries: firmy.cz a obecný google search
    queries = [
        f"site:firmy.cz {obor} {mesto}",
        f"{obor} {mesto} kontakt telefon",
    ]

    firms = []
    for query in queries:
        payload = {
            "q": query,
            "gl": "cz",
            "hl": "cs",
            "num": 10,
        }
        try:
            r = requests.post(SERPER_SEARCH_URL, headers=SERPER_HEADERS, json=payload, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  ⚠ Serper search chyba: {e}")
            continue

        for result in data.get("organic", []):
            title   = result.get("title", "")
            snippet = result.get("snippet", "")
            link    = result.get("link", "")

            # Extrahuj telefon ze snippetu
            phone_match = re.search(r"(\+420[\s\d]{9,13}|0[\d]{9}|[6-7]\d{8})", snippet.replace(" ", ""))
            phone = phone_match.group(0) if phone_match else ""

            # Extrahuj jméno firmy z titulku
            name = re.sub(r"\s*[-|–]\s*(Firmy\.cz|Zlaté stránky|Yelp|Facebook).*$", "", title, flags=re.I).strip()

            if name and len(name) > 3:
                # Zjisti web ze snippetu — hledáme "web:", "www.", "http"
                web_in_snippet = re.search(r"(?:web|www)\s*[:=]?\s*(https?://\S+|www\.\S+)", snippet, re.I)
                web = web_in_snippet.group(1) if web_in_snippet else ""

                firms.append({
                    "nazev":    name,
                    "adresa":   mesto,
                    "mesto":    mesto,
                    "telefon":  phone,
                    "web":      web,
                    "rating":   None,
                    "obor":     obor,
                    "zdroj":    f"serper_organic:{link[:60]}",
                    "place_id": "",
                })

    print(f"  🔍 Organic: {len(firms)} výsledků pro '{obor} {mesto}'")
    return firms


def run_scout(targets: list[tuple]) -> list[dict]:
    """SUB-AGENT 1: Scout — prohledá všechny targets."""
    print("\n🕵️  SUB-AGENT 1: SCOUT spuštěn")
    all_firms = []
    for obor, mesto in targets:
        # Primárně Maps (nejlepší data)
        firms = scout_maps(obor, mesto)
        # Doplňkově organic (více výsledků, ale méně strukturované)
        firms += scout_organic(obor, mesto)
        all_firms.extend(firms)
        time.sleep(0.5)  # rate limiting

    print(f"\n  Scout celkem: {len(all_firms)} surových výsledků")
    return all_firms


# ══════════════════════════════════════════════════════════════════════════════
# SUB-AGENT 2: QUALIFIER
# Zodpovědnost: filtrace, deduplikace, prioritizace
# Vstup: list[dict] surových | Výstup: list[dict] kvalifikovaných leadů
# ══════════════════════════════════════════════════════════════════════════════

def classify_web_status(web: str) -> tuple[str, int]:
    """
    Vrátí (web_status, priority):
      bez_webu    → 1 (nejlepší lead)
      jen_social  → 2 (dobrý lead)
      spatny_web  → 3 (slabý lead)
      ma_web      → None (přeskočit)
    """
    if not web or web.strip() == "":
        return "bez_webu", 1

    web_lower = web.lower()

    # Jen sociální sítě = nemá opravdový web
    for domain in SOCIAL_DOMAINS:
        if domain in web_lower:
            return "jen_social", 2

    # Má web — jde o URL s TLD
    if re.search(r"https?://|www\.", web_lower):
        # Špatný web: stará nebo placená šablona (neřeší se teď, přeskočit)
        return "ma_web", None

    # Nejasné — chovej se jako bez webu
    return "bez_webu", 1


def run_qualifier(firms: list[dict]) -> list[dict]:
    """SUB-AGENT 2: Qualifier — filtrace + deduplikace."""
    print("\n🔍 SUB-AGENT 2: QUALIFIER spuštěn")
    leads = []
    seen = set()

    for f in firms:
        # Deduplikace: název firmy (prvních 20 znaků lowercase)
        name_key = re.sub(r"\s+", "", f["nazev"].lower())[:20]
        if not name_key or name_key in seen:
            continue

        web_status, priority = classify_web_status(f.get("web", ""))
        if priority is None:
            continue  # má web → přeskočit

        # Vyžadujeme alespoň telefon NEBO jméno delší než 5 znaků
        if not f.get("telefon") and len(f.get("nazev", "")) < 5:
            continue

        seen.add(name_key)
        leads.append({
            **f,
            "web_status": web_status,
            "priority":   priority,
            "stav":       "novy",
        })

    # Seřadit: priority 1 s telefonem první
    leads.sort(key=lambda x: (x["priority"], 0 if x["telefon"] else 1))

    print(f"  Qualifier: {len(leads)} kvalifikovaných leadů (z {len(firms)} surových)")
    print(f"  Bez webu: {sum(1 for l in leads if l['web_status'] == 'bez_webu')}")
    print(f"  Jen social: {sum(1 for l in leads if l['web_status'] == 'jen_social')}")
    print(f"  S telefonem: {sum(1 for l in leads if l['telefon'])}")
    return leads


# ══════════════════════════════════════════════════════════════════════════════
# SUB-AGENT 3: EMAIL WRITER
# Zodpovědnost: Claude napíše personalizované emaily + volací skripty
# Vstup: top 10 leadů | Výstup: markdown s emaily
# ══════════════════════════════════════════════════════════════════════════════

def run_email_writer(leads: list[dict]) -> str:
    """SUB-AGENT 3: EmailWriter — personalizované cold emaily přes Claude."""
    print("\n✍️  SUB-AGENT 3: EMAIL WRITER spuštěn")

    if not ANTHROPIC_API_KEY or not leads:
        return "❌ Chybí API klíč nebo žádné leady."

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    top10 = leads[:10]

    leads_text = "\n".join(
        f"{i+1}. {l['nazev']} | {l['obor']} | {l['mesto']} | "
        f"tel: {l['telefon'] or '—'} | web: {l['web_status']} | "
        f"{'⭐' + str(l['rating']) if l.get('rating') else ''}"
        for i, l in enumerate(top10)
    )

    prompt = f"""Pro každou z těchto {len(top10)} CZ firem napiš:
1. Krátký volací skript (3-4 věty) — co říct při hovoru
2. Následný email po hovoru (bude odeslán POUZE po souhlasu při hovoru)

FIRMY:
{leads_text}

KONTEXT:
- Jsi Ondřej, CZ freelance webdesigner
- Firmy nemají web nebo mají jen Facebook stránku
- Nejdřív zavoláš a zmíníš že máš pro ně připravený návrh webu zdarma
- Teprve po souhlasu pošleš email s náhledem
- Weby děláš pro živnostníky a řemeslníky, cena 15-25 tisíc Kč
- Email se posílá z: ondrej.cabelka@gmail.com

FORMÁT PRO KAŽDOU FIRMU:
## {'{'}číslo{'}'}. [NÁZEV FIRMY]
**Volací skript:**
[3-4 věty co říct po telefonu]

**Email po souhlasu:**
Předmět: [max 55 znaků]
[tělo emailu, max 80 slov, zmíni konkrétní detail o firmě]
Podpis: Ondřej Čábelka | ondrej.cabelka@gmail.com

---

Pravidla:
- Styl: přirozený, neformální čeština
- Každý email unikátní — zmíní konkrétní obor nebo město
- Žádný spam jazyk (bez "AKCE!", "ZDARMA!!!")
- Volací skript je stručný a jde přímo k věci"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    result = msg.content[0].text
    print(f"  EmailWriter: vygenerováno {len(top10)} emailů + volacích skriptů")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRÁTOR: main()
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE UPSERT
# Uloží leady do WebHunter DB — graceful fallback pokud chybí klíče
# ══════════════════════════════════════════════════════════════════════════════

def save_to_supabase(leads: list[dict]) -> int:
    """Upsertuje leady do Supabase `leads` tabulky. Vrátí počet vložených."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\n  ⚠ SUPABASE_URL / SUPABASE_ANON_KEY nejsou v .env — přeskakuji DB upsert")
        print("    → Nastav proměnné v _config/.env pro ukládání do WebHunter dashboardu")
        return 0

    try:
        from supabase import create_client
    except ImportError:
        print("  ⚠ supabase-py není nainstalováno: pip install supabase")
        return 0

    try:
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"  ⚠ Supabase připojení selhalo: {e}")
        return 0

    inserted = 0
    skipped  = 0

    for lead in leads:
        # Mapování Factory A polí → DB schema
        place_id = lead.get("place_id") or ""
        if not place_id:
            # Vygeneruj deterministické ID z názvu+města (aby upsert fungoval)
            place_id = "gen_" + uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{lead['nazev'].lower()}_{lead['mesto'].lower()}"
            ).hex[:16]

        row = {
            "name":            lead.get("nazev", "")[:200],
            "obor":            lead.get("obor", "")[:100],
            "mesto":           lead.get("mesto", "")[:100],
            "telefon":         lead.get("telefon") or None,
            "email":           None,          # e-mail finder není součástí scraperu
            "web_status":      lead.get("web_status", "bez_webu"),
            "web_url":         lead.get("web") or None,
            "web_issues":      [],
            "priority":        lead.get("priority", 1),
            "stav":            "novy",
            "google_place_id": place_id,
            "tracking_id":     uuid.uuid4().hex,
        }

        try:
            # upsert: pokud google_place_id existuje → ignoruj (zachovej stav)
            db.table("leads").upsert(row, on_conflict="google_place_id", ignore_duplicates=True).execute()
            inserted += 1
        except Exception as e:
            err = str(e)
            if "duplicate" in err.lower() or "23505" in err:
                skipped += 1
            else:
                print(f"  ⚠ Upsert chyba ({lead.get('nazev', '?')}): {err[:80]}")

    print(f"\n  📦 Supabase: {inserted} vloženo, {skipped} přeskočeno (duplicita)")
    return inserted


def main():
    print("=" * 60)
    print("FACTORY A — WEB HUNTER v3 (Serper Maps + Sub-agenti)")
    print("Scout → Qualifier → EmailWriter")
    print("=" * 60)

    if not SERPER_API_KEY:
        print("❌ Chybí SERPER_API_KEY v _config/.env")
        return []

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # SUB-AGENT 1: Scout
    raw_firms = run_scout(SEARCH_TARGETS)

    # SUB-AGENT 2: Qualifier
    leads = run_qualifier(raw_firms)

    if not leads:
        print("\n⚠ Qualifier nenašel žádné leady. Zkontroluj Serper API key a SEARCH_TARGETS.")
        return []

    # Uložit do Supabase (WebHunter dashboard DB)
    save_to_supabase(leads)

    # Uložit leads jako CSV
    csv_path = OUTPUT_DIR / f"leads_{ts}.csv"
    fieldnames = ["nazev","obor","mesto","adresa","telefon","web","web_status","priority","rating","stav","zdroj"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(leads)
    print(f"\n✅ Leady CSV: {csv_path.name} ({len(leads)} leadů)")

    # Markdown přehled
    md_path = OUTPUT_DIR / f"leads_{ts}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Web Hunter Leady — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Celkem:** {len(leads)} leadů bez webu\n")
        f.write(f"**S telefonem:** {sum(1 for l in leads if l['telefon'])}\n\n")
        f.write("| # | NÁZEV | OBOR | MĚSTO | TELEFON | STATUS | ⭐ |\n")
        f.write("|---|-------|------|-------|---------|--------|----|\n")
        for i, l in enumerate(leads[:30], 1):
            f.write(
                f"| {i} | {l['nazev'][:35]} | {l['obor']} | {l['mesto']} | "
                f"{l['telefon'] or '—'} | {l['web_status']} | "
                f"{l.get('rating') or '—'} |\n"
            )
    print(f"✅ Leady MD: {md_path.name}")

    # SUB-AGENT 3: EmailWriter
    emails = run_email_writer(leads)
    emails_path = OUTPUT_DIR / f"outreach_{ts}.md"
    with open(emails_path, "w", encoding="utf-8") as f:
        f.write(f"# Outreach — Emaily + Volací skripty\n")
        f.write(f"Vygenerováno: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(emails)
    print(f"✅ Outreach: {emails_path.name}")

    # Souhrn
    top_with_phone = [l for l in leads if l["telefon"]][:5]
    print(f"\n📊 SOUHRN:")
    print(f"  Celkem leadů: {len(leads)}")
    print(f"  S telefonem: {len(top_with_phone)}")
    print(f"\n  Top 5 pro volání:")
    for l in top_with_phone:
        print(f"  → {l['nazev']} | {l['obor']} | {l['mesto']} | {l['telefon']}")

    return leads


if __name__ == "__main__":
    main()

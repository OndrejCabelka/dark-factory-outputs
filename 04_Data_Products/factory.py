"""
Factory D — ARES Data Products
Každý týden stáhne nově registrované firmy z CZ ARES API,
vyfiltruje podle oborů, vygeneruje CSV + MD report + summary.
Výstupy se prodávají jako data feed.
"""

import os, sys, csv, json, requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import anthropic

BASE_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=BASE_DIR / "_config" / ".env")

OUTPUT_DIR = BASE_DIR / "_outputs" / "data_products"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Obory které nás zajímají (firmy bez webu = potenciální WebHunter leady)
TARGET_NACE = {
    "4321": "Elektroinstalace",
    "4322": "Instalatérství, topenářství, plynárenství",
    "4331": "Omítkářství",
    "4332": "Truhlářství, tesařství",
    "4333": "Pokrývačství",
    "4334": "Malířství, lakýrnictví",
    "4339": "Ostatní dokončovací stavební práce",
    "4120": "Výstavba bytových a nebytových budov",
    "5610": "Restaurace a mobilní stravování",
    "9602": "Kadeřnictví, holičství",
    "9601": "Praní a čištění textilu",
    "8121": "Obecný úklid budov",
}


def fetch_ares_new_companies(days_back: int = 7) -> list[dict]:
    """Stáhne firmy z ARES podle oborových klíčových slov."""
    cutoff = (datetime.now() - timedelta(days=days_back * 10)).strftime("%Y-%m-%d")  # wider window
    url = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/vyhledat"
    results = []

    # Search by business name keywords — only reliable method on this API
    KEYWORDS = [
        ("instalatér", "Instalatérství"), ("klempíř", "Klempířství"),
        ("elektrikář", "Elektroinstalace"), ("elektro", "Elektroinstalace"),
        ("tesař", "Tesařství"), ("truhlář", "Truhlářství"),
        ("malíř", "Malířství"), ("zámečník", "Zámečnictví"),
        ("topenář", "Topenářství"), ("podlahář", "Podlahářství"),
        ("sklenář", "Sklenářství"), ("stavby", "Stavebnictví"),
        ("rekonstrukce", "Rekonstrukce"), ("montáž", "Montáž"),
    ]

    for keyword, obor in KEYWORDS:
        try:
            payload = {
                "pocet": 50,
                "obchodniJmeno": keyword,
            }
            r = requests.post(url, json=payload,
                              headers={"Content-Type": "application/json"}, timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            firmy = data.get("ekonomickeSubjekty", [])
            # Keep only firms founded recently
            for f in firmy:
                datum = f.get("datumVzniku", "")
                if datum and datum >= cutoff:
                    sidlo = f.get("sidlo", {})
                    results.append({
                        "ico":           f.get("ico", ""),
                        "nazev":         f.get("obchodniJmeno", ""),
                        "obor":          obor,
                        "keyword":       keyword,
                        "datum_vzniku":  datum,
                        "sidlo":         sidlo.get("textovaAdresa", ""),
                        "mesto":         sidlo.get("nazevObce", ""),
                        "kraj":          sidlo.get("nazevKraje", ""),
                        "psc":           str(sidlo.get("psc", "")),
                    })
            new = sum(1 for f in firmy if f.get("datumVzniku","") >= cutoff)
            print(f"  [{keyword}]: {data.get('pocetCelkem',0)} celkem, {new} nových")
        except Exception as e:
            print(f"  [{keyword}] chyba: {e}")

    # Deduplikace podle IČO
    seen = set()
    unique = []
    for f in sorted(results, key=lambda x: x["datum_vzniku"], reverse=True):
        if f["ico"] and f["ico"] not in seen:
            seen.add(f["ico"])
            unique.append(f)
    return unique


def save_csv(companies: list[dict], date_str: str) -> Path:
    path = OUTPUT_DIR / f"nove_firmy_CZ_{date_str}.csv"
    if not companies:
        return path
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=companies[0].keys())
        writer.writeheader()
        writer.writerows(companies)
    return path


def generate_report(companies: list[dict], date_str: str) -> Path:
    """Claude vygeneruje analytický report z dat."""
    if not ANTHROPIC_API_KEY:
        print("  Chybí ANTHROPIC_API_KEY — přeskakuji AI report")
        return None

    # Statistiky pro AI
    obory_count = {}
    mesta_count = {}
    for c in companies:
        obory_count[c["obor"]] = obory_count.get(c["obor"], 0) + 1
        if c["mesto"]:
            mesta_count[c["mesto"]] = mesta_count.get(c["mesto"], 0) + 1

    top_obory = sorted(obory_count.items(), key=lambda x: x[1], reverse=True)[:8]
    top_mesta = sorted(mesta_count.items(), key=lambda x: x[1], reverse=True)[:10]

    prompt = f"""Jsi analytik trhu. Na základě dat o nově registrovaných firmách v ČR za posledních 7 dní vytvoř stručný business report v Markdown.

STATISTIKY:
- Celkem nových firem: {len(companies)}
- Sledované období: {date_str}
- Top obory: {json.dumps(top_obory, ensure_ascii=False)}
- Top města: {json.dumps(top_mesta, ensure_ascii=False)}

Vytvoř report s těmito sekcemi:
1. Executive summary (3-4 věty)
2. Nejaktivnější obory (tabulka s počty a % z celku)
3. Geografické rozložení (top 10 měst)
4. Business insight — co tato data říkají o trhu (2-3 odstavce)
5. Obchodní příležitosti — konkrétní tipy jak tato data využít pro business development

Buď konkrétní, datově podložený. Report v češtině."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    report_text = msg.content[0].text

    path = OUTPUT_DIR / f"report_nove_firmy_CZ_{date_str}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Report: Nové firmy v ČR — {date_str}\n\n")
        f.write(report_text)
        f.write(f"\n\n---\n*Generováno: {datetime.now().strftime('%d.%m.%Y %H:%M')} | Dark Factory D*\n")
    return path


def factory_d():
    print("=" * 50)
    print("FACTORY D — ARES Data Products")
    print("=" * 50)

    date_str = datetime.now().strftime("%Y-%m-%d")

    print("\n📡 Stahuji nové firmy z ARES...")
    companies = fetch_ares_new_companies(days_back=7)
    print(f"\n✅ Nalezeno {len(companies)} nových firem")

    if not companies:
        print("⚠️  Žádné nové firmy — ARES API možná nedostupné nebo žádné nové registrace")
        return True

    print("\n💾 Ukládám CSV...")
    csv_path = save_csv(companies, date_str)
    print(f"  → {csv_path.name}")

    print("\n🤖 Generuji AI report...")
    try:
        report_path = generate_report(companies, date_str)
        if report_path:
            print(f"  → {report_path.name}")
    except Exception as e:
        print(f"  ⚠️  AI report přeskočen: {e}")
        report_path = None

    # Metadata soubor
    meta = {
        "date": date_str,
        "total_companies": len(companies),
        "by_obor": {},
        "by_mesto": {},
    }
    for c in companies:
        meta["by_obor"][c["obor"]] = meta["by_obor"].get(c["obor"], 0) + 1
        if c["mesto"]:
            meta["by_mesto"][c["mesto"]] = meta["by_mesto"].get(c["mesto"], 0) + 1

    with open(OUTPUT_DIR / f"meta_{date_str}.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Factory D hotova: {len(companies)} firem, CSV + report uloženy")
    return True


if __name__ == "__main__":
    factory_d()

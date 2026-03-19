"""
Factory F — Leads API Packaging
Každý týden exportuje čerstvé WebHunter leady jako CSV balíček.
Prodává se agenturám a freelancerům co dělají weby.
Cena: 500–2000 Kč/měsíc za přístup k feed.
"""

import os, csv, json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=BASE_DIR / "_config" / ".env")

OUTPUT_DIR = BASE_DIR / "_outputs" / "leads_api"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


def fetch_leads_from_supabase() -> list[dict]:
    """Stáhne čerstvé leady z WebHunter Supabase."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("  ⚠️  Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY")
        return []

    try:
        import requests
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        url = f"{SUPABASE_URL}/rest/v1/leads"
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        }
        params = {
            "select": "name,obor,mesto,telefon,web_status,priority,created_at",
            "created_at": f"gte.{week_ago}",
            "stav": "neq.odmitl",
            "order": "priority.asc,created_at.desc",
            "limit": "200",
        }
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
        print(f"  Supabase error: {r.status_code}")
        return []
    except Exception as e:
        print(f"  Fetch error: {e}")
        return []


def generate_sample_leads() -> list[dict]:
    """Fallback: sample data pokud Supabase nedostupná."""
    return [
        {"name": "Instalatérství Novák", "obor": "instalatér", "mesto": "Praha", "telefon": "+420 777 123 456", "web_status": "bez_webu", "priority": 1},
        {"name": "Elektro Svoboda s.r.o.", "obor": "elektrikář", "mesto": "Brno", "telefon": "+420 608 987 654", "web_status": "spatny_web", "priority": 2},
        {"name": "Tesařství Dvořák", "obor": "tesař", "mesto": "Ostrava", "telefon": "+420 731 456 789", "web_status": "bez_webu", "priority": 1},
    ]


def save_leads_csv(leads: list[dict], date_str: str) -> Path:
    if not leads:
        return None
    path = OUTPUT_DIR / f"leady_CZ_{date_str}.csv"
    fieldnames = ["name", "obor", "mesto", "telefon", "web_status", "priority"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[k for k in fieldnames if k in leads[0]])
        writer.writeheader()
        for lead in leads:
            writer.writerow({k: lead.get(k, "") for k in fieldnames if k in leads[0]})
    return path


def generate_summary(leads: list[dict], date_str: str) -> Path:
    """Vygeneruje JSON summary pro API konzumenty."""
    obory = {}
    mesta = {}
    bez_webu = sum(1 for l in leads if l.get("web_status") == "bez_webu")
    for l in leads:
        obory[l.get("obor", "?")] = obory.get(l.get("obor", "?"), 0) + 1
        if l.get("mesto"):
            mesta[l["mesto"]] = mesta.get(l["mesto"], 0) + 1

    summary = {
        "generated": datetime.now().isoformat(),
        "period": f"Týden do {date_str}",
        "total_leads": len(leads),
        "bez_webu": bez_webu,
        "spatny_web": len(leads) - bez_webu,
        "top_obory": sorted(obory.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_mesta": sorted(mesta.items(), key=lambda x: x[1], reverse=True)[:10],
        "pricing": {
            "monthly_feed": "500–2000 Kč/měsíc",
            "contact": "ondrej.cabelka@gmail.com",
            "info": "Týdenní CSV feed čerstvých CZ firem bez webu nebo se špatným webem. Ideální pro webové agentury a freelancery."
        }
    }

    path = OUTPUT_DIR / f"summary_{date_str}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return path


def generate_readme(leads: list[dict], date_str: str) -> Path:
    """README pro kupce balíčku."""
    bez_webu = sum(1 for l in leads if l.get("web_status") == "bez_webu")
    path = OUTPUT_DIR / f"README_{date_str}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"""# 🎯 WebHunter Lead Feed — {date_str}

## Co je v tomto balíčku?

Týdenní export **{len(leads)} čerstvých leadů** — CZ firmy bez webu nebo se špatným webem.
Ideální pro webové agentury, freelancery a web designery.

## Statistiky

| Metrika | Hodnota |
|---------|---------|
| Celkem leadů | {len(leads)} |
| Bez webu (Priorita 1) | {bez_webu} |
| Špatný web (Priorita 2) | {len(leads) - bez_webu} |
| Formát | CSV (UTF-8) |

## Sloupce v CSV

- **name** — název firmy
- **obor** — obor podnikání
- **mesto** — město
- **telefon** — telefonní číslo
- **web_status** — `bez_webu` nebo `spatny_web`
- **priority** — 1 (bez webu) nebo 2 (špatný web)

## Jak používat

1. Otevři CSV v Excelu nebo Google Sheets
2. Filtruj podle oboru nebo města
3. Zavolej nebo napiš — firma nemá web, je otevřená nabídce
4. Průměrná cena webu: 15 000–30 000 Kč

## Předplatné

Dostávej tento feed každý týden automaticky:
📧 ondrej.cabelka@gmail.com | 500–2000 Kč/měsíc

---
*Generováno: {datetime.now().strftime('%d.%m.%Y')} | Dark Factory F*
""")
    return path


def factory_f():
    print("=" * 50)
    print("FACTORY F — Leads API Packaging")
    print("=" * 50)

    date_str = datetime.now().strftime("%Y-%m-%d")

    print("\n📡 Stahuji leady z WebHunter...")
    leads = fetch_leads_from_supabase()

    if not leads:
        print("  Supabase nedostupná — používám sample data")
        leads = generate_sample_leads()

    print(f"  ✅ {len(leads)} leadů")

    print("\n💾 Generuji CSV balíček...")
    csv_path = save_leads_csv(leads, date_str)
    if csv_path:
        print(f"  → {csv_path.name}")

    print("\n📊 Generuji JSON summary...")
    summary_path = generate_summary(leads, date_str)
    print(f"  → {summary_path.name}")

    print("\n📄 Generuji README pro kupce...")
    readme_path = generate_readme(leads, date_str)
    print(f"  → {readme_path.name}")

    print(f"\n🎉 Factory F hotova: {len(leads)} leadů zabaleno a připraveno k prodeji")
    print(f"   Potenciální revenue: {len(leads) * 10}–{len(leads) * 50} Kč (při ceně 10–50 Kč/lead)")
    return True


if __name__ == "__main__":
    factory_f()

"""
WebHunter — Bulk CSV import leadů do Supabase
==============================================
Použití:
  python import_leads_csv.py cesta/k/souboru.csv [--limit N] [--dry-run]

Očekávané sloupce CSV (libovolný subset, zbytek se doplní):
  nazev / name, obor, mesto, telefon, email, web / web_url, web_status, priority

Příklad:
  python import_leads_csv.py _outputs/web_hunter/leady_20260323.csv
  python import_leads_csv.py leads.csv --dry-run
  python import_leads_csv.py leads.csv --limit 50
"""

import os, sys, csv, uuid, argparse, requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / "_config" / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

VALID_WEB_STATUS = {"bez_webu", "spatny_web", "jen_social"}
VALID_STAV       = {
    "novy","navrh_vygenerovan","ceka_na_hovor","hovor_proveden",
    "souhlas_k_mailu","odmitl","nedostupny","mail_odeslan",
    "otevrel_mail","navrh_odeslan","zakaznik","neodpovida"
}


def normalize_row(raw: dict) -> dict | None:
    """Normalizuje jeden CSV řádek na DB schéma. Vrátí None pokud je neplatný."""
    # Podpora pro různé názvy sloupců
    name = (raw.get("nazev") or raw.get("name") or "").strip()
    if not name or len(name) < 3:
        return None

    web_status = raw.get("web_status", "bez_webu").strip().lower()
    if web_status not in VALID_WEB_STATUS:
        web_status = "bez_webu"

    stav = raw.get("stav", "novy").strip().lower()
    if stav not in VALID_STAV:
        stav = "novy"

    try:
        priority = int(raw.get("priority", 1))
        if priority not in (1, 2):
            priority = 2
    except (ValueError, TypeError):
        priority = 2

    web_url = (raw.get("web") or raw.get("web_url") or "").strip() or None

    # Deterministické google_place_id z nazev+mesto (aby upsert fungoval)
    mesto = (raw.get("mesto") or "").strip()
    place_id = (raw.get("google_place_id") or raw.get("place_id") or "").strip()
    if not place_id:
        place_id = "import_" + uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"{name.lower()}_{mesto.lower()}"
        ).hex[:16]

    return {
        "name":            name[:200],
        "obor":            (raw.get("obor") or "").strip()[:100] or None,
        "mesto":           mesto[:100] or None,
        "telefon":         (raw.get("telefon") or raw.get("tel") or "").strip() or None,
        "email":           (raw.get("email") or "").strip().lower() or None,
        "web_status":      web_status,
        "web_url":         web_url,
        "priority":        priority,
        "stav":            stav,
        "google_place_id": place_id,
        "tracking_id":     uuid.uuid4().hex,
    }


def import_csv(csv_path: Path, limit: int = 0, dry_run: bool = False) -> dict:
    if not csv_path.exists():
        print(f"❌ Soubor nenalezen: {csv_path}")
        sys.exit(1)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Nastav SUPABASE_URL a SUPABASE_ANON_KEY v _config/.env")
        sys.exit(1)

    # resolution=merge-duplicates: upsert — aktualizuje kontaktní data, zachová stav
    # Pro zachování stavu existujících leadů vynecháme 'stav' z update při konfliktu
    headers_sb = {
        "apikey":          SUPABASE_KEY,
        "Authorization":   f"Bearer {SUPABASE_KEY}",
        "Content-Type":    "application/json",
        "Prefer":          "resolution=merge-duplicates,return=minimal",
    }

    # Načti CSV
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"📂 Načteno {len(rows)} řádků z {csv_path.name}")

    # Normalizuj
    valid, skipped = [], []
    for row in rows:
        normalized = normalize_row(row)
        if normalized:
            valid.append(normalized)
        else:
            skipped.append(row)

    if limit > 0:
        valid = valid[:limit]

    print(f"✅ Platných: {len(valid)} | ⚠ Přeskočeno (prázdný název): {len(skipped)}")
    if limit > 0:
        print(f"🔢 Limit: první {limit} leadů")

    if dry_run:
        print("\n🔍 DRY RUN — ukázka prvních 3 řádků:")
        for r in valid[:3]:
            print(f"  → {r['name']} | {r['obor']} | {r['mesto']} | {r['telefon']} | {r['web_status']}")
        print("\n(Spusť bez --dry-run pro skutečný import)")
        return {"inserted": 0, "skipped": len(skipped), "dry_run": True}

    # Upsert po dávkách 50
    BATCH = 50
    inserted = 0
    errors   = 0

    for i in range(0, len(valid), BATCH):
        batch = valid[i:i + BATCH]
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/leads?on_conflict=google_place_id",
            headers=headers_sb,
            json=batch,
            timeout=15,
        )
        if r.ok:
            inserted += len(batch)
            print(f"  📦 Batch {i//BATCH + 1}: {len(batch)} leadů vloženo")
        else:
            errors += len(batch)
            print(f"  ❌ Batch {i//BATCH + 1} selhal {r.status_code}: {r.text[:120]}")

    print(f"\n{'='*50}")
    print(f"📊 Import dokončen: {inserted} vloženo, {errors} chyb, {len(skipped)} přeskočeno")
    print(f"🔗 Dashboard: https://dark-factory.vercel.app")
    return {"inserted": inserted, "errors": errors, "skipped": len(skipped)}


def main():
    parser = argparse.ArgumentParser(description="WebHunter CSV import do Supabase")
    parser.add_argument("csv",            help="Cesta k CSV souboru")
    parser.add_argument("--limit",  "-n", type=int, default=0, help="Max počet leadů (0 = vše)")
    parser.add_argument("--dry-run", "-d", action="store_true",  help="Jen zobraz, nevkládej")
    args = parser.parse_args()

    import_csv(Path(args.csv), limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

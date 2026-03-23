"""
WebHunter — Batch Proposal Generator z Supabase
================================================
Načte priority-1 leady s telefonem ze Supabase,
vygeneruje HTML návrhy přes Claude, uloží zpět do Supabase.

Použití:
  python3 batch_proposals_supabase.py              # top 20 priority-1 leadů
  python3 batch_proposals_supabase.py --limit 5    # jen 5
  python3 batch_proposals_supabase.py --all        # všechny bez návrhu
  python3 batch_proposals_supabase.py --dry-run    # jen seznam, bez generování
"""

import os, sys, json, time, argparse
from pathlib import Path
from dotenv import load_dotenv
import requests

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / "_config" / ".env")

SUPABASE_URL  = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY  = os.getenv("SUPABASE_ANON_KEY", "") or os.getenv("SUPABASE_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v _config/.env")
    sys.exit(1)

SB_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


# ── SUPABASE HELPERS ──────────────────────────────────────────────────────────

def fetch_leads(limit: int = 20, priority_only: bool = True, fetch_all: bool = False) -> list[dict]:
    """Načte leady bez vygenerovaného návrhu z Supabase."""
    params = {
        "stav": "eq.novy",
        "telefon": "not.is.null",
        "select": "id,name,obor,mesto,telefon,web_url,web_status,priority,tracking_id",
        "order": "priority.asc,created_at.asc",
    }
    if priority_only and not fetch_all:
        params["priority"] = "eq.1"
    if not fetch_all:
        params["limit"] = str(limit)
    else:
        params["limit"] = "500"

    r = requests.get(f"{SUPABASE_URL}/rest/v1/leads", headers=SB_HEADERS, params=params)
    if r.status_code != 200:
        print(f"❌ Supabase fetch chyba {r.status_code}: {r.text[:200]}")
        return []

    leads = r.json()

    # Filtruj leady které už mají návrh
    ids = [l["id"] for l in leads]
    if not ids:
        return []

    existing = requests.get(
        f"{SUPABASE_URL}/rest/v1/web_navrhy",
        headers=SB_HEADERS,
        params={"lead_id": f"in.({','.join(ids)})", "select": "lead_id"},
    ).json()
    existing_ids = {e["lead_id"] for e in existing}

    filtered = [l for l in leads if l["id"] not in existing_ids]
    print(f"  Nalezeno {len(leads)} leadů, {len(existing_ids)} už má návrh → {len(filtered)} ke zpracování")
    return filtered


# ── MAIN BATCH ────────────────────────────────────────────────────────────────

def run_batch(limit: int = 20, dry_run: bool = False, fetch_all: bool = False):
    # Import generátoru
    sys.path.insert(0, str(BASE_DIR))
    try:
        from generate_web_proposal import generate_for_lead
    except ImportError as e:
        print(f"❌ Nelze importovat generate_web_proposal: {e}")
        sys.exit(1)

    print("=" * 60)
    print("WebHunter — Batch Proposal Generator (Supabase)")
    print("=" * 60)

    if not ANTHROPIC_KEY:
        print("❌ Chybí ANTHROPIC_API_KEY v _config/.env")
        sys.exit(1)

    leads = fetch_leads(limit=limit, priority_only=True, fetch_all=fetch_all)

    if not leads:
        print("✅ Žádné leady ke zpracování (všechny mají návrhy nebo žádné priority-1 leady s telefonem).")
        return

    if dry_run:
        print(f"\n🔍 DRY RUN — {len(leads)} leadů ke zpracování:\n")
        for i, l in enumerate(leads, 1):
            print(f"  {i:2}. [{l.get('priority','?')}] {l['name']} | {l.get('obor','?')} | {l.get('mesto','?')} | {l.get('telefon','?')}")
        return

    print(f"\n🚀 Generuji návrhy pro {len(leads)} leadů...\n")
    ok, fail = 0, 0

    for i, lead in enumerate(leads, 1):
        # Mapuj Supabase `name` → `nazev` pro generate_for_lead
        lead_mapped = {
            "id": lead["id"],
            "nazev": lead["name"],
            "name": lead["name"],
            "obor": lead.get("obor", "řemeslník"),
            "mesto": lead.get("mesto", "Praha"),
            "telefon": lead.get("telefon", ""),
            "web_url": lead.get("web_url", ""),
            "tracking_id": lead.get("tracking_id") or lead["id"],
        }

        print(f"\n[{i}/{len(leads)}] {lead['name']} ({lead.get('obor','?')}, {lead.get('mesto','?')})")

        try:
            result = generate_for_lead(lead_mapped)
            if result.get("url"):
                print(f"  ✅ Návrh: {result['url']}")
                ok += 1
            else:
                print(f"  ⚠ Bez URL: {result}")
                fail += 1
        except Exception as e:
            print(f"  ❌ Chyba: {e}")
            fail += 1

        # Rate limit — Claude API
        if i < len(leads):
            time.sleep(2)

    print(f"\n{'='*60}")
    print(f"✅ Hotovo: {ok} úspěšných, {fail} chyb z {len(leads)} leadů")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch proposal generator ze Supabase")
    parser.add_argument("--limit",   type=int, default=20, help="Max leadů (default: 20)")
    parser.add_argument("--all",     action="store_true",  help="Všechny priority-1 leady bez návrhu")
    parser.add_argument("--dry-run", action="store_true",  help="Jen seznam, bez generování")
    args = parser.parse_args()

    run_batch(limit=args.limit, dry_run=args.dry_run, fetch_all=args.all)

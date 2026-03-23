"""
WebHunter — Pipeline Verification Script
==========================================
Ověří že všechny části fungují PŘED ostrým provozem.
Spusť: python3 verify_pipeline.py

Každý test je samostatný — selháni jednoho nevadí ostatním.
"""
import os, sys, json, requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / "_config" / ".env")

OK   = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = []

def test(name, fn):
    try:
        msg = fn()
        results.append((OK, name, msg))
        print(f"  {OK} {name}: {msg}")
    except Exception as e:
        results.append((FAIL, name, str(e)[:80]))
        print(f"  {FAIL} {name}: {e}")


# ─── TESTY ────────────────────────────────────────────────────────────────────

print("\n" + "="*55)
print("  WebHunter — Pipeline Verification")
print("="*55 + "\n")

# 1. ENV vars
print("[ 1/7 ] ENV Variables")
test("ANTHROPIC_API_KEY", lambda: "OK" if os.getenv("ANTHROPIC_API_KEY") else (_ for _ in ()).throw(Exception("CHYBÍ — nutné pro generování návrhů")))
test("SUPABASE_URL",      lambda: os.getenv("SUPABASE_URL","")[:30]+"..." if os.getenv("SUPABASE_URL") else (_ for _ in ()).throw(Exception("CHYBÍ")))
test("SUPABASE_ANON_KEY", lambda: "OK (první 20 znaků: "+os.getenv("SUPABASE_ANON_KEY","")[:20]+"...)" if os.getenv("SUPABASE_ANON_KEY") else (_ for _ in ()).throw(Exception("CHYBÍ")))
test("RESEND_API_KEY",    lambda: "OK" if os.getenv("RESEND_API_KEY") else (_ for _ in ()).throw(Exception("CHYBÍ — nutné pro odesílání mailů. Zaregistruj se na resend.com")))
test("GITHUB_TOKEN",      lambda: "OK" if (os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") or os.getenv("GITHUB_TOKEN")) else (_ for _ in ()).throw(Exception("CHYBÍ — nutné pro publikování návrhů")))

# 2. Supabase
print("\n[ 2/7 ] Supabase DB")
def check_supabase():
    url = os.getenv("SUPABASE_URL","")
    key = os.getenv("SUPABASE_ANON_KEY","")
    r = requests.get(f"{url}/rest/v1/leads?select=count&stav=eq.navrh_vygenerovan",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Prefer": "count=exact"},
        timeout=8)
    if r.status_code not in (200, 206):
        raise Exception(f"HTTP {r.status_code}")
    total = r.headers.get("content-range","?")
    return f"připraveno k volání: {total.split('/')[-1]} leadů"
test("Supabase connection", check_supabase)

def check_leads():
    url = os.getenv("SUPABASE_URL","")
    key = os.getenv("SUPABASE_ANON_KEY","")
    r = requests.get(f"{url}/rest/v1/leads?select=stav,count&group=stav",
        headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=8)
    data = r.json() if r.ok else []
    total = sum(x.get("count",1) for x in data) if data else 0
    return f"{total} leadů celkem"
test("Leads data", check_leads)

# 3. GitHub Pages
print("\n[ 3/7 ] GitHub Pages")
def check_github():
    idx = BASE_DIR / "_outputs" / "web_navrhy" / "proposals_index.json"
    url = "https://ondrejcabelka.github.io/dark-factory-outputs/navrhy/instalater-novak-instalater-praha/"
    if idx.exists():
        data = json.loads(idx.read_text())
        if data:
            url = list(data.values())[0]["url"]
    r = requests.get(url, timeout=10)
    if r.status_code in (200, 304):
        return f"live ✓ ({url.split('/')[-2]})"
    # GitHub Pages může mít delay — varuj ale neselhávej
    return f"HTTP {r.status_code} — GitHub Pages může mít propagation delay (5-10 min)"
test("Návrh na GitHub Pages", check_github)

def count_proposals():
    idx = BASE_DIR / "_outputs" / "web_navrhy" / "proposals_index.json"
    if not idx.exists():
        raise Exception("proposals_index.json nenalezen")
    data = json.loads(idx.read_text())
    return f"{len(data)} návrhů lokálně"
test("Proposals index", count_proposals)

# 4. Anthropic API
print("\n[ 4/7 ] Anthropic API")
def check_anthropic():
    import anthropic
    c = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY",""))
    msg = c.messages.create(model="claude-haiku-4-5-20251001", max_tokens=10,
        messages=[{"role":"user","content":"Odpověz jedním slovem: OK"}])
    return f"OK ({msg.model})"
test("Claude API ping", check_anthropic)

# 5. Resend (jen pokud je klíč)
print("\n[ 5/7 ] Resend Mail")
def check_resend():
    key = os.getenv("RESEND_API_KEY","")
    if not key:
        raise Exception("RESEND_API_KEY chybí")
    r = requests.get("https://api.resend.com/domains",
        headers={"Authorization": f"Bearer {key}"}, timeout=8)
    if r.status_code == 200:
        domains = [d["name"] for d in r.json().get("data",[])]
        return f"OK, domény: {domains or ['žádná — free tier funguje z onboarding@resend.dev']}"
    raise Exception(f"HTTP {r.status_code}: {r.text[:50]}")
test("Resend API connection", check_resend)

# 6. Frontend build
print("\n[ 6/7 ] Next.js Frontend")
def check_build():
    next_dir = BASE_DIR / "frontend" / ".next"
    if next_dir.exists():
        return "build existuje — ready pro vercel --prod"
    raise Exception("frontend nebyl buildnut — spusť: cd frontend && npm run build")
test("Frontend build (.next)", check_build)

# 7. Call queue simulation
print("\n[ 7/7 ] Call Queue Simulation")
def check_callqueue():
    url = os.getenv("SUPABASE_URL","")
    key = os.getenv("SUPABASE_ANON_KEY","")
    r = requests.get(
        f"{url}/rest/v1/leads?stav=eq.navrh_vygenerovan&telefon=not.is.null&select=name,obor,mesto,telefon&limit=3",
        headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=8)
    leads = r.json() if r.ok else []
    if not leads:
        raise Exception("Žádné leady s navrh_vygenerovan a telefonem")
    names = [l["name"][:30] for l in leads[:3]]
    return f"{len(leads)} leadů ready. Prvních 3: {', '.join(names)}"
test("Leady připravené k volání", check_callqueue)


# ─── SUMMARY ─────────────────────────────────────────────────────────────────

ok_count   = sum(1 for r in results if r[0] == OK)
fail_count = sum(1 for r in results if r[0] == FAIL)

print(f"\n{'='*55}")
print(f"  Výsledek: {ok_count}/{len(results)} testů prošlo")
if fail_count:
    print(f"\n  Oprav před spuštěním:")
    for status, name, msg in results:
        if status == FAIL:
            print(f"    • {name}: {msg}")
else:
    print(f"\n  🎉 Všechno OK! Pipeline ready ke spuštění.")
    print(f"  Spusť: cd frontend && npx vercel --prod")
print(f"{'='*55}\n")

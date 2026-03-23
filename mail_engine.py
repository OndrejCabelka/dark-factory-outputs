"""
WebHunter — Fáze 4: Mail Engine
=================================
Posílá personalizovaný mail POUZE leadům se stavem 'souhlas_k_mailu'.
Mail obsahuje live preview link na vygenerovaný návrh webu.

Technologie: Resend.com API (nejlepší deliverability, CZ/SK support)

Použití:
  python3 mail_engine.py --lead-id <uuid>          # odešli mail jednomu leadu
  python3 mail_engine.py --send-pending             # odešli všem čekajícím
  python3 mail_engine.py --test --to test@example.com  # test mail

Setup:
  1. pip install resend
  2. Nastav RESEND_API_KEY v _config/.env
  3. Nastav MAIL_FROM_DOMAIN (doména musí být ověřena v Resend)
"""

import os, json, uuid
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / "_config" / ".env")

RESEND_API_KEY   = os.getenv("RESEND_API_KEY", "")
MAIL_FROM        = os.getenv("MAIL_FROM", "ondrej@webhunter.cz")
MAIL_FROM_NAME   = os.getenv("MAIL_FROM_NAME", "Ondřej Čábelka")
SUPABASE_URL     = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY     = os.getenv("SUPABASE_ANON_KEY", "")
PROPOSALS_BASE   = "https://ondrejcabelka.github.io/dark-factory-outputs/navrhy"
TRACKING_BASE    = os.getenv("BACKEND_URL", "https://dark-factory-production.up.railway.app")


# ── EMAIL ŠABLONA ─────────────────────────────────────────────────────────────

def build_email_html(lead: dict, proposal_url: str, tracking_pixel_url: str) -> str:
    nazev   = lead.get("name", lead.get("nazev", "Vaše firma"))
    obor    = lead.get("obor", "řemeslník")
    mesto   = lead.get("mesto", "")
    jmeno   = nazev.split()[0] if nazev else "Dobrý den"  # první slovo = oslovení

    return f"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Návrh webu pro {nazev}</title>
</head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:system-ui,-apple-system,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:30px 0">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 20px rgba(0,0,0,0.08)">

      <!-- HEADER -->
      <tr><td style="background:linear-gradient(135deg,#FF4D00,#ff7c47);padding:32px 40px;text-align:center">
        <div style="font-size:28px;font-weight:900;color:white;letter-spacing:-0.5px">⚙ WebHunter</div>
        <div style="color:rgba(255,255,255,0.85);font-size:14px;margin-top:6px">Návrh webu připravený speciálně pro vás</div>
      </td></tr>

      <!-- BODY -->
      <tr><td style="padding:36px 40px">
        <p style="font-size:16px;color:#111;margin:0 0 16px">Dobrý den,</p>

        <p style="font-size:15px;color:#333;line-height:1.7;margin:0 0 20px">
          jak jsem slíbil při hovoru — posílám vám <strong>bezplatný návrh webu</strong> pro
          <strong>{nazev}</strong> ({obor}, {mesto}).
        </p>

        <p style="font-size:15px;color:#333;line-height:1.7;margin:0 0 28px">
          Web jsem připravil tak, aby odpovídal vašemu oboru a byl okamžitě
          použitelný. Podívejte se na živý náhled:
        </p>

        <!-- CTA BUTTON -->
        <table cellpadding="0" cellspacing="0" style="margin:0 auto 32px">
          <tr><td style="background:#FF4D00;border-radius:8px;padding:0">
            <a href="{proposal_url}" target="_blank"
               style="display:block;padding:16px 36px;color:white;font-size:16px;font-weight:700;text-decoration:none;letter-spacing:0.3px">
              👀 Zobrazit návrh webu →
            </a>
          </td></tr>
        </table>

        <!-- BENEFITS -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9f9f9;border-radius:10px;padding:20px;margin-bottom:28px">
          <tr><td>
            <p style="font-size:13px;font-weight:700;color:#555;margin:0 0 12px;text-transform:uppercase;letter-spacing:1px">Co web obsahuje</p>
            {''.join(f'<p style="margin:6px 0;font-size:14px;color:#333">✅ {item}</p>' for item in [
                "Profesionální design přizpůsobený oboru",
                "Mobilní verze (funguje na telefonu)",
                "Kontaktní formulář + clickable telefon",
                "Sekce služeb a reference zákazníků",
                "Připraveno ke spuštění do 48 hodin",
            ])}
          </td></tr>
        </table>

        <p style="font-size:15px;color:#333;line-height:1.7;margin:0 0 12px">
          Pokud máte zájem o spolupráci nebo otázky, odpovězte na tento email
          nebo mi zavolejte — rád vše probereme.
        </p>

        <p style="font-size:15px;color:#333;line-height:1.7;margin:0 0 32px">
          S pozdravem,<br>
          <strong>Ondřej Čábelka</strong><br>
          <span style="color:#888;font-size:13px">Webdesigner · ondrej.cabelka@gmail.com</span>
        </p>

        <!-- SECONDARY CTA -->
        <div style="border-top:1px solid #eee;padding-top:20px;text-align:center">
          <a href="{proposal_url}" style="color:#FF4D00;font-size:14px;font-weight:600;text-decoration:none">
            🔗 {proposal_url}
          </a>
        </div>
      </td></tr>

      <!-- FOOTER -->
      <tr><td style="background:#f9f9f9;padding:20px 40px;text-align:center;border-top:1px solid #eee">
        <p style="font-size:11px;color:#aaa;margin:0">
          Tento email byl odeslán na základě vašeho souhlasu při telefonickém hovoru.
          Nechcete dostávat další zprávy?
          <a href="mailto:ondrej.cabelka@gmail.com?subject=Odhlasit&body=Prosim%20odhlaste%20me%20z%20odberuondrej.cabelka@gmail.com" style="color:#aaa">Odhlásit se</a>
        </p>
      </td></tr>

    </table>
    <!-- Tracking pixel -->
    <img src="{tracking_pixel_url}" width="1" height="1" alt="" style="display:block">
  </td></tr>
</table>
</body>
</html>"""


def build_email_text(lead: dict, proposal_url: str) -> str:
    """Plain-text fallback."""
    nazev = lead.get("name", lead.get("nazev", "Vaše firma"))
    obor  = lead.get("obor", "řemeslník")
    return f"""Dobrý den,

jak jsem slíbil při hovoru — posílám bezplatný návrh webu pro {nazev} ({obor}).

Živý náhled webu: {proposal_url}

Web obsahuje profesionální design, mobilní verzi, kontaktní sekci a výpis služeb.
Připraveno ke spuštění do 48 hodin.

S pozdravem,
Ondřej Čábelka
ondrej.cabelka@gmail.com

---
Odhlásit z odběru: odpovězte s předmětem "Odhlásit"
"""


# ── RESEND SENDER ─────────────────────────────────────────────────────────────

def send_mail(to_email: str, lead: dict, proposal_url: str, tracking_id: str) -> bool:
    """Odešle email přes Resend API. Vrátí True při úspěchu."""
    if not RESEND_API_KEY:
        print("  ⚠ Chybí RESEND_API_KEY — mail nebyl odeslán")
        print(f"    → Přidej do _config/.env: RESEND_API_KEY=re_xxxx")
        return False

    try:
        import resend
    except ImportError:
        print("  ⚠ Modul resend není nainstalován: pip install resend")
        return False

    resend.api_key = RESEND_API_KEY
    tracking_pixel = f"{TRACKING_BASE}/track/open/{tracking_id}"
    nazev = lead.get("name", lead.get("nazev", "Vaše firma"))

    try:
        r = resend.Emails.send({
            "from":    f"{MAIL_FROM_NAME} <{MAIL_FROM}>",
            "to":      [to_email],
            "subject": f"Návrh webu pro {nazev} — živý náhled",
            "html":    build_email_html(lead, proposal_url, tracking_pixel),
            "text":    build_email_text(lead, proposal_url),
            "headers": {
                "X-Entity-Ref-ID": tracking_id,
            },
        })
        print(f"  ✅ Mail odeslán → {to_email} (id: {r.get('id', '?')})")
        return True
    except Exception as e:
        print(f"  ❌ Chyba odeslání: {e}")
        return False


# ── SUPABASE INTEGRATION ──────────────────────────────────────────────────────

def get_pending_leads() -> list[dict]:
    """Vrátí leady se stavem 'souhlas_k_mailu' z Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("  ⚠ Supabase není nakonfigurováno")
        return []
    try:
        from supabase import create_client
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
        r = db.table("leads").select("*").eq("stav", "souhlas_k_mailu").is_("mail_odeslan_at", "null").execute()
        return r.data or []
    except Exception as e:
        print(f"  ⚠ Supabase chyba: {e}")
        return []


def mark_mail_sent(lead_id: str, tracking_id: str):
    """Označí lead jako mail odeslan v Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        from supabase import create_client
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
        db.table("leads").update({
            "stav": "mail_odeslan",
            "mail_odeslan_at": datetime.utcnow().isoformat(),
            "tracking_id": tracking_id,
        }).eq("id", lead_id).execute()
    except Exception as e:
        print(f"  ⚠ Supabase update chyba: {e}")


def get_proposal_url(lead: dict) -> str | None:
    """Najde URL návrhu webu pro lead."""
    # Zkus index soubor
    index_path = BASE_DIR / "_outputs" / "web_navrhy" / "proposals_index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text())
        # Hledáme podle jména nebo slugu
        nazev = lead.get("name", lead.get("nazev", ""))
        for slug, meta in index.items():
            if meta.get("nazev", "").lower() == nazev.lower():
                return meta["url"]
    # Fallback: vygeneruj slug a předpokládej URL
    try:
        from generate_web_proposal import slugify
        import unicodedata
        obor  = lead.get("obor", "")
        mesto = lead.get("mesto", "")
        nazev = lead.get("name", lead.get("nazev", ""))
        slug = slugify(f"{nazev}-{obor}-{mesto}")
        return f"{PROPOSALS_BASE}/{slug}/"
    except:
        return None


# ── CLI ───────────────────────────────────────────────────────────────────────

def cmd_send_pending():
    """Odešle maily všem leadům čekajícím na mail."""
    print("📬 Hledám leady se stavem 'souhlas_k_mailu'...")
    leads = get_pending_leads()

    if not leads:
        print("  Žádné čekající leady.")
        return 0

    print(f"  Nalezeno {len(leads)} leadů k mailování")
    sent = 0

    for lead in leads:
        email = lead.get("email")
        if not email:
            print(f"  ⏭ {lead.get('name', '?')} — chybí email, přeskakuji")
            continue

        proposal_url = get_proposal_url(lead)
        if not proposal_url:
            print(f"  ⚠ {lead.get('name', '?')} — návrh webu nenalezen, generuji...")
            # Auto-generuj návrh pokud chybí
            try:
                from generate_web_proposal import generate_for_lead
                meta = generate_for_lead(lead)
                proposal_url = meta["url"]
            except Exception as e:
                print(f"  ❌ Nepodařilo se vygenerovat návrh: {e}")
                continue

        tracking_id = lead.get("tracking_id") or uuid.uuid4().hex
        ok = send_mail(email, lead, proposal_url, tracking_id)

        if ok:
            mark_mail_sent(lead["id"], tracking_id)
            sent += 1

    print(f"\n✅ Odesláno {sent}/{len(leads)} mailů")
    return sent


def cmd_send_single(lead_id: str):
    """Odešle mail jednomu konkrétnímu leadu."""
    if not SUPABASE_URL:
        print("❌ Potřebuji Supabase pro načtení leadu")
        return
    try:
        from supabase import create_client
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
        r = db.table("leads").select("*").eq("id", lead_id).execute()
        if not r.data:
            print(f"❌ Lead {lead_id} nenalezen")
            return
        lead = r.data[0]
    except Exception as e:
        print(f"❌ Supabase chyba: {e}")
        return

    email = lead.get("email")
    if not email:
        print(f"❌ Lead nemá email: {lead.get('name')}")
        return

    proposal_url = get_proposal_url(lead) or f"{PROPOSALS_BASE}/demo/"
    tracking_id  = uuid.uuid4().hex
    send_mail(email, lead, proposal_url, tracking_id)


def cmd_test(to_email: str):
    """Test mail bez Supabase."""
    demo_lead = {
        "name": "Instalatér Novák", "obor": "instalatér",
        "mesto": "Praha", "telefon": "+420777123456",
    }
    proposal_url = f"{PROPOSALS_BASE}/instalater-novak-instalater-praha/"
    tracking_id  = "test_" + uuid.uuid4().hex[:8]
    print(f"📧 Posílám test mail → {to_email}")
    send_mail(to_email, demo_lead, proposal_url, tracking_id)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="WebHunter Mail Engine")
    parser.add_argument("--send-pending", action="store_true", help="Odešli maily všem čekajícím leadům")
    parser.add_argument("--lead-id",      help="Odešli mail konkrétnímu leadu (UUID)")
    parser.add_argument("--test",         action="store_true", help="Pošli testovací mail")
    parser.add_argument("--to",           default="ondrej.cabelka@gmail.com", help="Příjemce test mailu")
    args = parser.parse_args()

    print("=" * 55)
    print("WebHunter — Mail Engine (Resend.com)")
    print("=" * 55)

    if args.test:
        cmd_test(args.to)
    elif args.lead_id:
        cmd_send_single(args.lead_id)
    elif args.send_pending:
        cmd_send_pending()
    else:
        print("Použití:")
        print("  python3 mail_engine.py --send-pending")
        print("  python3 mail_engine.py --lead-id <uuid>")
        print("  python3 mail_engine.py --test --to tvuj@email.cz")
        print("\nPro fungování potřebuješ:")
        print("  RESEND_API_KEY=re_xxxx  (resend.com → API Keys)")
        print("  MAIL_FROM=ondrej@tvoja-domena.cz  (ověřená doména v Resend)")

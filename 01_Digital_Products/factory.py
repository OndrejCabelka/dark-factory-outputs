"""
DARK FACTORY - Factory B: Digital Products v2
Přímý Claude API - žádné CrewAI, žádné rate limit problémy.

Flow:
  1. Researcher  → najde niku s tržním potenciálem
  2. Writer      → napíše obsah produktu (PDF průvodce / prompt pack / checklist)
  3. Publisher   → vygeneruje PDF + listing copy

Výstupy (_outputs/digital_products/):
  product_content_{ts}.md  - obsah produktu
  digital_product_{ts}.md  - listing copy (název, popis, tagy pro Lemon Squeezy)
  product_{ts}.pdf         - hotový PDF produkt
"""

import os, re, textwrap
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import anthropic

BASE_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=BASE_DIR / "_config" / ".env")

OUTPUT_DIR = BASE_DIR / "_outputs" / "digital_products"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Rotující fronta produktových nápadů - různé niky, různé formáty
PRODUCT_IDEAS = [
    {
        "niche": "AI produktivita",
        "format": "prompt pack",
        "title": "200 ChatGPT & Claude Promptů pro Freelancery",
        "description": "Hotové prompty pro nabídky, emaily, smlouvy, faktury, klientskou komunikaci",
        "target_buyer": "freelancer, OSVČ, živnostník",
        "price_eur": 9,
        "pages": 25,
    },
    {
        "niche": "podnikání / e-commerce",
        "format": "checklist + průvodce",
        "title": "Průvodce: Jak spustit e-shop na Shoptet za víkend",
        "description": "Krok za krokem od nuly k prvnímu prodeji - bez agentury, bez zbytečných nákladů",
        "target_buyer": "začínající e-shop majitel v CZ/SK",
        "price_eur": 12,
        "pages": 30,
    },
    {
        "niche": "SEO / marketing",
        "format": "šablony + průvodce",
        "title": "CZ SEO Starter Pack: 50 šablon pro on-page optimalizaci",
        "description": "Šablony meta tagů, H1 vzorce, FAQ struktury, interní linking strategie pro CZ weby",
        "target_buyer": "majitel webu nebo malé agentury v CZ",
        "price_eur": 15,
        "pages": 35,
    },
    {
        "niche": "osobní finance CZ",
        "format": "kalkulátor + průvodce",
        "title": "Finanční nezávislost pro Čechy: FIRE kalkulátor + strategie 2025",
        "description": "Jak spočítat cestu k finanční svobodě, CZ ETF, stavební spoření, hypotéka vs. investice",
        "target_buyer": "30-45 let, CZ, zajímá se o osobní finance",
        "price_eur": 10,
        "pages": 28,
    },
    {
        "niche": "digitální nomádství",
        "format": "průvodce",
        "title": "Průvodce digitálního nomáda: Práce z Bali, Thajska a Španělska pro Čechy",
        "description": "Daně jako OSVČ v zahraničí, pojištění, banky, levné ubytování - vše pro CZ/SK",
        "target_buyer": "IT freelancer nebo remote worker z CZ/SK",
        "price_eur": 14,
        "pages": 32,
    },
]


def _get_next_product() -> dict:
    """Vybere produkt který ještě nebyl vygenerován."""
    done_titles = set()
    for f in OUTPUT_DIR.glob("digital_product_*.md"):
        text = f.read_text(encoding="utf-8")
        m = re.search(r"^# (.+)$", text, re.M)
        if m:
            done_titles.add(m.group(1).strip().lower()[:30])

    for p in PRODUCT_IDEAS:
        key = p["title"].lower()[:30]
        if key not in done_titles:
            return p

    # Všechny hotové - začni znovu s první
    return PRODUCT_IDEAS[0]


def _clean(text: str) -> str:
    """Odstraní Markdown syntaxi."""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    return text.strip()


def generate_pdf(title: str, content: str, output_path: Path) -> Path:
    """Generuje PDF pomocí reportlab - plna Unicode podpora."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.colors import HexColor
        from reportlab.lib.units import mm
        from reportlab.platypus import (SimpleDocTemplate, Paragraph,
                                        Spacer, HRFlowable, PageBreak)
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    except ImportError:
        print("  reportlab neni - PDF preskoceno")
        return None

    BLUE = HexColor("#1e40af")
    DARK = HexColor("#111827")
    GRAY = HexColor("#6b7280")

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=22*mm,
        title=title, author="Dark Factory",
    )

    s_title = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=20,
                              textColor=BLUE, spaceAfter=6, alignment=TA_CENTER)
    s_sub   = ParagraphStyle("S", fontName="Helvetica", fontSize=10,
                              textColor=GRAY, spaceAfter=4, alignment=TA_CENTER)
    s_h1    = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=15,
                              textColor=BLUE, spaceBefore=10, spaceAfter=4)
    s_h2    = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=12,
                              textColor=DARK, spaceBefore=8, spaceAfter=3)
    s_h3    = ParagraphStyle("H3", fontName="Helvetica-BoldOblique", fontSize=10,
                              textColor=DARK, spaceBefore=5, spaceAfter=2)
    s_body  = ParagraphStyle("B", fontName="Helvetica", fontSize=9.5,
                              textColor=DARK, spaceAfter=3, leading=13,
                              alignment=TA_JUSTIFY)
    s_li    = ParagraphStyle("L", fontName="Helvetica", fontSize=9.5,
                              textColor=DARK, spaceAfter=2, leading=12,
                              leftIndent=10)

    def esc(t):
        return (t.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;"))

    story = []
    story.append(Spacer(1, 25*mm))
    story.append(Paragraph(esc(title), s_title))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f"Dark Factory | {datetime.now().year}", s_sub))
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="100%", thickness=0.4,
                             color=HexColor("#e5e7eb")))
    story.append(PageBreak())

    in_code = False
    for line in content.split("\n"):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not s:
            story.append(Spacer(1, 1.5*mm))
            continue
        text = esc(_clean(s))
        if not text:
            continue
        if s.startswith("# "):
            story.append(Paragraph(esc(_clean(s[2:])), s_h1))
        elif s.startswith("## "):
            story.append(Paragraph(esc(_clean(s[3:])), s_h2))
        elif s.startswith("### "):
            story.append(Paragraph(esc(_clean(s[4:])), s_h3))
        elif s.startswith("---"):
            story.append(HRFlowable(width="100%", thickness=0.3,
                                    color=HexColor("#e5e7eb")))
        elif re.match(r"^[\-\*] ", s):
            story.append(Paragraph(f"&#8226;&nbsp;{esc(_clean(s[2:]))}", s_li))
        elif re.match(r"^\d+\. ", s):
            story.append(Paragraph(text, s_li))
        else:
            story.append(Paragraph(text, s_body))

    doc.build(story)
    return output_path

def run_researcher(product: dict, client: anthropic.Anthropic) -> str:
    """Sub-agent 1: Validuje trh a upřesní positioning."""
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{"role": "user", "content": f"""Validuj tržní potenciál tohoto digitálního produktu pro CZ/SK trh:

Název: {product['title']}
Niche: {product['niche']}
Cílový zákazník: {product['target_buyer']}
Formát: {product['format']}
Cena: {product['price_eur']} EUR

Odpověz stručně (max 200 slov):
1. Velikost trhu v CZ/SK (odhadovaný počet potencionálních zákazníků)
2. Top 3 bolestivé body cílového zákazníka které produkt řeší
3. Klíčové výhody oproti konkurenci (co dělá tento produkt jinak)
4. Doporučený unique selling point (1 věta)
5. Kde ho nejlépe prodávat: Lemon Squeezy, vlastní web, Gumroad?"""}]
    )
    return msg.content[0].text


def run_writer(product: dict, market_insights: str, client: anthropic.Anthropic) -> str:
    """Sub-agent 2: Napíše kompletní obsah produktu."""
    format_instructions = {
        "prompt pack": f"Napiš {product['pages'] * 6} konkrétních, hotových promptů rozdělených do kategorií. Každý prompt musí být okamžitě použitelný.",
        "checklist + průvodce": f"Napiš kompletní průvodce s checklisty, krok za krokem. Cca {product['pages']} stran A4 obsahu.",
        "šablony + průvodce": f"Napiš {product['pages']} konkrétních šablon s vysvětlením jak je používat.",
        "kalkulátor + průvodce": f"Napiš detailní průvodce s konkrétními výpočty, příklady a tabulkami. Cca {product['pages']} stran.",
        "průvodce": f"Napiš kompletní průvodce rozdělený do kapitol. Cca {product['pages']} stran A4.",
    }
    instruction = format_instructions.get(product["format"], f"Napiš kompletní obsah, cca {product['pages']} stran.")

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4500,
        messages=[{"role": "user", "content": f"""Napiš kompletní obsah digitálního produktu pro CZ/SK trh.

PRODUKT: {product['title']}
NICHE: {product['niche']}
CÍLOVÝ ZÁKAZNÍK: {product['target_buyer']}
FORMÁT: {product['format']}

TRŽNÍ INSIGHT (z výzkumu):
{market_insights}

INSTRUKCE:
{instruction}

POŽADAVKY:
- Psáno v češtině, profesionálně ale přístupně
- Konkrétní, actionable - žádné vaty, žádné obecné rady
- Strukturováno pomocí nadpisů (# ## ###)
- Reálná čísla, příklady z CZ trhu kde relevantní
- Každá sekce musí přinést jasnou hodnotu zákazníkovi

Piš rovnou obsah - bez úvodu o tom co budeš psát."""}]
    )
    return msg.content[0].text


def run_listing_writer(product: dict, content: str, client: anthropic.Anthropic) -> str:
    """Sub-agent 3: Napíše listing copy pro Lemon Squeezy."""
    word_count = len(content.split())
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": f"""Napiš listing copy pro prodej tohoto digitálního produktu na Lemon Squeezy.

PRODUKT: {product['title']}
CENA: {product['price_eur']} EUR
ROZSAH: {word_count} slov / ~{product['pages']} stran PDF
FORMÁT: {product['format']}
CÍLOVÝ ZÁKAZNÍK: {product['target_buyer']}

Napiš:
# [NÁZEV PRODUKTU]
**Tagline:** [max 10 slov, benefit-first]
**Popis (pro stránku produktu):** [150-200 slov, CZ, AIDA framework]
**Bullet points (5x):**
- ✅ ...
**Tagy:** [10 tagů oddělených čárkou]
**Cena doporučená:** {product['price_eur']} EUR"""}]
    )
    return msg.content[0].text


def main():
    print("=" * 55)
    print("FACTORY B - DIGITAL PRODUCTS v2 (přímý Claude API)")
    print("Researcher → Writer → ListingWriter")
    print("=" * 55)

    if not ANTHROPIC_API_KEY:
        print("❌ Chybí ANTHROPIC_API_KEY")
        return None

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    product = _get_next_product()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n📦 Produkt: {product['title']}")
    print(f"   Niche: {product['niche']} | Formát: {product['format']} | Cena: {product['price_eur']} EUR")

    # Sub-agent 1: Researcher
    print("\n🔍 Sub-agent 1: Researcher (validace trhu)...")
    market_insights = run_researcher(product, client)
    print(f"   ✅ Market insights ({len(market_insights.split())} slov)")

    # Sub-agent 2: Writer
    print("\n✍️  Sub-agent 2: Writer (obsah produktu)...")
    content = run_writer(product, market_insights, client)
    word_count = len(content.split())
    print(f"   ✅ Obsah: {word_count} slov")

    content_path = OUTPUT_DIR / f"product_content_{ts}.md"
    content_path.write_text(f"# {product['title']}\n\n{content}", encoding="utf-8")
    print(f"   📄 Uloženo: {content_path.name}")

    # Sub-agent 3: Listing writer
    print("\n📝 Sub-agent 3: Listing Writer (sales copy)...")
    listing = run_listing_writer(product, content, client)
    listing_path = OUTPUT_DIR / f"digital_product_{ts}.md"
    listing_path.write_text(listing, encoding="utf-8")
    print(f"   ✅ Listing: {listing_path.name}")

    # PDF generování
    print("\n📄 Generuji PDF...")
    pdf_path = OUTPUT_DIR / f"product_{ts}.pdf"
    result = generate_pdf(product["title"], content, pdf_path)
    if result and result.exists():
        size_kb = result.stat().st_size // 1024
        print(f"   ✅ PDF: {pdf_path.name} ({size_kb} kB)")
    else:
        print("   ⚠ PDF se nepodařilo vygenerovat")

    print(f"\n📊 SOUHRN:")
    print(f"   Produkt: {product['title']}")
    print(f"   Obsah: {word_count} slov | PDF: {pdf_path.name if result else 'chyba'}")
    print(f"   Doporučená cena: {product['price_eur']} EUR")
    print(f"   Listing copy: {listing_path.name}")
    # Auto-publish na Lemon Squeezy (pokud je API klíč nastaven)
    ls_key = os.getenv("LEMONSQUEEZY_API_KEY", "")
    if ls_key and result and result.exists():
        print(f"\n🛒 Auto-publish na Lemon Squeezy...")
        try:
            import sys
            sys.path.insert(0, str(BASE_DIR))
            from publish_lemonsqueezy import publish as ls_publish
            url = ls_publish(price_cents=int(product["price_eur"] * 100 / 25))  # EUR→CZK approx
            if url:
                print(f"   🎉 LIVE: {url}")
        except Exception as e:
            print(f"   ⚠ Lemon Squeezy publish selhal: {e}")
            print(f"   → Ruční upload: python3 publish_lemonsqueezy.py")
    else:
        print(f"\n→ Nastav LEMONSQUEEZY_API_KEY pro auto-publish, nebo:")
        print(f"   python3 publish_lemonsqueezy.py")

    return str(pdf_path) if result else str(content_path)


if __name__ == "__main__":
    main()

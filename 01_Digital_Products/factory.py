"""
DARK FACTORY — Factory B: Digital Products v2
Přímý Claude API — žádné CrewAI, žádné rate limit problémy.

Flow:
  1. Researcher  → najde niku s tržním potenciálem
  2. Writer      → napíše obsah produktu (PDF průvodce / prompt pack / checklist)
  3. Publisher   → vygeneruje PDF + listing copy

Výstupy (_outputs/digital_products/):
  product_content_{ts}.md  — obsah produktu
  digital_product_{ts}.md  — listing copy (název, popis, tagy pro Lemon Squeezy)
  product_{ts}.pdf         — hotový PDF produkt
"""

import os, re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import anthropic

BASE_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=BASE_DIR / "_config" / ".env")

OUTPUT_DIR = BASE_DIR / "_outputs" / "digital_products"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Rotující fronta produktových nápadů — různé niky, různé formáty
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
        "description": "Krok za krokem od nuly k prvnímu prodeji — bez agentury, bez zbytečných nákladů",
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
        "description": "Daně jako OSVČ v zahraničí, pojištění, banky, levné ubytování — vše pro CZ/SK",
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

    # Všechny hotové — začni znovu s první
    return PRODUCT_IDEAS[0]


def _clean_for_pdf(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"#{1,6}\s+", "", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def generate_pdf(title: str, content: str, output_path: Path) -> Path:
    try:
        from fpdf import FPDF
    except ImportError:
        print("  ⚠ fpdf2 není nainstalován — PDF přeskočeno")
        return None

    title_safe = _clean_for_pdf(title)

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, title_safe[:70], align="R")
            self.ln(8)
        def footer(self):
            self.set_y(-13)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8, f"Strana {self.page_no()}", align="C")

    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(True, margin=22)
    pdf.add_page()

    # Titulní strana
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(30, 64, 175)
    pdf.ln(18)
    pdf.multi_cell(0, 10, title_safe, align="C")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, f"Dark Factory — {datetime.now().year}", align="C")
    pdf.ln(30)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.add_page()

    # Obsah
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            pdf.ln(3)
            continue

        safe = _clean_for_pdf(stripped)

        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(30, 64, 175)
            pdf.ln(4)
            pdf.multi_cell(0, 8, safe[2:] if safe.startswith("# ") else safe)
            pdf.ln(2)
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(55, 65, 81)
            pdf.ln(3)
            pdf.multi_cell(0, 7, safe[3:] if safe.startswith("## ") else safe)
            pdf.ln(1)
        elif line.startswith("### "):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(75, 85, 99)
            pdf.multi_cell(0, 6, safe[4:] if safe.startswith("### ") else safe)
        elif stripped.startswith("- ") or stripped.startswith("• "):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            item = safe[2:] if safe.startswith("- ") else safe[2:]
            pdf.cell(6, 5, "•")
            pdf.multi_cell(0, 5, item)
        elif re.match(r"^\d+\.", stripped):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 5, safe)
        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 5, safe)

    pdf.output(str(output_path))
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
- Konkrétní, actionable — žádné vaty, žádné obecné rady
- Strukturováno pomocí nadpisů (# ## ###)
- Reálná čísla, příklady z CZ trhu kde relevantní
- Každá sekce musí přinést jasnou hodnotu zákazníkovi

Piš rovnou obsah — bez úvodu o tom co budeš psát."""}]
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
    print("FACTORY B — DIGITAL PRODUCTS v2 (přímý Claude API)")
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
    print(f"\n→ Nahraj PDF na Lemon Squeezy: https://app.lemonsqueezy.com/products")

    return str(pdf_path) if result else str(content_path)


if __name__ == "__main__":
    main()

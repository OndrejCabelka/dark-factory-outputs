"""
Factory E — SEO Affiliate Content
Generuje SEO-optimalizované články pro niche affiliate web.
Cíl: low-competition klíčová slova, CZ trh, affiliate produkty.
"""

import os, json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import anthropic

BASE_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=BASE_DIR / "_config" / ".env")

OUTPUT_DIR = BASE_DIR / "_outputs" / "seo_content"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Niche: stavební materiály, nářadí, dům a zahrada — vysoký AOV, dobré CZ affiliate programy
# Affilate: Heureka, Alza, Mall.cz, Hornbach

ARTICLE_QUEUE = [
    {
        "keyword": "nejlepší akumulátorová vrtačka 2025",
        "intent": "commercial",
        "affiliate_niche": "nářadí",
        "target_length": 1500,
        "affiliate_products": ["Bosch GSR 18V", "Makita DDF484", "DeWalt DCD796"],
    },
    {
        "keyword": "jak vybrat tlakový čistič na terasu",
        "intent": "informational",
        "affiliate_niche": "zahrada",
        "target_length": 1800,
        "affiliate_products": ["Kärcher K5", "Bosch UniversalAquatak 135", "Nilfisk Core 140"],
    },
    {
        "keyword": "srovnání robotických sekaček 2025",
        "intent": "commercial",
        "affiliate_niche": "zahrada",
        "target_length": 2000,
        "affiliate_products": ["Husqvarna Automower 305", "Gardena SILENO+", "Bosch Indego S+ 500"],
    },
    {
        "keyword": "nejlepší elektrická pila na dřevo pro domácnost",
        "intent": "commercial",
        "affiliate_niche": "nářadí",
        "target_length": 1600,
        "affiliate_products": ["Bosch PST 900 PEL", "Makita JV0600K", "DeWalt DCS331"],
    },
    {
        "keyword": "jak zateplení fasády šetří na topení",
        "intent": "informational",
        "affiliate_niche": "stavba",
        "target_length": 2200,
        "affiliate_products": ["Isover EPS 70F", "Rockwool Fasrock", "Baumit StarTherm"],
    },
    {
        "keyword": "recenze bezdrátový vysavač Dyson vs Xiaomi",
        "intent": "commercial",
        "affiliate_niche": "domácnost",
        "target_length": 1700,
        "affiliate_products": ["Dyson V15", "Xiaomi Dreame T30", "Rowenta X-Force Flex"],
    },
    {
        "keyword": "chytrá domácnost levně — nejlepší starter kit 2025",
        "intent": "commercial",
        "affiliate_niche": "smart home",
        "target_length": 1900,
        "affiliate_products": ["Philips Hue starter", "IKEA Trådfri", "Sonoff Basic"],
    },
]


def generate_seo_article(article_spec: dict) -> str:
    """Claude vygeneruje kompletní SEO článek."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    products_list = "\n".join(f"- {p}" for p in article_spec["affiliate_products"])

    prompt = f"""Jsi SEO copywriter specializovaný na CZ affiliate web o {article_spec['affiliate_niche']}.

Napiš kompletní SEO článek pro toto klíčové slovo:
**{article_spec['keyword']}**

Záměr hledání: {article_spec['intent']}
Cílová délka: ~{article_spec['target_length']} slov
Affiliate produkty k zmínění:
{products_list}

POŽADAVKY NA STRUKTURU:
1. H1 nadpis (musí obsahovat klíčové slovo)
2. Úvodní odstavec (2-3 věty, zachyť pozornost, zmíň klíčové slovo)
3. Obsah (rychlá navigace pro delší články)
4. H2/H3 sekce logicky rozdělující téma
5. Srovnávací tabulka produktů (pokud relevantní)
6. Pro/Contra pro každý produkt
7. Konkrétní doporučení — "Tento produkt je nejlepší pro..."
8. Závěr + CTA ("Koupit za nejlepší cenu na [Heureka/Alza]")

TECHNICKÉ SEO:
- Klíčové slovo v prvních 100 slovech
- LSI klíčová slova přirozeně rozptýlená
- Interní FAQ sekce (3-5 otázek)
- Meta description na konci (max 160 znaků)

Piš přirozeně česky, jako člověk který produkty zná a radí kamarádovi.
Výstup: čistý Markdown."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


def get_next_article() -> dict | None:
    """Vybere další článek z fronty který ještě nebyl vygenerován."""
    done_file = OUTPUT_DIR / "generated.json"
    done = set()
    if done_file.exists():
        with open(done_file) as f:
            done = set(json.load(f))

    for article in ARTICLE_QUEUE:
        slug = article["keyword"].replace(" ", "_")[:40]
        if slug not in done:
            return article, slug, done_file, done
    return None, None, None, None


def factory_e():
    print("=" * 50)
    print("FACTORY E — SEO Affiliate Content")
    print("=" * 50)

    if not ANTHROPIC_API_KEY:
        print("❌ Chybí ANTHROPIC_API_KEY")
        return False

    article_spec, slug, done_file, done = get_next_article()
    if not article_spec:
        print("✅ Všechny články ve frontě jsou vygenerované!")
        # Reset fronty pro nový cyklus
        if done_file and done_file.exists():
            done_file.unlink()
            print("  → Fronta resetována pro nový cyklus")
        return True

    print(f"\n📝 Generuji článek: '{article_spec['keyword']}'")
    print(f"  Niche: {article_spec['affiliate_niche']} | Délka: ~{article_spec['target_length']} slov")

    content = generate_seo_article(article_spec)

    # Uložit článek
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{date_str}_{slug}.md"
    filepath = OUTPUT_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"---\n")
        f.write(f"keyword: {article_spec['keyword']}\n")
        f.write(f"niche: {article_spec['affiliate_niche']}\n")
        f.write(f"generated: {datetime.now().isoformat()}\n")
        f.write(f"---\n\n")
        f.write(content)

    # Označit jako hotový
    done.add(slug)
    with open(done_file, "w") as f:
        json.dump(list(done), f)

    word_count = len(content.split())
    print(f"\n✅ Článek uložen: {filename} ({word_count} slov)")
    print(f"  Zbývá ve frontě: {len(ARTICLE_QUEUE) - len(done)} článků")
    return True


if __name__ == "__main__":
    factory_e()

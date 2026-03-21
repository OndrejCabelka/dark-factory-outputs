"""
Factory E — SEO Affiliate Content
Generuje SEO-optimalizované články pro niche affiliate web.
Cíl: low-competition klíčová slova, CZ trh, affiliate produkty s reálnými linky.
"""

import os, json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv
import anthropic

BASE_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=BASE_DIR / "_config" / ".env")

OUTPUT_DIR = BASE_DIR / "_outputs" / "seo_content"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def heureka_url(product: str) -> str:
    return f"https://www.heureka.cz/?h%5Bfraze%5D={quote_plus(product)}"


def alza_url(product: str) -> str:
    return f"https://www.alza.cz/search.htm?exps={quote_plus(product)}"


def mall_url(product: str) -> str:
    return f"https://www.mall.cz/search/{quote_plus(product)}"


def build_product_links(products: list[str]) -> str:
    """Vygeneruje markdown seznam produktů s affiliate linky na Heureka + Alza."""
    lines = []
    for p in products:
        h = heureka_url(p)
        a = alza_url(p)
        lines.append(f"- **{p}** — [Heureka]({h}) | [Alza]({a})")
    return "\n".join(lines)


# Niche: nářadí, dům a zahrada — vysoký AOV, dobré CZ affiliate programy
# Affiliate: Heureka, Alza, Mall.cz

ARTICLE_QUEUE = [
    {
        "keyword": "nejlepší akumulátorová vrtačka 2025",
        "intent": "commercial",
        "affiliate_niche": "nářadí",
        "target_length": 1500,
        "affiliate_products": ["Bosch GSR 18V-55", "Makita DDF484RTJ", "DeWalt DCD796P2"],
    },
    {
        "keyword": "jak vybrat tlakový čistič na terasu",
        "intent": "informational",
        "affiliate_niche": "zahrada",
        "target_length": 1800,
        "affiliate_products": ["Kärcher K5 Premium", "Bosch UniversalAquatak 135", "Nilfisk Core 140"],
    },
    {
        "keyword": "srovnání robotických sekaček 2025",
        "intent": "commercial",
        "affiliate_niche": "zahrada",
        "target_length": 2000,
        "affiliate_products": ["Husqvarna Automower 305", "Gardena SILENO+ 750", "Bosch Indego S+ 500"],
    },
    {
        "keyword": "nejlepší elektrická pila na dřevo pro domácnost",
        "intent": "commercial",
        "affiliate_niche": "nářadí",
        "target_length": 1600,
        "affiliate_products": ["Bosch PST 900 PEL", "Makita JV0600K", "DeWalt DCS331N"],
    },
    {
        "keyword": "jak zateplení fasády šetří na topení",
        "intent": "informational",
        "affiliate_niche": "stavba",
        "target_length": 2200,
        "affiliate_products": ["Isover EPS 70F", "Rockwool Fasrock L", "Baumit StarTherm"],
    },
    {
        "keyword": "recenze bezdrátový vysavač Dyson vs Xiaomi",
        "intent": "commercial",
        "affiliate_niche": "domácnost",
        "target_length": 1700,
        "affiliate_products": ["Dyson V15 Detect", "Dreame T30 Neo", "Rowenta X-Force Flex 14.60"],
    },
    {
        "keyword": "chytrá domácnost levně — nejlepší starter kit 2025",
        "intent": "commercial",
        "affiliate_niche": "smart home",
        "target_length": 1900,
        "affiliate_products": ["Philips Hue Starter Kit", "IKEA Trådfri Gateway", "Sonoff Basic R2"],
    },
    # --- Kolo 2: vyšší AOV, méně konkurence ---
    {
        "keyword": "nejlepší tepelné čerpadlo vzduch voda 2025",
        "intent": "commercial",
        "affiliate_niche": "vytápění",
        "target_length": 2200,
        "affiliate_products": ["Daikin Altherma 3", "Mitsubishi Ecodan PUD-SWM", "Vaillant aroTHERM plus"],
    },
    {
        "keyword": "jak vybrat zahradní sekačku s pojezdem",
        "intent": "informational",
        "affiliate_niche": "zahrada",
        "target_length": 1800,
        "affiliate_products": ["Honda HRX 476 VY", "Husqvarna LC 353V", "Bosch Rotak 43 LI"],
    },
    {
        "keyword": "recenze robotický vysavač iRobot vs Roborock 2025",
        "intent": "commercial",
        "affiliate_niche": "domácnost",
        "target_length": 1900,
        "affiliate_products": ["iRobot Roomba j7+", "Roborock S8 Pro Ultra", "Dreame L20 Ultra"],
    },
    {
        "keyword": "nejlepší akumulátorová bruska na dřevo 2025",
        "intent": "commercial",
        "affiliate_niche": "nářadí",
        "target_length": 1600,
        "affiliate_products": ["Bosch GEX 18V-125", "Makita DBO180Z", "DeWalt DCW210N"],
    },
    {
        "keyword": "jak vybrat střešní okno — Velux vs Fakro srovnání",
        "intent": "commercial",
        "affiliate_niche": "stavba",
        "target_length": 2000,
        "affiliate_products": ["Velux GGL 3066", "Fakro FTP-V U3", "Roto WDF R89"],
    },
    {
        "keyword": "srovnání parních čističů na podlahy 2025",
        "intent": "commercial",
        "affiliate_niche": "domácnost",
        "target_length": 1700,
        "affiliate_products": ["Kärcher SC 4 EasyFix", "Polti Vaporetto Style", "Bissell PowerFresh"],
    },
    {
        "keyword": "nejlepší garážová vrata sekční vs výklopná",
        "intent": "informational",
        "affiliate_niche": "stavba",
        "target_length": 2100,
        "affiliate_products": ["Hörmann LPU 40", "Wiśniowski Industry 2", "Normstahl Eco 2000"],
    },
    # --- Kolo 3: vyšší AOV, méně konkurence, CZ long-tail ---
    {
        "keyword": "nejlepší solární panely pro rodinný dům 2025",
        "intent": "commercial",
        "affiliate_niche": "energie",
        "target_length": 2200,
        "affiliate_products": ["Suntech STP320", "Jinko Solar Eagle 400W", "LONGi Hi-MO5 410W"],
    },
    {
        "keyword": "jak vybrat klimatizaci do bytu — split vs mobilní",
        "intent": "commercial",
        "affiliate_niche": "klimatizace",
        "target_length": 1900,
        "affiliate_products": ["Daikin Perfera FTXM35R", "Mitsubishi MSZ-AP35VGK", "LG Artcool S12ET"],
    },
    {
        "keyword": "nejlepší zahradní traktor sekačka 2025 srovnání",
        "intent": "commercial",
        "affiliate_niche": "zahrada",
        "target_length": 2100,
        "affiliate_products": ["Honda HF 2315 HME", "Husqvarna TS 347", "STIGA Tornado 3098 H"],
    },
    {
        "keyword": "recenze elektrické koloběžky pro dospělé 2025",
        "intent": "commercial",
        "affiliate_niche": "mobilita",
        "target_length": 1800,
        "affiliate_products": ["Xiaomi Electric Scooter 4 Pro", "Segway Ninebot Max G2", "Apollo City Pro"],
    },
    {
        "keyword": "nejlepší myčka nádobí do malé kuchyně 2025",
        "intent": "commercial",
        "affiliate_niche": "domácnost",
        "target_length": 1700,
        "affiliate_products": ["Bosch SMS2ITI12E", "Siemens SN23HW64CE", "AEG FSB52610Z"],
    },
    {
        "keyword": "jak vybrat pračku — přední vs vrchní plnění 2025",
        "intent": "informational",
        "affiliate_niche": "domácnost",
        "target_length": 1900,
        "affiliate_products": ["Samsung WW80T534DAE", "Miele WDB030 WCS", "Bosch WAX32M40BY"],
    },
    {
        "keyword": "nejlepší notebook do 20000 Kč 2025 — srovnání",
        "intent": "commercial",
        "affiliate_niche": "elektronika",
        "target_length": 2000,
        "affiliate_products": ["Lenovo ThinkPad E16 Gen 2", "ASUS VivoBook 16X", "HP EliteBook 640 G10"],
    },
    {
        "keyword": "recenze vzduchová fritéza — Philips vs Tefal vs Ninja",
        "intent": "commercial",
        "affiliate_niche": "domácnost",
        "target_length": 1800,
        "affiliate_products": ["Philips NA352/00", "Tefal Easy Fry XXL EY801D", "Ninja AF160EU"],
    },
    {
        "keyword": "nejlepší zahradní gril na dřevěné uhlí 2025",
        "intent": "commercial",
        "affiliate_niche": "zahrada",
        "target_length": 1700,
        "affiliate_products": ["Weber Master-Touch GBS Premium E-5775", "Char-Broil Kettleman", "Napoleon Rodeo PRO"],
    },
    {
        "keyword": "jak vybrat fotovoltaiku pro firmu — návratnost a cena 2025",
        "intent": "informational",
        "affiliate_niche": "energie",
        "target_length": 2400,
        "affiliate_products": ["Growatt SPH 10000TL3 BH-UP", "Solax X3-Hybrid G4 10kW", "SMA Sunny Tripower 10.0"],
    },
]



def generate_seo_article(article_spec: dict) -> str:
    """Claude vygeneruje kompletní SEO článek s reálnými affiliate linky."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    product_links = build_product_links(article_spec["affiliate_products"])

    # CTA sekce s linky na všechny produkty
    cta_links = []
    for p in article_spec["affiliate_products"]:
        cta_links.append(
            f"- [{p} na Heureka]({heureka_url(p)}) — porovnání cen\n"
            f"- [{p} na Alza]({alza_url(p)}) — rychlé doručení"
        )
    cta_block = "\n".join(cta_links)

    prompt = f"""Jsi SEO copywriter specializovaný na CZ affiliate web o {article_spec['affiliate_niche']}.

Napiš kompletní SEO článek pro toto klíčové slovo:
**{article_spec['keyword']}**

Záměr hledání: {article_spec['intent']}
Cílová délka: ~{article_spec['target_length']} slov

AFFILIATE PRODUKTY — použij PŘESNĚ tyto markdown linky v textu článku:
{product_links}

AFFILIATE CTA — vlož tuto sekci před závěr článku doslova (zachovej markdown linky):
### Kde koupit za nejlepší cenu?
{cta_block}

POŽADAVKY NA STRUKTURU:
1. H1 nadpis (musí obsahovat klíčové slovo)
2. Úvodní odstavec (2-3 věty, zachyť pozornost, zmíň klíčové slovo)
3. Obsah — rychlá navigace s kotevními linky (#sekce)
4. H2/H3 sekce logicky rozdělující téma
5. Srovnávací tabulka produktů v Markdown (| Produkt | Cena | Výkon | Hodnocení |)
6. Pro/Contra pro každý produkt (max 3+3 body)
7. "Který produkt je nejlepší pro..." — konkrétní doporučení
8. Sekce "Kde koupit za nejlepší cenu?" (viz výše — vlož doslova)
9. Závěr (2-3 věty, shrnutí, výzva k akci)
10. FAQ sekce (3-5 otázek s odpověďmi)
11. Meta description na konci (max 160 znaků, začni: "<!-- META: ")

TECHNICKÉ SEO:
- Klíčové slovo v prvních 100 slovech
- LSI klíčová slova přirozeně rozptýlená
- Affiliate linky musí být v textu přirozeně zapojené (ne jen v CTA sekci)

Piš přirozeně česky, jako člověk který produkty zná a radí kamarádovi.
DŮLEŽITÉ: Zachovej všechny markdown linky přesně jak jsou zadané — neměň URL adresy.
Výstup: čistý Markdown."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4500,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


def get_next_article():
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
        print("❌ Chybí ANTHROPIC_API_KEY — nastav v _config/.env")
        return False

    article_spec, slug, done_file, done = get_next_article()
    if not article_spec:
        print("✅ Všechny články ve frontě jsou vygenerované!")
        if done_file and done_file.exists():
            done_file.unlink()
            print("  → Fronta resetována pro nový cyklus")
        return True

    print(f"\n📝 Generuji článek: '{article_spec['keyword']}'")
    print(f"  Niche: {article_spec['affiliate_niche']} | Délka: ~{article_spec['target_length']} slov")
    print(f"  Produkty: {', '.join(article_spec['affiliate_products'])}")

    # Ukázka vygenerovaných URL před generováním
    print("\n  Affiliate linky:")
    for p in article_spec["affiliate_products"]:
        print(f"    {p} → {heureka_url(p)}")

    content = generate_seo_article(article_spec)

    # Ověř že jsou v obsahu skutečné linky
    link_count = content.count("heureka.cz") + content.count("alza.cz")
    print(f"\n  Affiliate linky v článku: {link_count}")

    # Uložit článek
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{date_str}_{slug}.md"
    filepath = OUTPUT_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"---\n")
        f.write(f"keyword: {article_spec['keyword']}\n")
        f.write(f"niche: {article_spec['affiliate_niche']}\n")
        f.write(f"generated: {datetime.now().isoformat()}\n")
        f.write(f"affiliate_links: {link_count}\n")
        f.write(f"---\n\n")
        f.write(content)

    # Označit jako hotový
    done.add(slug)
    with open(done_file, "w") as f:
        json.dump(list(done), f)

    word_count = len(content.split())
    print(f"\n✅ Článek uložen: {filename} ({word_count} slov, {link_count} affiliate linků)")
    print(f"  Zbývá ve frontě: {len(ARTICLE_QUEUE) - len(done)} článků")
    return True


if __name__ == "__main__":
    factory_e()

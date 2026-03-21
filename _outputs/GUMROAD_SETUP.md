# Gumroad Setup — 5 minut, jednou, manuálně

Gumroad API neumožňuje vytvořit produkt přes kód — musíš ho kliknout ručně jednou.
Po tomhle nastavení už vše poběží automaticky.

## Krok 1 — Vytvoř produkt na Gumroad

1. Jdi na: https://app.gumroad.com/products/new
2. Vyber typ: **Digital product**
3. Vyplň:
   - **Name:** `27 ChatGPT Prompts for Etsy Sellers — Ready-to-Use Templates`
   - **Price:** `$7` (nebo 0 pro free s pay-what-you-want)
   - **Description:** (kopíruj níže)
4. **Neklikej ještě Publish** — jen Save/Create

### Popis pro Gumroad:
```
Stop staring at a blank screen. These 27 battle-tested ChatGPT prompts help
Etsy sellers write product listings, social posts, and emails faster.

✅ 27 ready-to-use prompt templates
✅ Covers listings, SEO, social media, email sequences
✅ Works with ChatGPT-4 and free GPT-3.5
✅ Instant download PDF
```

## Krok 2 — Nahraj PDF

PDF je připravené tady:
`/Users/ondrejcabelka/Desktop/DarkFactory/_outputs/digital_products/product_20260319_214808.pdf`

V Gumroad: **Add a file** → nahraj tenhle PDF.

## Krok 3 — Získej Product ID

Po uložení se podívej na URL stránky produktu, bude vypadat takhle:
`https://app.gumroad.com/products/ABCD1234`

Ten `ABCD1234` je tvůj Product ID.

## Krok 4 — Přidej ID do .env

Otevři: `/Users/ondrejcabelka/Desktop/DarkFactory/_config/.env`

Přidej řádek:
```
GUMROAD_PRODUCT_ID=ABCD1234
```
(nahraď ABCD1234 svým skutečným ID)

## Krok 5 — Spusť publish skript

```bash
cd /Users/ondrejcabelka/Desktop/DarkFactory
source .venv/bin/activate
python3 publish_gumroad.py
```

Tohle automaticky:
- Aktualizuje název a popis produktu
- Nahraje PDF jako content file
- Zveřejní produkt

## Co se stane dál

Scheduler.py po každém spuštění Factory B automaticky volá publish_gumroad.py.
Každý den ráno se na Gumroad aktualizuje nový digitální produkt bez tvého zásahu.

---
Access token je už nastavený v .env: ✅ GUMROAD_ACCESS_TOKEN
Chybí jen: ❌ GUMROAD_PRODUCT_ID (jednorázový manuální krok výše)

"""
DARK FACTORY — Lemon Squeezy Publisher
Plné API — vytvoří produkt, nahraje soubor, publikuje automaticky.
Nastav: LEMONSQUEEZY_API_KEY + LEMONSQUEEZY_STORE_ID v _config/.env
Získej: https://app.lemonsqueezy.com/settings/api
"""
import os, sys, json, datetime, requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / "_config" / ".env")

API_KEY  = os.getenv("LEMONSQUEEZY_API_KEY", "").strip()
STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID", "").strip()
OUT_DIR  = BASE_DIR / "_outputs" / "digital_products"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/vnd.api+json",
    "Content-Type": "application/vnd.api+json",
}


def get_store_id() -> str:
    """Pokud STORE_ID není v .env, automaticky ho získá z API."""
    if STORE_ID:
        return STORE_ID
    r = requests.get("https://api.lemonsqueezy.com/v1/stores", headers=HEADERS)
    stores = r.json().get("data", [])
    if not stores:
        raise RuntimeError("Žádný store nenalezen. Vytvoř store na lemonsqueezy.com")
    sid = stores[0]["id"]
    print(f"  Store ID: {sid} ({stores[0]['attributes']['name']})")
    # Ulož do .env
    env = (BASE_DIR / "_config" / ".env").read_text()
    if "LEMONSQUEEZY_STORE_ID" not in env:
        with open(BASE_DIR / "_config" / ".env", "a") as f:
            f.write(f"\nLEMONSQUEEZY_STORE_ID={sid}\n")
    return sid


def get_latest_pdf() -> Path | None:
    pdfs = sorted(OUT_DIR.glob("product_*.pdf"), key=lambda f: f.stat().st_mtime, reverse=True)
    return pdfs[0] if pdfs else None


def get_product_meta() -> dict:
    """Extrahuje název + popis z nejnovějšího marketing MD."""
    mds = sorted(OUT_DIR.glob("digital_product_*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not mds:
        return {}
    lines = [l.strip() for l in mds[0].read_text(encoding="utf-8").splitlines() if l.strip()]
    title, desc_lines, in_desc = None, [], False
    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif "TITLE" in line.upper() and not title:
            idx = lines.index(line)
            for nl in lines[idx+1:idx+4]:
                if nl and not nl.startswith("#") and len(nl) < 120:
                    title = nl; break
        elif "DESCRIPTION" in line.upper():
            in_desc = True
        elif in_desc and line.startswith("##"):
            in_desc = False
        elif in_desc:
            desc_lines.append(line)
    return {
        "title": (title or "Digital Product by Dark Factory")[:80],
        "description": " ".join(desc_lines[:15]) or "Instant-download digital product.",
    }


def create_product(store_id: str, title: str, description: str, price_cents: int = 700) -> str:
    """Vytvoří produkt a vrátí product_id."""
    payload = {"data": {"type": "products", "attributes": {
        "name": title,
        "description": description,
        "price": price_cents,
        "pay_what_you_want": False,
        "store_id": int(store_id),
    }, "relationships": {"store": {"data": {"type": "stores", "id": store_id}}}}}
    r = requests.post("https://api.lemonsqueezy.com/v1/products", headers=HEADERS, json=payload)
    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"Chyba vytvoření produktu: {data['errors']}")
    return data["data"]["id"]


def create_variant(product_id: str, price_cents: int = 700) -> str:
    """Vytvoří variantu (Lemon Squeezy vyžaduje aspoň jednu)."""
    payload = {"data": {"type": "variants", "attributes": {
        "name": "Default",
        "price": price_cents,
        "is_subscription": False,
        "has_free_trial": False,
        "pay_what_you_want": False,
        "min_price": 0,
        "suggested_price": price_cents,
    }, "relationships": {"product": {"data": {"type": "products", "id": product_id}}}}}
    r = requests.post("https://api.lemonsqueezy.com/v1/variants", headers=HEADERS, json=payload)
    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"Chyba vytvoření varianty: {data['errors']}")
    return data["data"]["id"]


def upload_pdf_to_variant(variant_id: str, pdf_path: Path) -> str:
    """Nahraje PDF soubor jako digitální download na variantu."""
    import base64
    pdf_bytes = pdf_path.read_bytes()
    pdf_b64   = base64.b64encode(pdf_bytes).decode("ascii")

    payload = {"data": {"type": "files", "attributes": {
        "name": pdf_path.name,
        "data": pdf_b64,
    }, "relationships": {"variant": {"data": {"type": "variants", "id": variant_id}}}}}

    r = requests.post("https://api.lemonsqueezy.com/v1/files", headers=HEADERS, json=payload)
    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"Chyba nahrání souboru: {data['errors']}")
    file_id = data["data"]["id"]
    print(f"  ✅ PDF nahráno (file_id: {file_id}, {len(pdf_bytes)//1024} kB)")
    return file_id


def list_products(store_id: str) -> list:
    r = requests.get(f"https://api.lemonsqueezy.com/v1/products?filter[store_id]={store_id}", headers=HEADERS)
    return r.json().get("data", [])


def get_product_url(product_id: str) -> str:
    r = requests.get(f"https://api.lemonsqueezy.com/v1/products/{product_id}", headers=HEADERS)
    attrs = r.json()["data"]["attributes"]
    return attrs.get("buy_now_url") or attrs.get("url", "")


def publish(price_cents: int = 700) -> str | None:
    if not API_KEY:
        print("❌ LEMONSQUEEZY_API_KEY není nastaven.")
        print("   1. Jdi na: https://app.lemonsqueezy.com/settings/api")
        print("   2. Klikni 'Add API key', zkopíruj ho")
        print("   3. Přidej do _config/.env: LEMONSQUEEZY_API_KEY=tvuj_klic")
        return None

    pdf = get_latest_pdf()
    if not pdf:
        print("❌ Žádné PDF v _outputs/digital_products/")
        return None

    meta = get_product_meta()
    title = meta.get("title", "Digital Product by Dark Factory")
    description = meta.get("description", "Instant-download digital product.")

    print(f"📦 PDF: {pdf.name} ({pdf.stat().st_size // 1024}KB)")
    print(f"📝 Název: {title}")

    store_id = get_store_id()

    # Zkontroluj existující produkty — nepřidávej duplicity
    existing = list_products(store_id)
    for p in existing:
        if p["attributes"]["name"] == title:
            url = p["attributes"].get("buy_now_url", "")
            print(f"ℹ️  Produkt '{title}' již existuje: {url}")
            return url

    print(f"\n➕ Vytvářím produkt na Lemon Squeezy...")
    product_id = create_product(store_id, title, description, price_cents)
    print(f"  ✅ Product ID: {product_id}")

    variant_id = create_variant(product_id, price_cents)
    print(f"  ✅ Varianta vytvořena (id: {variant_id})")

    upload_pdf_to_variant(variant_id, pdf)
    print(f"  ✅ PDF soubor nahrán")

    url = get_product_url(product_id)
    print(f"\n🎉 LIVE: {url}")

    # Log
    log = OUT_DIR / "published_products.txt"
    with open(log, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} | LemonSqueezy | {url} | {pdf.name}\n")

    # Ulož product_id do .env pro příští update
    env = (BASE_DIR / "_config" / ".env").read_text()
    if "LEMONSQUEEZY_PRODUCT_ID" not in env:
        with open(BASE_DIR / "_config" / ".env", "a") as f:
            f.write(f"\nLEMONSQUEEZY_PRODUCT_ID={product_id}\n")

    return url


if __name__ == "__main__":
    result = publish()
    if result:
        print(f"\nProdejní link: {result}")
    else:
        print("\n⚠️  Zkontroluj LEMONSQUEEZY_API_KEY v _config/.env")

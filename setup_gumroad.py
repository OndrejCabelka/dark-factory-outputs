"""
DARK FACTORY — Gumroad One-Time Setup
Creates the initial product on Gumroad via browser automation,
extracts the product ID, and saves it to _config/.env.
Run ONCE manually. After that, publish_gumroad.py uses the API.
"""
import os, re, time
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / "_config" / ".env"
load_dotenv(env_path)

PDF_PATH = str(Path(__file__).parent / "_outputs" / "digital_products" / "Top5_Digital_Niches_2026.pdf")
TITLE    = "Top 5 Trending Digital Product Niches 2026 — Data-Backed Market Report"
PRICE    = "17"
DESCRIPTION = """You're sitting on the most valuable thing in digital product selling: knowing where to play before everyone else shows up.

This data-backed report ranks the Top 5 trending digital product niches for 2026 using live signals from Gumroad Discover, Etsy bestseller data, PromptBase, and eRank.

✅ Data-backed niche rankings — live Gumroad, Etsy & PromptBase data
✅ Real revenue benchmarks — documented sales figures from active sellers
✅ Specific opportunity edges — exact positioning to beat saturated competitors
✅ Platform-fit strategy — Gumroad vs Etsy vs Payhip, matched to your product
✅ Instant download, actionable in under an hour"""


def create_product_via_browser():
    from playwright.sync_api import sync_playwright

    email = os.getenv("GUMROAD_EMAIL", "").strip()
    password = os.getenv("GUMROAD_PASSWORD", "").strip()

    if not email or not password:
        print("❌ Nastav GUMROAD_EMAIL a GUMROAD_PASSWORD v _config/.env")
        print("   Nebo vytvoř produkt manuálně na gumroad.com a ulož ID do .env jako GUMROAD_PRODUCT_ID")
        return None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()

        print("🌐 Otevírám Gumroad...")
        page.goto("https://app.gumroad.com/login")
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_timeout(3000)

        print("➕ Vytvářím nový produkt...")
        page.goto("https://app.gumroad.com/products/new")
        page.wait_for_timeout(2000)

        # Fill in name
        try:
            page.fill('input[placeholder*="name"], input[name*="name"], #product-name', TITLE, timeout=5000)
        except:
            page.keyboard.type(TITLE)

        # Set price
        try:
            price_input = page.locator('input[name*="price"], input[placeholder*="price"], #price').first
            price_input.fill(PRICE)
        except Exception as e:
            print(f"  ⚠ Cena: {e}")

        page.wait_for_timeout(1000)

        # Upload file
        try:
            with page.expect_file_chooser() as fc:
                page.click('input[type="file"], [data-testid*="upload"], button:has-text("Add a file")', timeout=5000)
            fc.value.set_files(PDF_PATH)
            print("  📎 Soubor nahrán")
            page.wait_for_timeout(5000)
        except Exception as e:
            print(f"  ⚠ Upload: {e}")

        # Save/create
        try:
            page.click('button:has-text("Create"), button:has-text("Save"), button[type="submit"]', timeout=5000)
            page.wait_for_timeout(4000)
        except Exception as e:
            print(f"  ⚠ Save: {e}")

        # Extract product ID from URL
        url = page.url
        print(f"📍 URL: {url}")
        product_id = None

        match = re.search(r'/products/([a-zA-Z0-9_-]+)', url)
        if match:
            product_id = match.group(1)

        if not product_id:
            # Try from page content
            try:
                link = page.locator('a[href*="/l/"]').first.get_attribute("href")
                m = re.search(r'/l/([a-zA-Z0-9_-]+)', link or "")
                if m:
                    product_id = m.group(1)
            except:
                pass

        page.screenshot(path="/tmp/gumroad_setup.png")
        browser.close()
        return product_id


def save_product_id(product_id: str):
    """Append GUMROAD_PRODUCT_ID to .env file."""
    env_content = env_path.read_text()
    if "GUMROAD_PRODUCT_ID" in env_content:
        # Update existing
        lines = env_content.splitlines()
        lines = [f"GUMROAD_PRODUCT_ID={product_id}" if l.startswith("GUMROAD_PRODUCT_ID") else l for l in lines]
        env_path.write_text("\n".join(lines) + "\n")
    else:
        with open(env_path, "a") as f:
            f.write(f"\nGUMROAD_PRODUCT_ID={product_id}\n")
    print(f"✅ GUMROAD_PRODUCT_ID={product_id} uloženo do _config/.env")


if __name__ == "__main__":
    existing_id = os.getenv("GUMROAD_PRODUCT_ID", "").strip()
    if existing_id:
        print(f"✅ Produkt již existuje: GUMROAD_PRODUCT_ID={existing_id}")
        print("   Spusť publish_gumroad.py pro aktualizaci a publikování.")
    else:
        print("🔧 One-time Gumroad setup...")
        pid = create_product_via_browser()
        if pid:
            save_product_id(pid)
            print(f"\n🎉 Setup hotov! Product ID: {pid}")
            print("   Teď spusť: python3 publish_gumroad.py")
        else:
            print("\n⚠️  Nepodařilo se automaticky. Udělej to ručně:")
            print("   1. Jdi na gumroad.com → New Product")
            print("   2. Vytvoř produkt, nahraj PDF")
            print("   3. Z URL zkopíruj ID (např. /products/abcd1234)")
            print("   4. Přidej do _config/.env: GUMROAD_PRODUCT_ID=abcd1234")

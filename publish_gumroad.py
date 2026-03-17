"""
DARK FACTORY — Gumroad Auto-Publisher
Automaticky publikuje PDF produkt na Gumroad.
Spustí se po každém běhu Factory B.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / "_config" / ".env")

PDF_PATH = str(Path(__file__).parent / "_outputs" / "digital_products" / "Top5_Digital_Niches_2026.pdf")

TITLE = "Top 5 Trending Digital Product Niches 2026 — Data-Backed Market Report"
PRICE = "17"
DESCRIPTION = """You're sitting on the most valuable thing in digital product selling: knowing where to play before everyone else shows up.

This data-backed report ranks the Top 5 trending digital product niches for 2026 using live signals from Gumroad Discover, Etsy bestseller data, PromptBase, and eRank. Not opinions. Not predictions. What's actually selling right now.

For each niche you get: demand level, competition assessment, average price point, best platform, a specific opportunity edge to beat existing sellers, and real examples of products already making money.

✅ Data-backed niche rankings — live Gumroad, Etsy & PromptBase data
✅ Real revenue benchmarks — documented sales figures from active sellers  
✅ Specific opportunity edges — exact positioning to beat saturated competitors
✅ Platform-fit strategy — Gumroad vs Etsy vs Payhip, matched to your product
✅ BONUS: Freelancer OS Notion Template (Client CRM + Project Tracker + Invoice Tracker)
✅ Instant download, actionable in under an hour

No filler. Download instantly. Start building today."""


def publish_via_api(access_token: str):
    """Publish using Gumroad API v2."""
    import requests

    print("📡 Publishing via Gumroad API...")

    r = requests.post(
        "https://api.gumroad.com/v2/products",
        data={
            "access_token": access_token,
            "name": TITLE,
            "price": int(float(PRICE) * 100),  # cents
            "description": DESCRIPTION,
            "published": "true",
        }
    )
    data = r.json()
    if not data.get("success"):
        print(f"❌ API error: {data}")
        return None

    product_id  = data["product"]["id"]
    product_url = data["product"]["short_url"]
    print(f"✅ Product created: {product_url}")

    # Upload PDF file
    if os.path.exists(PDF_PATH):
        with open(PDF_PATH, "rb") as f:
            r2 = requests.put(
                f"https://api.gumroad.com/v2/products/{product_id}/files",
                data={"access_token": access_token},
                files={"file": ("Top5_Digital_Niches_2026.pdf", f, "application/pdf")}
            )
            if r2.status_code == 200:
                print("✅ PDF uploaded")
            else:
                print(f"⚠️  File upload status: {r2.status_code} — {r2.text[:200]}")
    else:
        print(f"⚠️  PDF not found at {PDF_PATH}")

    return product_url


def publish_via_browser():
    """Fully automatic: Playwright fills and submits Gumroad form."""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    print("🌐 Starting browser automation (Gumroad)...")

    with sync_playwright() as p:
        # Use non-persistent context with Chromium — avoids Chrome profile lock
        browser = p.chromium.launch(headless=False, args=["--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        # Load saved cookies if they exist (from previous login)
        cookie_file = Path(__file__).parent / "_config" / "gumroad_cookies.json"
        if cookie_file.exists():
            import json
            with open(cookie_file) as f:
                cookies = json.load(f)
            context.add_cookies(cookies)
            print("  ✅ Loaded saved cookies")

        page = context.new_page()

        # Check if logged in
        print("  → Checking login status...")
        page.goto("https://app.gumroad.com/dashboard", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        current_url = page.url
        if "login" in current_url or "sign_in" in current_url:
            print("  ⚠️  Not logged in — navigating to login page...")
            print("  ℹ️  Nelze se automaticky přihlásit. Použij API token.")
            print("  → Jak získat token: gumroad.com/settings/advanced → Applications → Access Token")
            browser.close()
            return None

        print("  ✅ Logged in to Gumroad")

        # Save cookies for next time
        cookies = context.cookies()
        import json
        with open(cookie_file, "w") as f:
            json.dump(cookies, f)
        print("  ✅ Cookies saved for next run")

        # Navigate to new product
        print("  → Navigating to new product form...")
        page.goto("https://app.gumroad.com/products/new", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # Take screenshot to see what we're working with
        screenshot_path = str(Path(__file__).parent / "_outputs" / "gumroad_form.png")
        page.screenshot(path=screenshot_path)
        print(f"  📸 Screenshot saved: {screenshot_path}")

        # Try to select "Digital product" type if shown
        for selector in ['text=Digital product', '[data-testid="digital"]', 'input[value="digital"]']:
            try:
                page.click(selector, timeout=2000)
                time.sleep(1)
                print("  ✅ Selected: Digital product")
                break
            except Exception:
                pass

        # Fill product name
        name_selectors = [
            'input[name="name"]',
            'input[placeholder*="Name"]',
            'input[placeholder*="name"]',
            'input[id*="name"]',
            '#name',
        ]
        filled_name = False
        for sel in name_selectors:
            try:
                page.fill(sel, TITLE, timeout=2000)
                print(f"  ✅ Name filled ({sel})")
                filled_name = True
                break
            except Exception:
                pass
        if not filled_name:
            print("  ⚠️  Could not fill name field")

        # Fill price
        price_selectors = [
            'input[name="price"]',
            'input[placeholder*="price"]',
            'input[placeholder*="Price"]',
            'input[id*="price"]',
        ]
        for sel in price_selectors:
            try:
                page.fill(sel, PRICE, timeout=2000)
                print(f"  ✅ Price filled ({sel})")
                break
            except Exception:
                pass

        # Fill description
        desc_selectors = [
            'textarea[name="description"]',
            'div[contenteditable="true"]',
            '.ProseMirror',
            'div[data-placeholder]',
        ]
        for sel in desc_selectors:
            try:
                el = page.locator(sel).first
                el.click(timeout=2000)
                el.fill(DESCRIPTION)
                print(f"  ✅ Description filled")
                break
            except Exception:
                pass

        # Upload PDF
        if os.path.exists(PDF_PATH):
            try:
                file_input = page.locator('input[type="file"]').first
                file_input.set_input_files(PDF_PATH)
                print("  ✅ PDF uploaded, waiting for processing...")
                time.sleep(5)
            except Exception as e:
                print(f"  ⚠️  File upload: {e}")
        else:
            print(f"  ⚠️  PDF not found: {PDF_PATH}")

        # Take screenshot before publishing
        page.screenshot(path=screenshot_path)
        print(f"  📸 Pre-publish screenshot: {screenshot_path}")

        # Click Publish / Save
        publish_selectors = [
            'button:has-text("Publish")',
            'button:has-text("Save and continue")',
            'button:has-text("Save")',
            'input[type="submit"]',
            '[data-testid="publish-button"]',
            'button[type="submit"]',
        ]
        published = False
        for sel in publish_selectors:
            try:
                page.click(sel, timeout=3000)
                print(f"  ✅ Clicked publish ({sel})")
                published = True
                time.sleep(4)
                break
            except Exception:
                pass

        if not published:
            print("  ⚠️  Nemohl jsem najít tlačítko Publish. Zkontroluj screenshot.")

        # Get the product URL from the page
        page.screenshot(path=screenshot_path.replace(".png", "_after.png"))

        final_url = page.url
        print(f"  📍 Final URL: {final_url}")

        # Try to extract product URL from page content
        try:
            product_link = page.locator('a[href*="gumroad.com/l/"]').first.get_attribute("href", timeout=3000)
            if product_link:
                final_url = product_link
        except Exception:
            pass

        browser.close()
        return final_url


def main():
    token = os.getenv("GUMROAD_ACCESS_TOKEN", "").strip()

    if token and token not in ("", "YOUR_TOKEN_HERE"):
        url = publish_via_api(token)
    else:
        print("ℹ️  Gumroad API token nenastaven — spouštím browser automation.")
        url = publish_via_browser()

    if url:
        print(f"\n🎉 PRODUKT LIVE: {url}")
        out = Path(__file__).parent / "_outputs" / "digital_products" / "published_products.txt"
        with open(out, "a") as f:
            import datetime
            f.write(f"{datetime.datetime.now().isoformat()} — {url}\n")
        print(f"✅ URL uložena do: {out}")
    else:
        print("\n❌ Publikování selhalo.")
        print("👉 Získej API token: gumroad.com/settings/advanced → Applications → Generate Token")
        print("   Přidej do .env: GUMROAD_ACCESS_TOKEN=tvuj_token")


if __name__ == "__main__":
    main()

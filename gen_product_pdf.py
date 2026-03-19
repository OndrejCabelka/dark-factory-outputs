"""
Standalone skript: vygeneruje 50 Etsy prompts přes Claude API a uloží jako PDF.
Spuštění: cd ~/Desktop/DarkFactory && source .venv/bin/activate && python3 gen_product_pdf.py
"""
import os, re, sys
from pathlib import Path
from datetime import datetime

# Load .env ručně
for line in Path("_config/.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

import anthropic

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_KEY:
    print("❌ ANTHROPIC_API_KEY chybí"); sys.exit(1)

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
print("🤖 Generuji 50 Etsy prompts (max_tokens=8000)...", flush=True)

PROMPT = """Create a complete digital product: "The Etsy Seller's AI Prompt Pack"

Write exactly 50 ready-to-use ChatGPT prompts for Etsy sellers.
Each prompt must be copy-paste ready — specific, actionable, with [PLACEHOLDERS] for customization.

Format EVERY prompt exactly like this:
**Prompt #X: [Title]**
```
Act as an expert Etsy SEO specialist. I sell [YOUR PRODUCT TYPE] on Etsy targeting [YOUR TARGET CUSTOMER]. 
[Continue with the full specific prompt — 3-5 sentences minimum. Be very specific about what ChatGPT should output.]
```
*When to use: [1 sentence explaining the exact scenario]*

---

CATEGORIES:

## Category 1: Listing Titles & SEO (Prompts 1-9)
Prompts for: writing keyword-rich titles, generating all 13 tags, analyzing competitor titles, refreshing underperforming listings, A/B testing titles, seasonal title optimization

## Category 2: Product Descriptions (Prompts 10-18)  
Prompts for: physical product descriptions, digital download descriptions, feature-to-benefit conversion, gift-angle rewrite, weak listing diagnosis, scarcity/urgency copy, international buyer versions

## Category 3: Shop Copy & Branding (Prompts 19-25)
Prompts for: About section, shop announcement, brand voice guide, policies (shipping/returns), shop FAQ, welcome message

## Category 4: Social Media & Pinterest (Prompts 26-34)
Prompts for: Instagram captions (3 variations), Pinterest descriptions, content calendar, TikTok hooks, hashtag strategy, Pinterest board descriptions

## Category 5: Customer Emails & Messages (Prompts 35-42)
Prompts for: order confirmation, shipping notification, follow-up review request, difficult customer response, refund policy explanation, repeat customer thank you, abandoned cart (if applicable)

## Category 6: Strategy & Growth (Prompts 43-50)
Prompts for: niche validation research, pricing strategy analysis, new product ideation, seasonal launch planning, competitor gap analysis, bundle strategy, holiday campaign planning

Write ALL 50 prompts in full. No placeholders like "continue here". Every prompt must work immediately."""

msg = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8000,
    messages=[{"role": "user", "content": PROMPT}]
)

content = msg.content[0].text
n_prompts = len(re.findall(r'\*\*Prompt #\d+', content))
print(f"✅ Generated {len(content):,} chars | {n_prompts} prompts found", flush=True)

# Ulož MD
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
out_dir = Path("_outputs/digital_products")
md_path = out_dir / f"product_content_{ts}.md"
full_md = f"# The Etsy Seller's AI Prompt Pack\n50 ChatGPT Prompts to Write Listings & Grow Sales\n\n---\n\n{content}"
md_path.write_text(full_md, encoding="utf-8")
print(f"✅ MD: {md_path.name} ({md_path.stat().st_size//1024} KB)", flush=True)

# Generuj PDF
def _clean(s):
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
    s = re.sub(r"\*(.*?)\*", r"\1", s)
    s = re.sub(r"```.*?```", "", s, flags=re.DOTALL)  # odstraň code blocks
    return s.encode("latin-1", errors="replace").decode("latin-1")

try:
    from fpdf import FPDF
    title_safe = _clean("The Etsy Seller's AI Prompt Pack")

    class P(FPDF):
        def header(self):
            self.set_font("Helvetica","B",9); self.set_text_color(120,120,120)
            self.cell(0,7,title_safe[:70],align="R"); self.ln(8)
        def footer(self):
            self.set_y(-13); self.set_font("Helvetica","I",8); self.set_text_color(150,150,150)
            self.cell(0,8,f"Page {self.page_no()}",align="C")

    pdf = P(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15,15,15); pdf.set_auto_page_break(True,20)
    pdf.add_page()

    # Cover
    pdf.ln(20); pdf.set_font("Helvetica","B",20); pdf.set_text_color(20,20,20)
    pdf.multi_cell(0,11,_clean("The Etsy Seller's AI Prompt Pack"),align="C")
    pdf.ln(5); pdf.set_font("Helvetica","",13); pdf.set_text_color(80,80,80)
    pdf.multi_cell(0,8,"50 ChatGPT Prompts to Write Listings & Grow Sales",align="C")
    pdf.ln(8); pdf.set_font("Helvetica","",10); pdf.set_text_color(120,120,120)
    pdf.cell(0,7,f"Dark Factory | {datetime.now().strftime('%B %Y')}",align="C")
    pdf.add_page()

    in_code_block = False
    for raw in full_md.split("\n"):
        s = raw.rstrip()
        try:
            if s.strip().startswith("```"):
                in_code_block = not in_code_block
                if in_code_block:
                    pdf.ln(2); pdf.set_fill_color(245,245,245)
                else:
                    pdf.ln(2)
                continue
            if in_code_block:
                pdf.set_font("Courier","",9); pdf.set_text_color(40,40,40)
                clean_s = s.encode("latin-1",errors="replace").decode("latin-1")
                if clean_s.strip():
                    pdf.multi_cell(0,5,clean_s,fill=True)
                continue
            if s.startswith("# "):
                pdf.ln(4); pdf.set_font("Helvetica","B",15); pdf.set_text_color(20,20,20)
                pdf.multi_cell(0,8,_clean(s[2:]))
            elif s.startswith("## "):
                pdf.ln(5); pdf.set_font("Helvetica","B",13); pdf.set_text_color(40,40,40)
                pdf.multi_cell(0,7,_clean(s[3:]))
                pdf.ln(1)
            elif s.startswith("### "):
                pdf.ln(3); pdf.set_font("Helvetica","B",11); pdf.set_text_color(60,60,60)
                pdf.multi_cell(0,6,_clean(s[4:]))
            elif s.startswith("---"):
                pdf.ln(3); pdf.set_draw_color(200,200,200)
                pdf.line(15,pdf.get_y(),195,pdf.get_y()); pdf.ln(3)
            elif s.strip() == "":
                pdf.ln(2)
            elif s.lstrip().startswith("- ") or s.lstrip().startswith("* "):
                pdf.set_font("Helvetica","",10); pdf.set_text_color(50,50,50)
                pdf.multi_cell(0,5.5,"  - "+_clean(s.lstrip()[2:]))
            elif s.startswith("*When to use:") or s.startswith("*Kdy"):
                pdf.set_font("Helvetica","I",9); pdf.set_text_color(100,100,100)
                pdf.multi_cell(0,5,_clean(s.strip("*")))
            else:
                pdf.set_font("Helvetica","",10); pdf.set_text_color(50,50,50)
                pdf.multi_cell(0,5.5,_clean(s))
        except Exception:
            pass

    pdf_path = out_dir / f"product_{ts}.pdf"
    pdf.output(str(pdf_path))
    size_kb = pdf_path.stat().st_size // 1024
    print(f"✅ PDF: {pdf_path.name} ({size_kb} KB)", flush=True)
    print(f"\n🎯 PRODUKT READY: {pdf_path}", flush=True)
    print(f"   Nastav GUMROAD_PRODUCT_ID a spusť: python3 publish_gumroad.py", flush=True)

except Exception as e:
    print(f"⚠️  PDF error: {e}", flush=True)

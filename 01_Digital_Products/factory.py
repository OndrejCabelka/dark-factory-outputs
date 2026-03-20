"""
DARK FACTORY — Factory B: Digital Products
CrewAI crew: výzkum trhu → vytvoří produkt → napíše listing → vygeneruje PDF

Výstupy (_outputs/digital_products/):
  digital_product_{ts}.md   — marketing copy (listing)
  product_content_{ts}.md   — obsah produktu (50 prompts apod.)
  product_{ts}.pdf          — PDF produktu → uploaduje se na Gumroad
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / "_config" / ".env"
load_dotenv(dotenv_path=env_path)

from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

OUTPUT_DIR = Path(__file__).parent.parent / "_outputs" / "digital_products"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── PDF GENERATOR ─────────────────────────────────────────────────────────────

def _clean(s: str) -> str:
    """Markdown → plain text, latin-1 safe pro fpdf2."""
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
    s = re.sub(r"\*(.*?)\*", r"\1", s)
    s = re.sub(r"__(.*?)__", r"\1", s)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def generate_pdf(title: str, content: str, output_path: Path) -> Path:
    from fpdf import FPDF
    title_safe = _clean(title)

    class P(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(120, 120, 120)
            self.cell(0, 7, title_safe[:70], align="R")
            self.ln(8)
        def footer(self):
            self.set_y(-13)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8, f"Page {self.page_no()}", align="C")

    pdf = P(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(True, 20)
    pdf.add_page()

    # Cover page
    pdf.ln(20)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(0, 10, title_safe, align="C")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 7, _clean(f"Dark Factory | {datetime.now().strftime('%B %Y')}"), align="C")
    pdf.add_page()

    for raw in content.split("\n"):
        s = raw.rstrip()
        try:
            if s.startswith("# "):
                pdf.ln(4); pdf.set_font("Helvetica", "B", 15); pdf.set_text_color(20, 20, 20)
                pdf.multi_cell(0, 8, _clean(s[2:]))
            elif s.startswith("## "):
                pdf.ln(3); pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(40, 40, 40)
                pdf.multi_cell(0, 7, _clean(s[3:]))
            elif s.startswith("### "):
                pdf.ln(2); pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(60, 60, 60)
                pdf.multi_cell(0, 6, _clean(s[4:]))
            elif s.startswith("---"):
                pdf.ln(3); pdf.set_draw_color(200, 200, 200)
                pdf.line(15, pdf.get_y(), 195, pdf.get_y()); pdf.ln(3)
            elif s.strip() == "":
                pdf.ln(2)
            elif s.lstrip().startswith("- ") or s.lstrip().startswith("* "):
                pdf.set_font("Helvetica", "", 10); pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 5.5, "  - " + _clean(s.lstrip()[2:]))
            elif re.match(r"^\s*\d+\.", s):
                pdf.set_font("Helvetica", "", 10); pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 5.5, "  " + _clean(s.strip()))
            else:
                pdf.set_font("Helvetica", "", 10); pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 5.5, _clean(s))
        except Exception:
            pass  # přeskoč problematický řádek

    pdf.output(str(output_path))
    return output_path


# ── AGENTS + TASKS ────────────────────────────────────────────────────────────

def build_crew():
    search_tool = SerperDevTool()
    scrape_tool = ScrapeWebsiteTool()

    market_researcher = Agent(
        role="Digital Product Market Researcher",
        goal="Find top 5 trending digital product niches with low competition and high demand on Gumroad/Etsy.",
        backstory="Sharp market analyst who spots trends early. Data-backed, zero fluff.",
        tools=[search_tool, scrape_tool],
        verbose=True, allow_delegation=False,
        max_iter=3,
        llm="anthropic/claude-haiku-4-5-20251001",
    )

    product_creator = Agent(
        role="Digital Product Creator",
        goal="Create a complete, immediately publishable digital product — full content, zero placeholders.",
        backstory="Prolific creator who has sold hundreds of products on Gumroad. Delivers actual content.",
        verbose=True, allow_delegation=False,
        max_iter=2,
        llm="anthropic/claude-sonnet-4-6",  # Sonnet pro kvalitu produktu
    )

    copywriter = Agent(
        role="Marketing & Sales Copywriter",
        goal="Write a compelling Gumroad/Etsy listing that converts: title, description, bullets, tags, price.",
        backstory="Direct-response copywriter specialising in digital products. Benefit-driven, specific.",
        verbose=True, allow_delegation=False,
        max_iter=2,
        llm="anthropic/claude-haiku-4-5-20251001",
    )

    research_task = Task(
        description=(
            "Search top 5 trending digital product niches now. "
            "Check gumroad.com/discover, Etsy digital downloads, AI prompt marketplaces. "
            "For each: niche name, demand, competition, avg price, why trending, example products. "
            "Rank #1–5, #1 = best opportunity. Clean markdown output."
        ),
        expected_output="Ranked markdown list of 5 niches with full analysis.",
        agent=market_researcher,
    )

    creation_task = Task(
        description=(
            "Take #1 niche from research. Create a COMPLETE digital product — full content only, no outlines. "
            "Prompt pack: write 25-30 ready-to-use prompts with usage instructions. "
            "Ebook: write all chapters, min 2000 words total. "
            "Templates: create 5-10 complete, usable templates. "
            "Zero placeholders. Immediately publishable."
        ),
        expected_output="Complete publish-ready product content in markdown. Full text, no outlines.",
        agent=product_creator,
        context=[research_task],
    )

    marketing_task = Task(
        description=(
            "Write full Gumroad/Etsy listing for the product. Deliver exactly under these headings: "
            "TITLE (max 80 chars, punchy, keyword-rich) | "
            "DESCRIPTION (500 words, benefit-driven) | "
            "BULLET POINTS (6 key benefits) | "
            "TAGS (15 tags comma-separated) | "
            "PRICING RECOMMENDATION (price + brief reasoning)"
        ),
        expected_output="Complete listing under 5 clear headings: TITLE, DESCRIPTION, BULLET POINTS, TAGS, PRICING.",
        agent=copywriter,
        context=[research_task, creation_task],
    )

    crew = Crew(
        agents=[market_researcher, product_creator, copywriter],
        tasks=[research_task, creation_task, marketing_task],
        process=Process.sequential,
        verbose=True,
        max_rpm=8,
    )
    return crew, creation_task, marketing_task


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("\n🏭 FACTORY B — DIGITAL PRODUCTS — STARTING\n")
    crew, creation_task, marketing_task = build_crew()
    crew.kickoff()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Zachyť výstupy jednotlivých tasků
    product_content = getattr(getattr(creation_task, "output", None), "raw", "") or ""
    marketing_copy  = getattr(getattr(marketing_task, "output", None), "raw", "") or ""

    # Extrahuj title z marketing copy
    product_title = "Digital Product"
    lines = marketing_copy.split("\n")
    in_title_section = False
    for line in lines:
        stripped = line.strip()
        if re.search(r"^#+\s*TITLE", stripped, re.I) or stripped.upper() == "TITLE":
            in_title_section = True
            continue
        if in_title_section and stripped and not stripped.startswith("#"):
            candidate = stripped.lstrip("*_").rstrip("*_").strip()
            if 5 < len(candidate) < 120:
                product_title = candidate
                break
        if in_title_section and stripped.startswith("#"):
            break  # další sekce

    # Ulož marketing copy
    mkt_file = OUTPUT_DIR / f"digital_product_{ts}.md"
    with open(mkt_file, "w", encoding="utf-8") as f:
        f.write(f"# Digital Product Output\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n")
        f.write(marketing_copy)
    print(f"✅ Marketing copy: {mkt_file.name}")

    # Ulož obsah produktu + vygeneruj PDF
    if product_content and len(product_content) > 200:
        content_file = OUTPUT_DIR / f"product_content_{ts}.md"
        with open(content_file, "w", encoding="utf-8") as f:
            f.write(f"# {product_title}\n\n{product_content}")
        print(f"✅ Product content: {content_file.name}")

        try:
            pdf_file = OUTPUT_DIR / f"product_{ts}.pdf"
            generate_pdf(product_title, product_content, pdf_file)
            size_kb = pdf_file.stat().st_size // 1024
            print(f"✅ PDF: {pdf_file.name} ({size_kb} KB)")
        except Exception as e:
            print(f"⚠️  PDF failed: {e}")
    else:
        print("⚠️  Product content prázdný — PDF přeskočen. Zkontroluj CrewAI task output.")

    return marketing_copy


if __name__ == "__main__":
    main()

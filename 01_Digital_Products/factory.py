"""
DARK FACTORY — Factory B: Digital Products
CrewAI crew that researches, creates and markets digital products.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load env
env_path = Path(__file__).parent.parent / "_config" / ".env"
load_dotenv(dotenv_path=env_path)

from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

OUTPUT_DIR = Path(__file__).parent.parent / "_outputs" / "digital_products"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_crew():
    search_tool = SerperDevTool()
    scrape_tool = ScrapeWebsiteTool()

    # ── AGENTS ──────────────────────────────────────────────────────────────

    market_researcher = Agent(
        role="Digital Product Market Researcher",
        goal=(
            "Find the top 5 trending digital product niches right now with low competition "
            "and high demand. Focus on Gumroad bestsellers, Etsy digital downloads, "
            "and AI prompt marketplaces."
        ),
        backstory=(
            "You are a sharp market analyst who lives on Gumroad, Etsy, and Product Hunt. "
            "You spot trends before they peak and know exactly what digital buyers want to pay for. "
            "You produce ranked, data-backed niche reports with zero fluff."
        ),
        tools=[search_tool, scrape_tool],
        verbose=True,
        allow_delegation=False,
        llm="anthropic/claude-sonnet-4-6",
    )

    product_creator = Agent(
        role="Digital Product Creator",
        goal=(
            "Create a complete, high-value digital product for the best niche identified. "
            "The product must be ready to publish — full content, not an outline."
        ),
        backstory=(
            "You are a prolific digital creator who has sold hundreds of products on Gumroad. "
            "You write ebooks, prompt packs, and template sets that people actually buy and use. "
            "You deliver complete, polished content — never placeholders."
        ),
        verbose=True,
        allow_delegation=False,
        llm="anthropic/claude-sonnet-4-6",
    )

    copywriter = Agent(
        role="Marketing & Sales Copywriter",
        goal=(
            "Write a compelling product listing that converts browsers into buyers. "
            "Deliver: title, 500-word description, bullet points, tags list, and pricing recommendation."
        ),
        backstory=(
            "You are a direct-response copywriter who specialises in digital product listings. "
            "You know what sells on Gumroad and Etsy. Your copy is benefit-driven, specific, "
            "and built around buyer psychology. Every word earns its place."
        ),
        verbose=True,
        allow_delegation=False,
        llm="anthropic/claude-sonnet-4-6",
    )

    # ── TASKS ────────────────────────────────────────────────────────────────

    research_task = Task(
        description=(
            "Search for the top 5 trending digital product niches right now. "
            "Check Gumroad (gumroad.com/discover), Etsy digital downloads bestsellers, "
            "and AI prompt marketplaces. "
            "For each niche provide: niche name, estimated demand level, competition level, "
            "average price point, why it's trending now, example products already selling well. "
            "Rank them #1–5 with #1 being the best opportunity. "
            "Output a clean markdown report."
        ),
        expected_output=(
            "Ranked markdown list of 5 digital product niches with full analysis for each. "
            "Must include: rank, niche name, demand, competition, avg price, trend reason, examples."
        ),
        agent=market_researcher,
    )

    creation_task = Task(
        description=(
            "Take the #1 ranked niche from the research report and create a COMPLETE digital product for it. "
            "Do NOT write an outline or a plan — write the actual full content. "
            "If it's a prompt pack: write 20–30 ready-to-use prompts with instructions. "
            "If it's an ebook: write all chapters with full text (min 2000 words total). "
            "If it's a template set: create 5–10 complete, usable templates. "
            "The product must be immediately publishable — zero placeholders allowed."
        ),
        expected_output=(
            "Complete, publish-ready digital product content in markdown format. "
            "Full text, no outlines, no 'add content here' placeholders."
        ),
        agent=product_creator,
        context=[research_task],
    )

    marketing_task = Task(
        description=(
            "Write the full Gumroad/Etsy product listing for the product just created. "
            "Deliver exactly: "
            "1) TITLE — one punchy, keyword-rich title (max 80 chars) "
            "2) DESCRIPTION — 500-word sales copy, benefit-driven, no fluff "
            "3) BULLET POINTS — 6 key benefits as short bullets "
            "4) TAGS — 15 relevant tags separated by commas "
            "5) PRICING RECOMMENDATION — suggested price with brief reasoning "
            "Format everything clearly under these 5 headings."
        ),
        expected_output=(
            "Complete Gumroad listing under 5 clear headings: "
            "TITLE, DESCRIPTION, BULLET POINTS, TAGS, PRICING RECOMMENDATION."
        ),
        agent=copywriter,
        context=[research_task, creation_task],
    )

    # ── CREW ─────────────────────────────────────────────────────────────────

    crew = Crew(
        agents=[market_researcher, product_creator, copywriter],
        tasks=[research_task, creation_task, marketing_task],
        process=Process.sequential,
        verbose=True,
    )

    return crew


def main():
    print("\n🏭 FACTORY B — DIGITAL PRODUCTS — STARTING\n")
    crew = build_crew()
    result = crew.kickoff()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"digital_product_{timestamp}.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Digital Product Output\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write(str(result))

    print(f"\n✅ Output saved to: {output_file}")
    return str(result)


if __name__ == "__main__":
    main()

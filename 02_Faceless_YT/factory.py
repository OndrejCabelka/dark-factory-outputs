"""
DARK FACTORY — Factory C: Faceless YouTube
CrewAI crew that finds trending niches, writes full video scripts and complete metadata.
"""

import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / "_config" / ".env"
load_dotenv(dotenv_path=env_path)

from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool

OUTPUT_DIR = Path(__file__).parent.parent / "_outputs" / "youtube"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_crew():
    search_tool = SerperDevTool()

    # ── AGENTS ──────────────────────────────────────────────────────────────

    trend_analyst = Agent(
        role="YouTube Trend & Niche Analyst",
        goal=(
            "Find the top 3 video topics right now with high CPM potential and relatively low competition. "
            "Prioritise niches: finance, tech, business, AI, health, self-improvement. "
            "For each topic: search volume signals, competitor view counts, CPM estimate, competition level."
        ),
        backstory=(
            "You are a data-obsessed YouTube strategist who has analysed thousands of channels. "
            "You know which niches pay $15+ CPM and which are saturated. "
            "You back every recommendation with real signals — not guesses. "
            "You find the gap between high demand and low supply."
        ),
        tools=[search_tool],
        verbose=True,
        allow_delegation=False,
        llm="anthropic/claude-sonnet-4-6",
    )

    script_writer = Agent(
        role="Viral YouTube Script Writer",
        goal=(
            "Write a complete 8-12 minute video script for the best topic found. "
            "Every sentence must earn its place. Hook must stop the scroll in 3 seconds. "
            "Structure: Hook → Intro → 5-8 main sections → CTA + Outro."
        ),
        backstory=(
            "You are a YouTube script writer with 50M+ views across faceless channels. "
            "You know that the hook is everything. You write like you talk — "
            "conversational, direct, no filler, no 'in this video I will show you'. "
            "You use pattern interrupts, open loops, and curiosity gaps naturally. "
            "Your scripts make editors' jobs easy with clear section labels."
        ),
        verbose=True,
        allow_delegation=False,
        llm="anthropic/claude-sonnet-4-6",
    )

    seo_specialist = Agent(
        role="YouTube SEO & Metadata Expert",
        goal=(
            "Maximise discoverability with a complete upload package: "
            "3 title options, full SEO description (500+ words), 20 tags, "
            "chapter timestamps, thumbnail brief, voiceover tone notes."
        ),
        backstory=(
            "You are a YouTube SEO specialist who has ranked hundreds of videos on page 1. "
            "You know exactly how the algorithm reads titles, descriptions, and tags. "
            "You write descriptions that serve both the algorithm and human readers. "
            "Your thumbnail briefs are specific enough that any designer can execute them immediately."
        ),
        verbose=True,
        allow_delegation=False,
        llm="anthropic/claude-sonnet-4-6",
    )

    # ── TASKS ────────────────────────────────────────────────────────────────

    research_task = Task(
        description=(
            "Search for the top 3 YouTube video opportunities right now. "
            "Use searches like: 'YouTube trending topics finance 2025', "
            "'high CPM YouTube niches', 'low competition YouTube topics tech', "
            "'viral YouTube video ideas business'. "
            "For each of the 3 topics provide: "
            "TOPIC NAME | NICHE | WHY TRENDING | CPM ESTIMATE ($) | COMPETITION (Low/Med/High) "
            "| EXAMPLE COMPETING VIDEOS WITH VIEW COUNTS | UNIQUE ANGLE WE CAN TAKE. "
            "Rank them #1–3. #1 = best opportunity right now."
        ),
        expected_output=(
            "Ranked analysis of 3 YouTube video opportunities. "
            "Each with: topic, niche, trend reason, CPM estimate, competition level, "
            "competitor examples, unique angle. Clear #1 recommendation."
        ),
        agent=trend_analyst,
    )

    script_task = Task(
        description=(
            "Write a COMPLETE 8-12 minute video script for the #1 ranked topic. "
            "Use this exact structure: "
            "[HOOK — 0:00-0:30] — grab attention immediately, start with the most shocking/interesting fact "
            "[INTRO — 0:30-1:00] — brief setup, promise what viewer will learn "
            "[SECTION 1] through [SECTION 5-8] — main content with smooth transitions "
            "[CTA — near end] — subscribe, like, comment prompt woven in naturally "
            "[OUTRO — last 30 sec] — wrap up, tease next video "
            "Include approximate timestamps for each section. "
            "Write full sentences — not bullet points. This is the actual script the voiceover artist reads. "
            "Target length: 1400-1800 words (8-12 min at average speaking pace)."
        ),
        expected_output=(
            "Complete video script with section labels and timestamps. "
            "Full sentences throughout — no bullet outlines. "
            "1400-1800 words. Hook in first 5 lines must be outstanding."
        ),
        agent=script_writer,
        context=[research_task],
    )

    metadata_task = Task(
        description=(
            "Create the complete YouTube upload package for this video. Deliver exactly: "
            "## TITLE OPTIONS (A/B/C) "
            "Three title variations to A/B test. Each max 60 chars. Include main keyword. "
            "## DESCRIPTION "
            "500+ word SEO-optimised description. First 2 lines must hook viewer before 'Show more'. "
            "Include: what the video covers, 3-5 relevant links as placeholders, timestamps, "
            "subscribe CTA, keywords woven in naturally. "
            "## TAGS "
            "20 tags, mix of broad and specific, comma separated. "
            "## CHAPTER TIMESTAMPS "
            "Full chapter list matching the script sections, in 0:00 format. "
            "## THUMBNAIL BRIEF "
            "Describe the thumbnail image in detail: background colour, main visual element, "
            "text overlay (max 4 words), facial expression if person shown, overall mood. "
            "## VOICEOVER NOTES "
            "Tone, pace, energy level, specific notes for each section."
        ),
        expected_output=(
            "Complete upload package under 6 clear headings: "
            "TITLE OPTIONS, DESCRIPTION, TAGS, CHAPTER TIMESTAMPS, THUMBNAIL BRIEF, VOICEOVER NOTES."
        ),
        agent=seo_specialist,
        context=[research_task, script_task],
    )

    # ── CREW ─────────────────────────────────────────────────────────────────

    crew = Crew(
        agents=[trend_analyst, script_writer, seo_specialist],
        tasks=[research_task, script_task, metadata_task],
        process=Process.sequential,
        verbose=True,
    )

    return crew


def main():
    print("\n🏭 FACTORY C — FACELESS YOUTUBE — STARTING\n")
    crew = build_crew()
    result = crew.kickoff()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"youtube_{timestamp}.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# YouTube Factory Output\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write(str(result))

    print(f"\n✅ Output saved to: {output_file}")
    return str(result)


if __name__ == "__main__":
    main()

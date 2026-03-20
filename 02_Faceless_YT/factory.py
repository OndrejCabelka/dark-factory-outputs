"""
DARK FACTORY — Factory C: Faceless YouTube
CrewAI crew: trend research → full script → SEO metadata

Výstupy (_outputs/youtube/):
  youtube_research_{ts}.md  — analýza trendů a doporučení
  youtube_script_{ts}.md    — kompletní video skript (hlavní výstup)
  youtube_metadata_{ts}.md  — upload balíček (titulky, popis, tagy)
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

    trend_analyst = Agent(
        role="YouTube Trend & Niche Analyst",
        goal=(
            "Find the top 3 video topics right now with high CPM potential and relatively low competition. "
            "Prioritise niches: finance, tech, business, AI, health, self-improvement."
        ),
        backstory=(
            "Data-obsessed YouTube strategist. Knows which niches pay $15+ CPM and which are saturated. "
            "Backs every recommendation with real signals — not guesses."
        ),
        tools=[search_tool],
        verbose=True, allow_delegation=False,
        max_iter=3,
        llm="anthropic/claude-haiku-4-5-20251001",  # Haiku stačí na research
    )

    script_writer = Agent(
        role="Viral YouTube Script Writer",
        goal=(
            "Write a complete 8-12 minute video script. "
            "Hook stops scroll in 3 seconds. Structure: Hook → Intro → 5-8 sections → CTA → Outro."
        ),
        backstory=(
            "YouTube script writer with 50M+ views across faceless channels. "
            "Conversational, direct, no filler. Uses pattern interrupts and curiosity gaps naturally."
        ),
        verbose=True, allow_delegation=False,
        max_iter=2,
        llm="anthropic/claude-sonnet-4-6",  # Sonnet pro kvalitu skriptu
    )

    seo_specialist = Agent(
        role="YouTube SEO & Metadata Expert",
        goal=(
            "Maximise discoverability: 3 title options, 500+ word description, "
            "20 tags, chapter timestamps, thumbnail brief, voiceover notes."
        ),
        backstory=(
            "YouTube SEO specialist who has ranked hundreds of videos on page 1. "
            "Writes descriptions that serve both algorithm and human readers."
        ),
        verbose=True, allow_delegation=False,
        max_iter=2,
        llm="anthropic/claude-haiku-4-5-20251001",  # Haiku stačí na metadata/SEO
    )

    research_task = Task(
        description=(
            "Search for top 3 YouTube video opportunities right now. "
            "Focus: finance, tech, business, AI, health, self-improvement. "
            "For each topic: TOPIC | NICHE | WHY TRENDING | CPM ESTIMATE ($) | COMPETITION | "
            "EXAMPLE COMPETING VIDEOS WITH VIEW COUNTS | UNIQUE ANGLE. "
            "Rank #1-3. #1 = best opportunity."
        ),
        expected_output="Ranked analysis of 3 YouTube opportunities with full data for each.",
        agent=trend_analyst,
    )

    script_task = Task(
        description=(
            "Write a COMPLETE 8-12 minute video script for the #1 ranked topic. "
            "Structure: [HOOK 0:00-0:30] [INTRO 0:30-1:00] [SECTION 1-6] [CTA] [OUTRO] "
            "Include timestamps. Write full sentences — this is the actual voiceover script. "
            "Target: 1400-1800 words. Hook in first 5 lines must be outstanding."
        ),
        expected_output="Complete video script with timestamps and section labels. 1400-1800 words. Full sentences only.",
        agent=script_writer,
        context=[research_task],
    )

    metadata_task = Task(
        description=(
            "Create complete YouTube upload package. Deliver under these headings: "
            "TITLE OPTIONS (A/B/C — 3 variations, max 60 chars each) | "
            "DESCRIPTION (500+ words, SEO-optimised, hook in first 2 lines) | "
            "TAGS (20 tags, broad + specific, comma-separated) | "
            "CHAPTER TIMESTAMPS (matching script sections, 0:00 format) | "
            "THUMBNAIL BRIEF (background, visual element, text overlay max 4 words, mood) | "
            "VOICEOVER NOTES (tone, pace, energy per section)"
        ),
        expected_output="Complete upload package under 6 headings: TITLE OPTIONS, DESCRIPTION, TAGS, CHAPTERS, THUMBNAIL, VOICEOVER.",
        agent=seo_specialist,
        context=[research_task, script_task],
    )

    crew = Crew(
        agents=[trend_analyst, script_writer, seo_specialist],
        tasks=[research_task, script_task, metadata_task],
        process=Process.sequential,
        verbose=True,
        max_rpm=8,
    )
    return crew, research_task, script_task, metadata_task


def main():
    print("\n🏭 FACTORY C — FACELESS YOUTUBE — STARTING\n")
    crew, research_task, script_task, metadata_task = build_crew()
    crew.kickoff()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Zachyť výstupy všech 3 tasků
    research_out = getattr(getattr(research_task, "output", None), "raw", "") or ""
    script_out   = getattr(getattr(script_task,   "output", None), "raw", "") or ""
    metadata_out = getattr(getattr(metadata_task, "output", None), "raw", "") or ""

    # Ulož research
    if research_out:
        f = OUTPUT_DIR / f"youtube_research_{ts}.md"
        f.write_text(f"# YouTube Trend Research\nGenerated: {datetime.now()}\n\n---\n\n{research_out}", encoding="utf-8")
        print(f"✅ Research: {f.name}")

    # Ulož skript (nejcennější output)
    if script_out:
        f = OUTPUT_DIR / f"youtube_script_{ts}.md"
        f.write_text(f"# YouTube Script\nGenerated: {datetime.now()}\n\n---\n\n{script_out}", encoding="utf-8")
        print(f"✅ Script: {f.name} ({len(script_out.split())} words)")
    else:
        print("⚠️  Script (Task 2) prázdný!")

    # Ulož metadata
    if metadata_out:
        f = OUTPUT_DIR / f"youtube_metadata_{ts}.md"
        f.write_text(f"# YouTube Upload Package\nGenerated: {datetime.now()}\n\n---\n\n{metadata_out}", encoding="utf-8")
        print(f"✅ Metadata: {f.name}")

    # Souhrnný soubor pro zpětnou kompatibilitu
    combined = "\n\n---\n\n".join([
        f"# RESEARCH\n\n{research_out}",
        f"# SCRIPT\n\n{script_out}",
        f"# METADATA\n\n{metadata_out}",
    ])
    f = OUTPUT_DIR / f"youtube_{ts}.md"
    f.write_text(f"# YouTube Factory Output\nGenerated: {datetime.now()}\n\n{combined}", encoding="utf-8")
    print(f"✅ Combined: {f.name}")

    return script_out or metadata_out


if __name__ == "__main__":
    main()

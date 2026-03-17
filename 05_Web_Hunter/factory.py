"""
DARK FACTORY — Factory A: Web Hunter
CrewAI crew that finds CZ/SK businesses without websites and writes Czech outreach emails.
"""

import os
import csv
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / "_config" / ".env"
load_dotenv(dotenv_path=env_path)

from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

OUTPUT_DIR = Path(__file__).parent.parent / "_outputs" / "web_hunter"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_crew():
    search_tool = SerperDevTool()
    scrape_tool = ScrapeWebsiteTool()

    # ── AGENTS ──────────────────────────────────────────────────────────────

    hunter = Agent(
        role="Obchodní průzkumník",
        goal=(
            "Najít 10 firem v ČR nebo SR které nemají web nebo mají zastaralý web (starší než 2010). "
            "Zaměř se na: restaurace, řemeslníky, malé obchody, lokální služby. "
            "Pro každou firmu sesbírej: název, lokalita, telefon, email (pokud dostupný), "
            "URL webu nebo 'bez webu', stav webu."
        ),
        backstory=(
            "Jsi zkušený obchodní průzkumník specializující se na český a slovenský trh. "
            "Umíš rychle najít malé firmy, které digitálně zaostávají. "
            "Prohledáváš firmy.cz, zlatestranky.cz, Google Maps a místní adresáře. "
            "Výsledky strukturuješ přesně a kompletně."
        ),
        tools=[search_tool, scrape_tool],
        verbose=True,
        allow_delegation=False,
        llm="claude-3-5-sonnet-20241022",
    )

    analyst = Agent(
        role="Obchodní analytik",
        goal=(
            "Zhodnotit potenciál každé firmy ze seznamu a seřadit top 5 podle priority. "
            "Kritéria: má telefonní nebo emailový kontakt, zdá se aktivní, nemá web nebo má velmi zastaralý, "
            "je to lokální firma (ne nadnárodní řetězec)."
        ),
        backstory=(
            "Jsi analytik s ostrým obchodním instinktem. "
            "Víš přesně které leady stojí za čas a které ne. "
            "Hodnotíš střízlivě, bez přehnaného optimismu. "
            "Tvé hodnocení je podkladem pro personalizovaný outreach."
        ),
        verbose=True,
        allow_delegation=False,
        llm="claude-3-5-sonnet-20241022",
    )

    outreach_specialist = Agent(
        role="Specialista na obchodní komunikaci",
        goal=(
            "Napsat personalizovaný email v češtině pro každou firmu z top 5 seznamu. "
            "Styl: přátelský, neagresivní, zmíní konkrétní věc o jejich firmě, nabídne zdarma mockup webu. "
            "Email nesmí vypadat jako hromadná rozesílka."
        ),
        backstory=(
            "Jsi mistr cold emailů v češtině. Tvoje emaily lidé čtou, protože jsou konkrétní, "
            "krátké a respektují příjemce. Nikdy nepíšeš generické šablony. "
            "Každý email zmiňuje něco specifického o dané firmě. "
            "Nabízíš hodnotu hned — zdarma mockup webu, bez závazků."
        ),
        verbose=True,
        allow_delegation=False,
        llm="claude-3-5-sonnet-20241022",
    )

    # ── TASKS ────────────────────────────────────────────────────────────────

    hunt_task = Task(
        description=(
            "Prohledej internet a najdi 10 českých nebo slovenských firem bez webu nebo se zastaralým webem. "
            "Použij tyto vyhledávací dotazy: "
            "'restaurace Praha bez webu kontakt', "
            "'instalatér Brno telefon bez webových stránek', "
            "'řemeslník Ostrava kontakt', "
            "'site:firmy.cz instalatér', "
            "'site:zlatestranky.cz řemeslník bez webu'. "
            "Pro každou firmu uveď: "
            "NÁZEV | OBOR | MĚSTO | TELEFON | EMAIL | WEB (nebo 'bez webu') | POZNÁMKA. "
            "Výstup: přehledná tabulka v markdown formátu s 10 firmami."
        ),
        expected_output=(
            "Markdown tabulka s 10 firmami. Sloupce: NÁZEV, OBOR, MĚSTO, TELEFON, EMAIL, WEB, POZNÁMKA. "
            "Každá firma na vlastním řádku. Žádné prázdné řádky bez dat."
        ),
        agent=hunter,
    )

    analysis_task = Task(
        description=(
            "Vezmi seznam 10 firem a vyber top 5 podle těchto kritérií (seřaď od nejlepšího): "
            "1) Má přímý kontakt (telefon nebo email) "
            "2) Lokální firma, ne řetězec "
            "3) Nemá web NEBO má web starší než 2010 "
            "4) Aktivní firma (neuzavřená, fungující) "
            "Pro každou z top 5 napiš krátké zdůvodnění (2-3 věty) proč je prioritní. "
            "Výstup: seřazený seznam top 5 s hodnocením."
        ),
        expected_output=(
            "Seřazený seznam top 5 firem s hodnocením. "
            "Každá firma: pořadí, název, kontakt, zdůvodnění priority (2-3 věty)."
        ),
        agent=analyst,
        context=[hunt_task],
    )

    outreach_task = Task(
        description=(
            "Pro každou firmu z top 5 seznamu napiš personalizovaný email v češtině. "
            "Každý email musí obsahovat: "
            "PŘEDMĚT: kreativní, osobní, max 60 znaků "
            "TĚLO: "
            "- Oslovení jménem firmy "
            "- 1 věta co konkrétního jsme si o nich všimli (nemají web, nebo web z roku 200X) "
            "- Představení: jsme malá česká agentura na weby pro živnostníky "
            "- Nabídka: zdarma připravíme mockup jejich webu, bez závazků "
            "- CTA: zavolejte nebo odpište, pošleme ukázku do 24 hodin "
            "- Podpis: Ondřej, ondrej.cabelka@gmail.com "
            "Styl: lidský, neformální, ne jako spam. Max 150 slov na email. "
            "Odděl emaily nadpisem ## Firma X — [název]"
        ),
        expected_output=(
            "5 kompletních emailů v češtině, každý pod nadpisem ## Firma X. "
            "Každý email: PŘEDMĚT a TĚLO. Maximálně 150 slov. Žádné generické fráze."
        ),
        agent=outreach_specialist,
        context=[hunt_task, analysis_task],
    )

    # ── CREW ─────────────────────────────────────────────────────────────────

    crew = Crew(
        agents=[hunter, analyst, outreach_specialist],
        tasks=[hunt_task, analysis_task, outreach_task],
        process=Process.sequential,
        verbose=True,
    )

    return crew


def main():
    print("\n🏭 FACTORY A — WEB HUNTER — STARTING\n")
    crew = build_crew()
    result = crew.kickoff()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save full markdown output
    md_file = OUTPUT_DIR / f"web_hunter_{timestamp}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(f"# Web Hunter Output\n")
        f.write(f"Vygenerováno: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write(str(result))

    # Save leads as basic CSV
    csv_file = OUTPUT_DIR / f"leads_{timestamp}.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["NÁZEV", "OBOR", "MĚSTO", "TELEFON", "EMAIL", "WEB", "STAV"])
        writer.writerow(["(leady jsou v markdown souboru výše)", "", "", "", "", "", ""])

    print(f"\n✅ Výstup uložen do: {md_file}")
    print(f"✅ CSV šablona uložena do: {csv_file}")
    return str(result)


if __name__ == "__main__":
    main()

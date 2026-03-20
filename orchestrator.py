"""
DARK FACTORY — Claude AI Orchestrator
Claude (Sonnet 4.6) je CEO. On rozhoduje co spustit, kdy, proč.

Architektura:
  orchestrator.py (tento soubor)
    → Claude API (mozek, rozhoduje)
    → Factory A: Scout + Qualifier + EmailWriter
    → Factory B: Researcher + Writer + Publisher
    → Factory C: TrendAnalyst + ScriptWriter + MetaGen
    → Factory D: DataScraper + Analyzer + Packager
    → Factory E: Researcher + Writer + Publisher
    → Factory F: LeadFinder + Verifier + Exporter

Claude dostane stav všech továren, jejich výstupy, revenue metriky
a sám rozhodne co spustit, v jakém pořadí, a proč.

Spuštění:
  python orchestrator.py          # jednorázový cyklus
  python orchestrator.py --loop   # nepřetržitá smyčka (jako scheduler.py)
  python orchestrator.py --status # jen zobrazí stav
"""

import os, sys, json, re, time, importlib.util, argparse
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import anthropic

BASE_DIR = Path(__file__).parent
load_dotenv(dotenv_path=BASE_DIR / "_config" / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OUTPUT_DIR = BASE_DIR / "_outputs"
LOG_DIR    = BASE_DIR / "_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = BASE_DIR / "_logs" / "orchestrator_state.json"


# ══════════════════════════════════════════════════════════════════════════════
# STATE MANAGER — co se kdy spustilo, s jakým výsledkem
# ══════════════════════════════════════════════════════════════════════════════

FACTORY_DEFINITIONS = {
    "a": {
        "name": "Web Hunter",
        "path": "05_Web_Hunter/factory.py",
        "module": "factory_a",
        "output_dir": "_outputs/web_hunter",
        "description": "Hledá CZ/SK firmy bez webu přes Serper Maps. Výstup: CSV leads + emaily.",
        "revenue_type": "B2B leads → weby za 15-25k Kč",
        "min_interval_hours": 6,
    },
    "b": {
        "name": "Digital Products",
        "path": "01_Digital_Products/factory.py",
        "module": "factory_b",
        "output_dir": "_outputs/digital_products",
        "description": "Generuje PDF průvodce a prodává je přes Lemon Squeezy.",
        "revenue_type": "Pasivní příjem: PDF prodej 5-20€/ks",
        "min_interval_hours": 24,
    },
    "c": {
        "name": "YouTube Scripts",
        "path": "02_Faceless_YT/factory.py",
        "module": "factory_c",
        "output_dir": "_outputs/youtube",
        "description": "Generuje YouTube skripty + metadata pro faceless kanál.",
        "revenue_type": "Budování kanálu → AdSense v 3-6 měsících",
        "min_interval_hours": 12,
    },
    "d": {
        "name": "Data Products",
        "path": "04_Data_Products/factory.py",
        "module": "factory_d",
        "output_dir": "_outputs/data_products",
        "description": "ARES + firmy data, exportuje CSV datasety.",
        "revenue_type": "B2B data prodej",
        "min_interval_hours": 24,
    },
    "e": {
        "name": "SEO Content",
        "path": "06_SEO_Content/factory.py",
        "module": "factory_e",
        "output_dir": "_outputs/seo_content",
        "description": "SEO affiliate články pro CZ trh, affiliate linky Heureka + Alza.",
        "revenue_type": "Affiliate komise: 2-8% z prodeje",
        "min_interval_hours": 4,
    },
    "f": {
        "name": "Leads API",
        "path": "07_Leads_API/factory.py",
        "module": "factory_f",
        "output_dir": "_outputs/leads_api",
        "description": "Exportuje leady jako API endpoint nebo CSV balíček.",
        "revenue_type": "Leads prodej B2B",
        "min_interval_hours": 12,
    },
}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {k: {"last_run": None, "last_result": "never", "run_count": 0, "errors": 0} for k in FACTORY_DEFINITIONS}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def get_output_summary(factory_key: str) -> dict:
    """Zjistí kolik výstupů factory produkovala a kdy naposledy."""
    factory = FACTORY_DEFINITIONS[factory_key]
    out_dir = BASE_DIR / factory["output_dir"]
    if not out_dir.exists():
        return {"files": 0, "latest": None, "size_kb": 0}

    files = sorted(out_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    total_size = sum(f.stat().st_size for f in files if f.is_file()) // 1024

    return {
        "files": len(files),
        "latest": files[0].name if files else None,
        "latest_mtime": datetime.fromtimestamp(files[0].stat().st_mtime).isoformat() if files else None,
        "size_kb": total_size,
    }


def build_status_report(state: dict) -> str:
    """Sestaví JSON status report pro Claude."""
    now = datetime.now()
    report = {"timestamp": now.isoformat(), "factories": {}}

    for key, factory in FACTORY_DEFINITIONS.items():
        s = state.get(key, {})
        output_info = get_output_summary(key)

        # Spočítej čas od posledního spuštění
        last_run = s.get("last_run")
        hours_since_run = None
        can_run = True
        if last_run:
            last_dt = datetime.fromisoformat(last_run) if isinstance(last_run, str) else last_run
            diff = (now - last_dt).total_seconds() / 3600
            hours_since_run = round(diff, 1)
            if diff < factory["min_interval_hours"]:
                can_run = False

        report["factories"][key] = {
            "name": factory["name"],
            "description": factory["description"],
            "revenue_type": factory["revenue_type"],
            "last_run": last_run,
            "hours_since_run": hours_since_run,
            "last_result": s.get("last_result", "never"),
            "run_count": s.get("run_count", 0),
            "errors": s.get("errors", 0),
            "can_run": can_run,
            "min_interval_hours": factory["min_interval_hours"],
            "outputs": output_info,
        }

    return json.dumps(report, indent=2, default=str)


# ══════════════════════════════════════════════════════════════════════════════
# CLAUDE AI BRAIN — rozhoduje co spustit
# ══════════════════════════════════════════════════════════════════════════════

CLAUDE_SYSTEM_PROMPT = """Jsi CEO Dark Factory — autonomního revenue systému.
Dark Factory má 6 výrobních linek (factories) které generují příjmy 24/7.

Tvůj úkol:
1. Zanalyzuj aktuální stav všech factories
2. Rozhodni které spustit v tomto cyklu (max 3 najednou)
3. Zdůvodni výběr z pohledu revenue potenciálu

Pravidla:
- Prioritizuj factory E (SEO Content) — nejrychlejší affiliate revenue, kratší interval
- Factory A (Web Hunter) je core byznys — Ondra volá leady osobně → přímé příjmy
- Nespouštěj factory které mají "can_run": false (ještě nedosáhly min_interval_hours)
- Nespouštěj factory s posledním výsledkem "error" pokud to nezní jako opravitelná chyba
- Mysli jako investor: co má nejvyšší ROI per hodina CPU?

Odpověz POUZE jako JSON (žádný jiný text):
{
  "run": ["e", "a"],
  "skip": ["b", "c", "d", "f"],
  "reasoning": "Factory E má nejkratší interval a přímé affiliate revenue. Factory A generuje B2B leady. Ostatní buď nedosáhly min_interval nebo mají nízký ROI.",
  "priority_order": ["e", "a"],
  "estimated_revenue_impact": "Factory E: +1-3 affiliate kliknutí/den. Factory A: 10-20 nových leadů pro Ondru."
}"""


def ask_claude_what_to_run(status_report: str) -> dict:
    """Claude rozhodne co spustit na základě aktuálního stavu."""
    if not ANTHROPIC_API_KEY:
        # Fallback: spusť E a A vždy
        return {"run": ["e", "a"], "skip": [], "reasoning": "Fallback (no API key)", "priority_order": ["e", "a"]}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=CLAUDE_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Aktuální stav Dark Factory:\n\n{status_report}\n\nCo spustit v tomto cyklu?"
            }]
        )
        raw = msg.content[0].text.strip()
        # Robustní extrakce JSON — najdi první { a poslední }
        start_idx = raw.find("{")
        end_idx   = raw.rfind("}")
        if start_idx == -1 or end_idx == -1:
            raise ValueError("Žádný JSON objekt v odpovědi")
        json_str = raw[start_idx:end_idx + 1]
        decision = json.loads(json_str)
        return decision
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  ⚠ Claude response není JSON: {e}")
        return {"run": ["e", "a"], "skip": [], "reasoning": "JSON parse failed, fallback to E+A", "priority_order": ["e", "a"]}
    except Exception as e:
        print(f"  ⚠ Claude API chyba: {e}")
        return {"run": ["e"], "skip": [], "reasoning": f"API error: {e}", "priority_order": ["e"]}


# ══════════════════════════════════════════════════════════════════════════════
# FACTORY RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_factory(key: str, state: dict) -> bool:
    """Spustí factory a aktualizuje state."""
    factory = FACTORY_DEFINITIONS[key]
    factory_path = BASE_DIR / factory["path"]

    if not factory_path.exists():
        print(f"  ⚠ Factory {key.upper()} soubor neexistuje: {factory_path}")
        state[key]["last_result"] = "missing_file"
        state[key]["errors"] += 1
        return False

    print(f"\n  ▶ Factory {key.upper()} — {factory['name']}")
    start = datetime.now()

    try:
        spec = importlib.util.spec_from_file_location(factory["module"], factory_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Zkouší main(), pak factory_{key}()
        fn = getattr(mod, "main", None) or getattr(mod, f"factory_{key}", None)
        if fn is None:
            raise AttributeError(f"Factory {key.upper()} nema funkci main() ani factory_{key}()")
        fn()

        elapsed = (datetime.now() - start).total_seconds()
        state[key]["last_run"]    = datetime.now().isoformat()
        state[key]["last_result"] = "success"
        state[key]["run_count"]   = state[key].get("run_count", 0) + 1
        print(f"  ✅ Factory {key.upper()} hotovo ({elapsed:.0f}s)")
        return True

    except Exception as e:
        elapsed = (datetime.now() - start).total_seconds()
        state[key]["last_run"]    = datetime.now().isoformat()
        state[key]["last_result"] = f"error: {str(e)[:100]}"
        state[key]["errors"]      = state[key].get("errors", 0) + 1
        print(f"  ❌ Factory {key.upper()} selhala ({elapsed:.0f}s): {e}")
        return False


def auto_publish_after_factory(key: str):
    """Po Factory E → automaticky publikuj na GitHub Pages."""
    if key == "e":
        pub_path = BASE_DIR / "publish_seo.py"
        if pub_path.exists():
            try:
                spec = importlib.util.spec_from_file_location("publish_seo", pub_path)
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                url = mod.main()
                print(f"  🌐 SEO auto-published: {url}")
            except Exception as e:
                print(f"  ⚠ SEO publish chyba: {e}")
    elif key == "b":
        ls_key = os.getenv("LEMONSQUEEZY_API_KEY", "").strip()
        if ls_key:
            pub_path = BASE_DIR / "publish_lemonsqueezy.py"
            if pub_path.exists():
                try:
                    spec = importlib.util.spec_from_file_location("publish_ls", pub_path)
                    mod  = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    url = mod.publish()
                    print(f"  🛒 Lemon Squeezy published: {url}")
                except Exception as e:
                    print(f"  ⚠ LemonSqueezy publish chyba: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATION CYCLE
# ══════════════════════════════════════════════════════════════════════════════

def run_cycle(state: dict, cycle_num: int = 1) -> dict:
    """Jeden orchestrační cyklus: status → Claude rozhodne → spusť → uložit."""

    print(f"\n{'━'*60}")
    print(f"  ORCHESTRATOR CYKLUS #{cycle_num} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'━'*60}")

    # 1. Sestav status report
    status_report = build_status_report(state)

    # 2. Claude rozhodne
    print("\n🧠 Claude analyzuje stav a rozhoduje...")
    decision = ask_claude_what_to_run(status_report)
    print(f"\n  Spustit:  {decision.get('run', [])}")
    print(f"  Skip:     {decision.get('skip', [])}")
    print(f"  Důvod:    {decision.get('reasoning', '—')[:120]}")

    # 3. Spusť factories v pořadí dle Claude
    run_results = {}
    priority_order = decision.get("priority_order", decision.get("run", []))

    for key in priority_order:
        if key not in FACTORY_DEFINITIONS:
            print(f"  ⚠ Neznámá factory '{key}', skip.")
            continue
        ok = run_factory(key, state)
        run_results[key] = "✅" if ok else "❌"
        if ok:
            auto_publish_after_factory(key)
        save_state(state)  # uložit po každé factory
        time.sleep(2)  # krátká pauza

    # 4. Souhrn cyklu
    summary = " | ".join(f"{k.upper()}:{v}" for k, v in run_results.items())
    print(f"\n  Výsledky cyklu #{cycle_num}: {summary}")
    print(f"  Klíčový dopad: {decision.get('estimated_revenue_impact', '—')[:100]}")

    # Log do souboru
    log_entry = {
        "cycle": cycle_num,
        "timestamp": datetime.now().isoformat(),
        "decision": decision,
        "results": run_results,
    }
    log_path = LOG_DIR / "orchestrator.jsonl"
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry, default=str) + "\n")

    return run_results


def show_status():
    """Zobrazí aktuální stav všech factories."""
    state = load_state()
    status_report = build_status_report(state)
    data = json.loads(status_report)

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║          DARK FACTORY — STATUS DASHBOARD            ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    for key, info in data["factories"].items():
        status_icon = "✅" if info["last_result"] == "success" else ("⏳" if info["last_result"] == "never" else "❌")
        can_run_icon = "🟢" if info["can_run"] else "🔴"
        print(f"  {can_run_icon} Factory {key.upper()} — {info['name']}")
        print(f"     Poslední běh: {info['last_run'] or 'nikdy'} ({info['hours_since_run'] or '?'}h zpět)")
        print(f"     Výsledek: {status_icon} {info['last_result']}")
        print(f"     Výstupy: {info['outputs']['files']} souborů, {info['outputs']['size_kb']} kB")
        print(f"     Revenue: {info['revenue_type']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Dark Factory Claude Orchestrator")
    parser.add_argument("--loop",   action="store_true", help="Nepřetržitá smyčka")
    parser.add_argument("--status", action="store_true", help="Zobrazit stav a skončit")
    parser.add_argument("--delay",  type=int, default=60, help="Pauza mezi cykly v minutách (default: 60)")
    parser.add_argument("--run",    type=str, help="Vynutit spuštění konkrétní factory (a/b/c/d/e/f)")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════╗")
    print("║     DARK FACTORY — CLAUDE AI ORCHESTRATOR           ║")
    print("║     Claude Sonnet 4.6 jako CEO | 24/7 autonomous    ║")
    print("╚══════════════════════════════════════════════════════╝")

    if args.status:
        show_status()
        return

    state = load_state()

    if args.run:
        # Manuální spuštění konkrétní factory
        key = args.run.lower()
        if key not in FACTORY_DEFINITIONS:
            print(f"❌ Neznámá factory '{key}'. Použij: a/b/c/d/e/f")
            return
        print(f"\n🔧 Manuální spuštění Factory {key.upper()}...")
        run_factory(key, state)
        auto_publish_after_factory(key)
        save_state(state)
        return

    if args.loop:
        print(f"\n🔄 LOOP MODE — Claude rozhoduje každých {args.delay} minut\n")
        cycle = 0
        while True:
            cycle += 1
            state = load_state()
            run_cycle(state, cycle)
            save_state(state)
            print(f"\n💤 Čekám {args.delay} minut před dalším cyklem... (Ctrl+C pro stop)")
            try:
                time.sleep(args.delay * 60)
            except KeyboardInterrupt:
                print("\n👋 Orchestrator zastaven.")
                break
    else:
        # Jednorázový cyklus
        state = load_state()
        run_cycle(state, cycle_num=1)
        save_state(state)
        print("\n✅ Cyklus hotov. Pro loop: python orchestrator.py --loop")


if __name__ == "__main__":
    main()

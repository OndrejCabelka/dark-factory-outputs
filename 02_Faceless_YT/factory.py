"""
DARK FACTORY — Factory C: Faceless YouTube + Clipping
======================================================
Dva módy, jedna factory:

  --mode script (default)
    CrewAI crew: trend research → full script → SEO metadata
    Výstupy: youtube_script_{ts}.md, youtube_metadata_{ts}.md

  --mode clip
    Auto clipping pipeline: scout trending → download → Whisper → Claude → ffmpeg
    Výstupy: {id}_transcript.json, {id}_clips.json, {id}_clip{n}.mp4

Sdílené výstupy: _outputs/youtube/

Spuštění:
  python factory.py                          # script mode (default)
  python factory.py --mode clip --batch      # najdi trending a oClipuj top 2
  python factory.py --mode clip --url URL    # konkrétní video
  python factory.py --mode clip --url URL --clips 3 --lang cs
"""

import os, sys, re, json, time, subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=BASE_DIR / "_config" / ".env")

import anthropic

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SERPER_API_KEY    = os.getenv("SERPER_API_KEY", "")

OUTPUT_DIR = BASE_DIR / "_outputs" / "youtube"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ══════════════════════════════════════════════════════════════════════════════
# MODUS A: SCRIPT MODE — CrewAI crew (stávající logika)
# ══════════════════════════════════════════════════════════════════════════════

def build_crew():
    from crewai import Agent, Task, Crew, Process
    from crewai_tools import SerperDevTool
    search_tool = SerperDevTool()

    trend_analyst = Agent(
        role="YouTube Trend & Niche Analyst",
        goal=(
            "Find the top 3 video topics right now with high CPM potential and low competition. "
            "Prioritise: finance, tech, business, AI, health, self-improvement."
        ),
        backstory=(
            "Data-obsessed YouTube strategist. Knows which niches pay $15+ CPM. "
            "Backs every recommendation with real signals — not guesses."
        ),
        tools=[search_tool], verbose=True, allow_delegation=False, max_iter=3,
        llm="anthropic/claude-haiku-4-5-20251001",
    )

    script_writer = Agent(
        role="Viral YouTube Script Writer",
        goal=(
            "Write a complete 8-12 minute video script. "
            "Hook stops scroll in 3 seconds. Structure: Hook → Intro → 5-8 sections → CTA → Outro."
        ),
        backstory=(
            "YouTube script writer with 50M+ views across faceless channels. "
            "Conversational, direct, no filler. Uses pattern interrupts naturally."
        ),
        verbose=True, allow_delegation=False, max_iter=2,
        llm="anthropic/claude-sonnet-4-6",
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
        verbose=True, allow_delegation=False, max_iter=2,
        llm="anthropic/claude-haiku-4-5-20251001",
    )

    research_task = Task(
        description=(
            "Search for top 3 YouTube video opportunities right now. "
            "Focus: finance, tech, business, AI, health, self-improvement. "
            "For each: TOPIC | NICHE | WHY TRENDING | CPM ESTIMATE | COMPETITION | UNIQUE ANGLE. Rank #1-3."
        ),
        expected_output="Ranked analysis of 3 YouTube opportunities with full data for each.",
        agent=trend_analyst,
    )

    script_task = Task(
        description=(
            "Write a COMPLETE 8-12 minute video script for the #1 ranked topic. "
            "Structure: [HOOK 0:00-0:30] [INTRO 0:30-1:00] [SECTION 1-6] [CTA] [OUTRO] "
            "Include timestamps. Full sentences. Target: 1400-1800 words."
        ),
        expected_output="Complete video script with timestamps. 1400-1800 words. Full sentences only.",
        agent=script_writer, context=[research_task],
    )

    metadata_task = Task(
        description=(
            "Create complete YouTube upload package: "
            "TITLE OPTIONS (A/B/C) | DESCRIPTION (500+ words) | TAGS (20) | "
            "CHAPTER TIMESTAMPS | THUMBNAIL BRIEF | VOICEOVER NOTES"
        ),
        expected_output="Complete upload package under 6 headings.",
        agent=seo_specialist, context=[research_task, script_task],
    )

    crew = Crew(
        agents=[trend_analyst, script_writer, seo_specialist],
        tasks=[research_task, script_task, metadata_task],
        process=Process.sequential, verbose=True, max_rpm=8,
    )
    return crew, research_task, script_task, metadata_task


def run_script_mode() -> str:
    print("\n🏭 FACTORY C — SCRIPT MODE — STARTING\n")
    crew, research_task, script_task, metadata_task = build_crew()
    crew.kickoff()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    research_out = getattr(getattr(research_task, "output", None), "raw", "") or ""
    script_out   = getattr(getattr(script_task,   "output", None), "raw", "") or ""
    metadata_out = getattr(getattr(metadata_task, "output", None), "raw", "") or ""

    if research_out:
        f = OUTPUT_DIR / f"youtube_research_{ts}.md"
        f.write_text(f"# YouTube Trend Research\n{datetime.now()}\n\n{research_out}", encoding="utf-8")
        print(f"✅ Research: {f.name}")
    if script_out:
        f = OUTPUT_DIR / f"youtube_script_{ts}.md"
        f.write_text(f"# YouTube Script\n{datetime.now()}\n\n{script_out}", encoding="utf-8")
        print(f"✅ Script: {f.name} ({len(script_out.split())} words)")
    if metadata_out:
        f = OUTPUT_DIR / f"youtube_metadata_{ts}.md"
        f.write_text(f"# YouTube Upload Package\n{datetime.now()}\n\n{metadata_out}", encoding="utf-8")
        print(f"✅ Metadata: {f.name}")

    combined = "\n\n---\n\n".join([
        f"# RESEARCH\n\n{research_out}",
        f"# SCRIPT\n\n{script_out}",
        f"# METADATA\n\n{metadata_out}",
    ])
    f = OUTPUT_DIR / f"youtube_{ts}.md"
    f.write_text(f"# YouTube Factory Output\n{datetime.now()}\n\n{combined}", encoding="utf-8")
    print(f"✅ Combined: {f.name}")
    return script_out or metadata_out


# ══════════════════════════════════════════════════════════════════════════════
# MODUS B: CLIP MODE — Scout → Download → Whisper → Claude → ffmpeg
# ══════════════════════════════════════════════════════════════════════════════

def scout_trending_videos(niche: str, lang: str = "cs", limit: int = 5) -> list[dict]:
    """Serper Video Search — najde trending YouTube videa v niche."""
    import requests as req
    if not SERPER_API_KEY:
        print("  ⚠ SERPER_API_KEY chybí")
        return []

    query = f'site:youtube.com "{niche}" {datetime.now().year}'
    if lang == "cs":
        query += " czech OR česky"

    r = req.post(
        "https://google.serper.dev/videos",
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
        json={"q": query, "gl": "cz", "hl": "cs", "num": limit * 2},
        timeout=8,
    )
    if not r.ok:
        print(f"  ⚠ Serper {r.status_code}")
        return []

    results = []
    for v in r.json().get("videos", []):
        link = v.get("link", "")
        if "youtube.com/watch" not in link and "youtu.be/" not in link:
            continue
        results.append({
            "url":     link,
            "title":   v.get("title", ""),
            "channel": v.get("channel", ""),
        })
        if len(results) >= limit:
            break

    print(f"  🔍 Scout: {len(results)} videí pro '{niche}'")
    return results


def download_video(url: str, max_duration_s: int = 900) -> dict | None:
    """yt-dlp stáhne video do dočasného souboru."""
    try:
        import yt_dlp
    except ImportError:
        print("  ⚠ yt-dlp: pip install yt-dlp")
        return None

    tmp_dir = OUTPUT_DIR / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    ydl_opts = {
        "format":        "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl":       str(tmp_dir / "%(id)s.%(ext)s"),
        "quiet":         True,
        "no_warnings":   True,
        "match_filter":  yt_dlp.utils.match_filter_func(f"duration <= {max_duration_s}"),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info  = ydl.extract_info(url, download=True)
            fpath = Path(ydl.prepare_filename(info))
            if not fpath.exists():
                fpath = fpath.with_suffix(".mp4")
            if not fpath.exists():
                return None
            return {
                "path":     str(fpath),
                "id":       info.get("id", ""),
                "title":    info.get("title", ""),
                "channel":  info.get("uploader", ""),
                "duration": info.get("duration", 0),
                "url":      url,
            }
    except Exception as e:
        print(f"  ⚠ Download: {e}")
        return None


def transcribe_video(video_path: str, language: str = "cs") -> list[dict] | None:
    """OpenAI Whisper — přepíše audio na text se segmenty + timestamps."""
    try:
        import whisper
    except ImportError:
        print("  ⚠ whisper: pip install openai-whisper")
        return None

    print(f"  🎙 Transkribuji {Path(video_path).name}...")
    try:
        model    = whisper.load_model("base")
        result   = model.transcribe(video_path, language=language, verbose=False)
        segments = [
            {"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()}
            for s in result.get("segments", [])
        ]
        print(f"  ✅ Transkripce: {len(segments)} segmentů")
        return segments
    except Exception as e:
        print(f"  ⚠ Whisper: {e}")
        return None


def select_clips(transcript: list[dict], title: str, n_clips: int = 3) -> list[dict]:
    """Claude vybere nejlepší momenty pro TikTok/Shorts clip."""
    text_ts = "\n".join(f"[{s['start']:.1f}s–{s['end']:.1f}s] {s['text']}" for s in transcript)

    prompt = f"""Jsi expert na virální krátká videa (TikTok, YouTube Shorts).

Video: "{title}"
Transcript:
{text_ts[:8000]}

Vyber PŘESNĚ {n_clips} nejlepší momenty (30–60 sekund každý):
- Silný hook v prvních 3 sekundách
- Soběstačný bez kontextu
- Emocionálně angažující
- Přirozený začátek i konec

Odpověz POUZE validním JSON polem:
[{{"clip_number":1,"start_s":45.0,"end_s":78.0,"hook":"První věta","reason":"Proč virální","title_suggestion":"Max 8 slov","tags":["#tag1","#tag2"]}}]"""

    try:
        resp  = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw   = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.content[0].text.strip(), flags=re.M)
        clips = json.loads(raw.strip())
        print(f"  🎬 ClipSelector: {len(clips)} clipů")
        return clips
    except Exception as e:
        print(f"  ⚠ ClipSelector: {e}")
        return []


def make_clip(video_path: str, start_s: float, end_s: float,
              output_path: str, title_text: str = "") -> bool:
    """ffmpeg — vystřihne clip, crop 9:16, burned-in titulek."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("  ⚠ ffmpeg: brew install ffmpeg")
        return False

    duration = end_s - start_s
    if duration < 5:
        return False

    vf = "crop=in_h*9/16:in_h,scale=1080:1920"
    if title_text:
        safe = title_text.replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")[:60]
        vf  += (
            f",drawtext=text='{safe}'"
            ":fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h*0.08"
            ":box=1:boxcolor=black@0.6:boxborderw=12:enable='between(t,0,3)'"
        )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_s), "-i", video_path, "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        output_path,
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode == 0 and Path(output_path).exists():
            mb = Path(output_path).stat().st_size / 1024 / 1024
            print(f"  ✂ Clip: {Path(output_path).name} ({mb:.1f} MB, {duration:.0f}s)")
            return True
        print(f"  ⚠ ffmpeg: {r.stderr[-150:]}")
        return False
    except subprocess.TimeoutExpired:
        return False


def process_video(url: str, n_clips: int = 3, lang: str = "cs") -> dict:
    """Kompletní clip pipeline pro jedno video."""
    print(f"\n{'='*60}\n🎬 Clip mode — {url}\n{'='*60}")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n[1/4] 📥 Stahuji...")
    meta = download_video(url)
    if not meta:
        return {"ok": False, "error": "download failed", "url": url}
    print(f"  ✅ {meta['title']} ({meta['duration']}s)")

    print("\n[2/4] 🎙 Transkribuji...")
    segments = transcribe_video(meta["path"], language=lang)
    if not segments:
        return {"ok": False, "error": "transcription failed"}

    t_path = OUTPUT_DIR / f"{meta['id']}_{ts}_transcript.json"
    t_path.write_text(json.dumps({"meta": meta, "segments": segments}, ensure_ascii=False, indent=2))

    print("\n[3/4] 🧠 Claude vybírá momenty...")
    clips = select_clips(segments, meta["title"], n_clips=n_clips)
    if not clips:
        return {"ok": False, "error": "no clips selected"}

    c_path = OUTPUT_DIR / f"{meta['id']}_{ts}_clips.json"
    c_path.write_text(json.dumps(clips, ensure_ascii=False, indent=2))

    print(f"\n[4/4] ✂ Stříhám {len(clips)} clipů...")
    output_files = []
    for clip in clips:
        n     = clip.get("clip_number", len(output_files) + 1)
        out_p = str(OUTPUT_DIR / f"{meta['id']}_{ts}_clip{n}.mp4")
        ok    = make_clip(meta["path"], clip["start_s"], clip["end_s"], out_p,
                          title_text=clip.get("title_suggestion", ""))
        if ok:
            output_files.append({
                "path": out_p, "clip_number": n,
                "title": clip.get("title_suggestion", ""),
                "hook": clip.get("hook", ""),
                "tags": clip.get("tags", []),
                "duration": clip["end_s"] - clip["start_s"],
            })

    try:
        Path(meta["path"]).unlink()
    except Exception:
        pass

    print(f"\n✅ {len(output_files)} clipů hotovo")
    for f in output_files:
        print(f"  → {Path(f['path']).name} | {f['title']}")

    return {"ok": True, "url": url, "video_title": meta["title"], "clips": output_files}


def run_clip_batch(niche: str = "motivace", lang: str = "cs", n_clips: int = 2) -> list[dict]:
    """Scout + zpracuj top 2 videa v niche."""
    print(f"\n🚀 FACTORY C — CLIP BATCH — niche: {niche}")
    videos = scout_trending_videos(niche, lang=lang, limit=5)
    if not videos:
        print("  Žádná videa")
        return []

    results = []
    for video in videos[:2]:
        results.append(process_video(video["url"], n_clips=n_clips, lang=lang))
        time.sleep(2)

    ok = sum(1 for r in results if r.get("ok"))
    print(f"\n📊 Clip batch: {ok}/{len(results)} zpracováno")
    return results


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — scheduler volá main(), CLI umožňuje oba módy
# ══════════════════════════════════════════════════════════════════════════════

def main(mode: str = "script", **kwargs) -> str | list:
    if mode == "clip":
        url    = kwargs.get("url")
        niche  = kwargs.get("niche", "motivace")
        lang   = kwargs.get("lang", "cs")
        n      = kwargs.get("clips", 3)
        batch  = kwargs.get("batch", False)
        if url:
            return process_video(url, n_clips=n, lang=lang)
        return run_clip_batch(niche=niche, lang=lang, n_clips=n)
    else:
        return run_script_mode()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Factory C — Faceless YouTube + Clipping")
    parser.add_argument("--mode",   choices=["script", "clip"], default="script")
    parser.add_argument("--url",    help="YouTube URL (clip mode)")
    parser.add_argument("--niche",  default="motivace", help="Niche pro scout (clip batch)")
    parser.add_argument("--lang",   default="cs")
    parser.add_argument("--clips",  type=int, default=3)
    parser.add_argument("--batch",  action="store_true")
    args = parser.parse_args()

    if args.mode == "clip":
        if args.url:
            process_video(args.url, n_clips=args.clips, lang=args.lang)
        else:
            run_clip_batch(niche=args.niche, lang=args.lang, n_clips=args.clips)
    else:
        run_script_mode()

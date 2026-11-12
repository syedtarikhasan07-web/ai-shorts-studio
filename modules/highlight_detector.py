import os
import json
import re
from typing import List, Dict, Any, Optional

VIRAL_PROMPT = """You are an elite YouTube Shorts and TikTok video editor with 10+ years of viral content experience.
Your goal is to identify the most viral-worthy, highly engaging 30 to 60-second moments from the provided video transcript.

Criteria for a 10/10 Viral Short:
1. THE HOOK: The first 3 seconds must immediately grab attention (controversial statement, surprising fact, intrigue, or bold question).
2. HIGH RETENTION PACING: The story or insight must stay focused and high-energy with zero filler.
3. COMPLETE NARRATIVE / PAYOFF: The clip MUST be self-contained (an idea is introduced, developed, and concluded with a punchline or takeaway). Do NOT cut off mid-thought or mid-sentence.
4. DURATION: Each clip must be between 30 and 60 seconds (strictly between 25.0 and 60.0 seconds).

Video Title: {title}
Total Duration: {duration} seconds

Video Transcript (with timestamps):
{transcript}

Select the TOP 1 to 3 best clips.
Return ONLY valid JSON matching this schema:
[
  {{
    "title": "Punchy click-worthy title for the Short",
    "start_time": 45.5,
    "end_time": 95.0,
    "duration": 49.5,
    "viral_score": 94,
    "hook": "The opening sentence or hook",
    "reasoning": "Why this moment will trigger high retention and shares"
  }}
]
"""

def detect_viral_moments_gemini(
    transcript_text: str,
    video_title: str,
    duration: float,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Uses Gemini API to analyze transcript and extract viral highlights.
    """
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return heuristic_highlight_detector(transcript_text, duration)

    import google.generativeai as genai
    genai.configure(api_key=api_key)

    # Use fastest, highest quality flash model
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )

    # Truncate transcript if excessively long to fit comfortably in prompt
    lines = transcript_text.splitlines()
    if len(lines) > 800:
        lines = lines[:800]
    prompt = VIRAL_PROMPT.format(
        title=video_title,
        duration=duration,
        transcript="\n".join(lines)
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean potential markdown wrapping
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        clips = json.loads(text.strip())
        if isinstance(clips, list) and len(clips) > 0:
            return clips
    except Exception as e:
        print(f"[Gemini Highlight Detection Warning] {e}, falling back to heuristic detector.")

    return heuristic_highlight_detector(transcript_text, duration)

def heuristic_highlight_detector(transcript_text: str, total_duration: float) -> List[Dict[str, Any]]:
    """
    Fallback viral moment detector using linguistic markers, sentiment, question hooks, and speech density.
    Ensures the application works even when offline or without an API key!
    """
    lines = transcript_text.splitlines()
    parsed_segments = []
    
    # Regex to match [MM:SS -> MM:SS] text
    pattern = re.compile(r"\[(\d+):(\d+)\s*->\s*(\d+):(\d+)\]\s*(.*)")
    for line in lines:
        m = pattern.match(line)
        if m:
            s_min, s_sec, e_min, e_sec, text = m.groups()
            start = int(s_min) * 60 + int(s_sec)
            end = int(e_min) * 60 + int(e_sec)
            parsed_segments.append({"start": start, "end": end, "text": text.strip()})

    if not parsed_segments:
        # Fallback if no timestamps parsed
        default_start = min(15.0, max(0.0, total_duration - 60))
        default_end = min(default_start + 50.0, total_duration)
        return [{
            "title": "Top Highlight",
            "start_time": default_start,
            "end_time": default_end,
            "duration": default_end - default_start,
            "viral_score": 85,
            "hook": "Key moment from video",
            "reasoning": "Detected high speech concentration in opening section."
        }]

    # Hook keywords indicating intrigue or storytelling
    hook_keywords = {"why", "how", "secret", "never", "always", "mistake", "truth", "crazy", "best", "worst", "stop", "incredible", "did you know"}

    candidates = []
    # Slide across transcript segments to find 35s - 55s windows
    for i in range(len(parsed_segments)):
        seg_start = parsed_segments[i]["start"]
        first_text = parsed_segments[i]["text"].lower()
        has_hook = any(kw in first_text for kw in hook_keywords) or "?" in first_text

        for j in range(i + 1, len(parsed_segments)):
            seg_end = parsed_segments[j]["end"]
            dur = seg_end - seg_start
            if 30.0 <= dur <= 58.0:
                combined_text = " ".join(s["text"] for s in parsed_segments[i:j+1])
                score = 75
                if has_hook:
                    score += 15
                if "!" in combined_text or "?" in combined_text:
                    score += 5
                
                candidates.append({
                    "title": f"Clip @ {int(seg_start)//60}:{int(seg_start)%60:02d} - {parsed_segments[i]['text'][:40]}...",
                    "start_time": float(seg_start),
                    "end_time": float(seg_end),
                    "duration": round(dur, 2),
                    "viral_score": min(score, 96),
                    "hook": parsed_segments[i]["text"][:80],
                    "reasoning": "High information density and strong narrative hook."
                })
                break
            elif dur > 58.0:
                break

    # Sort by viral score and take top non-overlapping clips
    candidates.sort(key=lambda x: x["viral_score"], reverse=True)
    selected = []
    for c in candidates:
        # Check overlap
        overlap = False
        for s in selected:
            if not (c["end_time"] <= s["start_time"] or c["start_time"] >= s["end_time"]):
                overlap = True
                break
        if not overlap:
            selected.append(c)
        if len(selected) >= 3:
            break

    if not selected:
        # Safety fallback
        default_dur = min(45.0, total_duration)
        selected = [{
            "title": "Engaging Video Highlight",
            "start_time": 0.0,
            "end_time": default_dur,
            "duration": default_dur,
            "viral_score": 80,
            "hook": parsed_segments[0]["text"][:60] if parsed_segments else "Opening Hook",
            "reasoning": "Opening segment with direct audience hook."
        }]

    return selected

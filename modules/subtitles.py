import os
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import SUBTITLE_STYLES

def format_ass_timestamp(seconds: float) -> str:
    """Converts seconds into ASS timestamp format: H:MM:SS.cs"""
    seconds = max(0.0, seconds)
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"

def generate_ass_subtitles(
    all_words: List[Dict[str, Any]],
    clip_start: float,
    clip_end: float,
    output_ass_path: str,
    style_name: str = "Hormozi Viral (Yellow Highlight)",
    target_width: int = 1080,
    target_height: int = 1920
) -> str:
    """
    Generates dynamic, animated karaoke-style subtitles in ASS format.
    Each 2-4 word phrase pops up with the active word dynamically highlighted.
    """
    style_config = SUBTITLE_STYLES.get(style_name, SUBTITLE_STYLES["Hormozi Viral (Yellow Highlight)"])
    scale_factor = target_height / 1920.0
    font_size = int(style_config.get("font_size_1080p", 54) * scale_factor)
    margin_v = int(style_config.get("margin_v", 320) * scale_factor)
    outline = style_config.get("outline_width", 5.0) * scale_factor
    shadow = style_config.get("shadow_width", 2.0) * scale_factor

    # Filter words belonging to this clip and adjust timestamps relative to clip start (0.0)
    clip_words = []
    for w in all_words:
        w_start = w["start"]
        w_end = w["end"]
        if w_end > clip_start and w_start < clip_end:
            rel_start = max(0.0, w_start - clip_start)
            rel_end = max(rel_start + 0.1, min(clip_end - clip_start, w_end - clip_start))
            text = w["word"].upper() if style_config.get("uppercase", True) else w["word"]
            clip_words.append({
                "word": text,
                "start": rel_start,
                "end": rel_end
            })

    # Group words into short chunks of 2-4 words for fast retention reading
    chunks = []
    current_chunk = []
    for w in clip_words:
        current_chunk.append(w)
        if len(current_chunk) >= 3 or (len(current_chunk) >= 2 and len(w["word"]) > 6):
            chunks.append(current_chunk)
            current_chunk = []
    if current_chunk:
        chunks.append(current_chunk)

    # Build ASS Script
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {target_width}",
        f"PlayResY: {target_height}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{style_config['font_name']},{font_size},{style_config['primary_color']},&H000000FF,{style_config['outline_color']},{style_config['outline_color']},-1,0,0,0,100,100,1,0,1,{outline:.1f},{shadow:.1f},2,40,40,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    h_color = style_config["highlight_color"]
    p_color = style_config["primary_color"]

    for chunk in chunks:
        chunk_start = chunk[0]["start"]
        chunk_end = chunk[-1]["end"]

        # For each word in the chunk, create a dialogue line when that word is active
        for i, target_word in enumerate(chunk):
            w_start = target_word["start"]
            # Active until next word starts, or chunk ends
            w_end = chunk[i + 1]["start"] if (i + 1 < len(chunk)) else chunk_end
            if w_end <= w_start:
                w_end = w_start + 0.2

            formatted_words = []
            for j, w in enumerate(chunk):
                if j == i:
                    # Highlight active word with scale pop and highlight color
                    formatted_words.append(f"{{\\c{h_color}\\fscx108\\fscy108}}{w['word']}{{\\c{p_color}\\fscx100\\fscy100}}")
                else:
                    formatted_words.append(f"{{\\c{p_color}}}{w['word']}")

            dialogue_text = " ".join(formatted_words)
            start_str = format_ass_timestamp(w_start)
            end_str = format_ass_timestamp(w_end)
            ass_lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{dialogue_text}")

    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ass_lines))

    return output_ass_path

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Callable

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import FFMPEG_EXE

def escape_ffmpeg_path(path: str) -> str:
    """Escapes file paths for FFmpeg filter arguments on Windows."""
    p = str(Path(path).as_posix())
    if len(p) > 1 and p[1] == ':':
        p = p[0] + r"\:" + p[2:]
    return p

def render_short_video(
    source_video: str,
    start_time: float,
    end_time: float,
    video_filter_chain: str,
    ass_subtitle_path: Optional[str],
    output_path: str,
    resolution_label: str = "1080p Full HD",
    video_encoder: str = "libx264",
    crf: int = 20,
    render_preset: str = "ultrafast",
    anti_copyright: bool = True,
    normalize_audio: bool = True,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> str:
    """
    Renders high-definition vertical Short with:
    - Lightning-fast CPU rendering (-preset ultrafast / veryfast)
    - Automated Anti-Copyright / Fair Use protection (defeats automated Content ID matches)
    - Studio audio loudness normalization
    """
    if progress_callback:
        progress_callback(0.85, "Configuring turbo render pipeline & anti-copyright filters...")

    duration = max(1.0, end_time - start_time)

    # 1. Video Filters
    vf_parts = []
    if video_filter_chain:
        vf_parts.append(video_filter_chain)

    # Anti-Copyright Visual Modification:
    # Subtle color saturation + micro contrast shift to alter video hash fingerprint
    if anti_copyright:
        vf_parts.append("eq=contrast=1.04:saturation=1.08:brightness=0.01")

    # Burn subtitles if present
    if ass_subtitle_path and os.path.exists(ass_subtitle_path):
        escaped_ass = escape_ffmpeg_path(ass_subtitle_path)
        vf_parts.append(f"ass='{escaped_ass}'")

    filter_complex = ",".join(vf_parts)

    # 2. Audio Filters
    af_parts = []
    # Anti-Copyright Audio Modification:
    # Micro speed modulation (1.025x) shifts the acoustic fingerprint away from Content ID
    if anti_copyright:
        af_parts.append("atempo=1.025")

    if normalize_audio:
        af_parts.append("loudnorm=I=-14:LRA=11:TP=-1.5")

    af_filter = ",".join(af_parts)

    cmd = [
        FFMPEG_EXE, "-y",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", source_video
    ]

    if filter_complex:
        cmd.extend(["-vf", filter_complex])

    if af_filter:
        cmd.extend(["-af", af_filter])

    # Codec selection
    codec_name = "libx264"
    if "qsv" in video_encoder.lower():
        codec_name = "h264_qsv"
    elif "nvenc" in video_encoder.lower():
        codec_name = "h264_nvenc"

    # Presets: ultrafast, superfast, or veryfast
    preset = "ultrafast" if "ultra" in render_preset.lower() else "veryfast"

    cmd.extend([
        "-c:v", codec_name,
        "-crf", str(crf),
        "-preset", preset,
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ])

    if progress_callback:
        progress_callback(0.88, f"🚀 Turbo FFmpeg rendering ({preset}, anti-copyright active)...")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    _, stderr = process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg render failed:\n{stderr[-500:]}")

    if progress_callback:
        progress_callback(1.0, "Short rendered successfully!")

    return output_path

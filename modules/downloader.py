import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Callable
import yt_dlp

# Ensure root config is importable regardless of working directory
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DOWNLOADS_DIR, TEMP_DIR, FFMPEG_EXE


def extract_video_info(url: str) -> Dict[str, Any]:
    """
    Extracts metadata from a YouTube video URL without downloading.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'id': info.get('id', ''),
            'title': info.get('title', 'Unknown Title'),
            'duration': info.get('duration', 0),
            'thumbnail': info.get('thumbnail', ''),
            'uploader': info.get('uploader', 'Unknown'),
            'view_count': info.get('view_count', 0),
            'description': info.get('description', '')
        }

def download_youtube_video(
    url: str,
    target_res: str = "1080p",
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Downloads YouTube video up to 4K (2160p) or 1080p with highest quality audio.
    Also extracts a 16kHz mono WAV for high-accuracy speech-to-text.

    Returns:
        (video_filepath, audio_filepath, video_metadata)
    """
    if progress_callback:
        progress_callback(0.05, "Fetching video metadata...")

    info = extract_video_info(url)
    video_id = info['id'] or "video"
    # Clean filename prefix
    safe_title = "".join(c for c in info['title'] if c.isalnum() or c in (' ', '_', '-')).rstrip()[:50]
    output_template = str(DOWNLOADS_DIR / f"{video_id}_{safe_title}.%(ext)s")

    max_height = 2160 if "4K" in target_res else 1080
    format_selector = (
        f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best"
    )

    def hook(d):
        if d['status'] == 'downloading' and progress_callback:
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            downloaded = d.get('downloaded_bytes', 0)
            percent = min(downloaded / total, 1.0)
            progress_callback(0.05 + percent * 0.45, f"Downloading video... {percent*100:.1f}%")

    ydl_opts = {
        'format': format_selector,
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'ffmpeg_location': FFMPEG_EXE,
        'progress_hooks': [hook],
        'quiet': True,
        'no_warnings': True,
    }

    if progress_callback:
        progress_callback(0.1, "Downloading high-resolution video streams...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        download_info = ydl.extract_info(url, download=True)
        video_filename = ydl.prepare_filename(download_info)
        # Handle merge output extension
        if not video_filename.endswith(".mp4"):
            base = os.path.splitext(video_filename)[0]
            if os.path.exists(f"{base}.mp4"):
                video_filename = f"{base}.mp4"

    if progress_callback:
        progress_callback(0.55, "Extracting audio for AI transcription...")

    # Extract 16kHz mono WAV for fast transcription
    audio_path = str(TEMP_DIR / f"{video_id}_audio.wav")
    ffmpeg_cmd = [
        FFMPEG_EXE, "-y",
        "-i", video_filename,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path
    ]
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    if progress_callback:
        progress_callback(0.60, "Audio ready for transcription.")

    return video_filename, audio_path, info

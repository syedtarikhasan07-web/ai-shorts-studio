import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Callable
import yt_dlp
import cv2

# Ensure root config is importable regardless of working directory
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DOWNLOADS_DIR, TEMP_DIR, FFMPEG_EXE


def get_cookie_file_path() -> Optional[str]:
    """Finds cookies.txt from project root, TEMP_DIR, or YOUTUBE_COOKIES env var."""
    root_cookie = Path(__file__).resolve().parent.parent / "cookies.txt"
    if root_cookie.exists():
        return str(root_cookie)

    temp_cookie = TEMP_DIR / "youtube_cookies.txt"
    if temp_cookie.exists():
        return str(temp_cookie)

    env_cookies = os.environ.get("YOUTUBE_COOKIES", "").strip()
    if env_cookies:
        if os.path.isfile(env_cookies):
            return env_cookies
        # Raw text in env var
        with open(temp_cookie, "w", encoding="utf-8") as f:
            f.write(env_cookies)
        return str(temp_cookie)

    return None




def get_base_ydl_opts() -> Dict[str, Any]:
    opts = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/125.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    cookie_path = get_cookie_file_path()

    if cookie_path:
        opts['cookiefile'] = cookie_path

    return opts



def extract_video_info(url: str) -> Dict[str, Any]:
    """
    Extracts metadata from a YouTube video URL without downloading.
    """
    ydl_opts = get_base_ydl_opts()
    ydl_opts['skip_download'] = True

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'id': info.get('id', ''),
                'title': info.get('title', 'Unknown Title'),
                'duration': int(info.get('duration') or 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'description': info.get('description', '')
            }
    except Exception as e:
        err_msg = str(e)
        if any(term in err_msg for term in ["bot", "Sign in", "429", "login", "automated", "player response", "Failed to extract"]):
            raise RuntimeError(
                "YouTube has blocked automated requests from this cloud server IP (anti-bot protection). "
                "Cloud datacenter IPs (such as Render/AWS) are restricted by YouTube without cookies. "
                "Recommended fixes: "
                "1) Run locally on your PC via 'START.bat' (your home IP is never blocked by YouTube!), "
                "2) Switch to the '📁 Upload Video File' tab to process any video directly, or "
                "3) Upload a YouTube cookies.txt in the sidebar settings."
            ) from e
        raise


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

    ydl_opts = get_base_ydl_opts()
    ydl_opts.update({
        'format': format_selector,
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'ffmpeg_location': FFMPEG_EXE,
        'progress_hooks': [hook],
    })

    if progress_callback:
        progress_callback(0.1, "Downloading high-resolution video streams...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            download_info = ydl.extract_info(url, download=True)
            video_filename = ydl.prepare_filename(download_info)
            if not video_filename.endswith(".mp4"):
                base = os.path.splitext(video_filename)[0]
                if os.path.exists(f"{base}.mp4"):
                    video_filename = f"{base}.mp4"
    except Exception as e:
        err_msg = str(e)
        if any(term in err_msg for term in ["bot", "Sign in", "429", "login", "automated", "player response", "Failed to extract"]):
            raise RuntimeError(
                "YouTube prevented the video stream download from this cloud IP. "
                "Please run locally on your PC via 'START.bat' (never blocked by YouTube) or use '📁 Upload Video File'."
            ) from e
        raise

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


def process_uploaded_video(
    uploaded_file,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Saves an uploaded video file, extracts metadata and 16kHz audio for AI processing.
    Completely bypasses YouTube restrictions.
    """
    if progress_callback:
        progress_callback(0.05, "Saving uploaded video...")

    clean_name = "".join(c for c in uploaded_file.name if c.isalnum() or c in (' ', '_', '-', '.')).strip()
    video_filepath = str(DOWNLOADS_DIR / clean_name)

    with open(video_filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if progress_callback:
        progress_callback(0.20, "Extracting video metadata...")

    # Get duration & info using OpenCV
    duration = 0
    cap = cv2.VideoCapture(video_filepath)
    if cap.isOpened():
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration = int(frame_count / fps)
        cap.release()

    stem = Path(clean_name).stem
    audio_path = str(TEMP_DIR / f"{stem}_audio.wav")

    if progress_callback:
        progress_callback(0.40, "Extracting audio for AI transcription...")

    ffmpeg_cmd = [
        FFMPEG_EXE, "-y",
        "-i", video_filepath,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path
    ]
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    info = {
        'id': stem,
        'title': stem,
        'duration': duration,
        'thumbnail': '',
        'uploader': 'Uploaded File',
        'view_count': 0,
        'description': ''
    }

    if progress_callback:
        progress_callback(0.60, "Video and audio ready for transcription.")

    return video_filepath, audio_path, info

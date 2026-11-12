import os
import subprocess
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
BIN_DIR = BASE_DIR / "bin"
DOWNLOADS_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"

for d in [BIN_DIR, DOWNLOADS_DIR, OUTPUT_DIR, TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Bundled FFmpeg & FFprobe configuration
FFMPEG_EXE = str(BIN_DIR / "ffmpeg.exe") if (BIN_DIR / "ffmpeg.exe").exists() else "ffmpeg"
FFPROBE_EXE = str(BIN_DIR / "ffprobe.exe") if (BIN_DIR / "ffprobe.exe").exists() else "ffprobe"

# Inject bin folder into process PATH so all tools (yt-dlp, subprocess) find FFmpeg immediately
if str(BIN_DIR) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = str(BIN_DIR) + os.pathsep + os.environ.get("PATH", "")

def get_ffmpeg_info() -> dict:
    """Returns FFmpeg version and supported hardware acceleration codecs."""
    try:
        res = subprocess.run([FFMPEG_EXE, "-version"], capture_output=True, text=True, check=False)
        first_line = res.stdout.splitlines()[0] if res.stdout else "FFmpeg Detected"
        return {
            "available": True,
            "path": FFMPEG_EXE,
            "version": first_line,
            "hardware_encoders": ["libx264 (CPU - Highest Quality)", "h264_qsv (Intel QuickSync)", "h264_nvenc (NVIDIA GPU)"]
        }
    except Exception as e:
        return {
            "available": False,
            "path": FFMPEG_EXE,
            "version": f"Not found: {e}",
            "hardware_encoders": ["libx264 (CPU)"]
        }

# Video Resolutions for YouTube Shorts (Vertical 9:16)
RESOLUTIONS = {
    "1080p Full HD": (1080, 1920),
    "4K Ultra HD": (2160, 3840)
}

# Subtitle Styles (Advanced SubStation Alpha / ASS configs)
SUBTITLE_STYLES = {
    "Hormozi Viral (Yellow Highlight)": {
        "font_name": "Arial",
        "font_size_1080p": 54,
        "primary_color": "&H00FFFFFF",      # White in BGR
        "highlight_color": "&H0000D7FF",    # Vibrant Yellow/Gold in BGR
        "outline_color": "&H00000000",      # Solid Black
        "outline_width": 5.0,
        "shadow_width": 2.0,
        "margin_v": 320,                    # Safe zone offset from bottom
        "uppercase": True
    },
    "Neon Cyber (Cyan & Green)": {
        "font_name": "Impact",
        "font_size_1080p": 56,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H00FFFF00",    # Cyan in BGR
        "outline_color": "&H00101010",
        "outline_width": 6.0,
        "shadow_width": 3.0,
        "margin_v": 330,
        "uppercase": True
    },
    "Clean Minimalist (White & Bold)": {
        "font_name": "Arial",
        "font_size_1080p": 48,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0000C8FF",    # Soft Amber
        "outline_color": "&H00202020",
        "outline_width": 4.0,
        "shadow_width": 1.5,
        "margin_v": 300,
        "uppercase": False
    }
}

# Cropping Modes
CROP_MODES = [
    "⚡ Instant Center Crop (0.0s)",
    "AI Face-Tracking Pan (Fast)",
    "Blurred Background Canvas"
]

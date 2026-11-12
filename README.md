# ⚡ AI Shorts Studio

An AI-powered program that automatically converts long YouTube videos into engaging, high-retention 1-minute YouTube Shorts (vertical 9:16) with **1080p Full HD** or **4K Ultra HD** resolution, smart face-tracking pan, and animated Hormozi-style subtitles.

---

## 🌟 Key Features

1. **One-Click YouTube Ingestion**:
   - Paste any YouTube link. Downloads the highest quality video (up to 4K 2160p) and uncompressed audio via `yt-dlp`.

2. **AI Viral Moment Detector**:
   - Analyzes full word-by-word transcripts for viral hooks, retention pacing, and complete narrative payoffs.
   - Evaluates clips between 30 and 60 seconds with Virality Scores (1-100) and rationale.
   - Works with Gemini 1.5/2.5 Flash API or with the built-in smart linguistic heuristic fallback (no API key required).

3. **Smart Vertical Framing (16:9 ➔ 9:16)**:
   - **AI Face-Tracking Pan**: Computer vision (OpenCV) detects speaker faces across the scene and smoothly tracks the speaker horizontally without jitter or sudden cuts.
   - **Blurred Background Canvas**: Keeps the original 16:9 video centered with a zoomed, blurred 9:16 backdrop (great for screen shares, tutorials, or wide shots).
   - **Static Center Crop**: Classic center crop.

4. **Animated Viral Subtitles (Hormozi Style)**:
   - Word-level timestamps powered by `faster-whisper`.
   - Karaoke-style active word highlighting (vibrant yellow/cyan) with thick black outlines for maximum readability.
   - Positioned in YouTube Shorts safe zones (avoids channel title and sidebar buttons).

5. **Broadcast Quality Rendering**:
   - Visually lossless rendering (`CRF 18`, `libx264`).
   - Integrated EBU R128 loudness normalization (`loudnorm`) so audio sounds loud, crisp, and studio-grade.

---

## 🚀 Quick Start

### 1. Launch the Web Interface
Double-click `run.bat` or run:
```bash
.venv\Scripts\activate
streamlit run app.py
```
This opens the web app in your browser at `http://localhost:8501`.

### 2. Create a Short in 3 Steps:
1. Paste a YouTube URL and click **"Analyze Video"**.
2. Click **"✨ 1-Click Detect Viral Moments & Prepare"**.
3. Select your favorite highlight from the AI list and click **"🚀 Render This Short Now"**.
4. Preview the vertical Short and click **"Download Ready-To-Upload Short"**!

---

## 📂 Project Structure

```
ai-shorts-generator/
│
├── app.py                     # Interactive Streamlit Web UI
├── config.py                  # Presets (resolutions, styles, paths)
├── requirements.txt           # Python dependencies
├── run.bat                    # 1-click launcher script
│
├── modules/
│   ├── downloader.py          # yt-dlp downloader & audio extractor
│   ├── transcriber.py         # faster-whisper word-level speech-to-text
│   ├── highlight_detector.py  # Gemini & heuristic viral moment AI
│   ├── face_tracker.py        # OpenCV face tracking & smooth 9:16 framing
│   ├── subtitles.py           # Animated karaoke ASS subtitle generator
│   └── video_editor.py        # High-definition FFmpeg renderer
│
├── downloads/                 # Downloaded source videos
├── temp/                      # Intermediate audio & subtitle files
└── output/                    # Ready-to-upload YouTube Shorts
```

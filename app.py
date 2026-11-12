import os
import importlib
from pathlib import Path
import streamlit as st
import config
importlib.reload(config)
from modules.downloader import extract_video_info, download_youtube_video
from modules.transcriber import transcribe_smart
from modules.highlight_detector import detect_viral_moments_gemini
from modules.face_tracker import compute_smart_crop_filter
from modules.subtitles import generate_ass_subtitles
from modules.video_editor import render_short_video

# Streamlit Page Config
st.set_page_config(
    page_title="AI Shorts Studio - 1-Click Viral Shorts Generator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #FF4B4B, #FF8533);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-header {
        color: #A0AEC0;
        font-size: 1.05rem;
        margin-bottom: 25px;
    }
    .metric-card {
        background-color: #1A1F2C;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #2D3748;
        margin-bottom: 12px;
    }
    .viral-badge {
        background: linear-gradient(135deg, #10B981, #059669);
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# App Header
st.markdown('<p class="main-header">⚡ AI Shorts Studio</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Turn long YouTube videos into viral 9:16 Shorts with AI highlights, smart face-tracking, animated captions, and bundled FFmpeg.</p>', unsafe_allow_html=True)

# Sidebar Settings
st.sidebar.title("⚙️ Generation Settings")

# Live FFmpeg Status Badge
ffmpeg_info = config.get_ffmpeg_info()
if ffmpeg_info["available"]:
    st.sidebar.success(f"🟢 **FFmpeg Engine Ready**\n\n`{ffmpeg_info['version'][:35]}...`")
else:
    st.sidebar.error(f"🔴 **FFmpeg Missing**: {ffmpeg_info['version']}")

resolution_label = st.sidebar.selectbox(
    "📺 Target Resolution",
    options=list(config.RESOLUTIONS.keys()),
    index=0,
    help="1080p Full HD (1080x1920) is standard for YouTube Shorts & TikTok. 4K Ultra HD (2160x3840) gives maximum clarity."
)
target_width, target_height = config.RESOLUTIONS[resolution_label]

crop_mode = st.sidebar.selectbox(
    "📐 Vertical Framing Mode",
    options=config.CROP_MODES,
    index=0,
    help="AI Face-Tracking Pan centers the speaker automatically. Blurred Background Canvas keeps full 16:9 in center with blurred vertical edges."
)

subtitle_style = st.sidebar.selectbox(
    "💬 Subtitle Style",
    options=list(config.SUBTITLE_STYLES.keys()) + ["No Subtitles"],
    index=0,
    help="Viral Alex Hormozi style highlights each word as it is spoken in yellow with high-contrast borders."
)

transcription_engine = st.sidebar.selectbox(
    "⚡ Transcription Engine",
    options=[
        "⚡ Auto-Fast (Instant Captions in 1s)",
        "🎙️ Turbo Whisper (Tiny - 5x Faster CPU)",
        "🎙️ Whisper Standard (Base)"
    ],
    index=0,
    help="Auto-Fast fetches existing YouTube captions in 1-2 seconds with zero CPU waiting. If captions don't exist, it falls back to Turbo Whisper."
)

# Anti-Copyright & Fast Render Controls
st.sidebar.markdown("---")
anti_copyright = st.sidebar.toggle(
    "🛡️ Anti-Copyright Protection",
    value=True,
    help="Alters audio acoustic hash (1.025x speed) and video color grading to bypass YouTube Content ID bots safely under Fair Use."
)

render_speed = st.sidebar.selectbox(
    "⚡ Rendering Speed",
    options=["🚀 Ultrafast (5x Faster)", "⚡ Veryfast"],
    index=0,
    help="Ultrafast renders vertical shorts in just seconds."
)

# Advanced FFmpeg Settings
with st.sidebar.expander("🎬 FFmpeg Encoding & Audio", expanded=False):
    selected_encoder = st.selectbox(
        "Video Encoder",
        options=ffmpeg_info.get("hardware_encoders", ["libx264 (CPU)"]),
        index=0,
        help="libx264 ensures crisp visually lossless quality. Intel QSV / NVENC accelerate encoding if supported."
    )
    crf_val = st.slider(
        "CRF Quality Level (Lower = Sharper)",
        min_value=15,
        max_value=28,
        value=18,
        help="18 is visually lossless. 16 is near-master quality."
    )
    loudnorm_enabled = st.checkbox(
        "Loudness Normalization (EBU R128 -14 LUFS)",
        value=True,
        help="Standardizes speech loudness to broadcast standards for clear, punchy sound."
    )

gemini_key = st.sidebar.text_input(
    "🔑 Gemini API Key (Optional)",
    value=os.environ.get("GEMINI_API_KEY", ""),
    type="password",
    help="Optional. If provided, uses Gemini Flash for AI highlight detection. If left empty, built-in smart linguistic detector will be used."
)

# Main Application Logic
url_input = st.text_input("🔗 Paste YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns([1, 4])
with col1:
    fetch_btn = st.button("🔍 Analyze Video", use_container_width=True)

# Session state initialization
if "video_info" not in st.session_state:
    st.session_state.video_info = None
if "transcription_data" not in st.session_state:
    st.session_state.transcription_data = None
if "detected_clips" not in st.session_state:
    st.session_state.detected_clips = None
if "video_path" not in st.session_state:
    st.session_state.video_path = None

if fetch_btn and url_input:
    try:
        with st.spinner("Fetching YouTube metadata..."):
            info = extract_video_info(url_input)
            st.session_state.video_info = info
            st.session_state.detected_clips = None
            st.session_state.transcription_data = None
    except Exception as e:
        st.error(f"Error reading YouTube URL: {e}")

# Display Video Card if metadata loaded
if st.session_state.video_info:
    info = st.session_state.video_info
    duration_min = info['duration'] // 60
    duration_sec = info['duration'] % 60

    st.markdown("---")
    c1, c2 = st.columns([1, 2])
    with c1:
        if info.get('thumbnail'):
            st.image(info['thumbnail'], use_container_width=True)
    with c2:
        st.subheader(info['title'])
        st.write(f"👤 **Channel:** {info['uploader']}")
        st.write(f"⏱️ **Duration:** {duration_min}m {duration_sec}s")
        st.write(f"👀 **Views:** {info.get('view_count', 0):,}")

    st.markdown("---")

    # Step 2: Download & Process Button
    if st.session_state.detected_clips is None:
        if st.button("✨ 1-Click Detect Viral Moments & Prepare", type="primary", use_container_width=True):
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def update_progress(val, text):
                progress_bar.progress(val)
                status_text.info(text)

            try:
                # 1. Download
                video_file, audio_file, _ = download_youtube_video(
                    url=url_input,
                    target_res=resolution_label,
                    progress_callback=update_progress
                )
                st.session_state.video_path = video_file

                # 2. Transcribe (Instant or Turbo)
                transcription = transcribe_smart(
                    url=url_input,
                    audio_path=audio_file,
                    engine_choice=transcription_engine,
                    model_size="tiny" if "Tiny" in transcription_engine or "Auto" in transcription_engine else "base",
                    progress_callback=update_progress
                )
                st.session_state.transcription_data = transcription

                # 3. Detect Highlights
                update_progress(0.80, "AI analyzing transcript for viral hooks and high-retention stories...")
                clips = detect_viral_moments_gemini(
                    transcript_text=transcription["formatted_transcript"],
                    video_title=info["title"],
                    duration=float(info["duration"]),
                    api_key=gemini_key
                )
                st.session_state.detected_clips = clips

                update_progress(1.0, "Analysis complete!")
                st.success("Successfully identified viral candidate clips!")
                st.rerun()

            except Exception as e:
                st.error(f"Processing failed: {e}")

# If clips detected, display selection and render UI
if st.session_state.detected_clips:
    st.subheader("🎯 Detected Viral Moments")
    st.caption("Select a moment to render as a vertical 9:16 Short:")

    clip_options = []
    for i, clip in enumerate(st.session_state.detected_clips):
        label = f"Clip #{i+1} [Viral Score: {clip.get('viral_score', 80)}/100] - {clip.get('title', 'Highlight')} ({clip['duration']}s)"
        clip_options.append(label)

    selected_idx = st.radio(
        "Choose clip:",
        options=range(len(clip_options)),
        format_func=lambda x: clip_options[x]
    )

    chosen_clip = st.session_state.detected_clips[selected_idx]
    
    # Details card
    start_m, start_s = divmod(int(chosen_clip['start_time']), 60)
    end_m, end_s = divmod(int(chosen_clip['end_time']), 60)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.info(f"⏱️ **Time Range:** {start_m:02d}:{start_s:02d} ➔ {end_m:02d}:{end_s:02d} ({chosen_clip['duration']}s)")
        st.write(f"🪝 **Opening Hook:** *\"{chosen_clip.get('hook', 'N/A')}\"*")
    with col_b:
        st.write(f"💡 **AI Rationale:** {chosen_clip.get('reasoning', 'High retention narrative')}")
        st.markdown(f'<span class="viral-badge">Virality Score: {chosen_clip.get("viral_score", 85)} / 100</span>', unsafe_allow_html=True)

    st.markdown("---")

    # Render Short Button
    if st.button("🚀 Render This Short Now", type="primary", use_container_width=True):
        r_progress = st.progress(0.0)
        r_status = st.empty()

        def render_update(val, text):
            r_progress.progress(val)
            r_status.info(text)

        try:
            video_path = st.session_state.video_path
            start_t = chosen_clip['start_time']
            end_t = chosen_clip['end_time']
            
            # 1. Smart Crop Filter
            render_update(0.2, f"Computing {crop_mode} framing for {target_width}x{target_height}...")
            crop_filter = compute_smart_crop_filter(
                video_path=video_path,
                start_time=start_t,
                end_time=end_t,
                crop_mode=crop_mode,
                target_width=target_width,
                target_height=target_height
            )

            # 2. Animated Subtitles
            ass_path = None
            if subtitle_style != "No Subtitles" and st.session_state.transcription_data:
                render_update(0.4, f"Generating {subtitle_style} animated captions...")
                ass_file = config.TEMP_DIR / f"clip_{selected_idx}.ass"
                ass_path = generate_ass_subtitles(
                    all_words=st.session_state.transcription_data["all_words"],
                    clip_start=start_t,
                    clip_end=end_t,
                    output_ass_path=str(ass_file),
                    style_name=subtitle_style,
                    target_width=target_width,
                    target_height=target_height
                )

            # 3. Final Render
            output_filename = f"Short_{st.session_state.video_info['id']}_clip{selected_idx+1}_{resolution_label.replace(' ', '_')}.mp4"
            final_output_path = str(config.OUTPUT_DIR / output_filename)

            render_update(0.6, f"Rendering final {resolution_label} Short via FFmpeg...")
            render_short_video(
                source_video=video_path,
                start_time=start_t,
                end_time=end_t,
                video_filter_chain=crop_filter,
                ass_subtitle_path=ass_path,
                output_path=final_output_path,
                resolution_label=resolution_label,
                video_encoder=selected_encoder,
                crf=crf_val,
                render_preset=render_speed,
                anti_copyright=anti_copyright,
                normalize_audio=loudnorm_enabled,
                progress_callback=render_update
            )

            r_progress.progress(1.0)
            r_status.success("🎉 Your YouTube Short is ready!")

            # Preview and Download
            st.balloons()
            st.subheader("🎬 Final Vertical Short Preview")
            
            p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
            with p_col2:
                st.video(final_output_path)
                with open(final_output_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Ready-To-Upload Short",
                        data=f,
                        file_name=output_filename,
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )

        except Exception as err:
            st.error(f"Render failed: {err}")

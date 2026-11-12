import os
import requests
from typing import List, Dict, Any, Optional, Callable
import yt_dlp
from faster_whisper import WhisperModel

def get_youtube_captions_fast(
    url: str,
    preferred_langs: List[str] = ["en", "en-US", "en-GB"],
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Optional[Dict[str, Any]]:
    """
    Extracts official or auto-generated YouTube captions with word/phrase timestamps in ~1-2 seconds!
    Bypasses heavy local CPU transcription completely.
    """
    if progress_callback:
        progress_callback(0.62, "Checking for instant YouTube captions (1-2s)...")

    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            sub_sources = [info.get('subtitles', {}), info.get('automatic_captions', {})]

            target_sub = None
            for source in sub_sources:
                if not source:
                    continue
                # 1. Try preferred languages
                for lang in preferred_langs:
                    if lang in source:
                        target_sub = source[lang]
                        break
                # 2. Try any English variation
                if not target_sub:
                    for k in source.keys():
                        if k.startswith("en"):
                            target_sub = source[k]
                            break
                # 3. Fallback to first available language
                if not target_sub and len(source) > 0:
                    target_sub = next(iter(source.values()))
                if target_sub:
                    break

            if not target_sub:
                return None

            # Look for json3 format (has precise timing metadata)
            json3_url = None
            for fmt in target_sub:
                if fmt.get('ext') == 'json3':
                    json3_url = fmt.get('url')
                    break
            if not json3_url and target_sub:
                json3_url = target_sub[0].get('url')

            if not json3_url:
                return None

            resp = requests.get(json3_url, timeout=10)
            if resp.status_code != 200:
                return None

            data = resp.json()
            events = data.get('events', [])
            if not events:
                return None

            all_words = []
            segments_data = []
            formatted_lines = []

            for idx, ev in enumerate(events):
                t_start = ev.get('tStartMs', 0) / 1000.0
                d_dur = ev.get('dDurationMs', 2000) / 1000.0
                t_end = t_start + d_dur
                segs = ev.get('segs', [])

                seg_text = ''.join(s.get('utf8', '') for s in segs).strip()
                if not seg_text or seg_text == '\n':
                    continue

                cleaned_text = ' '.join(seg_text.split())

                # Distribute word timings within segment
                seg_words = []
                words_in_seg = [w for w in cleaned_text.split() if w]
                if not words_in_seg:
                    continue

                word_duration = max(0.2, d_dur / len(words_in_seg))
                curr_w_start = t_start

                for w in words_in_seg:
                    w_end = min(t_end, curr_w_start + word_duration)
                    word_obj = {
                        "word": w,
                        "start": round(curr_w_start, 2),
                        "end": round(w_end, 2),
                        "probability": 1.0
                    }
                    seg_words.append(word_obj)
                    all_words.append(word_obj)
                    curr_w_start = w_end

                segments_data.append({
                    "id": idx,
                    "start": round(t_start, 2),
                    "end": round(t_end, 2),
                    "text": cleaned_text,
                    "words": seg_words
                })

                s_min, s_sec = divmod(int(t_start), 60)
                e_min, e_sec = divmod(int(t_end), 60)
                formatted_lines.append(
                    f"[{s_min:02d}:{s_sec:02d} -> {e_min:02d}:{e_sec:02d}] {cleaned_text}"
                )

            if all_words:
                if progress_callback:
                    progress_callback(0.78, "Instant YouTube captions parsed in ~1s!")
                return {
                    "source": "youtube_captions_fast",
                    "duration": round(segments_data[-1]["end"] if segments_data else 0, 2),
                    "segments": segments_data,
                    "all_words": all_words,
                    "formatted_transcript": "\n".join(formatted_lines)
                }

    except Exception as e:
        print(f"[Instant Captions Notice] {e}")

    return None

def transcribe_audio_whisper(
    audio_path: str,
    model_size: str = "tiny",
    device: str = "cpu",
    compute_type: str = "int8",
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Turbo-optimized faster-whisper transcription for CPU:
    - Uses greedy decoding (beam_size=1) for 500% speedup.
    - Utilizes all available CPU threads.
    - Faster VAD filter to skip silence.
    """
    cpu_cores = os.cpu_count() or 4
    if progress_callback:
        progress_callback(0.64, f"Running Turbo Whisper ({model_size}) on {cpu_cores} CPU threads...")

    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        cpu_threads=cpu_cores,
        num_workers=2
    )

    if progress_callback:
        progress_callback(0.68, "Fast speech-to-text transcribing...")

    segments_generator, info = model.transcribe(
        audio_path,
        beam_size=1,                      # Greedy decoding: 5x faster than beam_size=5!
        best_of=1,
        condition_on_previous_text=False, # Avoids slow repetitive loops
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=250)
    )

    segments_data = []
    all_words = []
    formatted_lines = []

    for seg in segments_generator:
        seg_words = []
        if seg.words:
            for w in seg.words:
                cleaned_word = w.word.strip()
                if cleaned_word:
                    word_obj = {
                        "word": cleaned_word,
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 2)
                    }
                    seg_words.append(word_obj)
                    all_words.append(word_obj)

        seg_dict = {
            "id": seg.id,
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
            "words": seg_words
        }
        segments_data.append(seg_dict)

        start_min, start_sec = divmod(int(seg.start), 60)
        end_min, end_sec = divmod(int(seg.end), 60)
        formatted_lines.append(
            f"[{start_min:02d}:{start_sec:02d} -> {end_min:02d}:{end_sec:02d}] {seg.text.strip()}"
        )

    formatted_transcript = "\n".join(formatted_lines)

    if progress_callback:
        progress_callback(0.78, "Turbo transcription completed.")

    return {
        "source": f"whisper_{model_size}",
        "language": getattr(info, "language", "en"),
        "duration": round(getattr(info, "duration", 0), 2),
        "segments": segments_data,
        "all_words": all_words,
        "formatted_transcript": formatted_transcript
    }

def transcribe_smart(
    url: str,
    audio_path: str,
    engine_choice: str = "⚡ Auto (Instant Captions > Turbo Whisper)",
    model_size: str = "tiny",
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Intelligent hybrid transcription:
    1. If Auto or Instant: Attempts to fetch YouTube captions in ~1 second.
    2. If unavailable or if Whisper explicitly chosen: runs Turbo Whisper on CPU.
    """
    if "Instant" in engine_choice or "Auto" in engine_choice:
        result = get_youtube_captions_fast(url, progress_callback=progress_callback)
        if result and len(result.get("all_words", [])) > 0:
            return result

    # Fallback to Turbo Whisper
    whisper_size = "tiny" if "tiny" in engine_choice.lower() else model_size
    return transcribe_audio_whisper(
        audio_path=audio_path,
        model_size=whisper_size,
        progress_callback=progress_callback
    )

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ASRSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class ASRResult:
    language: Optional[str]
    segments: list[ASRSegment]


def transcribe_with_faster_whisper(
    audio_path: Path,
    *,
    model_size: str = "small",
    compute_type: str = "int8",
    language: Optional[str] = "en",
    download_root: Optional[Path] = None,
) -> ASRResult:
    """
    Local ASR using faster-whisper.
    NOTE: This will download model weights on first run.
    """
    from faster_whisper import WhisperModel

    model = WhisperModel(
        model_size,
        device="auto",
        compute_type=compute_type,
        download_root=str(download_root) if download_root else None,
    )
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
        beam_size=5,
    )
    segments: list[ASRSegment] = []
    for s in segments_iter:
        txt = (s.text or "").strip()
        if not txt:
            continue
        segments.append(ASRSegment(start=float(s.start), end=float(s.end), text=txt))
    return ASRResult(language=getattr(info, "language", None), segments=segments)


def save_asr_result_json(result: ASRResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "language": result.language,
        "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in result.segments],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_asr_result_txt(result: ASRResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for s in result.segments:
        lines.append(f"[{s.start:0.2f}-{s.end:0.2f}] {s.text}")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


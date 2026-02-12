from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple

import httpx


def _safe_ext_from_type(audio_type: Optional[str]) -> str:
    if not audio_type:
        return ".audio"
    t = audio_type.lower()
    if "mpeg" in t or "mp3" in t:
        return ".mp3"
    if "mp4" in t or "m4a" in t:
        return ".m4a"
    if "wav" in t:
        return ".wav"
    if "ogg" in t:
        return ".ogg"
    return ".audio"


def build_audio_path(audio_root: Path, *, feed_slug: str, episode_id: str, audio_type: Optional[str]) -> Path:
    ext = _safe_ext_from_type(audio_type)
    return audio_root / feed_slug / f"{episode_id}{ext}"


def download_audio(url: str, dest: Path, *, timeout_s: float = 60.0) -> Tuple[Path, int]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")

    with httpx.stream("GET", url, timeout=timeout_s, follow_redirects=True) as r:
        r.raise_for_status()
        n = 0
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes():
                if not chunk:
                    continue
                f.write(chunk)
                n += len(chunk)

    tmp.replace(dest)
    return dest, n


def maybe_skip_download(dest: Path, expected_len: Optional[int]) -> bool:
    if not dest.exists():
        return False
    if expected_len is None:
        return True
    try:
        return dest.stat().st_size >= int(expected_len) * 0.95  # tolerate minor mismatch
    except Exception:
        return True


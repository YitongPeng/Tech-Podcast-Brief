from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import feedparser
import httpx
from dateutil import parser as dtparser

from .config import Feed


@dataclass(frozen=True)
class ParsedEpisode:
    title: str
    guid: Optional[str]
    published: Optional[str]  # ISO8601
    episode_url: Optional[str]
    audio_url: Optional[str]
    audio_type: Optional[str]
    audio_length_bytes: Optional[int]


def _to_iso8601(value: object) -> Optional[str]:
    if value is None:
        return None
    try:
        dt = dtparser.parse(str(value))
        if not dt.tzinfo:
            # treat as UTC if missing timezone
            dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return dt.isoformat()
    except Exception:
        return None


def parse_feed(feed: Feed, *, max_entries: int | None = None) -> list[ParsedEpisode]:
    # feedparser 直接拉 URL 在部分环境会遇到 SSL 验证问题；
    # 这里统一用 httpx(内置 certifi) 拉取后再交给 feedparser 解析。
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            r = httpx.get(
                feed.rss_url,
                timeout=30.0,
                follow_redirects=True,
                headers={"User-Agent": "podcast-brief/0.1"},
            )
            # 对 429 做轻量重试（避免 pod.link 这类代理限流导致全流程中断）
            if r.status_code == 429 and attempt < 2:
                continue
            r.raise_for_status()
            break
        except Exception as e:
            last_err = e
            if attempt >= 2:
                raise
    else:
        if last_err:
            raise last_err
    d = feedparser.parse(r.content)
    entries = d.entries[:max_entries] if max_entries else d.entries

    episodes: list[ParsedEpisode] = []
    for e in entries:
        title = (e.get("title") or "").strip() or "(untitled)"
        guid = e.get("id") or e.get("guid")
        published = _to_iso8601(e.get("published") or e.get("updated") or e.get("pubDate"))
        episode_url = e.get("link")

        audio_url = None
        audio_type = None
        audio_length_bytes = None
        for enc in e.get("enclosures", []) or []:
            href = enc.get("href")
            if not href:
                continue
            audio_url = href
            audio_type = enc.get("type")
            try:
                audio_length_bytes = int(enc.get("length")) if enc.get("length") else None
            except Exception:
                audio_length_bytes = None
            break

        # 一些 feed 会把 enclosure 放在 links 里
        if not audio_url:
            for l in e.get("links", []) or []:
                if l.get("rel") != "enclosure":
                    continue
                href = l.get("href")
                if not href:
                    continue
                audio_url = href
                audio_type = l.get("type")
                try:
                    audio_length_bytes = int(l.get("length")) if l.get("length") else None
                except Exception:
                    audio_length_bytes = None
                break

        episodes.append(
            ParsedEpisode(
                title=title,
                guid=str(guid) if guid else None,
                published=published,
                episode_url=str(episode_url) if episode_url else None,
                audio_url=str(audio_url) if audio_url else None,
                audio_type=str(audio_type) if audio_type else None,
                audio_length_bytes=audio_length_bytes,
            )
        )

    return episodes


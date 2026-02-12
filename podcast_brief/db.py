from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS episodes (
  episode_id TEXT PRIMARY KEY,
  feed_slug TEXT NOT NULL,
  feed_title TEXT NOT NULL,
  title TEXT NOT NULL,
  published TEXT,
  episode_url TEXT,
  audio_url TEXT,
  audio_type TEXT,
  audio_length_bytes INTEGER,
  status TEXT NOT NULL DEFAULT 'new',
  error TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_episodes_feed_published
ON episodes(feed_slug, published);
"""


def stable_episode_id(feed_slug: str, guid: Optional[str], audio_url: Optional[str], title: str) -> str:
    """
    Prefer feed-provided GUID; fall back to audio_url; finally title+feed.
    Returns a short hex string.
    """
    key = guid or audio_url or f"{feed_slug}:{title}"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return h[:24]


@dataclass(frozen=True)
class EpisodeRecord:
    episode_id: str
    feed_slug: str
    feed_title: str
    title: str
    published: Optional[str]
    episode_url: Optional[str]
    audio_url: Optional[str]
    audio_type: Optional[str]
    audio_length_bytes: Optional[int]
    status: str
    error: Optional[str]
    created_at: str
    updated_at: str


class EpisodeDB:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def close(self) -> None:
        self._conn.close()

    def _ensure_schema(self) -> None:
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    def upsert_episode(
        self,
        *,
        episode_id: str,
        feed_slug: str,
        feed_title: str,
        title: str,
        published: Optional[str],
        episode_url: Optional[str],
        audio_url: Optional[str],
        audio_type: Optional[str],
        audio_length_bytes: Optional[int],
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO episodes (
              episode_id, feed_slug, feed_title, title, published, episode_url,
              audio_url, audio_type, audio_length_bytes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(episode_id) DO UPDATE SET
              title=excluded.title,
              published=excluded.published,
              episode_url=excluded.episode_url,
              audio_url=excluded.audio_url,
              audio_type=excluded.audio_type,
              audio_length_bytes=excluded.audio_length_bytes,
              updated_at=datetime('now')
            """,
            (
                episode_id,
                feed_slug,
                feed_title,
                title,
                published,
                episode_url,
                audio_url,
                audio_type,
                audio_length_bytes,
            ),
        )
        self._conn.commit()

    def get_episode(self, episode_id: str) -> Optional[EpisodeRecord]:
        row = self._conn.execute(
            "SELECT * FROM episodes WHERE episode_id=?",
            (episode_id,),
        ).fetchone()
        if not row:
            return None
        return EpisodeRecord(**dict(row))

    def list_episodes(self, *, feed_slug: Optional[str] = None, status: Optional[str] = None) -> list[EpisodeRecord]:
        clauses = []
        params: list[object] = []
        if feed_slug:
            clauses.append("feed_slug=?")
            params.append(feed_slug)
        if status:
            clauses.append("status=?")
            params.append(status)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM episodes{where} ORDER BY published DESC, created_at DESC",
            params,
        ).fetchall()
        return [EpisodeRecord(**dict(r)) for r in rows]

    def set_status(self, episode_id: str, status: str, error: Optional[str] = None) -> None:
        self._conn.execute(
            """
            UPDATE episodes
            SET status=?, error=?, updated_at=datetime('now')
            WHERE episode_id=?
            """,
            (status, error, episode_id),
        )
        self._conn.commit()


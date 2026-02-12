from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from .db import EpisodeRecord


@dataclass(frozen=True)
class EpisodeWriteup:
    """
    MVP：先输出“可读、可追溯”的结构化 Markdown。
    后续接入 LLM 后，把 detail_sections/insights/labels 填充得更丰富即可。
    """

    episode_id: str
    feed_title: str
    title: str
    published: Optional[str]
    episode_url: Optional[str]
    audio_url: Optional[str]
    tags: list[str]
    bullets: list[str]


def render_episode_md(w: EpisodeWriteup) -> str:
    pub = w.published or ""
    lines = []
    lines.append(f"# {w.title}")
    lines.append("")
    lines.append(f"- **播客**：{w.feed_title}")
    if pub:
        lines.append(f"- **发布时间**：{pub}")
    if w.episode_url:
        lines.append(f"- **节目页**：{w.episode_url}")
    if w.audio_url:
        lines.append(f"- **音频**：{w.audio_url}")
    lines.append(f"- **Episode ID**：`{w.episode_id}`")
    lines.append("")

    if w.tags:
        lines.append("## 标签")
        lines.append("")
        lines.append("、".join([f"`{t}`" for t in w.tags]))
        lines.append("")

    if w.bullets:
        lines.append("## 要点")
        lines.append("")
        for b in w.bullets:
            lines.append(f"- {b}")
        lines.append("")

    lines.append("## 备注")
    lines.append("")
    lines.append("本文件为 MVP 产物：先保证**结构化**与**可追溯**。后续会接入翻译/主题聚合/启示生成。")
    lines.append("")
    return "\n".join(lines)


def render_daily_brief_md(date_str: str, episodes: list[EpisodeWriteup]) -> str:
    lines = []
    lines.append(f"# Daily Brief — {date_str}")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}")
    lines.append(f"- 今日新增：{len(episodes)} 集")
    lines.append("")

    for w in episodes:
        lines.append(f"## {w.feed_title} — {w.title}")
        lines.append("")
        if w.published:
            lines.append(f"- **发布时间**：{w.published}")
        if w.episode_url:
            lines.append(f"- **节目页**：{w.episode_url}")
        if w.audio_url:
            lines.append(f"- **音频**：{w.audio_url}")
        if w.tags:
            lines.append(f"- **标签**：{'、'.join([f'`{t}`' for t in w.tags])}")
        lines.append("")
        if w.bullets:
            for b in w.bullets[:8]:
                lines.append(f"- {b}")
            if len(w.bullets) > 8:
                lines.append(f"- （还有 {len(w.bullets) - 8} 条要点，详见单集文件）")
        else:
            lines.append("- （MVP 暂未生成要点：先完成 ASR 与入库）")
        lines.append("")

    return "\n".join(lines)


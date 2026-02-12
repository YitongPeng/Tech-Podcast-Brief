from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Feed:
    slug: str
    title: str
    rss_url: str


DEFAULT_FEEDS: list[Feed] = [
    # AI 技术与工程
    Feed(
        slug="latent-space",
        title="Latent Space",
        rss_url="https://feeds.flightcast.com/vgnxzgiwwzwke85ym53fjnzu.xml",
    ),
    # AI 产业与投资
    Feed(
        slug="no-priors",
        title="No Priors",
        rss_url="https://rss.art19.com/no-priors-ai",
    ),
    Feed(
        slug="a16z",
        title="The a16z Show",
        rss_url="https://feeds.soundcloud.com/users/soundcloud:users:62921190/sounds.rss",
    ),
    # 产品与增长
    Feed(
        slug="lennys-podcast",
        title="Lenny's Podcast",
        rss_url="https://pod.link/1627920305.rss",
    ),
    # 每日 AI 新闻
    Feed(
        slug="ai-daily-brief",
        title="The AI Daily Brief",
        rss_url="https://pod.link/1680633614.rss",
    ),
    # 科技新闻与访谈
    Feed(
        slug="bloomberg-tech",
        title="Bloomberg Tech",
        rss_url="https://www.omnycontent.com/d/playlist/e73c998e-6e60-432f-8610-ae210140c5b1/41764a4f-fc64-4e11-89ba-ae7c0030ab5e/9caafc41-289c-4115-995d-ae7c0030ab75/podcast.rss",
    ),
    Feed(
        slug="tech-brother",
        title="Technology Brother Podcast",
        rss_url="https://feeds.transistor.fm/technology-brother",
    ),
    # 创业与 YC
    Feed(
        slug="lightcone",
        title="Lightcone Podcast",
        rss_url="https://anchor.fm/s/f58d3330/podcast/rss",
    ),
    Feed(
        slug="minus-one",
        title="Minus One (SPC)",
        rss_url="https://anchor.fm/s/f91eac68/podcast/rss",
    ),
]


DATA_DIR_NAME = "data"


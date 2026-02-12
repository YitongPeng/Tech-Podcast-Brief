from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .audio import build_audio_path, download_audio, maybe_skip_download
from .asr import save_asr_result_json, save_asr_result_txt, transcribe_with_faster_whisper
from .config import DEFAULT_FEEDS
from .db import EpisodeDB, stable_episode_id
from .feishu import FeishuClient, get_feishu_config, send_feishu_webhook_message
from .feishu_publisher import publish_daily_brief_to_feishu_docx, publish_to_feishu_bitable
from .paths import get_project_paths
from .render import EpisodeWriteup, render_daily_brief_md, render_episode_md
from .rss import parse_feed
from .summarize import extract_summary_from_transcript
from .translate import get_deepseek_client, translate_transcript_file


app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def run(
    max_episodes_per_feed: int = typer.Option(1, help="每个 feed 处理最新几集（MVP 建议 1）"),
    asr: bool = typer.Option(True, help="是否执行本地 ASR（faster-whisper）"),
    asr_model: str = typer.Option("small", help="faster-whisper 模型大小：tiny/base/small/medium/large"),
    asr_compute_type: str = typer.Option("int8", help="faster-whisper compute_type，M1 推荐 int8"),
    translate: bool = typer.Option(True, help="是否翻译成中文（需要 DEEPSEEK_API_KEY）"),
    skip_existing: bool = typer.Option(True, help="已下载/已转写的内容是否跳过"),
    cleanup: bool = typer.Option(False, help="处理完后删除音频和转写文件（节省空间）"),
    keep_audio: bool = typer.Option(False, help="与 cleanup 配合使用：保留音频文件"),
    keep_transcripts: bool = typer.Option(False, help="与 cleanup 配合使用：保留转写文件"),
    publish_feishu: bool = typer.Option(False, help="发布到飞书多维表格和文档"),
    feishu_docx: bool = typer.Option(False, help="与 publish_feishu 配合使用：创建飞书 Daily Brief 文档"),
) -> None:
    """
    MVP：从默认 RSS 源拉取最新集 → 下载音频 → 本地 ASR → 翻译 → 总结 → 输出 Markdown + Daily Brief。
    """
    # 加载 .env
    load_dotenv()
    
    paths = get_project_paths()
    
    # 检查翻译所需的 API key
    deepseek_client = get_deepseek_client() if translate else None
    if translate and not deepseek_client:
        console.print("[yellow]提示：未配置 DEEPSEEK_API_KEY，将跳过翻译和总结步骤[/yellow]")
        console.print("[yellow]请在 .env 文件中配置（参考 .env.example）[/yellow]")
        translate = False
    
    # 检查飞书配置
    feishu_config = get_feishu_config() if publish_feishu else None
    feishu_client: Optional[FeishuClient] = None
    if publish_feishu:
        if not feishu_config:
            console.print("[yellow]提示：未配置飞书应用，将跳过飞书发布步骤[/yellow]")
            console.print("[yellow]请在 .env 文件中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET（参考 .env.example）[/yellow]")
            publish_feishu = False
        else:
            feishu_client = FeishuClient(feishu_config)
    paths.audio_dir.mkdir(parents=True, exist_ok=True)
    paths.transcripts_dir.mkdir(parents=True, exist_ok=True)
    paths.episode_outputs_dir.mkdir(parents=True, exist_ok=True)
    paths.daily_brief_dir.mkdir(parents=True, exist_ok=True)

    db = EpisodeDB(paths.db_path)
    new_writeups: list[EpisodeWriteup] = []
    model_cache_dir = paths.data_dir / "hf_models"

    try:
        for feed in DEFAULT_FEEDS:
            console.print(f"[bold]Feed[/bold] {feed.title} — {feed.rss_url}")
            try:
                episodes = parse_feed(feed, max_entries=max_episodes_per_feed)
            except Exception as e:
                console.print(f"[yellow]Feed 拉取失败，跳过[/yellow] {feed.title}: {e}")
                continue

            for ep in episodes:
                episode_id = stable_episode_id(feed.slug, ep.guid, ep.audio_url, ep.title)
                db.upsert_episode(
                    episode_id=episode_id,
                    feed_slug=feed.slug,
                    feed_title=feed.title,
                    title=ep.title,
                    published=ep.published,
                    episode_url=ep.episode_url,
                    audio_url=ep.audio_url,
                    audio_type=ep.audio_type,
                    audio_length_bytes=ep.audio_length_bytes,
                )

                rec = db.get_episode(episode_id)
                if not rec or not rec.audio_url:
                    db.set_status(episode_id, "no_audio", error="no audio_url in feed")
                    continue

                audio_path = build_audio_path(paths.audio_dir, feed_slug=feed.slug, episode_id=episode_id, audio_type=rec.audio_type)
                if not (skip_existing and maybe_skip_download(audio_path, rec.audio_length_bytes)):
                    try:
                        db.set_status(episode_id, "downloading", error=None)
                        download_audio(rec.audio_url, audio_path)
                        db.set_status(episode_id, "downloaded", error=None)
                    except Exception as e:
                        db.set_status(episode_id, "failed_download", error=str(e))
                        console.print(f"[red]下载失败[/red] {feed.title} — {rec.title}: {e}")
                        continue
                else:
                    if rec.status in ("new", "no_audio"):
                        db.set_status(episode_id, "downloaded", error=None)

                # ASR
                transcript_json = paths.transcripts_dir / feed.slug / f"{episode_id}.json"
                transcript_txt = paths.transcripts_dir / feed.slug / f"{episode_id}.txt"
                do_asr = asr and (not (skip_existing and transcript_json.exists()))
                if do_asr:
                    try:
                        db.set_status(episode_id, "asr_running", error=None)
                        result = transcribe_with_faster_whisper(
                            audio_path,
                            model_size=asr_model,
                            compute_type=asr_compute_type,
                            language="en",
                            download_root=model_cache_dir,
                        )
                        save_asr_result_json(result, transcript_json)
                        save_asr_result_txt(result, transcript_txt)
                        db.set_status(episode_id, "asr_done", error=None)
                    except Exception as e:
                        db.set_status(episode_id, "failed_asr", error=str(e))
                        console.print(f"[red]ASR 失败[/red] {feed.title} — {rec.title}: {e}")
                        continue
                else:
                    if rec.status == "downloaded" and transcript_json.exists():
                        db.set_status(episode_id, "asr_done", error=None)

                # 翻译
                transcript_cn_txt = paths.transcripts_dir / feed.slug / f"{episode_id}_cn.txt"
                do_translate = translate and deepseek_client and transcript_txt.exists()
                do_translate = do_translate and not (skip_existing and transcript_cn_txt.exists())
                if do_translate:
                    try:
                        db.set_status(episode_id, "translating", error=None)
                        console.print(f"[cyan]翻译中[/cyan] {feed.title} — {rec.title}")
                        translate_transcript_file(
                            transcript_txt,
                            transcript_cn_txt,
                            client=deepseek_client,
                            chunk_size=15,
                        )
                        db.set_status(episode_id, "translated", error=None)
                    except Exception as e:
                        db.set_status(episode_id, "failed_translation", error=str(e))
                        console.print(f"[red]翻译失败[/red] {feed.title} — {rec.title}: {e}")
                        # 翻译失败不影响后续流程，继续生成英文版
                else:
                    if transcript_cn_txt.exists():
                        db.set_status(episode_id, "translated", error=None)

                # 结构化总结（用 LLM 提取要点，而不是傻瓜式截取前 N 行）
                tags: list[str] = []
                bullets: list[str] = []
                
                # 如果有中文转写 + API key，用 LLM 提取核心内容
                if transcript_cn_txt.exists() and deepseek_client:
                    try:
                        db.set_status(episode_id, "summarizing", error=None)
                        console.print(f"[cyan]总结中[/cyan] {feed.title} — {rec.title}")
                        summary = extract_summary_from_transcript(
                            transcript_cn_txt,
                            client=deepseek_client,
                            episode_title=rec.title,
                            feed_title=feed.title,
                        )
                        tags = summary.tags
                        bullets = summary.key_points
                        db.set_status(episode_id, "summarized", error=None)
                        console.print(f"[green]✓ 总结完成[/green] {len(bullets)} 个要点")
                    except Exception as e:
                        db.set_status(episode_id, "failed_summary", error=str(e))
                        console.print(f"[yellow]总结失败[/yellow] {feed.title} — {rec.title}: {e}")
                        # 总结失败不影响流程，继续用占位内容
                        bullets = ["（LLM 总结失败，使用占位内容）"]
                else:
                    # 如果没有中文转写或 API key，用简单占位
                    bullets = ["（未启用 LLM 总结，这是占位内容）"]

                w = EpisodeWriteup(
                    episode_id=episode_id,
                    feed_title=feed.title,
                    title=rec.title,
                    published=rec.published,
                    episode_url=rec.episode_url,
                    audio_url=rec.audio_url,
                    tags=tags,
                    bullets=bullets,
                )
                out_path = paths.episode_outputs_dir / feed.slug / f"{episode_id}.md"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(render_episode_md(w), encoding="utf-8")
                db.set_status(episode_id, "rendered", error=None)
                new_writeups.append(w)

        # Daily brief（按今天生成）
        today = date.today().isoformat()
        daily_path = paths.daily_brief_dir / f"{today}.md"
        daily_path.write_text(render_daily_brief_md(today, new_writeups), encoding="utf-8")

        # 打印结果表
        table = Table(title="本次处理结果")
        table.add_column("Feed")
        table.add_column("Title")
        table.add_column("Episode ID")
        table.add_column("Status")
        for w in new_writeups:
            rec = db.get_episode(w.episode_id)
            table.add_row(w.feed_title, w.title[:60], w.episode_id, rec.status if rec else "-")
        console.print(table)
        console.print(f"[green]Daily Brief 已生成[/green] {daily_path}")
        
        # 发布到飞书（如果启用）
        # 飞书发布结果（用于后续webhook通知）
        feishu_publish_result = {
            "success": False,
            "new_records": 0,
            "skipped_records": 0,
            "all_tags": [],
            "doc_url": None,
        }
        
        if publish_feishu and feishu_client and feishu_config:
            console.print("\n[cyan]发布到飞书...[/cyan]")
            
            try:
                # 发布到多维表格
                if feishu_config.bitable_app_token and feishu_config.bitable_table_id:
                    console.print("  - 检查并写入多维表格...")
                    bitable_records, all_tags, skipped = publish_to_feishu_bitable(
                        feishu_client,
                        feishu_config,
                        new_writeups,
                    )
                    
                    feishu_publish_result["new_records"] = len(bitable_records) if bitable_records else 0
                    feishu_publish_result["skipped_records"] = skipped
                    feishu_publish_result["all_tags"] = all_tags
                    
                    if bitable_records:
                        console.print(f"[green]  ✓ 多维表格写入成功[/green] {len(bitable_records)} 条新记录")
                    if skipped > 0:
                        console.print(f"[yellow]  ⊙ 跳过重复记录[/yellow] {skipped} 条")
                    
                    # 显示本次使用的所有标签（提示用户检查飞书字段选项）
                    if all_tags:
                        console.print(f"\n[cyan]本次播客标签[/cyan] ({len(all_tags)} 个):")
                        console.print(f"  {', '.join(all_tags)}")
                        console.print("\n[yellow]提示[/yellow]: 如果某些标签未在飞书表格中显示，")
                        console.print("  请在飞书「标签」字段设置中添加对应选项")
                else:
                    console.print("[yellow]  跳过多维表格（未配置 FEISHU_BITABLE_APP_TOKEN 或 FEISHU_BITABLE_TABLE_ID）[/yellow]")
                
                # 创建飞书文档（可选）
                if feishu_docx:
                    console.print("  - 创建 Daily Brief 文档...")
                    docx_result = publish_daily_brief_to_feishu_docx(
                        feishu_client,
                        new_writeups,
                        today,
                        folder_token=None,  # 可以后续支持指定文件夹
                    )
                    console.print(f"[green]  ✓ 文档创建成功[/green] {docx_result['title']}")
                    console.print(f"  文档 ID: {docx_result['document_id']}")
                    
                    # 如果配置了飞书域名，显示完整链接
                    if feishu_config.domain:
                        doc_url = f"https://{feishu_config.domain}.feishu.cn/docx/{docx_result['document_id']}"
                        console.print(f"  [link={doc_url}]📄 点击打开文档[/link]")
                        console.print(f"  链接: {doc_url}")
                        feishu_publish_result["doc_url"] = doc_url
                
                feishu_publish_result["success"] = True
            except Exception as e:
                console.print(f"[red]飞书发布失败[/red] {e}")
            finally:
                if feishu_client:
                    feishu_client.close()
        
        # 清理中间文件（如果启用）
        if cleanup:
            console.print("\n[cyan]清理中间文件...[/cyan]")
            cleaned_audio_size = 0
            cleaned_transcript_size = 0
            
            for w in new_writeups:
                rec = db.get_episode(w.episode_id)
                if not rec:
                    continue
                
                # 清理音频
                if not keep_audio:
                    audio_path = build_audio_path(
                        paths.audio_dir,
                        feed_slug=rec.feed_slug,
                        episode_id=rec.episode_id,
                        audio_type=rec.audio_type,
                    )
                    if audio_path.exists():
                        cleaned_audio_size += audio_path.stat().st_size
                        audio_path.unlink()
                
                # 清理转写文件
                if not keep_transcripts:
                    transcript_json = paths.transcripts_dir / rec.feed_slug / f"{rec.episode_id}.json"
                    transcript_txt = paths.transcripts_dir / rec.feed_slug / f"{rec.episode_id}.txt"
                    transcript_cn_txt = paths.transcripts_dir / rec.feed_slug / f"{rec.episode_id}_cn.txt"
                    
                    for f in [transcript_json, transcript_txt, transcript_cn_txt]:
                        if f.exists():
                            cleaned_transcript_size += f.stat().st_size
                            f.unlink()
            
            # 显示清理结果
            total_cleaned_mb = (cleaned_audio_size + cleaned_transcript_size) / (1024 * 1024)
            console.print(f"[green]✓ 清理完成[/green] 释放空间: {total_cleaned_mb:.1f} MB")
            if not keep_audio:
                console.print(f"  - 音频: {cleaned_audio_size / (1024 * 1024):.1f} MB")
            if not keep_transcripts:
                console.print(f"  - 转写: {cleaned_transcript_size / (1024 * 1024):.2f} MB")
        
        # 发送飞书 Webhook 通知（如果配置了）
        webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
        if webhook_url and feishu_publish_result["success"]:
            console.print("\n[cyan]📬 发送飞书通知...[/cyan]")
            
            # 构建消息内容
            content_lines = []
            
            # 统计信息
            content_lines.append(f"**今日处理**：{len(new_writeups)} 集播客")
            if feishu_publish_result["new_records"] > 0:
                content_lines.append(f"**新增记录**：{feishu_publish_result['new_records']} 条")
            if feishu_publish_result["skipped_records"] > 0:
                content_lines.append(f"**跳过重复**：{feishu_publish_result['skipped_records']} 条")
            
            # 标签信息
            if feishu_publish_result["all_tags"]:
                tags_text = "、".join(feishu_publish_result["all_tags"][:10])
                if len(feishu_publish_result["all_tags"]) > 10:
                    tags_text += f" 等 {len(feishu_publish_result['all_tags'])} 个"
                content_lines.append(f"\n**本次标签**：{tags_text}")
                content_lines.append("\n_如标签未显示，请在飞书「标签」字段中添加选项_")
            
            send_feishu_webhook_message(
                webhook_url=webhook_url,
                title=f"🎙️ 播客更新通知 — {today}",
                content_lines=content_lines,
                doc_url=feishu_publish_result.get("doc_url"),
            )
            console.print("[green]  ✓ 通知已发送[/green]")
    finally:
        db.close()


@app.command()
def clean(
    keep_audio: bool = typer.Option(False, help="保留音频文件"),
    keep_transcripts: bool = typer.Option(False, help="保留转写文件"),
    dry_run: bool = typer.Option(False, help="预览将删除的文件，不实际删除"),
) -> None:
    """
    清理历史中间文件（音频、转写），释放存储空间。
    """
    paths = get_project_paths()
    
    # 统计文件
    audio_files = list(paths.audio_dir.rglob("*")) if paths.audio_dir.exists() else []
    transcript_files = list(paths.transcripts_dir.rglob("*")) if paths.transcripts_dir.exists() else []
    
    # 过滤出文件（不包括目录）
    audio_files = [f for f in audio_files if f.is_file()]
    transcript_files = [f for f in transcript_files if f.is_file()]
    
    audio_size = sum(f.stat().st_size for f in audio_files) if not keep_audio else 0
    transcript_size = sum(f.stat().st_size for f in transcript_files) if not keep_transcripts else 0
    
    console.print(f"\n[cyan]扫描结果[/cyan]")
    if not keep_audio:
        console.print(f"  - 音频文件: {len(audio_files)} 个，{audio_size / (1024 * 1024):.1f} MB")
    if not keep_transcripts:
        console.print(f"  - 转写文件: {len(transcript_files)} 个，{transcript_size / (1024 * 1024):.2f} MB")
    
    total_mb = (audio_size + transcript_size) / (1024 * 1024)
    console.print(f"  - [bold]总计: {total_mb:.1f} MB[/bold]")
    
    if dry_run:
        console.print("\n[yellow]预览模式：不会实际删除文件[/yellow]")
        return
    
    # 确认删除
    if total_mb > 0:
        confirm = typer.confirm("\n确定要删除这些文件吗？")
        if not confirm:
            console.print("[yellow]已取消[/yellow]")
            return
        
        # 执行删除
        if not keep_audio:
            for f in audio_files:
                f.unlink()
        if not keep_transcripts:
            for f in transcript_files:
                f.unlink()
        
        console.print(f"\n[green]✓ 清理完成[/green] 释放空间: {total_mb:.1f} MB")
    else:
        console.print("\n[yellow]没有文件需要清理[/yellow]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()

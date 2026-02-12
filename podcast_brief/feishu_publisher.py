from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from dateutil import parser as date_parser

from .feishu import FeishuClient, FeishuConfig
from .render import EpisodeWriteup


def _parse_date_to_timestamp(date_str: Optional[str]) -> Optional[int]:
    """
    将日期字符串转换为飞书日期字段所需的时间戳（毫秒）。
    
    飞书日期字段接受：
    - 时间戳（毫秒）：例如 1707696300000
    - null（不填）
    
    不接受 ISO 8601 字符串。
    """
    if not date_str:
        return None
    
    try:
        dt = date_parser.parse(date_str)
        # 转换为毫秒时间戳
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def episode_to_bitable_record(episode: EpisodeWriteup) -> dict[str, Any]:
    """
    将 EpisodeWriteup 转换为飞书多维表格记录格式。
    
    字段映射：
    - 播客名称：单行文本
    - Episode 标题：单行文本
    - 发布时间：日期（时间戳毫秒）
    - 节目页：URL
    - 音频：URL
    - 标签：多选（只包含已在飞书中配置的选项）
    - 核心要点：多行文本
    - Episode ID：单行文本
    
    注意：
    - 如果 LLM 返回的标签不在飞书字段选项中，写入时会被飞书忽略
    - 未匹配的标签会在日志中显示，提示用户手动添加
    """
    # 格式化要点（带序号）
    bullets_text = "\n".join([f"{i+1}. {b}" for i, b in enumerate(episode.bullets)])
    
    # 标签列表（飞书多选字段）
    # 注意：只有在飞书字段选项中存在的标签才会被保存
    # 新标签需要先在飞书界面手动添加到字段选项
    tags = episode.tags if episode.tags else []
    
    # 转换日期为时间戳
    published_timestamp = _parse_date_to_timestamp(episode.published)
    
    record = {
        "播客名称": episode.feed_title,
        "Episode 标题": episode.title,
        "标签": tags,  # 多选字段
        "核心要点": bullets_text,
        "Episode ID": episode.episode_id,
    }
    
    # 可选字段：只有在有值时才添加
    if published_timestamp:
        record["发布时间"] = published_timestamp
    
    # 飞书 URL 字段格式：可以是字符串或对象 {"link": "url", "text": "显示文本"}
    # 这里尝试使用对象格式
    if episode.episode_url:
        record["节目页"] = {"link": episode.episode_url}
    
    if episode.audio_url:
        record["音频"] = {"link": episode.audio_url}
    
    return record


def publish_to_feishu_bitable(
    client: FeishuClient,
    config: FeishuConfig,
    episodes: list[EpisodeWriteup],
) -> tuple[list[dict], list[str], int]:
    """
    批量发布播客记录到飞书多维表格（自动去重）。
    
    Returns:
        (创建的记录列表, 所有标签列表, 跳过的重复记录数)
    """
    if not config.bitable_app_token or not config.bitable_table_id:
        raise ValueError("未配置飞书多维表格（FEISHU_BITABLE_APP_TOKEN 或 FEISHU_BITABLE_TABLE_ID 缺失）")
    
    # 过滤出需要发布的记录（检查是否已存在）
    records_to_publish = []
    skipped_count = 0
    
    for ep in episodes:
        # 通过 Episode ID 查询是否已存在
        existing = client.search_bitable_records(
            app_token=config.bitable_app_token,
            table_id=config.bitable_table_id,
            field_name="Episode ID",
            field_value=ep.episode_id,
        )
        
        if existing:
            # 已存在，跳过
            skipped_count += 1
            continue
        
        # 不存在，添加到待发布列表
        records_to_publish.append(episode_to_bitable_record(ep))
    
    # 收集所有标签（用于后续提示用户）
    all_tags = set()
    for ep in episodes:
        all_tags.update(ep.tags)
    
    # 如果没有需要发布的记录，直接返回
    if not records_to_publish:
        return [], sorted(all_tags), skipped_count
    
    # 飞书批量创建最多 500 条，这里暂时不考虑分批
    result = client.batch_add_bitable_records(
        app_token=config.bitable_app_token,
        table_id=config.bitable_table_id,
        records=records_to_publish,
    )
    
    return result.get("data", {}).get("records", []), sorted(all_tags), skipped_count


def generate_feishu_docx_blocks(episodes: list[EpisodeWriteup], date_str: str) -> list[dict]:
    """
    生成飞书文档的内容块列表（用于 Daily Brief）。
    
    飞书文档块类型（正确定义）：
    - block_type: 2 = 文本段落（text）
    - block_type: 3 = 一级标题（heading1）
    - block_type: 4 = 二级标题（heading2）
    
    文档：https://open.feishu.cn/document/server-docs/docs/docs-v2/document-block/block_type
    """
    blocks = []
    
    # 标题（一级标题）
    blocks.append({
        "block_type": 3,  # heading1
        "heading1": {
            "elements": [{"text_run": {"content": f"Daily Brief — {date_str}"}}],
            "style": {}
        },
    })
    
    # 元信息（文本段落）
    meta_text = f"生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}\n今日新增：{len(episodes)} 集"
    blocks.append({
        "block_type": 2,  # text（文本段落）
        "text": {
            "elements": [{"text_run": {"content": meta_text}}],
            "style": {}
        },
    })
    
    # 每集内容
    for ep in episodes:
        # 二级标题：播客名 — Episode 标题
        blocks.append({
            "block_type": 4,  # heading2（二级标题）
            "heading2": {
                "elements": [{"text_run": {"content": f"{ep.feed_title} — {ep.title}"}}],
                "style": {}
            },
        })
        
        # 元信息（发布时间、链接）
        meta_lines = []
        if ep.published:
            meta_lines.append(f"发布时间：{ep.published}")
        if ep.episode_url:
            meta_lines.append(f"节目页：{ep.episode_url}")
        if ep.audio_url:
            meta_lines.append(f"音频：{ep.audio_url}")
        if ep.tags:
            meta_lines.append(f"标签：{'、'.join([f'`{t}`' for t in ep.tags])}")
        
        if meta_lines:
            blocks.append({
                "block_type": 2,  # text（文本段落）
                "text": {
                    "elements": [{"text_run": {"content": "\n".join(meta_lines)}}],
                    "style": {}
                },
            })
        
        # 核心要点（简化：合并为一个文本块）
        if ep.bullets:
            bullets_text = "核心要点：\n" + "\n".join([f"• {b}" for b in ep.bullets[:8]])
            if len(ep.bullets) > 8:
                bullets_text += f"\n（还有 {len(ep.bullets) - 8} 条要点，详见多维表格）"
            
            blocks.append({
                "block_type": 2,  # text（文本段落）
                "text": {
                    "elements": [{"text_run": {"content": bullets_text}}],
                    "style": {}
                },
            })
        
        # 空行分隔
        blocks.append({
            "block_type": 2,  # text（文本段落）
            "text": {
                "elements": [{"text_run": {"content": ""}}],
                "style": {}
            },
        })
    
    return blocks


def publish_daily_brief_to_feishu_docx(
    client: FeishuClient,
    episodes: list[EpisodeWriteup],
    date_str: str,
    folder_token: str | None = None,
) -> dict:
    """
    发布 Daily Brief 到飞书文档。
    
    Args:
        client: 飞书客户端
        episodes: 播客列表
        date_str: 日期字符串（例如 "2026-02-11"）
        folder_token: 飞书文件夹 token（可选）
    
    Returns:
        文档信息（包括 document_id 和 url）
    """
    title = f"Daily Brief — {date_str}"
    
    # 创建文档
    doc_result = client.create_docx(folder_token=folder_token, title=title)
    document_id = doc_result["data"]["document"]["document_id"]
    
    # 生成内容块
    blocks = generate_feishu_docx_blocks(episodes, date_str)
    
    # 写入内容
    client.update_docx_content(document_id, blocks)
    
    return {
        "document_id": document_id,
        "url": f"https://example.feishu.cn/docx/{document_id}",  # 飞书文档链接
        "title": title,
    }

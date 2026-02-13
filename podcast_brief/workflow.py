"""
LangGraph 工作流定义
将播客处理流程改造为状态图
"""
from __future__ import annotations

from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END


class PodcastEpisodeState(TypedDict):
    """单集播客处理状态"""
    # 基础信息
    feed_name: str
    episode_id: str
    episode_title: str
    episode_url: str
    published_date: str
    
    # 处理路径
    audio_path: Optional[str]
    transcript_en_path: Optional[str]
    transcript_cn_path: Optional[str]
    markdown_path: Optional[str]
    
    # 内容数据
    transcript_en: Optional[str]
    transcript_cn: Optional[str]
    tags: List[str]
    bullets: List[str]
    guest_info: Optional[str]
    episode_type: str
    
    # 状态标记
    audio_downloaded: bool
    transcribed: bool
    translated: bool
    summarized: bool
    published_to_feishu: bool
    
    # 错误信息
    error: Optional[str]


def download_audio_node(state: PodcastEpisodeState) -> PodcastEpisodeState:
    """下载音频节点"""
    from .audio import download_audio, build_audio_path
    from .paths import get_project_paths
    
    paths = get_project_paths()
    audio_path = build_audio_path(
        paths.audio_dir,
        feed_slug=state["feed_name"],
        episode_id=state["episode_id"],
        audio_type=None,
    )
    
    try:
        download_audio(state["episode_url"], audio_path)
        return {
            **state,
            "audio_path": str(audio_path),
            "audio_downloaded": True,
        }
    except Exception as e:
        return {
            **state,
            "error": f"下载音频失败: {str(e)}",
            "audio_downloaded": False,
        }


def transcribe_node(state: PodcastEpisodeState) -> PodcastEpisodeState:
    """ASR 转写节点"""
    from .asr import transcribe_with_faster_whisper, save_asr_result_json, save_asr_result_txt
    from .paths import get_project_paths
    from pathlib import Path
    
    if not state["audio_downloaded"]:
        return {**state, "error": "音频未下载，跳过转写"}
    
    paths = get_project_paths()
    audio_path = Path(state["audio_path"])
    
    try:
        segments = transcribe_with_faster_whisper(
            audio_path, 
            model_size="tiny",
            compute_type="int8",
            language="en",
        )
        
        # 保存结果
        json_path = paths.transcripts_dir / state["feed_name"] / f"{state['episode_id']}.json"
        txt_path = paths.transcripts_dir / state["feed_name"] / f"{state['episode_id']}.txt"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        save_asr_result_json(segments, json_path)
        save_asr_result_txt(segments, txt_path)
        
        # 读取文本内容
        transcript_en = txt_path.read_text(encoding="utf-8")
        
        return {
            **state,
            "transcript_en_path": str(txt_path),
            "transcript_en": transcript_en,
            "transcribed": True,
        }
    except Exception as e:
        return {
            **state,
            "error": f"转写失败: {str(e)}",
            "transcribed": False,
        }


def translate_node(state: PodcastEpisodeState) -> PodcastEpisodeState:
    """翻译节点"""
    from .translate import translate_transcript_file, get_deepseek_client
    from .paths import get_project_paths
    from pathlib import Path
    
    if not state["transcribed"]:
        return {**state, "error": "转写未完成，跳过翻译"}
    
    paths = get_project_paths()
    client = get_deepseek_client()
    
    try:
        en_path = Path(state["transcript_en_path"])
        cn_path = paths.transcripts_dir / state["feed_name"] / f"{state['episode_id']}_cn.txt"
        
        result = translate_transcript_file(
            en_path,
            cn_path,
            client=client,
        )
        
        transcript_cn = cn_path.read_text(encoding="utf-8")
        
        return {
            **state,
            "transcript_cn_path": str(cn_path),
            "transcript_cn": transcript_cn,
            "translated": True,
        }
    except Exception as e:
        return {
            **state,
            "error": f"翻译失败: {str(e)}",
            "translated": False,
        }


def summarize_node(state: PodcastEpisodeState) -> PodcastEpisodeState:
    """总结节点"""
    from .summarize import extract_summary_from_transcript
    from .translate import get_deepseek_client
    
    if not state["translated"]:
        return {**state, "error": "翻译未完成，跳过总结"}
    
    client = get_deepseek_client()
    
    try:
        from pathlib import Path
        cn_path = Path(state["transcript_cn_path"])
        
        summary = extract_summary_from_transcript(
            cn_path,
            client=client,
            episode_title=state["episode_title"],
            feed_title=state["feed_name"],
        )
        
        return {
            **state,
            "tags": summary.tags,
            "bullets": summary.key_points,
            "guest_info": summary.guest_info,
            "episode_type": summary.episode_type,
            "summarized": True,
        }
    except Exception as e:
        return {
            **state,
            "error": f"总结失败: {str(e)}",
            "summarized": False,
        }


def publish_node(state: PodcastEpisodeState) -> PodcastEpisodeState:
    """飞书发布节点"""
    from .render import EpisodeWriteup, render_episode_md
    from .feishu_publisher import publish_to_feishu_bitable
    from .feishu import get_feishu_config, FeishuClient
    from .paths import get_project_paths
    from pathlib import Path
    
    if not state["summarized"]:
        return {**state, "error": "总结未完成，跳过发布"}
    
    paths = get_project_paths()
    
    try:
        # 生成 Markdown
        writeup = EpisodeWriteup(
            episode_id=state["episode_id"],
            feed_title=state["feed_name"],
            title=state["episode_title"],
            published=state["published_date"],
            episode_url=state["episode_url"],
            audio_url=state["episode_url"],
            tags=state["tags"],
            bullets=state["bullets"],
        )
        
        md_content = render_episode_md(writeup)
        md_path = paths.episode_outputs_dir / state["feed_name"] / f"{state['episode_id']}.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md_content, encoding="utf-8")
        
        # 发布到飞书
        feishu_config = get_feishu_config()
        if feishu_config:
            client = FeishuClient(feishu_config)
            publish_to_feishu_bitable(client, feishu_config, [writeup])
        
        return {
            **state,
            "markdown_path": str(md_path),
            "published_to_feishu": True,
        }
    except Exception as e:
        return {
            **state,
            "error": f"发布失败: {str(e)}",
            "published_to_feishu": False,
        }


def build_podcast_workflow() -> StateGraph:
    """构建播客处理工作流"""
    workflow = StateGraph(PodcastEpisodeState)
    
    # 添加节点
    workflow.add_node("download", download_audio_node)
    workflow.add_node("transcribe", transcribe_node)
    workflow.add_node("translate", translate_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("publish", publish_node)
    
    # 定义流程
    workflow.set_entry_point("download")
    workflow.add_edge("download", "transcribe")
    workflow.add_edge("transcribe", "translate")
    workflow.add_edge("translate", "summarize")
    workflow.add_edge("summarize", "publish")
    workflow.add_edge("publish", END)
    
    return workflow


def process_episode_with_workflow(
    feed_name: str,
    episode_id: str,
    episode_title: str,
    episode_url: str,
    published_date: str,
) -> PodcastEpisodeState:
    """使用 LangGraph 工作流处理单集播客"""
    workflow = build_podcast_workflow()
    app = workflow.compile()
    
    initial_state: PodcastEpisodeState = {
        "feed_name": feed_name,
        "episode_id": episode_id,
        "episode_title": episode_title,
        "episode_url": episode_url,
        "published_date": published_date,
        "audio_path": None,
        "transcript_en_path": None,
        "transcript_cn_path": None,
        "markdown_path": None,
        "transcript_en": None,
        "transcript_cn": None,
        "tags": [],
        "bullets": [],
        "guest_info": None,
        "episode_type": "interview",
        "audio_downloaded": False,
        "transcribed": False,
        "translated": False,
        "summarized": False,
        "published_to_feishu": False,
        "error": None,
    }
    
    result = app.invoke(initial_state)
    return result

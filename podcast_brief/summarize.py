from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from openai import OpenAI


@dataclass(frozen=True)
class EpisodeSummary:
    """
    单集结构化总结。
    """
    tags: list[str]  # 主题标签（技术/产品/公司）
    key_points: list[str]  # 核心要点（3-8 条）
    guest_info: Optional[str] = None  # 嘉宾信息（如果是访谈类）
    episode_type: str = "interview"  # interview/narrative


def extract_summary_from_transcript(
    transcript_path: Path,
    *,
    client: OpenAI,
    episode_title: str,
    feed_title: str,
    model: str = "deepseek-chat",
) -> EpisodeSummary:
    """
    从中文转写中提取结构化总结。
    
    核心逻辑：
    1. 识别播客类型（访谈 vs 讲述）
    2. 过滤无意义内容（广告、寒暄、赞助商）
    3. 提取核心要点（技术/产品/案例/观点）
    4. 提取关键引用（带时间戳）
    5. 生成主题标签
    """
    # 读取完整转写
    content = transcript_path.read_text(encoding="utf-8")
    
    # 如果转写太长，取中间部分（跳过开头的广告/介绍）
    lines = content.splitlines()
    if len(lines) > 100:
        # 跳过前 20%（通常是广告/介绍），取中间 80%
        start_idx = len(lines) // 5
        lines = lines[start_idx:]
    
    # 重新组装（保留时间戳）
    content = "\n".join(lines)
    
    # 如果还是太长，截断到前 8000 字（避免 token 超限）
    if len(content) > 8000:
        content = content[:8000] + "\n\n[...后续内容省略...]"
    
    system_prompt = """你是一个专业的播客内容分析助手。

你的任务是从播客转写中提取**有价值的核心内容**，过滤掉无意义的寒暄、广告、赞助商信息。

## 输出要求（JSON 格式）

```json
{
  "episode_type": "interview 或 narrative",
  "guest_info": "嘉宾姓名、职位、公司（如果是访谈类）",
  "tags": ["标签1", "标签2", "标签3"],
  "key_points": [
    "要点1（如果是访谈类：问题是什么？谁回答了？用了什么技术/产品/案例？）",
    "要点2（如果是讲述类：讲了什么技术/事件？关键观点是什么？）",
    "..."
  ]
}
```

## 要点提取规则

**访谈类**：
- 每个要点应该包含：问题 + 回答者 + 核心观点/技术/产品/案例
- 示例："讨论了 RAG（检索增强生成）在产品中的应用。嘉宾提到他们在 Notion AI 中使用 Pinecone 作为向量数据库，实现了 95% 的召回率。"

**讲述类**：
- 每个要点应该包含：主题 + 关键观点/技术/数据
- 示例："OpenAI 的 GPT-4 Turbo 更新降低了 3 倍的成本，输入价格从 $0.03 降至 $0.01/1K tokens。"

## 标签规则

从以下类别中选择 2-5 个最相关的标签：
- 技术：`RAG`、`Agent`、`Fine-tuning`、`Embedding`、`Prompt Engineering`
- 产品：`ChatGPT`、`Claude`、`Notion AI`、`Cursor`、`GitHub Copilot`
- 领域：`产品增长`、`用户留存`、`商业化`、`开源`、`企业服务`
- 公司：`OpenAI`、`Anthropic`、`Google`、`Meta`、`a16z`

## 过滤规则

以下内容**必须过滤**，不要出现在要点中：
- 广告、赞助商信息
- 主持人寒暄（"欢迎来到..."、"今天很高兴..."）
- 过渡语（"那么..."、"接下来..."、"好的..."）
- 无实质内容的客套话
"""

    user_prompt = f"""播客信息：
- 播客名称：{feed_title}
- 本集标题：{episode_title}

转写内容（已过滤开头广告/介绍）：

{content}

---

请提取核心内容，返回 JSON。"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
        response_format={"type": "json_object"},  # 强制返回 JSON
    )
    
    result_text = response.choices[0].message.content.strip()
    
    # 解析 JSON
    try:
        result = json.loads(result_text)
    except json.JSONDecodeError:
        # 如果 JSON 解析失败，返回空结果
        return EpisodeSummary(
            tags=[],
            key_points=["（LLM 返回格式错误，无法解析）"],
            guest_info=None,
            episode_type="unknown",
        )
    
    return EpisodeSummary(
        tags=result.get("tags", []),
        key_points=result.get("key_points", []),
        guest_info=result.get("guest_info"),
        episode_type=result.get("episode_type", "interview"),
    )

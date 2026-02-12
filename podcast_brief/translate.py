from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from openai import OpenAI


# AI/产品领域常见术语表（保证翻译一致性）
TERM_GLOSSARY = {
    "RAG": "RAG（检索增强生成）",
    "Retrieval-Augmented Generation": "检索增强生成（RAG）",
    "Agent": "Agent（智能体）",
    "LLM": "LLM（大语言模型）",
    "Large Language Model": "大语言模型（LLM）",
    "Fine-tuning": "微调",
    "Prompt": "提示词",
    "Embedding": "向量化/Embedding",
    "Token": "Token",
    "Inference": "推理",
    "Hallucination": "幻觉",
    "Context window": "上下文窗口",
    "Multi-modal": "多模态",
    "Mechanistic Interpretability": "机制可解释性",
    "Interpretability": "可解释性",
    "Vector database": "向量数据库",
    "Latent space": "潜在空间",
    "Foundation model": "基础模型",
    "Transformer": "Transformer",
    "Attention": "注意力机制",
    "Chain-of-thought": "思维链",
    "Few-shot": "少样本学习",
    "Zero-shot": "零样本学习",
    "Product-market fit": "产品市场契合度（PMF）",
    "Go-to-market": "市场推广策略（GTM）",
    "User retention": "用户留存",
    "Churn rate": "流失率",
    "Conversion": "转化",
    "A/B testing": "A/B 测试",
    "KPI": "关键绩效指标（KPI）",
    "ROI": "投资回报率（ROI）",
}


@dataclass(frozen=True)
class TranslationResult:
    original_segments: list[str]  # 原文分段
    translated_segments: list[str]  # 对应的中文翻译
    glossary_used: dict[str, str]  # 本次使用的术语映射


def get_deepseek_client() -> Optional[OpenAI]:
    """
    返回配置好的 DeepSeek client（OpenAI SDK 兼容）。
    如果未配置 API key，返回 None。
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key.startswith("sk-your-"):
        return None
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def translate_segments(
    segments: list[str],
    *,
    client: OpenAI,
    glossary: dict[str, str] = TERM_GLOSSARY,
    model: str = "deepseek-chat",
) -> list[str]:
    """
    分段翻译（避免单次太长）。
    每段调用一次 API，保持术语一致性。
    """
    glossary_text = "\n".join([f"- {en} → {zh}" for en, zh in glossary.items()])
    system_prompt = f"""你是一个专业的 AI/科技播客翻译助手。

翻译要求：
1. 保持自然流畅的中文表达，不要逐字翻译
2. 术语使用以下对照表（保持一致）：

{glossary_text}

3. 人名/公司名/产品名保留英文
4. 数字、时间、金额按中文习惯表达
5. 返回纯文本，不要 Markdown 格式
"""

    translated: list[str] = []
    for seg in segments:
        if not seg.strip():
            translated.append("")
            continue
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"翻译以下内容：\n\n{seg}"},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        translated.append(response.choices[0].message.content.strip())
    
    return translated


def translate_transcript_file(
    transcript_txt: Path,
    output_path: Path,
    *,
    client: OpenAI,
    chunk_size: int = 15,
) -> TranslationResult:
    """
    读取英文转写文件 → 按段落分块 → 翻译 → 保存中文版。
    chunk_size: 每次翻译多少段（避免单次太长/太短）
    """
    lines = transcript_txt.read_text(encoding="utf-8").splitlines()
    
    # 每 chunk_size 行合并成一段（保留时间戳）
    chunks: list[str] = []
    current_chunk = []
    for i, ln in enumerate(lines):
        current_chunk.append(ln)
        if (i + 1) % chunk_size == 0 or i == len(lines) - 1:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
    
    # 翻译
    translated_chunks = translate_segments(chunks, client=client, glossary=TERM_GLOSSARY)
    
    # 保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n".join(translated_chunks), encoding="utf-8")
    
    return TranslationResult(
        original_segments=chunks,
        translated_segments=translated_chunks,
        glossary_used=TERM_GLOSSARY,
    )

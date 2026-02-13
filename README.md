## Tech Podcast Brief — 多 Agent 播客处理系统

一个基于 **LangGraph** 的多 Agent 系统，自动完成：播客 RSS 订阅 → 音频下载 → 本地 ASR 转写 → 英译中翻译 → 智能总结 → 飞书发布 + 通知。

---

### 技术架构

```
┌─────────────────────────────────────────────────────┐
│  n8n（调度层）- 手动/定时触发                          │
└────────────┬────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────┐
│  LangGraph StateGraph（编排层）                       │
│                                                      │
│  [RSS 采集] → [音频下载] → [ASR 转写] → [翻译] → [总结] → [发布]  │
│                                                      │
│  每个节点独立执行，状态可追踪，错误可恢复               │
└─────────────────────────────────────────────────────┘
```

### 核心 Agent

| Agent | 技术实现 | 说明 |
|-------|---------|------|
| **采集 Agent** | RSS + feedparser + httpx | 9 个英文科技播客源，增量去重 |
| **多模态 Agent** | faster-whisper (Whisper ASR) | 本地音频→文本，零 API 成本 |
| **翻译 Agent** | DeepSeek API + 术语表 | 英→中，专业术语对齐 |
| **总结 Agent** | DeepSeek API + 结构化提示词 | 智能过滤噪音，提取核心要点 |
| **发布 Agent** | 飞书 Open API | 多维表格 + 文档 + Webhook 通知 |

### 目标产物

- **飞书多维表格**：结构化数据管理（标签、要点、发布时间）
- **飞书 Daily Brief 文档**：每日自动生成汇总
- **飞书群通知**：Webhook 机器人自动推送更新
- **本地 Markdown**：结构化资产库 + SQLite 数据库

---

## 快速开始

### 1）安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2）配置

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 和飞书配置
```

### 3）运行

```bash
# 基础模式（本地 Markdown）
python -m podcast_brief run --max-episodes-per-feed 1

# 完整模式（飞书发布 + 文档 + 通知）
python -m podcast_brief run --max-episodes-per-feed 1 --publish-feishu --feishu-docx

# LangGraph 工作流版本（状态可追踪）
python -m podcast_brief run-workflow --max-episodes-per-feed 1
```

### 4）自动化（n8n）

```bash
# 安装并启动 n8n
npm install -g n8n
n8n start

# 在 http://localhost:5678 创建手动/定时触发工作流
```

---

## 项目结构

```
podcast_brief/
├── config.py          # 播客源配置（9 个 RSS Feed）
├── rss.py             # RSS 采集 Agent
├── audio.py           # 音频下载
├── asr.py             # ASR 转写 Agent（faster-whisper）
├── translate.py       # 翻译 Agent（DeepSeek API）
├── summarize.py       # 总结 Agent（DeepSeek API）
├── render.py          # Markdown 渲染
├── feishu.py          # 飞书 API 客户端
├── feishu_publisher.py # 飞书发布逻辑
├── workflow.py        # LangGraph 工作流定义
├── db.py              # SQLite 数据管理
├── paths.py           # 路径管理
├── cli.py             # CLI 命令入口
└── __main__.py        # 模块入口
```

---

## 技术栈

| 类别 | 技术 |
|------|------|
| **工作流编排** | LangGraph (StateGraph) |
| **语音识别** | faster-whisper (OpenAI Whisper) |
| **LLM** | DeepSeek API (OpenAI SDK 兼容) |
| **数据存储** | SQLite + 本地文件系统 |
| **内容发布** | 飞书 Open API (Bitable + Docx + Webhook) |
| **任务调度** | n8n (手动/定时触发) |
| **CLI** | Typer + Rich |
| **网络请求** | httpx |

---

## 成本

| 项目 | 费用 |
|------|------|
| **ASR（本地 Whisper）** | 免费 |
| **翻译 + 总结（DeepSeek API）** | ~¥0.15-0.30/集 |
| **飞书** | 免费 |
| **n8n** | 免费（本地运行） |

---

## 文档

- [飞书配置教程](docs/feishu_setup.md)
- [标签管理说明](docs/feishu_tags.md)

## Tech Podcast Brief — 多 Agent 播客处理系统

一个基于 **LangGraph** 编排的多 Agent 系统，自动完成英文科技播客的全链路处理：
RSS 订阅 → 音频下载 → 本地 ASR 转写 → 英译中翻译 → 智能总结 → 飞书发布 + 群通知。

---

## 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                    n8n（调度层）                           │
│          手动触发 / 定时触发 → 执行命令                     │
└────────────────────────┬─────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────┐
│               LangGraph StateGraph（编排层）               │
│                                                           │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐ │
│  │ RSS 采集 │ → │音频下载  │ → │ASR 转写  │ → │  翻译   │ │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘ │
│                                                    ↓      │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────┐      │
│  │飞书 Webhook  │ ← │飞书文档/表格  │ ← │  总结   │      │
│  └──────────────┘   └──────────────┘   └─────────┘      │
│                                                           │
│  每个节点独立执行 · 状态可追踪 · 错误可恢复                  │
└──────────────────────────────────────────────────────────┘
```

---

## 核心 Agent

| Agent | 技术实现 | 说明 |
|-------|---------|------|
| **采集 Agent** | feedparser + httpx | 9 个英文科技播客 RSS 源，增量去重 |
| **多模态 Agent** | faster-whisper (OpenAI Whisper) | 本地音频→文本转写，零 API 成本 |
| **翻译 Agent** | DeepSeek API + 术语表 | 英→中翻译，AI/科技领域专业术语对齐 |
| **总结 Agent** | DeepSeek API + 结构化提示词 | 智能过滤广告/寒暄，提取核心要点与标签 |
| **发布 Agent** | 飞书 Open API | 多维表格 + Daily Brief 文档 + Webhook 群通知 |

---

## 目标产物

| 产物 | 说明 |
|------|------|
| **飞书多维表格** | 每集一行，字段包括：播客名、标题、发布时间、标签、要点 |
| **飞书 Daily Brief** | 每日自动生成汇总文档，按播客分组展示要点 |
| **飞书群通知** | Webhook 机器人推送处理结果和文档链接 |
| **本地 Markdown** | 单集详情 + Daily Brief，结构化存储 |
| **SQLite 数据库** | 节目元数据 + 处理状态追踪 |

---

## 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| **工作流编排** | LangGraph (StateGraph) | Agent 间状态流转与节点管理 |
| **语音识别（ASR）** | faster-whisper (OpenAI Whisper) | 本地音频转文本，支持 tiny/small/medium 模型 |
| **大语言模型（LLM）** | DeepSeek API (OpenAI SDK 兼容) | 翻译 + 总结 |
| **数据存储** | SQLite + 本地文件系统 | 去重、状态管理、中间产物存储 |
| **内容发布** | 飞书 Open API | Bitable 多维表格 + Docx 文档 + Webhook |
| **任务调度** | n8n | 手动/定时触发，可视化工作流 |
| **CLI 框架** | Typer + Rich | 命令行界面，彩色状态输出 |
| **网络请求** | httpx | RSS 拉取、音频下载、API 调用 |

---

## 快速开始

### 1）安装依赖

```bash
git clone https://github.com/YitongPeng/Tech-Podcast-Brief.git
cd Tech-Podcast-Brief
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2）配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入：
# - DEEPSEEK_API_KEY（必需）
# - 飞书相关配置（可选，详见 docs/feishu_setup.md）
```

### 3）运行

```bash
# 推荐：LangGraph 工作流版本（自动清理中间文件）
python -m podcast_brief run-workflow --max-episodes-per-feed 1

# 如果想保留音频/转写文件用于调试
python -m podcast_brief run-workflow --no-cleanup
```

**就这么简单！** 一行命令完成全部流程：
- ✅ 自动下载音频 → 转写 → 翻译 → 总结
- ✅ 自动发布到飞书（多维表格 + Daily Brief 文档）
- ✅ 自动发送群通知
- ✅ **自动清理中间文件**，节省磁盘空间

#### 常用参数

```bash
--max-episodes-per-feed 1     # 每个播客处理最新 N 集（默认 1）
--no-cleanup                  # 保留所有中间文件（用于调试）
--keep-audio                  # 仅保留音频文件
--keep-transcripts            # 仅保留转写文件
```

---

## 定时运行（可选）

如果需要每天自动运行，推荐使用 **macOS cron**（比 n8n 更简单）：

```bash
# 编辑定时任务
crontab -e

# 添加：每天早上 8 点自动运行
0 8 * * * cd /path/to/Tech-Podcast-Brief && source .venv/bin/activate && python -m podcast_brief run-workflow >> ~/podcast.log 2>&1
```

> **关于 n8n**：本项目也支持 n8n 可视化调度，但对于单命令任务来说，直接终端运行或 cron 定时更简单高效。n8n 更适合需要连接多个外部服务的复杂工作流场景。

详细操作指南请见 **[`docs/operation_guide.md`](docs/operation_guide.md)**

---

## 项目结构

```
Tech-Podcast-Brief/
├── podcast_brief/             # 核心代码
│   ├── workflow.py            # LangGraph 工作流定义（StateGraph）
│   ├── config.py              # 播客源配置（9 个 RSS Feed）
│   ├── rss.py                 # RSS 采集 Agent
│   ├── audio.py               # 音频下载与缓存
│   ├── asr.py                 # ASR 转写 Agent（faster-whisper）
│   ├── translate.py           # 翻译 Agent（DeepSeek API + 术语表）
│   ├── summarize.py           # 总结 Agent（DeepSeek API）
│   ├── render.py              # Markdown 渲染
│   ├── feishu.py              # 飞书 API 客户端
│   ├── feishu_publisher.py    # 飞书发布逻辑（表格 + 文档）
│   ├── db.py                  # SQLite 数据管理与去重
│   ├── paths.py               # 路径管理
│   ├── cli.py                 # CLI 入口（run / run-workflow / clean）
│   └── __main__.py            # 模块入口
├── docs/                      # 文档
│   ├── operation_guide.md     # 操作指南（启动流程、工具说明）
│   ├── feishu_setup.md        # 飞书配置教程
│   └── feishu_tags.md         # 标签管理说明
├── data/                      # 运行时数据（git 忽略）
├── requirements.txt           # Python 依赖
├── .env.example               # 环境变量模板
└── .gitignore
```

---

## 成本估算

| 项目 | 费用 | 说明 |
|------|------|------|
| **ASR（本地 Whisper）** | 免费 | faster-whisper 本地运行 |
| **翻译 + 总结（DeepSeek）** | ~¥0.15-0.30/集 | 约 ¥13-27/月（每天 3 集） |
| **飞书** | 免费 | 开放平台免费额度 |
| **n8n** | 免费 | 本地运行 |

---

## 文档

| 文档 | 说明 |
|------|------|
| [操作指南](docs/operation_guide.md) | 完整启动流程、每步工具说明、架构详解 |
| [飞书配置教程](docs/feishu_setup.md) | 飞书应用创建、权限配置、多维表格设置 |
| [标签管理](docs/feishu_tags.md) | 动态标签机制说明 |

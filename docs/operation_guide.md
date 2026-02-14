# 操作指南

本文档详细说明项目的完整启动流程、每一步使用的工具和服务、以及系统架构。

---

## 一、环境准备

### 1.1 系统要求

| 项目 | 要求 |
|------|------|
| **操作系统** | macOS（推荐 M1/M2）/ Linux |
| **Python** | 3.10+ |
| **Node.js** | v18 / v20 / v22（n8n 需要） |
| **内存** | 建议 8GB+（ASR 模型需要 1-2GB） |
| **磁盘** | 建议 10GB+（音频缓存 + ASR 模型） |
| **网络** | 需要访问国外 RSS 源、DeepSeek API、飞书 API |

### 1.2 安装依赖

```bash
# 克隆项目
git clone https://github.com/YitongPeng/Tech-Podcast-Brief.git
cd Tech-Podcast-Brief

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 n8n（可选，用于自动化调度）
npm install -g n8n
```

### 1.3 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# === 必需配置 ===

# DeepSeek API（用于翻译和总结）
DEEPSEEK_API_KEY=your_deepseek_api_key

# === 可选配置（飞书发布） ===

# 飞书应用凭证（在飞书开放平台创建应用获取）
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret

# 飞书多维表格（从表格 URL 中提取）
FEISHU_BITABLE_APP_TOKEN=your_bitable_app_token
FEISHU_BITABLE_TABLE_ID=your_table_id

# 飞书域名（用于生成文档链接）
FEISHU_DOMAIN=your_domain

# 飞书 Webhook（用于群通知）
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your_hook_id
```

> 飞书配置详细教程请见 [feishu_setup.md](feishu_setup.md)

---

## 二、运行方式（推荐）

### 2.1 方式一：终端直接运行 ⭐ 最简单

```bash
# 激活虚拟环境
source .venv/bin/activate

# LangGraph 工作流版本（推荐）
python -m podcast_brief run-workflow --max-episodes-per-feed 1

# 原版命令（功能等价）
python -m podcast_brief run --max-episodes-per-feed 1 --publish-feishu --feishu-docx
```

**推荐理由：**
- ✅ 一行命令搞定
- ✅ 无需额外服务
- ✅ 输出日志清晰
- ✅ 执行速度快

### 2.2 方式二：定时自动运行（cron）

**适合场景：** 每天固定时间自动执行

```bash
# 编辑定时任务
crontab -e

# 添加：每天早上 8 点自动运行
0 8 * * * cd /Users/pengyitong/Documents/Project/Multi_agent && source .venv/bin/activate && python -m podcast_brief run-workflow >> ~/podcast.log 2>&1
```

### 2.3 方式三：n8n 可视化（可选）

> **注意：** 对于本项目这种"单一命令执行"的场景，n8n 显得有些复杂。n8n 更适合需要集成多个外部服务、有复杂条件分支或需要可视化监控的工作流。如果只是简单的定时执行，推荐使用 **cron**（方式二）。

如果你仍想使用 n8n：

#### 步骤 1：启动 n8n

```bash
# 打开一个终端窗口（保持运行）
n8n start
# n8n 会在 http://localhost:5678 启动
```

#### 步骤 2：配置工作流

1. 打开浏览器访问 `http://localhost:5678`
2. 创建新工作流
3. 添加节点：
   - **Manual Trigger** 或 **Schedule Trigger**（定时触发）
   - **Execute Command**（执行命令）
4. Execute Command 节点配置：

```bash
bash -c "cd /path/to/Tech-Podcast-Brief && source .venv/bin/activate && python -m podcast_brief run-workflow --max-episodes-per-feed 1"
```

5. 保存工作流

#### 步骤 3：运行

- 手动触发：点击 **"Execute Workflow"** 按钮
- 定时触发：配置 Schedule Trigger，设置运行时间

---

## 三、执行过程可视化

### 终端日志输出

执行命令后，终端会显示实时进度：

```
🎙️ 播客自动处理（LangGraph 版本）

Feed Latent Space — https://feeds.flightcast.com/...
  ⏩ 跳过已处理 Owning the AI Pareto Frontier

Feed The a16z Show — https://feeds.soundcloud.com/...
  ▶ 处理 New Episode Title
    发布日期: 2026-02-13
    ✓ 下载音频
    ✓ ASR 转写
    ✓ 翻译中文
    ✓ 生成总结
    ✓ 发布飞书
    ✓ 处理完成

📊 发布到飞书
  ✓ 多维表格 新增 1 条
  📌 本次标签：Agent、产品增长、RAG

📄 创建飞书文档
  ✓ 文档创建成功 Daily Brief — 2026-02-13
  📄 点击打开文档
  链接: https://your-domain.feishu.cn/docx/xxxxx

🔔 发送飞书通知
  ✓ 通知已发送

🎉 所有任务完成！
```

**每一步的状态都清晰可见！** 这就是 LangGraph 的"可视化"！

---

## 三、完整处理流程

一次执行会依次经过以下 6 个步骤：

### 步骤 1：RSS 采集

| 项目 | 说明 |
|------|------|
| **工具** | feedparser + httpx |
| **输入** | 9 个播客 RSS 源 URL（配置在 `config.py`） |
| **输出** | 每个源的最新节目列表（标题、发布时间、音频 URL） |
| **去重** | 通过 SQLite 数据库检查，已处理的节目自动跳过 |

**当前订阅的播客源：**

| 播客 | 分类 |
|------|------|
| Latent Space | AI 技术与工程 |
| No Priors | AI 产业与投资 |
| The a16z Show | AI 产业与投资 |
| Lenny's Podcast | 产品与增长 |
| The AI Daily Brief | 每日 AI 新闻 |
| Bloomberg Tech | 科技新闻与访谈 |
| Technology Brother Podcast | 科技新闻 |
| Lightcone Podcast | 创业与 YC |
| Minus One (SPC) | 创业与 YC |

### 步骤 2：音频下载

| 项目 | 说明 |
|------|------|
| **工具** | httpx |
| **输入** | 音频 URL |
| **输出** | 本地音频文件（`data/audio/{feed}/{episode}.mp3`） |
| **特性** | 断点续传、自动跳过已下载文件 |

### 步骤 3：ASR 转写（多模态）

| 项目 | 说明 |
|------|------|
| **工具** | faster-whisper（OpenAI Whisper 优化版） |
| **模型** | tiny / small / medium（默认 tiny） |
| **输入** | 本地音频文件 |
| **输出** | 英文转写文本（`data/transcripts/{feed}/{episode}.txt`） |
| **运行方式** | 完全本地，无需 API 调用 |
| **成本** | 免费 |

> **关于模型选择：**
> - `tiny`：速度快，内存占用小（~1GB），适合低配机器
> - `small`：准确度更高，需要 2-3GB 内存
> - `medium`：最准确，需要 5GB+ 内存

### 步骤 4：英译中翻译

| 项目 | 说明 |
|------|------|
| **工具** | DeepSeek API（通过 OpenAI SDK 调用） |
| **模型** | deepseek-chat |
| **输入** | 英文转写文本 |
| **输出** | 中文翻译文本（`data/transcripts/{feed}/{episode}_cn.txt`） |
| **特性** | 分段翻译（每 15 行一段）、内置 AI/科技术语表 |
| **成本** | ~¥0.05-0.10/集 |

### 步骤 5：智能总结

| 项目 | 说明 |
|------|------|
| **工具** | DeepSeek API |
| **模型** | deepseek-chat |
| **输入** | 中文翻译文本 |
| **输出** | 结构化总结（标签、要点、嘉宾信息、节目类型） |
| **特性** | 自动识别访谈/讲述类型，过滤广告和无意义寒暄 |
| **成本** | ~¥0.05-0.15/集 |

**总结输出格式：**

```json
{
  "episode_type": "interview",
  "guest_info": "嘉宾姓名、职位、公司",
  "tags": ["Agent", "RAG", "产品增长"],
  "key_points": [
    "要点1：讨论了什么技术，用了什么产品...",
    "要点2：...",
    "..."
  ]
}
```

### 步骤 6：发布

| 产物 | 工具 | 说明 |
|------|------|------|
| **飞书多维表格** | 飞书 Bitable API | 每集一行记录，包含标签、要点等字段 |
| **飞书 Daily Brief** | 飞书 Docx API | 每日汇总文档，按播客分组 |
| **飞书群通知** | 飞书 Webhook Bot | 推送处理结果 + 文档链接到群聊 |
| **本地 Markdown** | 文件系统 | 单集文件 + Daily Brief |
| **SQLite 更新** | sqlite3 | 标记处理状态为完成 |

---

## 四、LangGraph 编排说明

### 4.1 状态定义

```python
class PodcastEpisodeState(TypedDict):
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
    
    # 状态标记
    audio_downloaded: bool
    transcribed: bool
    translated: bool
    summarized: bool
    published_to_feishu: bool
    
    # 错误信息
    error: Optional[str]
```

### 4.2 节点定义

| 节点 | 函数 | 输入状态 | 输出状态 |
|------|------|---------|---------|
| download | `download_audio_node` | episode_url | audio_downloaded, audio_path |
| transcribe | `transcribe_node` | audio_path | transcribed, transcript_en_path |
| translate | `translate_node` | transcript_en_path | translated, transcript_cn_path |
| summarize | `summarize_node` | transcript_cn_path | summarized, tags, bullets |
| publish | `publish_node` | tags, bullets | published_to_feishu |

### 4.3 执行流程

```
START → download → transcribe → translate → summarize → publish → END
```

每个节点独立执行，失败时记录错误信息到状态中，不影响后续节点的判断。

---

## 五、CLI 命令参考

### run-workflow（推荐）

```bash
python -m podcast_brief run-workflow [OPTIONS]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max-episodes-per-feed` | 1 | 每个源处理几集 |
| `--publish-feishu / --no-publish-feishu` | True | 是否发布到飞书 |
| `--feishu-docx / --no-feishu-docx` | True | 是否创建飞书文档 |

### run（原版）

```bash
python -m podcast_brief run [OPTIONS]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max-episodes-per-feed` | 1 | 每个源处理几集 |
| `--asr / --no-asr` | True | 是否执行 ASR |
| `--asr-model` | small | ASR 模型大小 |
| `--translate / --no-translate` | True | 是否翻译 |
| `--publish-feishu / --no-publish-feishu` | False | 是否发布飞书 |
| `--feishu-docx / --no-feishu-docx` | False | 是否创建飞书文档 |
| `--cleanup / --no-cleanup` | False | 处理后清理中间文件 |

### clean

```bash
python -m podcast_brief clean [OPTIONS]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--dry-run / --no-dry-run` | False | 预览模式 |
| `--keep-audio / --no-keep-audio` | False | 保留音频文件 |
| `--keep-transcripts / --no-keep-transcripts` | False | 保留转写文件 |

---

## 六、数据目录结构

```
data/
├── episodes.sqlite              # SQLite 数据库（节目元数据 + 状态）
├── hf_models/                   # ASR 模型缓存（首次下载后复用）
├── audio/                       # 音频文件
│   ├── latent-space/
│   ├── no-priors/
│   └── ...
├── transcripts/                 # 转写文件
│   ├── latent-space/
│   │   ├── {episode_id}.json    # ASR 原始输出（含时间戳）
│   │   ├── {episode_id}.txt     # 英文纯文本
│   │   └── {episode_id}_cn.txt  # 中文翻译
│   └── ...
└── outputs/                     # 输出文件
    ├── episodes/                # 单集 Markdown
    │   ├── latent-space/
    │   └── ...
    └── daily_brief/             # Daily Brief
        └── 2026-02-13.md
```

---

## 七、外部服务清单

| 服务 | 用途 | 是否必需 | 费用 |
|------|------|---------|------|
| **DeepSeek API** | 翻译 + 总结 | 必需 | ~¥0.15-0.30/集 |
| **飞书开放平台** | 多维表格 + 文档 + 通知 | 可选 | 免费 |
| **Hugging Face Hub** | 下载 Whisper ASR 模型 | 仅首次运行 | 免费 |
| **n8n** | 任务调度 | 可选 | 免费（本地运行） |

---

## 八、常见问题

### Q: 第一次运行很慢？
**A:** 首次运行需要下载 ASR 模型（约 75MB-1.5GB，取决于模型大小），之后会缓存到 `data/hf_models/`，后续运行不再下载。

### Q: 某些播客源报 429 错误？
**A:** `pod.link` 等代理域名有访问频率限制，程序会自动跳过并处理其他源。下次运行时通常可以正常获取。

### Q: 内存不足（Killed）？
**A:** ASR 模型需要较多内存。解决方案：
- 使用更小的模型：`--asr-model tiny`（约 1GB 内存）
- 关闭其他内存占用大的应用

### Q: 如何添加新的播客源？
**A:** 编辑 `podcast_brief/config.py` 中的 `DEFAULT_FEEDS` 列表，添加新的 `Feed` 对象：

```python
Feed(
    slug="new-podcast",        # 唯一标识（用于文件路径）
    title="New Podcast Name",  # 显示名称
    rss_url="https://...",     # RSS 源 URL
),
```

### Q: 如何只运行不发布飞书？
**A:** 使用 `--no-publish-feishu` 参数：

```bash
python -m podcast_brief run-workflow --no-publish-feishu --no-feishu-docx
```

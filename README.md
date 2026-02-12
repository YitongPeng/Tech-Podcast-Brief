## Multi-agent Podcast Brief（MVP）
一个"播客 → 本地 ASR → 中英翻译 → 中文结构化总结 → Daily Brief"的多模态产品项目。

### 目标产物

- **结构化资产库（本地）**：`data/episodes.sqlite` + `data/outputs/episodes/*.md`
- **中英双语转写**：`data/transcripts/{feed}/{episode_id}.txt`（英文） + `{episode_id}_cn.txt`（中文）
- **Daily Brief（本地）**：`data/outputs/daily_brief/YYYY-MM-DD.md`
- **飞书多维表格**：自动发布到飞书，可视化管理
- **飞书 Daily Brief 文档**：每日自动生成汇总文档
- **飞书通知**：完成后自动推送到飞书群聊

后续扩展：主题聚合 Agent、启示生成 Agent、LangGraph 编排。

---

## 📚 部署方式

### 本地运行（开发/测试）
- 适合：本地开发、调试、测试
- [本地快速开始](#快速开始) ⬇️

### 服务器自动化（生产环境）⭐ 推荐
- 适合：24/7 自动运行，不依赖本地电脑
- **[🚀 服务器部署快速开始](docs/QUICK_START_SERVER.md)** ← 3 步完成部署
- [详细部署文档](docs/server_deployment.md)

---

## 快速开始（本地）

### 1）创建虚拟环境并安装依赖

```bash
cd /Users/pengyitong/Documents/Project/Multi_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2）配置 API Key 和飞书（可选）

```bash
cp .env.example .env
# 然后编辑 .env，填入以下配置
```

**必需配置**：
- `DEEPSEEK_API_KEY`：用于翻译和总结（如果找不到，去 DeepSeek 后台创建）

**可选配置（飞书发布）**：
- `FEISHU_APP_ID`：飞书应用 ID
- `FEISHU_APP_SECRET`：飞书应用密钥
- `FEISHU_BITABLE_APP_TOKEN`：多维表格 app_token
- `FEISHU_BITABLE_TABLE_ID`：多维表格 table_id

**飞书配置教程**：详见 [`docs/feishu_setup.md`](docs/feishu_setup.md)

### 3）运行完整 pipeline

```bash
# 基础模式：本地输出（Markdown + Daily Brief）
python -m podcast_brief --max-episodes-per-feed 1

# 发布到飞书多维表格
python -m podcast_brief --max-episodes-per-feed 1 --publish-feishu

# 发布到飞书 + 创建 Daily Brief 文档
python -m podcast_brief --max-episodes-per-feed 1 --publish-feishu --feishu-docx

# 节省空间模式：处理完自动清理音频和转写
python -m podcast_brief --max-episodes-per-feed 1 --cleanup

# 完整模式：翻译 + 总结 + 飞书发布 + 自动清理
python -m podcast_brief --max-episodes-per-feed 3 --publish-feishu --cleanup
```

### 4）清理历史文件（释放空间）

```bash
# 预览将删除的文件（不实际删除）
python -m podcast_brief clean --dry-run

# 删除所有音频和转写
python -m podcast_brief clean

# 只删除音频，保留转写
python -m podcast_brief clean --keep-transcripts

# 只删除转写，保留音频
python -m podcast_brief clean --keep-audio
```

你会在 `data/outputs/` 里看到生成的中文 Markdown 文件。

---

## 配置

- **播客源**：`podcast_brief/config.py` → `DEFAULT_FEEDS`
- **术语表**：`podcast_brief/translate.py` → `TERM_GLOSSARY`（AI/产品领域术语）
- **ASR 模型**：默认 `small` + `int8`（M1/M2 推荐）

---

## 架构

```
RSS Collector → Audio Downloader → ASR (faster-whisper) → Translator (DeepSeek) → Markdown Generator → Daily Brief
```

**Agent 分工**：
1. **采集 Agent**：RSS 解析 + 增量去重（`rss.py` + `db.py`）
2. **多模态 Agent**：音频 → 文本 ASR（`asr.py`）
3. **翻译 Agent**：英文 → 中文 + 术语对齐（`translate.py`）
4. **总结 Agent**：LLM 智能提取核心要点 + 过滤无意义内容（`summarize.py`）
5. **发布 Agent**：
   - 本地：结构化 Markdown + Daily Brief（`render.py`）
   - 飞书：多维表格 + 飞书文档（`feishu_publisher.py`）

后续扩展：
- **启示生成 Agent**：提取对 AI 产品的可执行建议
- **LangGraph 编排**：把 pipeline 改写成 stateful graph

---

## 成本与存储

**API 成本**：
- **本地 ASR**：免费（faster-whisper）
- **翻译 + 总结 API（DeepSeek）**：~¥0.15-0.30/集，每天 3 集约 ¥13.5-27/月

**存储空间**（每集平均）：
- **音频**：~45 MB/集（60 分钟播客）
- **转写**：~200 KB/集（英文 + 中文）
- **输出**：~10 KB/集（Markdown）
- **ASR 模型**：473 MB（一次性下载，可复用）

**推荐策略**：
- ✅ 日常运行：使用 `--cleanup` 自动清理，节省空间
- ✅ 调试阶段：保留中间文件，使用 `--keep-transcripts`
- ✅ 每周清理：运行 `python -m podcast_brief clean`

---

## 说明（为什么这样设计）

为了保证在 2/17 前可交付 + 体现 AI PM 能力：
1. **多模态**：ASR 体现音频处理能力（区别于纯文本爬虫项目）
2. **Agent 分工**：每个模块独立，职责明确，易于扩展和维护
3. **本地 + 云端混合**：ASR 本地（降低成本），翻译云端（保证质量）
4. **结构化产物**：Markdown + SQLite 双重存储，便于后续接入飞书/RAG/主题聚合
5. **术语表管理**：保证翻译一致性（AI/产品领域专业术语）

---

## 产物示例

### 单集 Markdown（`data/outputs/episodes/{feed}/{episode_id}.md`）

```markdown
# Episode Title

- **播客**：Latent Space
- **发布时间**：2026-02-11
- **节目页**：https://...
- **音频**：https://...
- **Episode ID**：`latent-space-abc123`

## 标签

`Agent`、`RAG`、`产品增长`

## 要点

- 讨论了 RAG（检索增强生成）在产品中的应用
- OpenAI 的最新 API 更新...
- ...

## 关键引用（带时间戳）

- [00:12:34] "我们发现用户对 RAG 的准确性要求非常高..."
- [00:25:11] "产品市场契合度（PMF）是关键..."
```

### Daily Brief（`data/outputs/daily_brief/2026-02-11.md`）

汇总当天所有新增播客的要点、标签、时间戳引用。

---

## 下一步

你现在需要做的：
1. **复制 `.env.example` 为 `.env`**，填入 DeepSeek API Key
2. **运行一次带翻译的 pipeline**：`python -m podcast_brief run --max-episodes-per-feed 1`
3. 看看 `data/transcripts/` 和 `data/outputs/` 里生成的中文内容

成功后，我们继续做：
- 主题聚合 Agent（按问答/技术点分类）
- 启示生成 Agent（提取可执行建议）
- 飞书发布 Agent（写入多维表格）
- LangGraph 重构（最后一步）

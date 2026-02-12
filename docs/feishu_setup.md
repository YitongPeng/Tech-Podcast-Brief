# 飞书配置指南

## 一、创建飞书自建应用

### 1. 访问飞书开放平台
https://open.feishu.cn/app

### 2. 创建应用
- 点击「创建企业自建应用」
- 填写应用名称：`Podcast Brief`
- 填写应用描述：`AI 播客内容聚合与分析`
- 上传应用图标（可选）

### 3. 获取凭证
创建完成后，进入「凭证与基础信息」页面：
- 复制 **App ID**（格式：`cli_xxxxxxxxxxxxxxxx`）
- 复制 **App Secret**（格式：`xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`）

### 4. 配置权限
进入「权限管理」页面，开通以下权限：

**多维表格权限**：
- `bitable:app` - 获取多维表格元数据
- `bitable:app:readonly` - 查看多维表格
- `bitable:app:write` - 编辑多维表格

**文档权限**：
- `docx:document` - 创建文档
- `docx:document:readonly` - 查看文档
- `docx:document:write` - 编辑文档
- `drive:drive` - 访问云空间

### 5. 发布版本
- 在「版本管理与发布」页面创建版本
- 申请发布（企业内部应用会自动通过）

---

## 二、创建多维表格

### 1. 创建 Base
- 访问飞书多维表格：https://example.feishu.cn/base/
- 点击「创建 Base」
- 命名：`Podcast 资产库`

### 2. 创建表格
- 在 Base 中创建表格，命名：`Episodes`

### 3. 创建字段
按照以下顺序创建字段：

| 字段名称 | 字段类型 | 说明 |
|---------|---------|------|
| 播客名称 | 单行文本 | 自动填充 |
| Episode 标题 | 单行文本 | 自动填充 |
| 发布时间 | 日期 | 自动填充 |
| 节目页 | URL | 自动填充 |
| 音频 | URL | 自动填充 |
| 标签 | 多选 | 需要预设选项（见下方） |
| 核心要点 | 多行文本 | 自动填充 |
| Episode ID | 单行文本 | 自动填充 |

### 4. 配置「标签」字段选项
点击「标签」字段设置，添加以下选项：

**技术类**：
- `RAG`
- `Agent`
- `Fine-tuning`
- `Embedding`
- `Prompt Engineering`
- `Transformer`

**产品类**：
- `产品增长`
- `商业化`
- `用户留存`
- `A/B 测试`
- `PMF`

**公司/产品**：
- `OpenAI`
- `Anthropic`
- `Google`
- `Meta`
- `ChatGPT`
- `Claude`

**领域**：
- `企业服务`
- `开源`
- `投资策略`

### 5. 获取配置参数
打开表格后，从浏览器地址栏复制参数：

**URL 格式**：
```
https://example.feishu.cn/base/{app_token}?table={table_id}&view={view_id}
```

**提取参数**：
- `app_token`：`base/` 后面的字符串（例如：`bascnxxxxxxxxxxxxxx`）
- `table_id`：`table=` 后面的字符串（例如：`tblxxxxxxxxxxxxxx`）

### 6. 配置应用权限
- 在表格右上角点击「…」→「高级设置」→「权限设置」
- 添加应用「Podcast Brief」为协作者，权限设置为「可编辑」

---

## 三、配置 .env 文件

复制以下内容到 `.env` 文件：

```bash
# DeepSeek API
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# 飞书应用凭证（从「凭证与基础信息」页面获取）
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 飞书多维表格配置（从表格 URL 中提取）
FEISHU_BITABLE_APP_TOKEN=bascnxxxxxxxxxxxxxx
FEISHU_BITABLE_TABLE_ID=tblxxxxxxxxxxxxxx
```

---

## 四、测试发布

### 1. 运行测试命令
```bash
python -m podcast_brief --max-episodes-per-feed 1 --publish-feishu
```

### 2. 检查结果
- 打开飞书多维表格，应该能看到新增的播客记录
- 检查字段是否正确填充（标题、时间、标签、要点、引用）

### 3. 创建飞书文档（可选）
```bash
python -m podcast_brief --max-episodes-per-feed 1 --publish-feishu --feishu-docx
```

---

## 五、创建视图（可选）

在多维表格中创建以下视图，方便筛选和查看：

### 1. 今日新增
- 筛选条件：`发布时间 = 今天`

### 2. Agent/RAG
- 筛选条件：`标签 包含 Agent 或 RAG`

### 3. 产品增长/商业化
- 筛选条件：`标签 包含 产品增长 或 商业化`

### 4. 本周趋势
- 筛选条件：`发布时间 在本周内`
- 分组依据：`标签`

---

## 六、常见问题

### Q1: 提示「权限不足」怎么办？
**A**: 检查应用权限是否已开通并发布版本。进入「权限管理」页面确认所有必需权限已勾选。

### Q2: 标签字段写入失败？
**A**: 确保「标签」字段的选项已经预设好。飞书多选字段只能选择已存在的选项，不能动态创建。

### Q3: 如何获取 app_token 和 table_id？
**A**: 打开表格，查看浏览器地址栏：
```
https://example.feishu.cn/base/{app_token}?table={table_id}
```
提取花括号中的内容。

### Q4: 应用需要审核吗？
**A**: 企业自建应用在企业内部使用，通常不需要审核。如果是发布到应用市场，需要审核。

---

## 七、后续优化

1. **定时任务**：使用 cron 或 GitHub Actions 每天自动运行
2. **飞书机器人**：配置飞书机器人，处理完成后发送通知
3. **仪表盘**：基于多维表格创建飞书仪表盘，可视化播客趋势
4. **视图管理**：根据团队需求创建更多自定义视图

---

## 参考文档

- 飞书开放平台：https://open.feishu.cn/document/home/introduction-to-custom-app-development/self-built-application-development-process
- 多维表格 API：https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/create
- 飞书文档 API：https://open.feishu.cn/document/server-docs/docs/docs-v2/document/create

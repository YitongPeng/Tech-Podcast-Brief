# 🚀 服务器部署快速开始（3 步完成）

## 📋 准备工作

**你需要：**
- ✅ 一台服务器（阿里云/腾讯云/AWS 等）
- ✅ 服务器 IP 地址
- ✅ SSH 登录权限
- ✅ 本地电脑能 SSH 连接到服务器

**时间：** 30-45 分钟

---

## 🎯 方案 B：直接部署 + n8n Docker

**最佳平衡方案：**
- 播客项目：直接部署（简单、高效）
- n8n：Docker 容器（可视化管理定时任务）

---

## 🏃 快速部署（3 步）

### 步骤 1：从本地上传代码到服务器

**在你的 Mac 上运行：**

```bash
cd /Users/pengyitong/Documents/Project/Multi_agent
./scripts/upload_to_server.sh
```

**按提示输入：**
- 服务器 IP 地址（例如：`123.45.67.89`）
- 服务器用户名（例如：`ubuntu` 或 `root`）
- 目标目录（默认：`~/podcast_brief`）

**如果提示权限错误，先执行：**
```bash
chmod +x ./scripts/upload_to_server.sh
```

---

### 步骤 2：SSH 登录服务器并运行部署脚本

```bash
# 1. SSH 登录服务器
ssh ubuntu@你的服务器IP

# 2. 进入项目目录
cd ~/podcast_brief

# 3. 运行部署脚本
bash scripts/deploy_server.sh
```

**脚本会自动：**
- ✅ 安装 Python 3、Docker、FFmpeg
- ✅ 创建虚拟环境
- ✅ 安装所有依赖
- ✅ 提示你配置环境变量

**按照脚本提示：**
1. 编辑 `.env` 文件填入 API keys
2. 测试运行一次
3. 安装 n8n（复制脚本给出的命令）

---

### 步骤 3：配置 n8n 定时任务

**3.1 访问 n8n Web 界面**

在浏览器打开：
```
http://你的服务器IP:5678
```

**首次访问：**
- 创建管理员账号
- 设置邮箱和密码

**3.2 创建工作流**

1. 点击 **「+ New Workflow」**
2. 命名：`Podcast Daily Update`

**3.3 添加定时触发器**

1. 点击左侧 **「+」**
2. 搜索 **「Schedule Trigger」**
3. 配置：
   - Trigger Interval: `Days`
   - Days Between Triggers: `1`
   - Trigger at Hour: `8`（早上 8 点）
   - Trigger at Minute: `0`
   - Timezone: `Asia/Shanghai`

**3.4 添加执行命令**

1. 点击触发器右侧 **「+」**
2. 搜索 **「Execute Command」**
3. 在 **Command** 框填入：

```bash
cd /home/ubuntu/podcast_brief && source .venv/bin/activate && python -m podcast_brief run --max-episodes-per-feed 2 --publish-feishu --feishu-docx --cleanup
```

**⚠️ 重要：** 把 `/home/ubuntu` 替换成你的实际路径！

查看路径：在服务器运行 `echo $HOME`

**3.5 保存并激活**

1. 点击右上角 **「Save」**
2. 点击右上角的开关，激活工作流（变绿）

**3.6 测试执行**

点击左下角 **「Execute Workflow」** 手动测试

---

## ✅ 完成！

**现在：**
- ✅ 每天早上 8 点自动运行
- ✅ 自动发送飞书通知
- ✅ 本地电脑可以随意关机
- ✅ 在 n8n 查看执行历史

---

## 🔧 常用命令

### 查看 n8n 状态
```bash
docker ps | grep n8n
docker logs n8n --tail 50
```

### 手动测试运行
```bash
cd ~/podcast_brief
source .venv/bin/activate
python -m podcast_brief run --max-episodes-per-feed 1 --publish-feishu --feishu-docx
```

### 重启 n8n
```bash
docker restart n8n
```

### 更新代码
```bash
# 在本地电脑运行
cd /Users/pengyitong/Documents/Project/Multi_agent
./scripts/upload_to_server.sh

# 然后在服务器运行
cd ~/podcast_brief
git pull  # 如果用 Git
pip install -r requirements.txt  # 更新依赖
```

---

## 🆘 遇到问题？

### 问题 1：SSH 连接失败
- 检查服务器 IP 是否正确
- 检查服务器防火墙设置
- 确认 SSH 端口（默认 22）

### 问题 2：n8n 无法访问
- 检查服务器防火墙是否开放 5678 端口
- 使用 SSH 隧道：`ssh -L 5678:localhost:5678 user@server`

### 问题 3：播客处理失败
- 查看日志：n8n Web 界面查看执行历史
- 手动运行测试
- 检查 `.env` 文件配置

---

## 📚 详细文档

- [完整部署文档](./server_deployment.md)
- [项目 README](../README.md)
- [飞书配置指南](./feishu_setup.md)

---

## 🎉 享受自动化！

现在你可以：
- 😴 每天早上起床查看飞书通知
- 📱 手机随时查看更新
- 💻 本地电脑不再需要保持开机
- ⏰ 不用担心忘记运行

# 服务器部署指南（方案 B：直接部署 + n8n）

## 📋 部署概览

**部署架构：**
```
服务器
├── Python 环境（播客项目运行环境）
├── /home/user/podcast_brief/（播客项目代码）
├── faster-whisper 模型（ASR）
└── n8n（Docker 容器，负责定时调度）
```

**预计时间：** 45-60 分钟

---

## ⚙️ 服务器要求

### 最低配置
- **CPU**: 2 核
- **内存**: 2 GB
- **存储**: 20 GB
- **系统**: Ubuntu 20.04/22.04 或 CentOS 7/8
- **网络**: 能访问国际网络（下载模型）

### 推荐配置
- **CPU**: 2 核
- **内存**: 4 GB
- **存储**: 30 GB

---

## 🚀 部署步骤

### 步骤 1：准备服务器环境

#### 1.1 登录服务器
```bash
ssh user@your-server-ip
```

#### 1.2 安装必要软件
```bash
# 更新包管理器
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# 或
sudo yum update -y  # CentOS

# 安装 Python 3.10+
sudo apt install python3 python3-pip python3-venv -y  # Ubuntu
# 或
sudo yum install python3 python3-pip -y  # CentOS

# 安装 Docker（用于运行 n8n）
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 将当前用户添加到 docker 组（避免每次都用 sudo）
sudo usermod -aG docker $USER
# 退出并重新登录以使更改生效
```

#### 1.3 验证安装
```bash
python3 --version  # 应显示 3.10 或更高
docker --version   # 应显示 Docker 版本
```

---

### 步骤 2：部署播客项目

#### 2.1 创建项目目录
```bash
mkdir -p ~/podcast_brief
cd ~/podcast_brief
```

#### 2.2 上传代码（从本地）

**方法 1：使用 scp（推荐）**
```bash
# 在你的本地电脑运行：
cd /Users/pengyitong/Documents/Project/Multi_agent
scp -r podcast_brief requirements.txt .env.example user@your-server-ip:~/podcast_brief/
```

**方法 2：使用 Git**
```bash
# 如果你的项目在 GitHub：
git clone https://github.com/your-username/podcast_brief.git
cd podcast_brief
```

#### 2.3 创建 Python 虚拟环境
```bash
cd ~/podcast_brief
python3 -m venv .venv
source .venv/bin/activate
```

#### 2.4 安装依赖
```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装系统依赖（faster-whisper 需要）
sudo apt install ffmpeg -y  # Ubuntu
# 或
sudo yum install ffmpeg -y  # CentOS
```

#### 2.5 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
# 或
vim .env
```

**填入以下内容：**
```bash
# DeepSeek API
DEEPSEEK_API_KEY=sk-9a31cd52b14c4c44bc16d87857e42da4

# 飞书配置
FEISHU_APP_ID=cli_a90641a439f8dcd2
FEISHU_APP_SECRET=ppH8GvPi8hIYOG7Y6134FgPxeCyu7YSs
FEISHU_BITABLE_APP_TOKEN=Y3bDbt42qaNynAssoFgcdqRAnFh
FEISHU_BITABLE_TABLE_ID=tblFcFBNNXOF1Oqy
FEISHU_DOMAIN=rcns5ppx1h0z
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/bb2f13e1-b791-4603-aee7-2180461a0a5b
```

#### 2.6 测试运行
```bash
# 激活虚拟环境
source ~/podcast_brief/.venv/bin/activate

# 测试运行（处理 1 集播客）
python -m podcast_brief run --max-episodes-per-feed 1 --publish-feishu --feishu-docx --cleanup
```

**如果成功：**
- ✅ 你会收到飞书通知
- ✅ 控制台显示处理日志

---

### 步骤 3：安装 n8n

#### 3.1 使用 Docker 安装 n8n
```bash
# 创建 n8n 数据目录
mkdir -p ~/.n8n

# 运行 n8n 容器
docker run -d --restart unless-stopped \
  --name n8n \
  -p 5678:5678 \
  -e GENERIC_TIMEZONE="Asia/Shanghai" \
  -e TZ="Asia/Shanghai" \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

#### 3.2 验证 n8n 运行状态
```bash
docker ps | grep n8n
# 应该显示 n8n 容器正在运行
```

#### 3.3 访问 n8n Web 界面
```bash
# 在浏览器中打开：
http://你的服务器IP:5678
```

**首次访问：**
1. 创建管理员账号
2. 设置邮箱和密码
3. 进入 n8n 主界面

---

### 步骤 4：配置 n8n 工作流

#### 4.1 创建新工作流

1. 点击右上角 **「+ New Workflow」**
2. 工作流名称：`Podcast Daily Update`

#### 4.2 添加定时触发器

1. 点击左侧 **「+」** 按钮
2. 搜索并选择 **「Schedule Trigger」**
3. 配置：
   - **Trigger Interval**: `Days`
   - **Days Between Triggers**: `1`
   - **Trigger at Hour**: `8` (早上 8 点)
   - **Trigger at Minute**: `0`
   - **Timezone**: `Asia/Shanghai`

#### 4.3 添加执行命令节点

1. 点击触发器右侧的 **「+」** 按钮
2. 搜索并选择 **「Execute Command」**
3. 配置：
   - **Command**: 填入以下内容
   ```bash
   cd /home/你的用户名/podcast_brief && source .venv/bin/activate && python -m podcast_brief run --max-episodes-per-feed 2 --publish-feishu --feishu-docx --cleanup
   ```
   - **Execute Once**: 开启（勾选）

**重要：** 把 `/home/你的用户名` 替换成你的实际路径！

可以通过以下命令查看：
```bash
echo $HOME
# 输出例如：/home/ubuntu
```

#### 4.4 保存并激活工作流

1. 点击右上角 **「Save」** 保存工作流
2. 点击右上角的开关按钮，**激活工作流**（开关变为绿色）

#### 4.5 测试手动执行

1. 点击左下角 **「Execute Workflow」**
2. 查看执行结果：
   - ✅ 成功：显示绿色对勾
   - ❌ 失败：显示错误信息

---

### 步骤 5：配置防火墙（可选）

#### 5.1 开放 n8n 端口
```bash
# Ubuntu (ufw)
sudo ufw allow 5678/tcp

# CentOS (firewalld)
sudo firewall-cmd --permanent --add-port=5678/tcp
sudo firewall-cmd --reload
```

#### 5.2 安全建议

**n8n Web 界面暴露在公网有风险，建议：**

**方案 1：只允许特定 IP 访问**
```bash
# 只允许你的本地 IP 访问
sudo ufw allow from 你的公网IP to any port 5678
```

**方案 2：使用 SSH 隧道（推荐）**
```bash
# 在本地电脑运行（不开放公网端口）
ssh -L 5678:localhost:5678 user@your-server-ip

# 然后在浏览器访问：
http://localhost:5678
```

**方案 3：配置 Nginx 反向代理 + SSL**
- 超出本文档范围，但更安全
- 可以后续配置

---

## 📊 运行状态检查

### 检查 n8n 状态
```bash
docker ps | grep n8n
docker logs n8n --tail 50
```

### 检查播客项目日志
```bash
# n8n 执行日志在 n8n Web 界面查看

# 或者手动运行查看：
cd ~/podcast_brief
source .venv/bin/activate
python -m podcast_brief run --max-episodes-per-feed 1 --publish-feishu --feishu-docx
```

### 查看系统资源占用
```bash
# 内存
free -h

# CPU
top
# 按 q 退出

# 磁盘空间
df -h
```

---

## 🔧 常见问题

### 问题 1：faster-whisper 模型下载失败

**原因：** 网络问题，无法访问 Hugging Face

**解决方案 1：使用镜像站**
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

**解决方案 2：手动下载模型**
1. 在本地下载模型
2. 上传到服务器
3. 配置环境变量指向本地路径

### 问题 2：n8n 无法执行命令

**可能原因：**
- 路径错误
- 虚拟环境未激活
- 权限问题

**解决方案：**
```bash
# 确保命令中的路径正确
cd /home/你的用户名/podcast_brief && \
source .venv/bin/activate && \
which python  # 应显示虚拟环境中的 Python 路径
```

### 问题 3：飞书通知未收到

**检查清单：**
- [ ] `.env` 文件中的 API keys 正确
- [ ] 服务器能访问飞书 API（`curl https://open.feishu.cn`）
- [ ] Webhook URL 正确

---

## 🎉 部署完成检查清单

- [ ] 服务器环境配置完成（Python、Docker）
- [ ] 播客项目代码上传并配置
- [ ] 依赖安装完成（requirements.txt）
- [ ] 环境变量配置正确（.env）
- [ ] 手动测试运行成功
- [ ] n8n Docker 容器运行正常
- [ ] n8n 工作流配置完成
- [ ] n8n 工作流已激活（绿色开关）
- [ ] 手动执行测试成功
- [ ] 收到飞书通知

---

## 📅 下一步

**部署完成后：**
1. ✅ 每天早上 8 点自动运行
2. ✅ 自动发送飞书通知
3. ✅ 本地电脑可以随意关机
4. ✅ 在 n8n Web 界面查看执行历史

**定期维护：**
- 每周检查一次执行日志
- 定期清理服务器存储空间
- 关注播客源变化，及时更新

---

## 🔗 相关文档

- [n8n 官方文档](https://docs.n8n.io/)
- [faster-whisper GitHub](https://github.com/guillaumekln/faster-whisper)
- [飞书开放平台](https://open.feishu.cn/)

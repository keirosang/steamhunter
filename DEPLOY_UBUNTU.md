# 🐧 Steam 蒸汽猎手 (Hugo-Page) Ubuntu 服务器部署与自动化运维手册

> **目标仓库**：[https://github.com/keirosang/steamhunter.git](https://github.com/keirosang/steamhunter.git)  
> **线上站点**：[https://keirosang.github.io/steamhunter/](https://keirosang.github.io/steamhunter/)  
> **程序目录**：`hugo-page/`（纯独立采集与发布程序，无外部依赖）

---

## 📋 目录导航
1. [一键初始化与手动环境安装](#1-一键初始化与手动环境安装)
2. [Hugo Extended 静态引擎安装](#2-hugo-extended-静态引擎安装)
3. [GitHub 仓库授权与配置（免密推送）](#3-github-仓库授权与配置免密推送)
4. [开启 GitHub Pages 自动化工作流](#4-开启-github-pages-自动化工作流)
5. [环境变量配置检查 (.env)](#5-环境变量配置检查-env)
6. [初次手动执行与验证](#6-初次手动执行与验证)
7. [Crontab 定时巡检发布配置](#7-crontab-定时巡检发布配置)
8. [进阶：Systemd Timer 服务化托管（可选）](#8-进阶systemd-timer-服务化托管可选)
9. [常见问题与排错指引 (FAQ)](#9-常见问题与排错指引-faq)

---

## 1. 一键初始化与手动环境安装

将 `hugo-page` 整个目录上传或克隆至 Ubuntu 服务器（例如放在 `/home/ubuntu/hugo-page` 或 `/root/hugo-page`）。

### 方法 A：一键全自动安装（推荐）
进入目录并执行自带的一键脚本：
```bash
cd hugo-page
chmod +x setup_ubuntu.sh run_cron.sh
./setup_ubuntu.sh
```
脚本会自动安装 Python3、Git、vEnv，并下载安装最新的 Hugo Extended 版本及依赖。

---

### 方法 B：手动分步安装
若希望手动控制每一步，可按以下命令依次执行：
```bash
# 1. 更新 apt 并安装核心基础软件
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv git curl wget tar

# 2. 进入项目目录并创建独立虚拟环境
cd hugo-page
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖包
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. Hugo Extended 静态引擎安装

> ⚠️ **重要**：必须安装 **Hugo Extended (扩展版)**，系统默认 `apt install hugo` 通常版本过旧且不含扩展模块。

在 Ubuntu 上直接下载官方 `.deb` 安装包（速度快且原生集成系统 PATH）：

### x86_64 (常见 64 位 Intel / AMD 服务器)：
```bash
HUGO_VER="0.145.0"
wget -q --show-progress "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VER}/hugo_extended_${HUGO_VER}_linux-amd64.deb"
sudo dpkg -i hugo_extended_${HUGO_VER}_linux-amd64.deb
rm -f hugo_extended_${HUGO_VER}_linux-amd64.deb
```

### ARM64 (例如甲骨文 ARM / 树莓派)：
```bash
HUGO_VER="0.145.0"
wget -q --show-progress "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VER}/hugo_extended_${HUGO_VER}_linux-arm64.deb"
sudo dpkg -i hugo_extended_${HUGO_VER}_linux-arm64.deb
rm -f hugo_extended_${HUGO_VER}_linux-arm64.deb
```

### 验证安装：
```bash
hugo version
# 输出示例：hugo v0.145.0+extended linux/amd64 ... 即表示成功
```

---

## 3. GitHub 仓库授权与配置（免密推送）

由于程序在后台定时执行时**无人值守**，必须确保服务器具备向 GitHub 仓库免密推送的权限。

### 推荐方案：配置服务器 SSH 密钥（最稳定、永不过期）

#### 步骤 3.1：在 Ubuntu 上生成专属 SSH 密钥
```bash
ssh-keygen -t ed25519 -C "steamhunter-ubuntu" -f ~/.ssh/id_steamhunter -N ""
```

#### 步骤 3.2：将公钥添加到 GitHub
查看刚生成的公钥内容：
```bash
cat ~/.ssh/id_steamhunter.pub
# 会输出类似 ssh-ed25519 AAAAC3NzaC... steamhunter-ubuntu
```
1. 打开浏览器登录 GitHub，进入仓库的 Deploy Keys 设置，或者个人设置：
   👉 **个人 Settings** -> **SSH and GPG keys** -> 点击 **New SSH key**
   （或进入仓库 `https://github.com/keirosang/steamhunter/settings/keys` 点击 **Add deploy key**，勾选 **Allow write access**）；
2. 粘贴公钥内容并保存。

#### 步骤 3.3：配置 SSH 识别此密钥并测试连接
编辑或创建 `~/.ssh/config`：
```bash
cat << 'EOF' >> ~/.ssh/config
Host github.com
    User git
    IdentityFile ~/.ssh/id_steamhunter
    StrictHostKeyChecking no
EOF
chmod 600 ~/.ssh/config
```

测试 GitHub 连通性：
```bash
ssh -T git@github.com
# 看到 Hi keirosang! You've successfully authenticated... 即表示权限通过！
```

#### 步骤 3.4：配置本地 Git 仓库远程地址为 SSH 格式
```bash
cd hugo-page
git remote set-url origin git@github.com:keirosang/steamhunter.git
```

---

## 4. 开启 GitHub Pages 自动化工作流

项目内已包含官方标准化工作流文件：[`.github/workflows/hugo.yml`](file:///Users/luoqi/WORK/work006/hugo-page/.github/workflows/hugo.yml)。

为了让 GitHub 在收到推送时自动构建并发布网站，**必须在仓库页面开启 Actions 权限**：

1. 打开浏览器，访问仓库设置：  
   👉 `https://github.com/keirosang/steamhunter/settings/pages`
2. 在页面中找到 **Build and deployment**；
3. 将 **Source** 从默认的 "Deploy from a branch" 改选为：  
   👉 **GitHub Actions**
4. 保存即可！此后每次推送新文章，GitHub 将在后台自动编译静态网页并刷新站点。

---

## 5. 环境变量配置检查 (.env)

确保 `hugo-page/.env` 中的参数符合当前环境：

```ini
# 1. LLM 智能润色模型配置
OPENAI_API_KEY=sk-UhYSI7glgR2T5Tlh7VorG30upaDY5cUIXwSgPlsHcXrsscWM
OPENAI_API_BASE=https://api.relayrouter.ai/v1
OPENAI_MODEL=gemini-3.8-flash
OPENAI_TEMPERATURE=0.7

# 2. 采集源与频率
CRAWL_NEWS=true
CRAWL_SPECIALS=true
MAX_POSTS_PER_RUN=5
# 文章采集跨度（单位：天，最少 1 天。配置 1 则仅采集 24 小时以内的最新鲜文章）
CRAWL_MAX_AGE_DAYS=1
WATCHED_APPIDS=2358720,1808500,730,1091500,1086940,271590,2344520,1172620,1623730,570,578080,1172470,413150,582010

# 3. 静态图床本地化（避免 GitHub Pages 防盗链 403 破图）
LOCALIZE_IMAGES=true

# 4. 站点基准地址
SITE_BASE_URL=https://keirosang.github.io/steamhunter/
SITE_TITLE=Steam 蒸汽猎手 | 游戏情报站
SITE_AUTHOR=SteamHunter
AUTO_HUGO_BUILD=true

# 5. GitHub 自动推送（部署到 Ubuntu 定时执行时请改为 true）
GITHUB_AUTO_PUSH=true
GITHUB_REPO_URL=git@github.com:keirosang/steamhunter.git
GITHUB_BRANCH=main
GIT_AUTHOR_NAME=SteamHunter Bot
GIT_AUTHOR_EMAIL=bot@steamhunter.local
```

---

## 6. 初次手动执行与验证

在配置定时任务之前，建议在 Ubuntu 上手动运行一次验证整体流程：

```bash
cd hugo-page

# 执行专属巡检脚本（限制单次 2 篇以快速验证）
./run_cron.sh --limit 2
```

实时观察日志输出：
```bash
tail -f logs/cron.log
```

若看到以下输出日志，说明全链路打通：
1. `[新情报捕获] ...`
2. `✨ 润色完成: ...`
3. `📝 正在生成 Hugo Markdown 并本地化缓存配图...`
4. `[Hugo 构建成功] 静态资源编译完成`
5. `[Git 推送成功] GitHub Pages 仓库同步完成！`

此时打开你的 GitHub 仓库 `https://github.com/keirosang/steamhunter` 即可看到新增文章，几分钟后访问 `https://keirosang.github.io/steamhunter/` 即可看到线上站点！

---

## 7. Crontab 定时巡检发布配置

使用 Linux 自带的 `crontab` 守护程序实现全自动轮巡。

### 步骤 7.1：打开当前用户的定时任务编辑器
```bash
crontab -e
```

### 步骤 7.2：添加定时规则
假定你的程序放置于 `/home/ubuntu/hugo-page`（**请根据实际路径替换**）：

```cron
# ==============================================================================
# Steam 蒸汽猎手：每 3 小时全自动巡检采集并推送到 GitHub Pages 一次
# ==============================================================================
0 */3 * * * /bin/bash /home/ubuntu/hugo-page/run_cron.sh >> /home/ubuntu/hugo-page/logs/system_cron.log 2>&1
```

#### 常见巡检周期参考：
- **每 2 小时检查一次**：`0 */2 * * * /bin/bash /绝对路径/run_cron.sh >/dev/null 2>&1`
- **每 4 小时检查一次**：`0 */4 * * * /bin/bash /绝对路径/run_cron.sh >/dev/null 2>&1`
- **每天上午 9 点和下午 18 点各巡检一次**：`0 9,18 * * * /bin/bash /绝对路径/run_cron.sh >/dev/null 2>&1`

> 💡 **防重机制说明**：`run_cron.sh` 脚本内集成了 `flock` 文件锁。即使某次网络波动导致采集时间变长，后续的定时任务也会自动避让，绝不会发生并发冲突。

---

## 8. 进阶：Systemd Timer 服务化托管（可选）

对于企业级 Ubuntu 主机，可使用 `systemd` 服务与定时器进行监控管理：

### 1. 创建 Service 单元：`/etc/systemd/system/steamhunter.service`
```ini
[Unit]
Description=Steam Hunter Hugo Pages Auto Publisher
After=network-online.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/hugo-page
ExecStart=/bin/bash /home/ubuntu/hugo-page/run_cron.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 2. 创建 Timer 定时器：`/etc/systemd/system/steamhunter.timer`
```ini
[Unit]
Description=Run Steam Hunter periodically

[Timer]
OnBootSec=5min
OnUnitActiveSec=3h
Persistent=true

[Install]
WantedBy=timers.target
```

### 3. 启用并启动定时器
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now steamhunter.timer
sudo systemctl list-timers steamhunter.timer
```

---

## 9. 常见问题与排错指引 (FAQ)

### Q1: Crontab 执行报错 `hugo: command not found`？
- **原因**：Linux 定时任务的非交互式 Shell 默认 `$PATH` 仅包含 `/usr/bin:/bin`。
- **解决**：`run_cron.sh` 脚本已在顶部显式导出完整的 `export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin:$PATH"`，确保使用 `./run_cron.sh` 启动即可完美解决。

### Q2: Git 推送提示 `Permission to keirosang/steamhunter.git denied`？
- **原因**：SSH 密钥未正确添加到 GitHub 或未赋予写权限。
- **排查**：
  1. 运行 `ssh -T git@github.com` 确认返回 `successfully authenticated`；
  2. 若使用的是仓库专属的 **Deploy Key**，必须在 GitHub 仓库设置中勾选 **Allow write access**（允许写权限）；
  3. 确认 `.env` 中 `GITHUB_REPO_URL` 格式为 `git@github.com:keirosang/steamhunter.git`。

### Q3: 线上 GitHub Pages 页面排版错乱或样式加载 404？
- **原因**：仓库属于二级路径 (`/steamhunter/`)，若 `baseURL` 未带子目录会导致静态资源寻址错误。
- **排查**：检查 `hugo.toml` 与 `.env` 中的 `baseURL` 必须严格为 `https://keirosang.github.io/steamhunter/`（末尾包含斜杠）。本系统已预设适配此规范。

### Q4: 如何查看历史收录总量与运营状态？
随时在命令行运行状态查询：
```bash
cd hugo-page
./run_cron.sh --status
```
将以整齐的表格形式列出收录文章数、数据库路径与最新录入的文章记录。

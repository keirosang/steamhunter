# 🎮 Steam 蒸汽猎手 · Hugo + GitHub Pages 独立采集发布系统

> **独立运行 | 独立配置 | LLM 玩家主理人润色 | 本地防盗链图床 | 自动 Hugo 构建 | 一键同步 GitHub Pages**

---

## 📖 项目简介

本项目是专门针对 **GitHub Pages 静态托管** 打造的 Steam 游戏情报与特惠专栏自动生成系统。

- **完全独立**：程序位于 `hugo-page/` 目录内，拥有独立的 Python 采集程序、独立的数据库与独立的配置文件（`hugo-page/.env`），**与原工程代码无任何依赖和关联**。
- **AI 智能润色**：深度对接 OpenAI 协议（OpenAI、DeepSeek、Gemini、通义千问等），自动将官方公告与特惠重构成排版精美、充满玩家行话、利于 SEO 的中文精品长文；无网络或未配 Key 时内置离线智能重构保底引擎。
- **本地化防盗链图床**：自动解析 Steam 各种 Clan 占位符并流式下载至 `static/images/`，彻底根除 GitHub Pages 防外链 403 破图问题。
- **极速 Hugo 静态站**：内置自包含现代化电竞风响应式模板（支持暗黑/明亮模式切换、文章目录 TOC、即时卡片筛选、分类标签云、Steam 客户端直达协议）。
- **全自动发布闭环**：支持一键完成采集 -> 润色 -> 生成 Markdown -> 本地 Hugo 编译 -> Git 提交与 GitHub 远程同步。

---

## 📁 目录架构说明

```text
hugo-page/
├── .env                        # 独立环境变量配置（已自动生成）
├── .env.example                # 环境变量配置模板
├── .gitignore                  # Git 忽略配置（忽略密钥与缓存）
├── requirements.txt            # 独立 Python 依赖
├── hugo.toml                   # Hugo 全局站点配置
├── main.py                     # 独立采集与发布主入口 CLI
├── config.py                   # 独立配置加载模块
├── collector.py                # 独立 Steam 情报与特惠采集引擎
├── ai_polisher.py              # LLM 玩家主理人风格润色模块（含离线保底）
├── hugo_generator.py           # Hugo Markdown 文章与本地化配图生成器
├── git_syncer.py               # 本地 Hugo 构建与 Git 提交推送器
├── storage.py                  # 独立轻量 SQLite 去重底表模块
├── .github/
│   └── workflows/
│       └── hugo.yml            # GitHub Pages 官方推荐自动构建 Action 脚本
├── archetypes/                 # Hugo 内容原型
├── content/
│   ├── posts/                  # 自动生成的 Markdown 文章目录
│   └── about.md                # 关于本站内页
├── layouts/                    # 自包含高颜值响应式 Hugo 模板
│   ├── _default/
│   │   ├── baseof.html         # 页面骨架
│   │   ├── list.html           # 列表页/分类页
│   │   ├── single.html         # 文章详情页（含 TOC 与 Steam 直达按钮）
│   │   └── terms.html          # 标签索引页
│   ├── index.html              # 站点首页
│   └── partials/
│       ├── header.html         # 导航栏（明暗切换、搜索、移动端适配）
│       ├── footer.html         # 页脚
│       ├── head.html           # SEO、OpenGraph 与字体
│       └── summary.html        # 文章卡片
├── static/
│   ├── css/style.css           # 现代化深浅电竞风极客 CSS
│   ├── js/main.js              # 交互逻辑（明暗切换、即时筛选、复制链接）
│   └── images/                 # 本地化静态图床配图
└── data/
    └── hugo_crawler.db         # 本地 SQLite 增量去重底表
```

---

## ⚙️ 独立环境变量配置 (`hugo-page/.env`)

| 配置项 | 说明 | 默认值 / 示例 |
|---|---|---|
| `OPENAI_API_KEY` | LLM API 密钥（支持 OpenAI/DeepSeek/Gemini 等） | 必填（未填时自动启用离线重构引擎） |
| `OPENAI_API_BASE` | API 请求基地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 模型名称 | `gemini-3.8-flash` / `gpt-4o-mini` |
| `OPENAI_TEMPERATURE` | 模型发散度 | `0.7` |
| `CRAWL_NEWS` | 是否采集官方更新与补丁公告 | `true` |
| `CRAWL_SPECIALS` | 是否采集 Steam 特惠大促与超值折扣 | `true` |
| `MAX_POSTS_PER_RUN` | 单次运行最大抓取生成篇数 | `5` |
| `CRAWL_MAX_AGE_DAYS` | 文章采集跨度（天数，最少 1 天，低于 1 自动保底按 1 天处理） | `1` |
| `WATCHED_APPIDS` | 重点巡检的 Steam AppID 列表 | 英文逗号分隔热门 AppID |
| `LOCALIZE_IMAGES` | 是否将配图下载到 `static/images/` 防盗链 | `true` |
| `SITE_BASE_URL` | 线上访问基准地址（用于 Hugo 编译） | `https://<用户名>.github.io/<仓库名>/` |
| `AUTO_HUGO_BUILD` | 生成文章后是否本地执行 `hugo` 静态编译 | `true` |
| `GITHUB_AUTO_PUSH` | 是否在生成后自动执行 `git push` | `false`（配置仓库后改为 `true`） |
| `GITHUB_REPO_URL` | 目标 GitHub Pages 仓库地址 | `git@github.com:username/repo.git` |
| `GITHUB_BRANCH` | 目标分支 | `main` |

---

## 🚀 常用运行命令

进入 `hugo-page/` 目录即可独立运行：

```bash
cd hugo-page

# 1. 完整全流程执行（采集 -> AI润色 -> 写入Markdown -> Hugo构建 -> Git提交）
python main.py

# 2. 指定单次抓取最大篇数（例如只抓取 2 篇）
python main.py --limit 2

# 3. 试运行模式（抓取数据并打印，不写入文件、不消耗算力、不入库）
python main.py --dry-run

# 4. 查看当前已收录文章数量与最近记录
python main.py --status

# 5. 仅执行采集与 Markdown 生成（跳过 Hugo 构建与 Git 提交）
python main.py --crawl

# 6. 仅执行本地 Hugo 静态网页构建
python main.py --build

# 7. 本地实时预览站点效果（Hugo 内置服务器）
hugo server
# 打开浏览器访问 http://localhost:1313 即可预览
```

---

## 🌐 部署至 GitHub Pages 详细步骤

本项目推荐使用 **GitHub 官方原生 GitHub Actions 方式** 自动构建与部署。

### 步骤 1：在 GitHub 创建仓库
在 GitHub 上创建一个新仓库（例如名为 `steam-hunter-pages` 或 `<用户名>.github.io`）。

### 步骤 2：绑定远程仓库并开启自动推送
在 `hugo-page/.env` 中填入你的 GitHub 仓库地址，并开启自动推送：
```env
GITHUB_REPO_URL=git@github.com:你的用户名/你的仓库名.git
GITHUB_AUTO_PUSH=true
```

或者手动添加远程地址并初次推送：
```bash
cd hugo-page
git remote add origin git@github.com:你的用户名/你的仓库名.git
git push -u origin main
```

### 步骤 3：在 GitHub 仓库开启 Pages 服务
1. 进入 GitHub 仓库页面，点击 **Settings** -> **Pages**；
2. 在 **Build and deployment** 下方的 **Source** 下拉菜单中选择：
   👉 **GitHub Actions**
3. 以后每次推送代码，`.github/workflows/hugo.yml` 将自动触发，在云端自动编译 Hugo 并部署到 GitHub Pages！

---

## ⏰ 定时自动化巡检配置（可选）

若希望本机每天/每小时自动巡检并发布到 GitHub Pages，可在本机设置定时任务：

```bash
# 打开 crontab 编辑
crontab -e

# 添加如下定时任务（例如每 4 小时自动巡检一次并推送发布）：
0 */4 * * * cd /Users/luoqi/WORK/work006/hugo-page && /Users/luoqi/WORK/work006/.venv/bin/python main.py >> /Users/luoqi/WORK/work006/hugo-page/cron.log 2>&1
```

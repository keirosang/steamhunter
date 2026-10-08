#!/usr/bin/env bash
# ==============================================================================
# Steam 蒸汽猎手 - Ubuntu 服务器一键初始化脚本
# 支持系统：Ubuntu 20.04 / 22.04 / 24.04 (x86_64 / arm64)
# ==============================================================================

set -e

echo "=========================================================="
echo "🚀 开始安装 SteamHunter Hugo-Page Ubuntu 运行环境..."
echo "=========================================================="

# 1. 更新系统包索引并安装基础软件
echo "📦 [1/5] 安装 Python3、Git、Curl 等基础系统工具..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git curl wget tar

# 2. 安装 Hugo Extended 最新版
echo "🌐 [2/5] 检测并安装 Hugo Extended 静态构建引擎..."
if command -v hugo &> /dev/null; then
    echo "  ✅ 检测到系统已安装 Hugo: $(hugo version)"
else
    ARCH=$(uname -m)
    HUGO_VER="0.145.0"
    if [ "$ARCH" = "x86_64" ]; then
        HUGO_PKG="hugo_extended_${HUGO_VER}_linux-amd64.deb"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        HUGO_PKG="hugo_extended_${HUGO_VER}_linux-arm64.deb"
    else
        echo "  ❌ 未知架构: $ARCH，请手动安装 Hugo"
        exit 1
    fi

    echo "  ⬇️ 正在从 GitHub 下载 Hugo Extended (${HUGO_PKG})..."
    wget -q --show-progress "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VER}/${HUGO_PKG}" -O "/tmp/${HUGO_PKG}"
    sudo dpkg -i "/tmp/${HUGO_PKG}" || sudo apt-get install -f -y
    rm -f "/tmp/${HUGO_PKG}"
    echo "  ✅ Hugo 安装成功: $(hugo version)"
fi

# 3. 准备当前工作目录与 Python 虚拟环境
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$SCRIPT_DIR"

echo "🐍 [3/5] 创建 Python 虚拟环境 (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

echo "📦 [4/5] 安装 Python 独立依赖清单..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. 赋予执行脚本权限并创建日志目录
echo "⚙️ [5/5] 配置脚本执行权限与日志目录..."
chmod +x main.py run_cron.sh setup_ubuntu.sh
mkdir -p logs data

echo ""
echo "=========================================================="
echo "🎉 Ubuntu 环境初始化完成！"
echo "=========================================================="
echo "下一步操作建议："
echo "1. 检查并确认配置文件：nano .env"
echo "2. 测试执行一次全流程：./run_cron.sh --limit 2"
echo "3. 设置定时任务（crontab -e），可参考 DEPLOY_UBUNTU.md 详细文档"
echo "=========================================================="

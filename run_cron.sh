#!/usr/bin/env bash
# ==============================================================================
# Steam 蒸汽猎手 - Linux / Ubuntu 定时巡检执行入口脚本 (支持 Crontab & Systemd)
# ==============================================================================

# 1. 确保包含完整的系统命令搜索路径（解决 Crontab 找不到 hugo / git 问题）
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin:$PATH"

# 2. 定位到脚本所在实际目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$SCRIPT_DIR"

# 3. 准备日志目录与锁文件（防止前一个任务未结束导致并发冲突）
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/cron.log"
LOCK_FILE="$SCRIPT_DIR/data/.cron.lock"

mkdir -p "$LOG_DIR" "$SCRIPT_DIR/data"

# 4. 单实例锁检查（避免并发执行）
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️ 上一个采集任务仍在执行中，本次跳过。" >> "$LOG_FILE"
    exit 0
fi

echo "==========================================================" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚀 开始执行自动化采集与发布流程..." >> "$LOG_FILE"

# 5. 激活虚拟环境并执行程序
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
    PYTHON_EXEC="$SCRIPT_DIR/.venv/bin/python3"
else
    PYTHON_EXEC="$(command -v python3)"
fi

# 执行 Python 核心流程并将日志输出到标准输出和日志文件
"$PYTHON_EXEC" "$SCRIPT_DIR/main.py" "$@" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 本轮自动化流程执行成功。" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ 执行异常退出，退出码: $EXIT_CODE" >> "$LOG_FILE"
fi

# 日志文件维护：若日志超过 10MB 自动保留最近 2000 行
if [ -f "$LOG_FILE" ] && [ $(wc -c < "$LOG_FILE") -gt 10485760 ]; then
    tail -n 2000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi

exit $EXIT_CODE

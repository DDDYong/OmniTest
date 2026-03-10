#!/bin/bash

# ========================================================
# 启动多个Appium服务的脚本
# ========================================================

set -e

echo "======================================"
echo "  启动Appium服务"
echo "======================================"

# 配置参数
NUM_SERVERS=${1:-2}
BASE_PORT=4723
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"

mkdir -p "$LOG_DIR"

echo "配置信息："
echo "  Appium服务数量: $NUM_SERVERS"
echo "  基础端口: $BASE_PORT"
echo "  日志目录: $LOG_DIR"
echo ""

# 检查Appium是否安装
if ! command -v appium &> /dev/null; then
    echo "❌ 错误: Appium 未安装"
    echo "   请运行: npm install -g appium"
    exit 1
fi

# 函数：检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 启动Appium服务
pids=()
for i in $(seq 0 $((NUM_SERVERS - 1))); do
    PORT=$((BASE_PORT + i))
    LOG_FILE="$LOG_DIR/appium_${PORT}.log"
    
    echo "--- Appium服务 $i (端口: $PORT) ---"
    
    if check_port $PORT; then
        echo "   ⚠️  端口 $PORT 已被占用"
        echo "   尝试停止现有服务..."
        pkill -f "appium.*--port $PORT" 2>/dev/null || true
        sleep 3
    fi
    
    echo "   启动Appium服务..."
    appium --port "$PORT" \
           --log "$LOG_FILE" \
           --log-level info \
           --relaxed-security \
           --allow-insecure=chromedriver_autodownload &
    
    APPIUM_PID=$!
    pids+=($APPIUM_PID)
    echo "   PID: $APPIUM_PID"
    echo "   日志: $LOG_FILE"
    
    sleep 2
    
    # 检查服务是否启动成功
    for j in {1..15}; do
        if curl -s "http://127.0.0.1:$PORT/status" >/dev/null 2>&1; then
            echo "   ✅ Appium服务 $i 启动成功"
            break
        fi
        sleep 1
    done
    
    echo ""
done

echo "======================================"
echo "  ✅ Appium服务启动完成"
echo "======================================"
echo ""
echo "服务列表："
for i in $(seq 0 $((NUM_SERVERS - 1))); do
    PORT=$((BASE_PORT + i))
    echo "  服务 $i: http://127.0.0.1:$PORT"
done
echo ""
echo "运行并行测试命令："
echo "  pytest cases/app/test_app_login_parallel_simple.py -m parallel -n $NUM_SERVERS"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 等待所有子进程
wait

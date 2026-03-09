#!/bin/bash

# ========================================================
# 并行测试环境启动脚本
# 用于启动多个Android模拟器和Appium服务
# ========================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================"
echo "  启动并行测试环境"
echo "======================================"

# 配置参数
NUM_DEVICES=${1:-2}  # 默认启动2个设备
BASE_EMULATOR_PORT=5554
BASE_APPIUM_PORT=4723
BASE_SYSTEM_PORT=8200

echo "配置信息："
echo "  设备数量: $NUM_DEVICES"
echo "  基础模拟器端口: $BASE_EMULATOR_PORT"
echo "  基础Appium端口: $BASE_APPIUM_PORT"
echo "  基础System端口: $BASE_SYSTEM_PORT"
echo ""

# 检查Android SDK
if [ -z "$ANDROID_HOME" ]; then
    echo "⚠️  警告: ANDROID_HOME 环境变量未设置"
    echo "   请先设置 ANDROID_HOME 环境变量"
fi

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
        return 0  # 端口被占用
    else
        return 1  # 端口可用
    fi
}

# 函数：获取可用的模拟器
get_available_emulators() {
    if command -v emulator &> /dev/null; then
        emulator -list-avds 2>/dev/null || true
    fi
}

# 函数：启动模拟器
start_emulator() {
    local device_idx=$1
    local emulator_port=$((BASE_EMULATOR_PORT + device_idx * 2))
    local avd_name=$2
    
    echo "📱  启动模拟器 $device_idx (端口: $emulator_port)..."
    
    if [ -n "$avd_name" ]; then
        if command -v emulator &> /dev/null; then
            echo "   使用AVD: $avd_name"
            emulator -avd "$avd_name" -port "$emulator_port" -no-boot-anim -no-window -gpu swiftshader_indirect &
            EMULATOR_PID=$!
            echo "   模拟器PID: $EMULATOR_PID"
            
            # 等待模拟器启动
            echo "   等待模拟器启动..."
            sleep 30
            
            # 等待设备就绪
            local adb_port=$((emulator_port + 1))
            local device_serial="emulator-$emulator_port"
            
            for i in {1..60}; do
                if adb -s "$device_serial" shell getprop dev.bootcomplete 2>/dev/null | grep -q "1"; then
                    echo "   ✅ 模拟器 $device_idx 启动成功: $device_serial"
                    echo "$EMULATOR_PID" > /tmp/emulator_${device_idx}.pid
                    return 0
                fi
                sleep 2
            done
            
            echo "   ❌ 模拟器 $device_idx 启动超时"
            return 1
        else
            echo "   ⚠️  emulator命令不可用，跳过模拟器启动"
            return 0
        fi
    else
        echo "   ⚠️  未指定AVD名称，假设设备已连接"
        return 0
    fi
}

# 函数：启动Appium服务
start_appium() {
    local device_idx=$1
    local appium_port=$((BASE_APPIUM_PORT + device_idx))
    local system_port=$((BASE_SYSTEM_PORT + device_idx))
    
    echo "🚀  启动Appium服务 $device_idx (端口: $appium_port)..."
    
    # 检查端口是否被占用
    if check_port $appium_port; then
        echo "   ⚠️  端口 $appium_port 已被占用，尝试停止现有服务..."
        pkill -f "appium.*--port $appium_port" 2>/dev/null || true
        sleep 3
    fi
    
    # 启动Appium
    LOG_DIR="$PROJECT_ROOT/logs"
    mkdir -p "$LOG_DIR"
    
    appium --port "$appium_port" \
           --log "$LOG_DIR/appium_${device_idx}.log" \
           --log-level info \
           --relaxed-security \
           --allow-insecure=chromedriver_autodownload &
    
    APPIUM_PID=$!
    echo "   Appium PID: $APPIUM_PID"
    echo "$APPIUM_PID" > /tmp/appium_${device_idx}.pid
    
    # 等待Appium启动
    echo "   等待Appium服务启动..."
    for i in {1..30}; do
        if curl -s "http://127.0.0.1:$appium_port/status" >/dev/null 2>&1; then
            echo "   ✅ Appium服务 $device_idx 启动成功"
            return 0
        fi
        sleep 1
    done
    
    echo "   ❌ Appium服务 $device_idx 启动超时"
    return 1
}

# 函数：停止所有服务
stop_all() {
    echo ""
    echo "停止所有服务..."
    
    # 停止Appium服务
    for i in $(seq 0 $((NUM_DEVICES - 1))); do
        if [ -f /tmp/appium_${i}.pid ]; then
            PID=$(cat /tmp/appium_${i}.pid 2>/dev/null || true)
            if [ -n "$PID" ] && kill -0 $PID 2>/dev/null; then
                echo "  停止Appium服务 $i (PID: $PID)..."
                kill $PID 2>/dev/null || true
                wait $PID 2>/dev/null || true
            fi
            rm -f /tmp/appium_${i}.pid
        fi
    done
    
    # 停止模拟器
    for i in $(seq 0 $((NUM_DEVICES - 1))); do
        if [ -f /tmp/emulator_${i}.pid ]; then
            PID=$(cat /tmp/emulator_${i}.pid 2>/dev/null || true)
            if [ -n "$PID" ] && kill -0 $PID 2>/dev/null; then
                echo "  停止模拟器 $i (PID: $PID)..."
                kill $PID 2>/dev/null || true
                wait $PID 2>/dev/null || true
            fi
            rm -f /tmp/emulator_${i}.pid
        fi
    done
    
    echo "所有服务已停止"
    exit 0
}

# 设置信号处理
trap stop_all SIGINT SIGTERM

# 获取可用的模拟器列表
echo ""
echo "📋  可用的Android模拟器："
AVDS=($(get_available_emulators))
if [ ${#AVDS[@]} -eq 0 ]; then
    echo "  未找到可用的模拟器"
    echo "  请确保已创建模拟器或使用物理设备"
else
    for i in "${!AVDS[@]}"; do
        echo "  $((i + 1)). ${AVDS[$i]}"
    done
fi
echo ""

# 启动服务
echo "🚀  开始启动服务..."
echo ""

for i in $(seq 0 $((NUM_DEVICES - 1))); do
    echo "--- 设备 $i ---"
    
    # 启动模拟器（如果有AVD）
    AVD_NAME=${AVDS[$i]:-}
    start_emulator $i "$AVD_NAME"
    
    # 启动Appium服务
    start_appium $i
    
    echo ""
done

echo "======================================"
echo "  ✅ 并行测试环境启动完成"
echo "======================================"
echo ""
echo "设备配置："
for i in $(seq 0 $((NUM_DEVICES - 1))); do
    EMULATOR_PORT=$((BASE_EMULATOR_PORT + i * 2))
    APPIUM_PORT=$((BASE_APPIUM_PORT + i))
    SYSTEM_PORT=$((BASE_SYSTEM_PORT + i))
    echo "  设备 $i:"
    echo "    设备ID: emulator-$EMULATOR_PORT"
    echo "    Appium端口: $APPIUM_PORT"
    echo "    System端口: $SYSTEM_PORT"
done
echo ""
echo "运行并行测试命令："
echo "  pytest cases/app/test_app_login_parallel.py -m parallel -n $NUM_DEVICES"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 保持脚本运行
wait

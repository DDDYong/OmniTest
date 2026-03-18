#!/bin/zsh

# ========================================================
# 测试环境启动脚本
# 支持配置设备数量、是否启动模拟器
# 自动分配端口，为每个设备启动独立 Appium 服务
# ========================================================

set -e

# 正确计算项目根目录
SCRIPT_PATH="$0"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"
echo "当前工作目录: $(pwd)"

echo "======================================"
echo "  启动测试环境"
echo "======================================"

# 配置参数
NUM_DEVICES=${1:-2}  # 默认设备数量
START_EMULATORS=${2:-true}  # 是否启动模拟器
BASE_EMULATOR_PORT=5554
BASE_APPIUM_PORT=4723
BASE_SYSTEM_PORT=8200

echo "配置信息: "
echo "  设备数量: $NUM_DEVICES"
echo "  启动模拟器: $START_EMULATORS"
echo "  基础模拟器端口: $BASE_EMULATOR_PORT"
echo "  基础Appium端口: $BASE_APPIUM_PORT"
echo "  基础System端口: $BASE_SYSTEM_PORT"
echo ""

# 检查Android SDK
if [[ -z "$ANDROID_HOME" ]]; then
    echo "⚠️  警告: ANDROID_HOME 环境变量未设置"
    echo "   请先设置 ANDROID_HOME 环境变量"
fi

# 检查Appium是否安装
if ! command -v appium &> /dev/null; then
    echo "❌ 错误: Appium 未安装"
    echo "   请运行: npm install -g appium"
    exit 1
fi

# 函数: 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # 端口被占用
    else
        return 1  # 端口可用
    fi
}

# 函数: 获取可用的模拟器
get_available_emulators() {
    if command -v emulator &> /dev/null; then
        emulator -list-avds 2>/dev/null || true
    fi
}

# 函数: 获取已连接的设备
get_connected_devices() {
    if command -v adb &> /dev/null; then
        adb devices | grep -v "List of devices" | grep -v "^$" | awk '{print $1}'
    fi
}

# 函数: 启动模拟器
start_emulator() {
    local device_idx=$1
    local emulator_port=$((BASE_EMULATOR_PORT + device_idx * 2))
    local avd_name=$2
    
    echo "📱  启动模拟器 $device_idx (端口: $emulator_port)..."
    
    if [[ -n "$avd_name" ]]; then
        if command -v emulator &> /dev/null; then
            echo "   使用AVD: $avd_name"
            emulator -avd "$avd_name" -port "$emulator_port" -no-boot-anim -no-window -gpu swiftshader_indirect &
            local EMULATOR_PID=$!
            echo "   模拟器PID: $EMULATOR_PID"
            
            # 等待模拟器启动
            echo "   等待模拟器启动..."
            sleep 30
            
            # 等待设备就绪
            local adb_port=$((emulator_port + 1))
            local device_serial="emulator-$emulator_port"
            
            for ((i=1; i<=60; i++)); do
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
            echo "   ⚠️  emulator命令不可用, 跳过模拟器启动"
            return 0
        fi
    else
        echo "   ⚠️  未指定AVD名称, 跳过模拟器启动"
        return 0
    fi
}

# 函数: 启动Appium服务
start_appium() {
    local device_idx=$1
    local device_serial=$2
    local appium_port=$((BASE_APPIUM_PORT + device_idx))
    local system_port=$((BASE_SYSTEM_PORT + device_idx))
    
    echo "🚀  启动Appium服务 $device_idx (端口: $appium_port) for $device_serial..."
    
    # 检查端口是否被占用
    if check_port $appium_port; then
        echo "   ⚠️  端口 $appium_port 已被占用, 尝试停止现有服务..."
        pkill -f "appium.*--port $appium_port" 2>/dev/null || true
        sleep 3
    fi
    
    # 启动Appium
    local LOG_DIR="$PROJECT_ROOT/logs"
    mkdir -p "$LOG_DIR"
    
    # 设置Appium临时目录以避免权限问题
    export APPIUM_HOME="$PROJECT_ROOT/.appium"
    mkdir -p "$APPIUM_HOME"
    
    appium --port "$appium_port" \
           --log "$LOG_DIR/appium_${device_idx}_${device_serial}.log" \
           --log-level info \
           --relaxed-security \
           --allow-insecure=chromedriver_autodownload &
    
    local APPIUM_PID=$!
    echo "   Appium PID: $APPIUM_PID"
    echo "$APPIUM_PID" > /tmp/appium_${device_idx}_${device_serial}.pid
    
    # 等待Appium启动
    echo "   等待Appium服务启动..."
    for ((i=1; i<=30; i++)); do
        if curl -s "http://127.0.0.1:$appium_port/status" >/dev/null 2>&1; then
            echo "   ✅ Appium服务 $device_idx 启动成功"
            return 0
        fi
        sleep 1
    done
    
    echo "   ❌ Appium服务 $device_idx 启动超时"
    return 1
}

# 函数: 停止所有服务
stop_all() {
    echo ""
    echo "停止所有服务..."
    
    # 停止Appium服务
    for pid_file in /tmp/appium_*.pid; do
        if [[ -f "$pid_file" ]]; then
            local PID=$(cat "$pid_file" 2>/dev/null || true)
            if [[ -n "$PID" && $(kill -0 $PID 2>/dev/null; echo $?) -eq 0 ]]; then
                echo "  停止Appium服务 (PID: $PID)..."
                kill $PID 2>/dev/null || true
                wait $PID 2>/dev/null || true
            fi
            rm -f "$pid_file"
        fi
    done
    
    # 停止模拟器
    for pid_file in /tmp/emulator_*.pid; do
        if [[ -f "$pid_file" ]]; then
            local PID=$(cat "$pid_file" 2>/dev/null || true)
            if [[ -n "$PID" && $(kill -0 $PID 2>/dev/null; echo $?) -eq 0 ]]; then
                echo "  停止模拟器 (PID: $PID)..."
                kill $PID 2>/dev/null || true
                wait $PID 2>/dev/null || true
            fi
            rm -f "$pid_file"
        fi
    done
    
    echo "所有服务已停止"
    exit 0
}

# 设置信号处理
trap stop_all SIGINT SIGTERM

# 获取可用的模拟器列表
echo ""
echo "📋  可用的Android模拟器: "
local AVDS=()
if command -v emulator &> /dev/null; then
    AVDS=($(emulator -list-avds 2>/dev/null || true))
fi

if [[ ${#AVDS[@]} -eq 0 ]]; then
    echo "  未找到可用的模拟器"
    if [[ "$START_EMULATORS" = "true" ]]; then
        echo "  警告: 未找到可用的模拟器, 将使用已连接的设备"
        START_EMULATORS=false
    fi
else
    local index=1
    for avd in "${AVDS[@]}"; do
        echo "  $index. $avd"
        index=$((index + 1))
    done
fi

# 获取已连接的设备
echo ""
echo "📱  已连接的设备: "
local CONNECTED_DEVICES=()
if command -v adb &> /dev/null; then
    # 直接解析adb devices输出
    while read -r line; do
        # 跳过空行和标题行
        if [[ -n "$line" && ! "$line" =~ "List of devices" ]]; then
            # 提取设备ID
            local device_id=$(echo "$line" | awk '{print $1}')
            if [[ -n "$device_id" ]]; then
                CONNECTED_DEVICES+=($device_id)
                echo "  添加设备: $device_id"
            fi
        fi
    done < <(adb devices)
fi



if [[ ${#CONNECTED_DEVICES[@]} -eq 0 ]]; then
    echo "  未找到已连接的设备"
    if [[ "$START_EMULATORS" = "false" ]]; then
        echo "  错误: 未找到已连接的设备, 且未设置启动模拟器"
        exit 1
    fi
else
    local index=1
    for device in "${CONNECTED_DEVICES[@]}"; do
        echo "  $index. $device"
        index=$((index + 1))
    done
fi

echo ""

# 启动服务
echo "🚀  开始启动服务..."
echo ""

# 管理设备和服务
local device_serials=()

# 1. 使用已连接的设备
local count=0
for device in "${CONNECTED_DEVICES[@]}"; do
    if [[ $count -lt $NUM_DEVICES ]]; then
        # 在zsh中, 使用+=来添加元素
        device_serials+=("$device")
        count=$((count + 1))
    else
        break
    fi
done

# 2. 如果需要, 启动模拟器
if [[ ${#device_serials[@]} -lt $NUM_DEVICES && "$START_EMULATORS" = "true" ]]; then
    local start_idx=${#device_serials[@]}
    for ((i=start_idx; i<NUM_DEVICES; i++)); do
        local AVD_NAME=${AVDS[i]:-}
        if [[ -n "$AVD_NAME" ]]; then
            start_emulator $i "$AVD_NAME"
            local emulator_port=$((BASE_EMULATOR_PORT + i * 2))
            local device_serial="emulator-$emulator_port"
            device_serials+=($device_serial)
        else
            echo "⚠️  没有足够的模拟器可用, 将使用已连接的设备"
            break
        fi
    done
fi

# 3. 启动Appium服务
if [[ ${#device_serials[@]} -eq 0 ]]; then
    echo "❌ 错误: 没有可用的设备"
    exit 1
fi

# 启动Appium服务
local device_idx=0
for device in "${device_serials[@]}"; do
    echo "--- 设备 $device_idx ---"
    echo "  设备ID: $device"
    start_appium $device_idx "$device"
    echo ""
    device_idx=$((device_idx + 1))
done

echo "======================================"
echo "  ✅ 测试环境启动完成"
echo "======================================"
echo ""
echo "设备配置: "
local i=0
for device in "${device_serials[@]}"; do
    local APPIUM_PORT=$((BASE_APPIUM_PORT + i))
    local SYSTEM_PORT=$((BASE_SYSTEM_PORT + i))
    echo "  设备 $i:"
    echo "    设备ID: $device"
    echo "    Appium端口: $APPIUM_PORT"
    echo "    System端口: $SYSTEM_PORT"
    i=$((i + 1))
done
echo ""
echo "运行并行测试命令: "
echo "  pytest cases/app/test_app_login.py -m parallel -n ${#device_serials[@]}"
echo "  或使用run.py: "
echo "  python run.py parallel --file test_app_login.py --workers ${#device_serials[@]}"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 保持脚本运行
wait
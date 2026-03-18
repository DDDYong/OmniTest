#!/bin/bash

# 用于管理虚拟环境的综合脚本
# 支持自动检测、激活、创建、退出虚拟环境
# 支持 .venv 和 Conda 环境

# 基本用法
# ./venv.sh --venv    # 优先使用 .venv 环境
# ./venv.sh --conda   # 优先使用 Conda 环境
# ./venv.sh --exit    # 退出当前虚拟环境
# ./venv.sh --create  # 创建虚拟环境
# ./venv.sh --update  # 更新依赖
# ./venv.sh --info    # 显示环境信息
# ./venv.sh --auto    # 生成自动激活配置
# ./venv.sh --help    # 显示帮助信息

# 颜色定义
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
PURPLE="\033[0;35m"
NC="\033[0m" # No Color

# 脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 项目根目录
PROJECT_ROOT="$SCRIPT_DIR"

# 虚拟环境路径 - 优先使用项目本地的 .venv
VENV_PATH="$PROJECT_ROOT/.venv"

# Conda 环境名称
CONDA_ENV_NAME="omnitest"

# 依赖文件路径
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"

# 检查是否已在虚拟环境中
is_in_venv() {
    if [ -n "$VIRTUAL_ENV" ] || [ -n "$CONDA_PREFIX" ]; then
        return 0
    else
        return 1
    fi
}

# 检查 .venv 环境是否存在
check_venv() {
    if [ -d "$VENV_PATH" ] && [ -f "$VENV_PATH/bin/activate" ]; then
        return 0
    else
        return 1
    fi
}

# 检查 Conda 环境是否存在
check_conda_env() {
    if conda env list | grep -q "^$CONDA_ENV_NAME "; then
        return 0
    else
        return 1
    fi
}

# 激活 .venv 环境
activate_venv() {
    echo -e "${GREEN}找到 .venv 虚拟环境: $VENV_PATH${NC}"
    echo -e "${GREEN}正在激活虚拟环境...${NC}"
    source "$VENV_PATH/bin/activate"
    echo -e "${GREEN}虚拟环境激活成功!${NC}"
    echo -e "${YELLOW}Python 解释器: $(which python)${NC}"
    echo -e "${YELLOW}Python 版本: $(python --version)${NC}"
}

# 激活 Conda 环境
activate_conda_env() {
    echo -e "${GREEN}找到 Conda 环境: $CONDA_ENV_NAME${NC}"
    echo -e "${GREEN}正在激活 Conda 环境...${NC}"
    conda activate "$CONDA_ENV_NAME"
    echo -e "${GREEN}Conda 环境激活成功!${NC}"
    echo -e "${YELLOW}Python 解释器: $(which python)${NC}"
    echo -e "${YELLOW}Python 版本: $(python --version)${NC}"
}

# 退出虚拟环境
exit_venv() {
    # 先检查是否在 .venv 环境中
    if [ -n "$VIRTUAL_ENV" ]; then
        echo -e "${YELLOW}正在退出 .venv 环境...${NC}"
        # 尝试使用 deactivate 命令
        deactivate 2>/dev/null || true
        echo -e "${GREEN}已成功退出 .venv 环境${NC}"
    fi

    # 再检查是否在 Conda 环境中
    if [ -n "$CONDA_PREFIX" ]; then
        echo -e "${YELLOW}正在退出 Conda 环境...${NC}"
        # 执行多次以完全退出到系统环境
        conda deactivate 2>/dev/null || true
        conda deactivate 2>/dev/null || true
        conda deactivate 2>/dev/null || true
        echo -e "${GREEN}已成功退出 Conda 环境${NC}"
    fi

    # 最后检查是否真的退出了所有环境
    if is_in_venv; then
        echo -e "${YELLOW}警告: 环境可能没有完全退出${NC}"
        echo -e "${YELLOW}当前状态: $(which python)${NC}"
    else
        echo -e "${GREEN}已成功退出所有虚拟环境${NC}"
    fi
    echo -e "${YELLOW}注意: 脚本在子shell中执行，无法直接修改父shell环境${NC}"
    echo -e "${YELLOW}请在终端中执行以下命令来完全退出环境:${NC}"
    echo ""
    echo "# 退出 .venv 环境"
    echo "deactivate"
    echo ""
    echo "# 退出 Conda 环境（可能需要执行多次）"
    echo "conda deactivate"
    echo "conda deactivate"
    echo ""
    echo "# 或者执行以下命令一次性退出所有环境"
    echo "deactivate 2>/dev/null || true && conda deactivate 2>/dev/null || true && conda deactivate 2>/dev/null || true"
    echo ""

    # 提示用户如何使用 source 命令来执行脚本
    echo -e "${BLUE}提示: 您也可以使用 source 命令执行此脚本，使其在当前shell中运行:${NC}"
    echo "source ./venv.sh --exit"
}

# 创建虚拟环境
create_venv() {
    echo -e "${BLUE}=== 创建虚拟环境 ===${NC}"
    echo "请选择要创建的环境类型:"
    echo "1. .venv 环境"
    echo "2. Conda 环境"
    echo "3. 取消"

    read -p "请输入选项 (1-3): " choice

    case "$choice" in
        1)
            echo -e "${GREEN}正在创建 .venv 环境...${NC}"
            if [ -d "$VENV_PATH" ]; then
                echo -e "${YELLOW}警告: .venv 目录已存在，将覆盖${NC}"
                rm -rf "$VENV_PATH"
            fi
            python3 -m venv "$VENV_PATH"
            echo -e "${GREEN}.venv 环境创建成功!${NC}"

            echo -e "${GREEN}正在激活环境...${NC}"
            source "$VENV_PATH/bin/activate"

            if [ -f "$REQUIREMENTS_FILE" ]; then
                echo -e "${GREEN}正在安装依赖...${NC}"
                pip3 install -r "$REQUIREMENTS_FILE" -i https://pypi.tuna.tsinghua.edu.cn/simple
                echo -e "${GREEN}依赖安装成功!${NC}"
            else
                echo -e "${YELLOW}警告: 未找到 requirements.txt 文件，跳过依赖安装${NC}"
            fi
            ;;
        2)
            echo -e "${GREEN}正在创建 Conda 环境...${NC}"
            if check_conda_env; then
                echo -e "${YELLOW}警告: Conda 环境 '$CONDA_ENV_NAME' 已存在，将覆盖${NC}"
                conda env remove -n "$CONDA_ENV_NAME"
            fi
            conda create -n "$CONDA_ENV_NAME" python=3.12 -y
            echo -e "${GREEN}Conda 环境创建成功!${NC}"

            echo -e "${GREEN}正在激活环境...${NC}"
            conda activate "$CONDA_ENV_NAME"

            if [ -f "$REQUIREMENTS_FILE" ]; then
                echo -e "${GREEN}正在安装依赖...${NC}"
                pip3 install -r "$REQUIREMENTS_FILE" -i https://pypi.tuna.tsinghua.edu.cn/simple
                echo -e "${GREEN}依赖安装成功!${NC}"
            else
                echo -e "${YELLOW}警告: 未找到 requirements.txt 文件，跳过依赖安装${NC}"
            fi
            ;;
        3)
            echo -e "${YELLOW}取消创建环境${NC}"
            ;;
        *)
            echo -e "${RED}错误: 无效的选项${NC}"
            ;;
    esac
}

# 更新依赖
update_dependencies() {
    if ! is_in_venv; then
        echo -e "${RED}错误: 请先激活虚拟环境${NC}"
        return 1
    fi

    if [ -f "$REQUIREMENTS_FILE" ]; then
        echo -e "${GREEN}正在更新依赖...${NC}"
        pip3 install --upgrade -r "$REQUIREMENTS_FILE" -i https://pypi.tuna.tsinghua.edu.cn/simple
        echo -e "${GREEN}依赖更新成功!${NC}"
    else
        echo -e "${RED}错误: 未找到 requirements.txt 文件${NC}"
        return 1
    fi
}

# 显示环境信息
show_env_info() {
    echo -e "${BLUE}=== 环境信息 ===${NC}"

    if is_in_venv; then
        echo -e "${GREEN}当前状态: 已在虚拟环境中${NC}"
        echo -e "${YELLOW}Python 解释器: $(which python)${NC}"
        echo -e "${YELLOW}Python 版本: $(python --version)${NC}"

        if [ -n "$VIRTUAL_ENV" ]; then
            echo -e "${YELLOW}环境类型: .venv${NC}"
            echo -e "${YELLOW}环境路径: $VIRTUAL_ENV${NC}"
        elif [ -n "$CONDA_PREFIX" ]; then
            echo -e "${YELLOW}环境类型: Conda${NC}"
            echo -e "${YELLOW}环境路径: $CONDA_PREFIX${NC}"
            echo -e "${YELLOW}环境名称: $(basename "$CONDA_PREFIX")${NC}"
        fi

        echo -e "${PURPLE}已安装的主要包:${NC}"
        pip list | grep -E "(numpy|pandas|selenium|appium|pytest)" | head -10
    else
        echo -e "${YELLOW}当前状态: 未在虚拟环境中${NC}"
        echo -e "${YELLOW}系统 Python 解释器: $(which python)${NC}"
        echo -e "${YELLOW}系统 Python 版本: $(python --version)${NC}"
    fi

    echo -e "${BLUE}=== 可用环境 ===${NC}"
    if check_venv; then
        echo -e "${GREEN}.venv 环境: 可用${NC}"
        echo -e "${YELLOW}路径: $VENV_PATH${NC}"
    else
        echo -e "${RED}.venv 环境: 不可用${NC}"
    fi

    if check_conda_env; then
        echo -e "${GREEN}Conda 环境 '$CONDA_ENV_NAME': 可用${NC}"
    else
        echo -e "${RED}Conda 环境 '$CONDA_ENV_NAME': 不可用${NC}"
    fi
}

# 显示帮助信息
show_help() {
    echo -e "${GREEN}=== 虚拟环境管理脚本 ===${NC}"
    echo "用法: ./venv.sh [选项]"
    echo ""
    echo "选项:"
    echo "  --venv     优先使用 .venv 环境"
    echo "  --conda    优先使用 Conda 环境"
    echo "  --exit     退出当前虚拟环境"
    echo "  --create   创建新的虚拟环境"
    echo "  --update   更新环境依赖"
    echo "  --info     显示环境信息"
    echo "  --auto     生成自动激活配置"
    echo "  --help     显示此帮助信息"
    echo ""
    echo "功能:"
    echo "  1. 自动检测并激活项目中的虚拟环境"
    echo "  2. 支持 .venv 和 Conda 环境"
    echo "  3. 提供环境创建、退出、更新功能"
    echo "  4. 显示详细的环境信息"
    echo "  5. 提供环境状态检查和错误处理"
    echo "  6. 支持自动激活虚拟环境配置"
    echo ""
}

# 自动激活OmniTest项目的虚拟环境
auto_activate_omnitest_venv() {
    # 检查当前目录是否在OmniTest项目中
    if [[ "$PWD" == *"OmniTest"* ]]; then
        # 找到项目根目录
        local project_root="$PWD"
        while [[ "$project_root" != "/" && ! -f "$project_root/venv.sh" ]]; do
            project_root="$(dirname "$project_root")"
        done
        
        # 如果找到项目根目录
        if [[ -f "$project_root/venv.sh" ]]; then
            # 检查是否已在虚拟环境中
            if [[ -z "$VIRTUAL_ENV" && -z "$CONDA_PREFIX" ]]; then
                # 检查.venv环境是否存在
                if [[ -d "$project_root/.venv" && -f "$project_root/.venv/bin/activate" ]]; then
                    echo "🔍 检测到OmniTest项目，自动激活虚拟环境..."
                    source "$project_root/.venv/bin/activate"
                    echo "✅ 虚拟环境激活成功: $(which python)"
                fi
            fi
        fi
    fi
}

# 生成自动激活配置
generate_auto_activate_config() {
    echo -e "${BLUE}=== 生成自动激活配置 ===${NC}"
    echo "正在生成自动激活配置..."
    
    # 创建自动激活配置内容
    cat << 'EOF'

# 自动激活OmniTest项目的虚拟环境
function auto_activate_omnitest_venv() {
    # 检查当前目录是否在OmniTest项目中
    if [[ "$PWD" == *"OmniTest"* ]]; then
        # 找到项目根目录
        local project_root="$PWD"
        while [[ "$project_root" != "/" && ! -f "$project_root/venv.sh" ]]; do
            project_root="$(dirname "$project_root")"
        done
        
        # 如果找到项目根目录
        if [[ -f "$project_root/venv.sh" ]]; then
            # 检查是否已在虚拟环境中
            if [[ -z "$VIRTUAL_ENV" && -z "$CONDA_PREFIX" ]]; then
                # 检查.venv环境是否存在
                if [[ -d "$project_root/.venv" && -f "$project_root/.venv/bin/activate" ]]; then
                    echo "🔍 检测到OmniTest项目，自动激活虚拟环境..."
                    source "$project_root/.venv/bin/activate"
                    echo "✅ 虚拟环境激活成功: $(which python)"
                fi
            fi
        fi
    fi
}

# 当终端启动时执行
auto_activate_omnitest_venv
EOF
    
    # 提示用户如何添加到.zshrc
    echo ""
    echo -e "${YELLOW}请将以上内容添加到您的 ~/.zshrc 文件末尾:${NC}"
    echo ""
    echo "1. 打开终端，执行以下命令:"
    echo "   echo '' >> ~/.zshrc"
    echo "   echo '# 自动激活OmniTest项目的虚拟环境' >> ~/.zshrc"
    echo "   ./venv.sh --auto >> ~/.zshrc"
    echo ""
    echo "2. 重新加载配置:"
    echo "   source ~/.zshrc"
    echo ""
    echo -e "${GREEN}配置完成后，在OmniTest项目目录中打开新终端时会自动激活虚拟环境。${NC}"
}

# 主函数
main() {
    # 处理命令行参数
    if [ $# -eq 0 ]; then
        # 无参数时，默认激活环境
        if is_in_venv; then
            echo -e "${YELLOW}警告: 您已经在虚拟环境中${NC}"
            echo -e "${YELLOW}当前 Python 解释器: $(which python)${NC}"
            return 0
        fi

        # 激活环境
        if check_venv; then
            activate_venv
        elif check_conda_env; then
            activate_conda_env
        else
            echo -e "${RED}错误: 找不到可用的虚拟环境${NC}"
            echo -e "${YELLOW}请使用 --create 选项创建环境${NC}"
            return 1
        fi
        return 0
    fi

    while [ $# -gt 0 ]; do
        case "$1" in
            --venv)
                if is_in_venv; then
                    echo -e "${YELLOW}警告: 您已经在虚拟环境中${NC}"
                    echo -e "${YELLOW}当前 Python 解释器: $(which python)${NC}"
                elif check_venv; then
                    activate_venv
                else
                    echo -e "${RED}错误: .venv 环境不存在${NC}"
                    echo -e "${YELLOW}请使用 --create 选项创建环境${NC}"
                    return 1
                fi
                ;;
            --conda)
                if is_in_venv; then
                    echo -e "${YELLOW}警告: 您已经在虚拟环境中${NC}"
                    echo -e "${YELLOW}当前 Python 解释器: $(which python)${NC}"
                elif check_conda_env; then
                    activate_conda_env
                else
                    echo -e "${RED}错误: Conda 环境不存在${NC}"
                    echo -e "${YELLOW}请使用 --create 选项创建环境${NC}"
                    return 1
                fi
                ;;
            --exit)
                exit_venv
                ;;
            --create)
                create_venv
                ;;
            --update)
                update_dependencies
                ;;
            --info)
                show_env_info
                ;;
            --auto)
                generate_auto_activate_config
                ;;
            --help)
                show_help
                ;;
            *)
                echo -e "${RED}错误: 未知选项 '$1'${NC}"
                show_help
                return 1
                ;;
        esac
        shift
    done
}

# 执行主函数
main "$@"
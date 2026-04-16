#!/bin/zsh
# 虚拟环境管理脚本 | 支持.venv/Conda | 兼容zoxide/cd | 自动激活/退出
# 用法: ./venv.sh --venv/--conda/--exit/--create/--update/--info/--auto/--help

# 颜色定义（简洁高亮）
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m" # 重置颜色

# 脚本/项目路径配置
SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_PATH="$PROJECT_ROOT/.venv"
CONDA_ENV_NAME="omnitest"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"

# 检查是否已在虚拟环境中
is_in_venv() {
    [[ -n "$VIRTUAL_ENV" || -n "$CONDA_PREFIX" ]] && return 0 || return 1
}

# 检查.venv环境是否存在
check_venv() {
    [[ -d "$VENV_PATH" && -f "$VENV_PATH/bin/activate" ]] && return 0 || return 1
}

# 检查Conda环境是否存在
check_conda_env() {
    conda env list | grep -q "^$CONDA_ENV_NAME " && return 0 || return 1
}

# 激活.venv环境
activate_venv() {
    echo -e "${GREEN}✅ 激活.venv环境${NC}"
    source "$VENV_PATH/bin/activate"
    echo -e "${BLUE}🔧 Python: $(python --version) | 路径: $(which python)${NC}"
    # 重新初始化 Starship
    if command -v starship &> /dev/null; then
        eval "$(starship init zsh)"
    fi
}

# 激活Conda环境
activate_conda_env() {
    echo -e "${GREEN}✅ 激活Conda环境: $CONDA_ENV_NAME${NC}"
    conda activate "$CONDA_ENV_NAME"
    echo -e "${BLUE}🔧 Python: $(python --version) | 路径: $(which python)${NC}"
    # 重新初始化 Starship
    if command -v starship &> /dev/null; then
        eval "$(starship init zsh)"
    fi
}

# 退出虚拟环境
exit_venv() {
    # 退出.venv
    if [[ -n "$VIRTUAL_ENV" ]]; then
        deactivate 2>/dev/null || true
        # 显式清除环境变量
        unset VIRTUAL_ENV
        echo -e "${YELLOW}🔚 退出.venv环境${NC}"
    fi
    # 退出Conda
    if [[ -n "$CONDA_PREFIX" ]]; then
        conda deactivate 2>/dev/null || true
        conda deactivate 2>/dev/null || true
        # 显式清除环境变量
        unset CONDA_PREFIX
        echo -e "${YELLOW}🔚 退出Conda环境${NC}"
    fi
    # 验证退出结果
    is_in_venv && echo -e "${RED}⚠️  环境未完全退出${NC}" || echo -e "${GREEN}✅ 已退出所有虚拟环境${NC}"
    echo -e "${BLUE}💡 提示: 脚本需用source执行才会修改当前shell: source ./venv.sh --exit${NC}"
}

# 创建虚拟环境
create_venv() {
    echo -e "${BLUE}=== 创建虚拟环境 ===${NC}"
    echo "1. .venv 环境 | 2. Conda 环境 | 3. 取消"
    read -p "请选择(1-3): " choice

    case "$choice" in
        1)
            [[ -d "$VENV_PATH" ]] && { echo -e "${YELLOW}⚠️  覆盖已存在的.venv${NC}"; rm -rf "$VENV_PATH"; }
            echo -e "${GREEN}🔨 正在创建.venv...${NC}"
            python3 -m venv "$VENV_PATH" && source "$VENV_PATH/bin/activate"
            # 安装依赖
            if [[ -f "$REQUIREMENTS_FILE" ]]; then
                echo -e "${GREEN}📦 安装依赖...${NC}"
                pip3 install -r "$REQUIREMENTS_FILE" -i https://pypi.tuna.tsinghua.edu.cn/simple
                echo -e "${GREEN}✅ 依赖安装完成${NC}"
            else
                echo -e "${YELLOW}⚠️  未找到requirements.txt，跳过依赖安装${NC}"
            fi
            echo -e "${GREEN}✅ .venv环境创建并激活成功${NC}"
            ;;
        2)
            check_conda_env && { echo -e "${YELLOW}⚠️  覆盖已存在的Conda环境${NC}"; conda env remove -n "$CONDA_ENV_NAME" -y; }
            echo -e "${GREEN}🔨 正在创建Conda环境...${NC}"
            conda create -n "$CONDA_ENV_NAME" python=3.12 -y && conda activate "$CONDA_ENV_NAME"
            # 安装依赖
            if [[ -f "$REQUIREMENTS_FILE" ]]; then
                echo -e "${GREEN}📦 安装依赖...${NC}"
                pip3 install -r "$REQUIREMENTS_FILE" -i https://pypi.tuna.tsinghua.edu.cn/simple
                echo -e "${GREEN}✅ 依赖安装完成${NC}"
            else
                echo -e "${YELLOW}⚠️  未找到requirements.txt，跳过依赖安装${NC}"
            fi
            echo -e "${GREEN}✅ Conda环境创建并激活成功${NC}"
            ;;
        3) echo -e "${YELLOW}🔚 取消创建环境${NC}" ;;
        *) echo -e "${RED}❌ 无效选项${NC}" ;;
    esac
}

# 更新依赖
update_dependencies() {
    if ! is_in_venv; then
        echo -e "${RED}❌ 请先激活虚拟环境${NC}"
        return 1
    fi
    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        echo -e "${GREEN}📦 更新依赖...${NC}"
        pip3 install --upgrade -r "$REQUIREMENTS_FILE" -i https://pypi.tuna.tsinghua.edu.cn/simple
        echo -e "${GREEN}✅ 依赖更新完成${NC}"
    else
        echo -e "${RED}❌ 未找到requirements.txt${NC}"
        return 1
    fi
}

# 显示环境信息
show_env_info() {
    echo -e "${BLUE}=== 环境信息 ===${NC}"
    if is_in_venv; then
        echo -e "${GREEN}✅ 当前状态: 已激活虚拟环境${NC}"
        echo -e "${BLUE}🔧 Python: $(python --version) | 路径: $(which python)${NC}"
        if [[ -n "$VIRTUAL_ENV" ]]; then
            echo -e "${BLUE}📁 环境类型: .venv | 路径: $VIRTUAL_ENV${NC}"
        else
            echo -e "${BLUE}📁 环境类型: Conda | 名称: $(basename "$CONDA_PREFIX")${NC}"
        fi
        echo -e "${BLUE}=== 已安装核心包 ===${NC}"
        pip list | grep -E "(numpy|pandas|selenium|appium|pytest)" | head -10 || echo "无核心包"
    else
        echo -e "${YELLOW}⚠️  当前状态: 未激活虚拟环境${NC}"
        echo -e "${BLUE}🔧 系统Python: $(python --version) | 路径: $(which python)${NC}"
    fi
    # 可用环境检测
    echo -e "${BLUE}=== 可用环境 ===${NC}"
    check_venv && echo -e "${GREEN}✅ .venv: 可用 (路径: $VENV_PATH)${NC}" || echo -e "${RED}❌ .venv: 不可用${NC}"
    check_conda_env && echo -e "${GREEN}✅ Conda-$CONDA_ENV_NAME: 可用${NC}" || echo -e "${RED}❌ Conda-$CONDA_ENV_NAME: 不可用${NC}"
}

# 显示帮助信息
show_help() {
    echo -e "${GREEN}=== 虚拟环境管理脚本 ===${NC}"
    echo "用法: ./venv.sh [选项]"
    echo -e "${BLUE}选项:${NC}"
    echo "  --venv     激活.venv环境 | --conda    激活Conda环境"
    echo "  --exit     退出虚拟环境  | --create   创建新环境"
    echo "  --update   更新依赖      | --info     查看环境信息"
    echo "  --auto     生成自动配置  | --help     显示帮助"
}

auto_activate_omnitest_venv() {
    # 检查是否真的改变了目录
    if [[ "$OLDPWD" != "$PWD" ]]; then
        if [[ "$PWD" == *"OmniTest"* ]]; then
            local project_root="$PWD"
            while [[ "$project_root" != "/" && ! -f "$project_root/venv.sh" ]]; do
                project_root="$(dirname "$project_root")"
            done
            # 找到脚本且未激活环境时，自动激活.venv
            if [[ -f "$project_root/venv.sh" && -z "$VIRTUAL_ENV" && -z "$CONDA_PREFIX" ]]; then
                if [[ -d "$project_root/.venv" && -f "$project_root/.venv/bin/activate" ]]; then
                    source "$project_root/.venv/bin/activate"
                    echo -e "${GREEN}✅ 自动激活OmniTest虚拟环境${NC}"
                    # 重新初始化 Starship
                    if command -v starship &> /dev/null; then
                        eval "$(starship init zsh)"
                    fi
                fi
            fi
        fi
    fi
}

auto_deactivate_omnitest_venv() {
    # 检查是否真的改变了目录
    if [[ "$OLDPWD" != "$PWD" ]]; then
        # 离开项目目录且已激活.venv时，自动退出
        if [[ "$PWD" != *"OmniTest"* && -n "$VIRTUAL_ENV" ]]; then
            deactivate
            echo -e "${YELLOW}🔚 自动退出OmniTest虚拟环境${NC}"
            # 重新初始化 Starship
            if command -v starship &> /dev/null; then
                eval "$(starship init zsh)"
            fi
        fi
    fi
}

# 注册zsh钩子，兼容cd/zoxide所有跳转方式
autoload -U add-zsh-hook
add-zsh-hook chpwd auto_activate_omnitest_venv
add-zsh-hook chpwd auto_deactivate_omnitest_venv

# 终端启动/新建Tab时，强制执行一次自动检测
auto_activate_omnitest_venv
auto_deactivate_omnitest_venv
# ==============================================================================

# 生成自动激活配置
generate_auto_activate_config() {
    echo -e "${BLUE}=== 生成自动激活配置 ===${NC}"
    cat << 'EOF'
# OmniTest虚拟环境-自动激活/退出（兼容cd/zoxide）
auto_activate_omnitest_venv() {
    # 检查是否真的改变了目录
    if [[ "$OLDPWD" != "$PWD" ]]; then
        if [[ "$PWD" == *"OmniTest"* ]]; then
            local project_root="$PWD"
            while [[ "$project_root" != "/" && ! -f "$project_root/venv.sh" ]]; do
                project_root="$(dirname "$project_root")"
            done
            # 找到脚本且未激活环境时，自动激活.venv
            if [[ -f "$project_root/venv.sh" && -z "$VIRTUAL_ENV" && -z "$CONDA_PREFIX" ]]; then
                if [[ -d "$project_root/.venv" && -f "$project_root/.venv/bin/activate" ]]; then
                    source "$project_root/.venv/bin/activate"
                    echo -e "${GREEN}✅ 自动激活OmniTest虚拟环境${NC}"
                    # 重新初始化 Starship
                    if command -v starship &> /dev/null; then
                        eval "$(starship init zsh)"
                    fi
                fi
            fi
        fi
    fi
}

auto_deactivate_omnitest_venv() {
    # 检查是否真的改变了目录
    if [[ "$OLDPWD" != "$PWD" ]]; then
        # 离开项目目录且已激活.venv时，自动退出
        if [[ "$PWD" != *"OmniTest"* && -n "$VIRTUAL_ENV" ]]; then
            deactivate
            echo -e "${YELLOW}🔚 自动退出OmniTest虚拟环境${NC}"
            # 重新初始化 Starship
            if command -v starship &> /dev/null; then
                eval "$(starship init zsh)"
            fi
        fi
    fi
}
autoload -U add-zsh-hook
add-zsh-hook chpwd auto_activate_omnitest_venv
add-zsh-hook chpwd auto_deactivate_omnitest_venv
auto_activate_omnitest_venv
auto_deactivate_omnitest_venv
EOF
    echo -e "${YELLOW}💡 执行以下命令添加到.zshrc并生效:${NC}"
    echo "echo '' >> ~/.zshrc && echo '# OmniTest自动激活虚拟环境' >> ~/.zshrc && ./venv.sh --auto >> ~/.zshrc && source ~/.zshrc"
}

# 主函数
main() {
    # 无参数时，默认激活环境
    if [[ $# -eq 0 ]]; then
        if is_in_venv; then
            echo -e "${YELLOW}⚠️  已在虚拟环境中 | Python: $(which python)${NC}"
            return 0
        fi
        check_venv && activate_venv || (check_conda_env && activate_conda_env || echo -e "${RED}❌ 无可用虚拟环境，请执行--create创建${NC}")
        return 0
    fi
    # 处理命令行参数
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --venv) is_in_venv && echo -e "${YELLOW}⚠️  已激活虚拟环境${NC}" || (check_venv && activate_venv || echo -e "${RED}❌ .venv环境不存在${NC}") ;;
            --conda) is_in_venv && echo -e "${YELLOW}⚠️  已激活虚拟环境${NC}" || (check_conda_env && activate_conda_env || echo -e "${RED}❌ Conda环境不存在${NC}") ;;
            --exit) exit_venv ;;
            --create) create_venv ;;
            --update) update_dependencies ;;
            --info) show_env_info ;;
            --auto) generate_auto_activate_config ;;
            --help) show_help ;;
            *) echo -e "${RED}❌ 未知选项: $1 | 执行--help查看用法${NC}" ;;
        esac
        shift
    done
}

# 执行主函数
main "$@"
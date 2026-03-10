#!/bin/bash

# 用于激活已有的虚拟环境

# 虚拟环境路径 - 使用PyCharm的虚拟环境路径
VENV_PATH="/Users/apple/duanyang/PyProduct/.venv"

# 检查虚拟环境是否存在
if [ -d "$VENV_PATH" ] && [ -f "$VENV_PATH/bin/activate" ]; then
    echo "找到虚拟环境: $VENV_PATH"
    echo "正在激活虚拟环境..."
    echo ""
    echo "请在终端中执行以下命令:"
    echo "source $VENV_PATH/bin/activate"
    echo ""
    echo "激活后,可以通过以下命令验证:"
    echo "which python"
    echo "python --version"
else
    echo "错误: 找不到虚拟环境或激活脚本"
    echo "请检查路径: $VENV_PATH"
    echo ""
    echo "如果虚拟环境不存在,请执行以下命令创建:"
    echo "python3 -m venv .venv"
    echo "source .venv/bin/activate"
    echo "pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"
fi
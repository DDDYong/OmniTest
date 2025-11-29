"""
-------------------------------------------------
File:           main.py
Author:         duanyang
Date:           2025/11/27
-------------------------------------------------
Description:
OmniTest自动化测试框架的命令行入口点,仅作为命令行工具入口
-------------------------------------------------
"""

# 导入omni_test模块的所有公共内容以保持向后兼容性

# 从run.py导入main函数以支持命令行调用
from run import main as run_main


if __name__ == "__main__":
    # 当直接运行main.py时,调用run.py中的main函数
    run_main()

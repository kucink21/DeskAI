# main.py

import ctypes

# 导入我们自己的模块
# 必须先导入utils并调用setup_logging，这样其他模块才能使用log
from core.utils import setup_logging, log
from core.controller import MainController

# 在程序启动时立即配置日志系统
setup_logging()

def main():
    """程序主入口函数"""
    # DPI感知设置
    try:
        ctypes.windll.shcore.SetProcessDpiAwarenessContext(-2)
        log("DPI感知级别已设置为 Per Monitor Aware。")
    except AttributeError:
        # 在一些旧系统上可能没有shcore.dll，回退到旧API
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            log("DPI感知级别已设置为 System Aware (旧版API)。")
        except Exception as e:
            log(f"无法设置DPI感知级别: {e}")

    # 安全地启动主程序
    controller = MainController()
    controller.run()

if __name__ == "__main__":
    main()
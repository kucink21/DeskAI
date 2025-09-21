# main.py

import ctypes
from tkinterdnd2 import TkinterDnD
import customtkinter as ctk 
from core.controller import MainController
from core.utils import setup_logging, log, get_screen_scaling_factor

setup_logging()

def main():
    """程序主入口函数"""
    log("应用程序启动...")
    
    # 2. 严格地在创建任何窗口之前，设置DPI感知
    # 这是解决截图区域和字体缩放问题的关键
    try:
        ctypes.windll.shcore.SetProcessDpiAwarenessContext(-2)
        log("DPI感知级别已设置为 Per Monitor Aware。")
    except (AttributeError, OSError):
        # 捕获AttributeError（在非Windows上）和OSError（在某些Windows版本上）
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            log("DPI感知级别已设置为 System Aware (旧版API)。")
        except Exception as e:
            log(f"无法设置DPI感知级别: {e}")

    # 3. 现在可以安全地创建TkinterDnD窗口了
    # 此时Tkinter会获取到正确的、缩放后的屏幕尺寸
    root = TkinterDnD.Tk()
    root.withdraw()

    # 4. 手动设置 customtkinter 的缩放作为双重保险
    # 即使自动检测失败，这也能保证UI大小正确
    log("正在设置UI缩放...")
    scaling_factor = get_screen_scaling_factor()
    ctk.set_widget_scaling(scaling_factor)
    log(f"UI缩放比例已手动设置为: {scaling_factor}")
    
    # 5. 启动主控制器
    controller = MainController(root)
    controller.run()

if __name__ == "__main__":
    main()
# features/tray_icon.py

import pystray
from PIL import Image
import threading
import os
import sys

# 从上级目录的core模块导入log
from core.utils import log

class TrayIcon:
    def __init__(self, on_show_callback, on_exit_callback):
        """
        初始化系统托盘图标
        :param on_show_callback: 点击“显示”时调用的函数
        :param on_exit_callback: 点击“退出”时调用的函数
        """
        self.on_show_callback = on_show_callback
        self.on_exit_callback = on_exit_callback
        self.icon = None
        self.thread = None

        # 确定图标路径
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(__file__))
        self.icon_path = os.path.join(base_path, 'icon', 'ball.ico')

    def _create_menu(self):
        """创建托盘菜单"""
        return pystray.Menu(
            pystray.MenuItem('显示悬浮球', self.on_show_callback, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('退出', self.on_exit_callback)
        )

    def run(self):
        """在独立线程中运行托盘图标"""
        if not os.path.exists(self.icon_path):
            log(f"错误：找不到托盘图标文件 at {self.icon_path}")
            return
            
        image = Image.open(self.icon_path)
        menu = self._create_menu()
        self.icon = pystray.Icon("gemini_helper", image, "Gemini助手", menu)
        
        log("系统托盘图标已启动。")
        self.icon.run()

    def start(self):
        """启动托盘图标线程"""
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        """停止托盘图标"""
        if self.icon:
            log("正在停止系统托盘图标...")
            self.icon.stop()
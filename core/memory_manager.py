# core/memory_manager.py

import os
import sys
from .utils import log

class MemoryManager:
    """负责管理和持久化用户记忆的类"""
    def __init__(self, filename="memory.txt"):
        if getattr(sys, 'frozen', False):
            self.app_dir = os.path.dirname(sys.executable)
        else:
            # __file__ -> memory_manager.py, dirname -> core, dirname -> project root
            self.app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.filepath = os.path.join(self.app_dir, filename)

    def load_memory(self) -> str:
        """
        从文件中加载记忆内容。
        如果文件不存在，返回空字符串。
        """
        if not os.path.exists(self.filepath):
            log("记忆文件不存在，将使用空记忆。")
            return ""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                log("成功加载记忆文件。")
                return content
        except Exception as e:
            log(f"错误：加载记忆文件失败: {e}")
            return "" # 出错时也返回空字符串，保证程序健壮性

    def save_memory(self, content: str) -> bool:
        """
        将记忆内容写入文件。
        成功返回 True，失败返回 False。
        """
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            log("记忆文件已成功保存。")
            return True
        except Exception as e:
            log(f"错误：保存记忆文件失败: {e}")
            return False
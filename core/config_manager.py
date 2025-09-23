# core/config_manager.py

import os
import sys
import json
from .utils import log 

class ConfigManager:
    """负责加载和保存JSON配置文件"""
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.app_dir = os.path.dirname(sys.executable)
        else:
            self.app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def get_filepath(self, filename: str) -> str:
        """获取配置文件的完整路径"""
        return os.path.join(self.app_dir, filename)

    def load_json(self, filename: str) -> dict:
        """从指定的JSON文件中加载数据"""
        filepath = self.get_filepath(filename)
        if not os.path.exists(filepath):
            log(f"配置文件 '{filename}' 不存在。")
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"加载 '{filename}' 失败: {e}")
            return {}

    def save_json(self, filename: str, data: dict) -> bool:
        """将数据保存到指定的JSON文件"""
        filepath = self.get_filepath(filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            log(f"配置已成功写入到 '{filepath}'")
            return True
        except Exception as e:
            log(f"错误：无法写入配置文件 '{filename}': {e}")
            return False
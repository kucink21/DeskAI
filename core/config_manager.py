# core/config_manager.py

import os
import sys
import json
from .utils import log # 从同级目录的utils模块导入log

class ConfigManager:
    def __init__(self, filename="config.json"):
        if getattr(sys, 'frozen', False):
            self.app_dir = os.path.dirname(sys.executable)
        else:
            self.app_dir = os.path.dirname(os.path.dirname(__file__)) # 同样，回到上级目录
        self.filepath = os.path.join(self.app_dir, filename)

    def load_config(self):
        if not os.path.exists(self.filepath):
            return None
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"fail to load config: {e}")
            return None
# core/ai_provider.py

from abc import ABC, abstractmethod
from PIL import Image
from typing import List, Optional

class BaseAIProvider(ABC):
    """
    所有AI服务提供者的抽象基类。
    它定义了一个所有模型实现都必须遵守的统一接口。
    """
    def __init__(self, model_name: str, api_key: str):
        """
        :param model_name: 此提供者实例将要使用的具体模型名称
        :param api_key: 用于此提供者的API密钥。
        """
        self.model_name = model_name
        self.api_key = api_key
        self.model = None

    @property
    def friendly_name(self) -> str:
        """返回一个用于UI显示的、友好的模型名称。"""
        return self.model_name
    
    @abstractmethod
    def initialize_model(self, proxy_url: Optional[str] = None):
        """
        初始化或配置模型。这个方法应该在程序启动时被调用。
        如果初始化失败，应该抛出异常。
        :param proxy_url: 可选的代理URL。
        """
        pass

    @abstractmethod
    def generate_content(self, prompt: str, task_data, timeout: int = 60) -> str:
        """
        生成内容的核心方法。
        :param prompt: 结合了记忆和任务的最终提示词。
        :param task_data: 任务相关的数据（例如，图片路径、文本内容、(文本, [图片])元组）。
        :param timeout: 请求的超时时间。
        :return: AI生成的文本字符串。
        """
        pass

    @abstractmethod
    def start_chat_session(self, history):
        """
        为后续的追问创建一个聊天会话。
        :param history: 初始的对话历史。
        :return: 一个聊天会话对象。
        """
        pass
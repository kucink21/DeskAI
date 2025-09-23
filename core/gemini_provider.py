# core/gemini_provider.py

import google.generativeai as genai
from PIL import Image
from typing import List, Optional

from .ai_provider import BaseAIProvider
from .utils import log

class GeminiProvider(BaseAIProvider):
    """Gemini AI模型的具体实现"""

    def initialize_model(self, proxy_url: Optional[str] = None):
        """配置并初始化Gemini模型"""
        log(f"正在初始化Gemini Provider，模型: {self.model_name}")
        try:
            # Gemini的配置是全局的，但我们在这里执行
            genai.configure(api_key=self.api_key, transport='rest')
            self.model = genai.GenerativeModel(self.model_name)
            # 简单地测试一下模型是否可用
            self.model.count_tokens("test") 
            log("Gemini Provider 初始化成功。")
        except Exception as e:
            log(f"Gemini Provider 初始化失败: {e}")
            # 抛出异常，让上层捕获并处理
            raise ConnectionError(f"无法初始化Gemini模型 '{self.model_name}': {e}")

    def generate_content(self, prompt: str, task_data, timeout: int = 60) -> str:
        """使用Gemini生成内容"""
        content_parts = self._build_content_parts(prompt, task_data)
        
        log(f"向Gemini发送请求，包含 {len(content_parts)} 个部分...")
        response = self.model.generate_content(
            content_parts,
            request_options={"timeout": timeout}
        )
        return response.text.strip()

    def start_chat_session(self, history):
        """为Gemini启动一个聊天会话"""
        return self.model.start_chat(history=history)

    def _build_content_parts(self, prompt: str, task_data) -> list:
        """
        一个辅助方法，根据task_data构建发送给Gemini的content列表。
        这部分逻辑是从 ResultWindow 迁移过来的。
        """
        content_parts = [prompt]
        task_type, data = task_data

        if task_type == 'pdf_multimodal':
            pdf_text, pdf_images = data
            if pdf_text: content_parts.append(pdf_text)
            if pdf_images: content_parts.extend(pdf_images)
        
        elif task_type in ['image', 'image_from_path']:
            image_path = data
            try:
                loaded_image = Image.open(image_path)
                content_parts.append(loaded_image)
            except Exception as e:
                log(f"无法加载图片: {image_path}, {e}")
                # 抛出异常让上层处理
                raise ValueError(f"无法加载图片: {image_path}")

        elif task_type == 'text':
            text_data = data
            if text_data: content_parts.append(text_data)
            
        return content_parts
# core/openai_provider.py

from openai import OpenAI
from PIL import Image
import base64
import io
from typing import List, Optional

from .ai_provider import BaseAIProvider
from .utils import log

class OpenAIProvider(BaseAIProvider):
    """OpenAI (ChatGPT) 模型的具体实现"""

    def initialize_model(self, proxy_url: Optional[str] = None):
        """初始化OpenAI客户端"""
        log(f"正在初始化OpenAI Provider，模型: {self.model_name}")
        try:
            # OpenAI的Python库会自动从环境变量中读取代理
            self.client = OpenAI(api_key=self.api_key)
            # 测试一下API Key是否有效
            self.client.models.list()
            log("OpenAI Provider 初始化成功。")
        except Exception as e:
            log(f"OpenAI Provider 初始化失败: {e}")
            raise ConnectionError(f"无法初始化OpenAI模型 '{self.model_name}': {e}")

    def generate_content(self, prompt: str, task_data, timeout: int = 60) -> str:
        """使用OpenAI生成内容"""
        messages = self._build_messages(prompt, task_data)
        
        log(f"向OpenAI发送请求，模型: {self.model_name}...")
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=2048,
            timeout=timeout
        )
        return response.choices[0].message.content.strip()

    def start_chat_session(self, history):
        """
        OpenAI的chat API是无状态的，所以我们模拟一个会话。
        我们将返回一个包含历史记录的 "session" 对象。
        """
        # 简单地返回一个包含历史的字典作为session
        return {"history": history}

    def _build_messages(self, prompt: str, task_data) -> list:
        """构建发送给OpenAI的'messages'列表"""
        task_type, data = task_data
        
        user_content = []

        if "---" in prompt:
            parts = prompt.split("---", 1)
            system_context = parts[0].strip()
            user_request = parts[1].strip()
            # 更好的方式是直接将整个prompt作为第一个user message
            user_content.append({"type": "text", "text": prompt})
        else:
            user_content.append({"type": "text", "text": prompt})

        # 2. 添加图片部分 (如果任务是多模态的)
        images = []
        if task_type == 'pdf_multimodal':
            _, pdf_images = data
            images.extend(pdf_images)
        elif task_type in ['image', 'image_from_path']:
            try:
                images.append(Image.open(data))
            except Exception as e:
                raise ValueError(f"无法加载图片: {data}")
        
        # 将Pillow图片转换为Base64编码的字符串
        for img in images:
            buffered = io.BytesIO()
            # 确保图片是RGB模式，避免PNG的透明通道问题
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_str}"
                }
            })
            
        return [{"role": "user", "content": user_content}]
# core/deepseek_provider.py

from openai import OpenAI
from PIL import Image
import base64
import io
from typing import Optional

from .ai_provider import BaseAIProvider
from .utils import log

# DeepSeek 的 API 端点
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

class DeepSeekProvider(BaseAIProvider):
    """DeepSeek 模型的具体实现。
    由于其API与OpenAI兼容，此类大量复用了 OpenAIProvider 的逻辑。
    """

    def initialize_model(self, proxy_url: Optional[str] = None):
        """初始化指向DeepSeek端点的OpenAI客户端"""
        log(f"正在初始化DeepSeek Provider，模型: {self.model_name}")
        try:
            # OpenAI的Python库会自动从环境变量中读取代理
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=DEEPSEEK_BASE_URL
            )
            # 通过列出模型来测试API Key和连接
            self.client.models.list()
            log("DeepSeek Provider 初始化成功。")
        except Exception as e:
            log(f"DeepSeek Provider 初始化失败: {e}")
            raise ConnectionError(f"无法初始化DeepSeek模型 '{self.model_name}': {e}")

    def generate_content(self, prompt: str, task_data, timeout: int = 60) -> str:
        """使用DeepSeek生成内容"""
        # 复用OpenAI的messages构建逻辑
        messages = self._build_messages(prompt, task_data)
        
        log(f"向DeepSeek发送请求，模型: {self.model_name}...")
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=2048,
            timeout=timeout
        )
        return response.choices[0].message.content.strip()

    def start_chat_session(self, history):
        """与OpenAI一样，模拟一个无状态的会话"""
        return {"history": history}

    def _build_messages(self, prompt: str, task_data) -> list:
        """
        构建发送给DeepSeek的'messages'列表。
        此方法直接从 OpenAIProvider 复制而来，因为API格式兼容。
        注意：需要测试DeepSeek对Base64图片的支持情况。
        """
        task_type, data = task_data
        
        user_content = [{"type": "text", "text": prompt}]

        images = []
        if task_type == 'pdf_multimodal':
            _, pdf_images = data
            images.extend(pdf_images)
        elif task_type in ['image', 'image_from_path']:
            try:
                images.append(Image.open(data))
            except Exception as e:
                raise ValueError(f"无法加载图片: {data}")
        
        if images:
            log("正在为DeepSeek准备图片数据...")
            for img in images:
                buffered = io.BytesIO()
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
        else:
            # 如果没有图片，content 应该是一个纯字符串
            # (根据OpenAI最新API，列表形式也兼容，但纯字符串更标准)
            # 为了简单起见，保持列表形式
            pass
            
        return [{"role": "user", "content": user_content}]
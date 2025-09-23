# core/claude_provider.py

import anthropic
from PIL import Image
from typing import Optional, Tuple
import base64
import io
import httpx
from typing import Optional

from .ai_provider import BaseAIProvider
from .utils import log

class ClaudeProvider(BaseAIProvider):
    """Anthropic (Claude) 模型的具体实现"""

    def initialize_model(self, proxy_url: Optional[str] = None):
        """初始化Anthropic客户端，并配置代理"""
        log(f"正在初始化Claude Provider，模型: {self.model_name}")
        try:
            http_client = None
            if proxy_url:
                proxy = httpx.Proxy(url=proxy_url)
                transport = httpx.HTTPTransport(proxy=proxy)
                http_client = httpx.Client(transport=transport)
                log("Claude Provider已配置代理。")
            
            self.client = anthropic.Anthropic(api_key=self.api_key, http_client=http_client)
            log("Claude Provider 初始化成功。")
        except Exception as e:
            log(f"Claude Provider 初始化失败: {e}")
            raise ConnectionError(f"无法初始化Claude模型 '{self.model_name}': {e}")

    def generate_content(self, prompt: str, task_data, timeout: int = 60) -> str:
        """使用Claude生成内容"""
        messages, system_prompt = self._build_messages(prompt, task_data)
        
        log(f"向Claude发送请求，模型: {self.model_name}...")
        response = self.client.messages.create(
            model=self.model_name,
            system=system_prompt, # Claude 推荐将系统/背景信息放在独立的system参数中
            messages=messages,
            max_tokens=2048,
            timeout=timeout
        )
        return response.content[0].text.strip()

    def start_chat_session(self, history):
        """Claude API也是无状态的，我们同样模拟一个会话"""
        return {"history": history}

    def _build_messages(self, prompt: str, task_data) -> Tuple[list, str]:
        """构建发送给Claude的'messages'列表和'system'提示"""
        task_type, data = task_data
        
        # Claude 对 system prompt 有很好的支持
        system_prompt = ""
        user_request = prompt

        # 尝试从总prompt中分离背景信息
        if "<USER_BACKGROUND>" in prompt:
            try:
                system_prompt = prompt.split("<USER_BACKGROUND>")[1].split("</USER_BACKGROUND>")[0].strip()
                user_request = prompt.split("---")[-1].strip()
            except IndexError:
                # 解析失败，则将整个prompt作为用户请求
                system_prompt = "You are a helpful assistant."
                user_request = prompt

        user_content = [{"type": "text", "text": user_request}]

        # 添加图片部分
        images = []
        if task_type == 'pdf_multimodal':
            _, pdf_images = data
            images.extend(pdf_images)
        elif task_type in ['image', 'image_from_path']:
            try:
                images.append(Image.open(data))
            except Exception as e:
                raise ValueError(f"无法加载图片: {data}")
        
        # 将Pillow图片转换为Claude接受的格式 (Base64)
        for img in images:
            buffered = io.BytesIO()
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            user_content.insert(0, { # 图片通常放在文本前面
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_str,
                }
            })
            
        return ([{"role": "user", "content": user_content}], system_prompt)
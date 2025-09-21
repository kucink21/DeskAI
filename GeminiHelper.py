# GeminiHelper

import tkinter as tk
from tkinter import scrolledtext, messagebox
from PIL import Image, ImageGrab
import google.generativeai as genai
import os
import sys
import threading
import ctypes
from pynput import keyboard
import json 
import urllib.request
import logging
import customtkinter as ctk

class ConfigManager:
    def __init__(self, filename="config.json"):
        if getattr(sys, 'frozen', False): self.app_dir = os.path.dirname(sys.executable)
        else: self.app_dir = os.path.dirname(__file__)
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
        
def setup_logging():
    """配置日志系统，使其同时输出到控制台和文件"""
    
    # 确定日志文件的路径
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(__file__)
    log_filepath = os.path.join(app_dir, "log.txt")

    # 获取根 logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # 设置日志记录的最低级别

    # 清除任何可能已经存在的处理器，防止日志重复
    if logger.hasHandlers():
        logger.handlers.clear()

    # 创建格式化器
    formatter = logging.Formatter('[%(asctime)s][Thread:%(thread)d] %(message)s', datefmt='%H:%M:%S')

    # 创建并配置 StreamHandler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 5. 创建并配置 FileHandler 
    try:
        file_handler = logging.FileHandler(log_filepath, mode='w', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"无法创建日志文件: {e}")

setup_logging()

# 全局的 log 函数
def log(message):
    """全局日志函数，使用 logging.info"""
    logging.info(message)

def set_proxy(config_proxy_url):
    """
    智能设置代理。
    优先级：用户在 config.json 中明确指定的代理 > 系统代理 > 无代理
    返回最终确定的代理URL，如果没有则返回 None。
    """
    final_proxy = None
    
    # 检查用户是否在 config.json 中强制指定了代理
    if config_proxy_url:
        log(f"用户在 config.json 中指定了代理: {config_proxy_url}")
        final_proxy = config_proxy_url
    else:
        # 如果用户未指定，则尝试自动检测系统代理
        log("尝试自动检测系统代理...")
        try:
            # 使用 urllib.request.getproxies() 这个 Python 内置的功能来获取系统代理
            system_proxies = urllib.request.getproxies()
            # 优先获取 https 代理，其次是 http
            http_proxy = system_proxies.get('https') or system_proxies.get('http')
            
            if http_proxy:
                log(f"成功检测到系统代理: {http_proxy}")
                final_proxy = http_proxy
            else:
                log("未检测到系统代理。")
        except Exception as e:
            log(f"自动检测系统代理时发生错误: {e}")

    # 3. 如果找到了代理，则设置环境变量
    if final_proxy:
        if not final_proxy.startswith(('http://', 'https://')):
            final_proxy = 'http://' + final_proxy

        os.environ['HTTP_PROXY'] = final_proxy
        os.environ['HTTPS_PROXY'] = final_proxy
        log(f"最终生效的代理已设置为: {final_proxy}")
    else:
        log("最终未设置代理，将进行直接连接。")

    return final_proxy 

def configure_gemini(api_key, model_name, proxy_url=None): # proxy_url 参数保留，但函数体内不用
    try:
        # 强制使用 'rest' 传输协议。
        # 这会使库使用标准的 HTTPS 请求，从而自动遵循 os.environ 中设置的代理。
        # 不再需要手动传递 proxies 参数。
        genai.configure(
            api_key=api_key,
            transport='rest'
        )
        
        model = genai.GenerativeModel(model_name) 
        log(f"Gemini model '{model_name}' set successfully using REST transport")
        return model
    except Exception as e:
        log(f"Gemini model failed: {e}")
        return None

def get_screen_scaling_factor():
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        hdc = ctypes.windll.user32.GetDC(0)
        physical_width = ctypes.windll.gdi32.GetDeviceCaps(hdc, 118)
        logical_width = ctypes.windll.gdi32.GetDeviceCaps(hdc, 8)
        ctypes.windll.user32.ReleaseDC(0, hdc)
        scaling_factor = physical_width / logical_width
        log(f"screen scaling factor is: {scaling_factor}")
        return scaling_factor
    except Exception:
        log("use default: 1.0, failed to get screen scaling factor")
        return 1.0

class ScreenshotTaker:
    def __init__(self, scaling_factor, on_done_callback, screenshot_path): # screenshot_path
        self.screenshot_path = screenshot_path 
        self.scaling_factor = scaling_factor
        self.on_done_callback = on_done_callback
        
        log("[LOG-S2] 准备创建 Toplevel 截图窗口...")
        self.root = tk.Toplevel()
        log("[LOG-S3] 截图窗口已创建。")

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        log(f"获取到屏幕尺寸: {screen_width}x{screen_height}")
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        
        log("强制更新窗口几何状态...")
        self.root.update_idletasks()
        
        self.root.overrideredirect(True)
        self.root.update_idletasks()

        self.root.attributes("-alpha", 0.70) 

        self.canvas = tk.Canvas(self.root, bg='black', cursor="cross", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.start_x = self.start_y = 0
        self.selection_rect = None
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.root.bind("<Escape>", self.exit_and_cleanup)

        self.root.lift()
        self.root.attributes('-topmost', True)

        log("[LOG-S9] 事件绑定完成，ScreenshotTaker 初始化结束。")

    def on_button_press(self, event):
        log("[LOG-S10] 鼠标按下。")
        self.start_x, self.start_y = event.x, event.y
        if not self.selection_rect:
            self.selection_rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, 
                self.start_x, self.start_y,
                fill="#4AAEE8",  
                outline=''     
            )

    def on_mouse_drag(self, event):
        if self.selection_rect:
            self.canvas.coords(self.selection_rect, self.start_x, self.start_y, event.x, event.y)

    def on_button_release(self, event):
        if self.selection_rect:
            self.canvas.itemconfig(self.selection_rect, state='hidden')
            self.canvas.update_idletasks()
        log("[LOG-S11] 鼠标释放。")
        x1, y1, x2, y2 = min(self.start_x, event.x), min(self.start_y, event.y), max(self.start_x, event.x), max(self.start_y, event.y)
        log("[LOG-S12] 准备隐藏截图窗口。")
        self.root.withdraw()
        self.root.after(200, self._perform_screenshot_and_cleanup, x1, y1, x2, y2)

    def _perform_screenshot_and_cleanup(self, x1, y1, x2, y2):
        log("[LOG-S13] 延迟任务执行，准备截图。")
        self._grab_and_save(x1, y1, x2, y2)
        log("[LOG-S14] 截图流程结束，准备销毁窗口。")
        self.root.destroy()
        log("[LOG-S15] 截图窗口已销毁。")

    def _grab_and_save(self, x1, y1, x2, y2):
        x1_phys, y1_phys = x1 * self.scaling_factor, y1 * self.scaling_factor
        x2_phys, y2_phys = x2 * self.scaling_factor, y2 * self.scaling_factor
        try:
            log(f"[LOG-S16] 调用 ImageGrab.grab，坐标: ({x1_phys}, {y1_phys}, {x2_phys}, {y2_phys})")
            screenshot = ImageGrab.grab(bbox=(x1_phys, y1_phys, x2_phys, y2_phys))
            screenshot.save(self.screenshot_path)
            log(f"截图成功，已保存为: {self.screenshot_path}")
            if self.on_done_callback:
                log("[LOG-S18] 准备调用回调函数 on_done_callback。")
                self.on_done_callback()
                log("[LOG-S19] 回调函数 on_done_callback 调用完成。")
        except Exception as e:
            log(f"!!! 截图失败: {e}")
            if self.on_done_callback:
                self.on_done_callback(cancelled=True)
    
    def exit_and_cleanup(self, event=None):
        log("截图被用户通过ESC取消。")
        self.root.destroy()
        if self.on_done_callback:
            self.on_done_callback(cancelled=True)


class ResultWindow(tk.Toplevel):
    def __init__(self, model, config_manager, prompt, task_type, task_data):
        super().__init__()
        self.model = model
        self.config_manager = config_manager
        
        # 新增: 存储传入的任务信息
        self.initial_prompt = prompt
        self.task_type = task_type
        self.task_data = task_data

        # self.screenshot_path 不再需要了，因为信息在 task_data 中
        self.chat_session = None
        self.loaded_image = None # 仅在图片任务中被赋值
        self.timeout_job = None
        self.typewriter_job = None 
        
        self.setup_ui()
        
        #  process_image_and_get_response 重命名为 process_initial_request
        threading.Thread(target=self.process_initial_request, daemon=True).start()

    def on_timeout(self):
        """当API调用超时时，由主线程的定时器调用"""
        # 检查一下，确保任务真的还在运行（防止极小概率的竞争）
        # 如果 self.timeout_job 为 None，说明任务已经正常完成了，直接返回
        if self.timeout_job is None:
            return
            
        log("API 调用超时！")
        # 直接调用我们的UI更新函数来显示错误
        error_message = (
            "请求超时。\n\n"
            "这通常由以下原因导致：\n"
            "1. 网络连接问题。\n"
            "2. 代理设置错误 (端口不匹配或代理服务器无响应)。\n"
            "3. 防火墙阻止了连接。"
        )
        self._update_ui(error=error_message)

    def setup_ui(self):
        self.title(" Gemini 识别结果 --> 你可以发送消息继续这个聊天 :) ")
        self.geometry("1200x1050")
        
        main_frame = ctk.CTkFrame(
            self,
            fg_color="#F5F5F5",   # 内部背景
            corner_radius=15,     # 圆角
            border_width=2,
            border_color="#B0B3B9"  # 边框颜色（浅灰）
        )
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        input_frame = tk.Frame(main_frame)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        self.entry = ctk.CTkEntry(
            input_frame,
            placeholder_text=" >> 发送消息以继续临时聊天 << ",
            font=("微软雅黑", 14),
            width=400,
            height=40,
            corner_radius=12,    # 圆角
            fg_color="#F5F5F5",  # 背景
            text_color="#333333"
        )
        self.entry.insert(0, " >> 发送消息以继续临时聊天 << ")
        self.entry.bind("<FocusIn>", lambda e: self.entry.delete(0, "end"))

        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.entry.bind("<Return>", self.send_follow_up_question)

        self.send_button = ctk.CTkButton(
            input_frame,
            text="➤ 发送",
            font=("微软雅黑", 12, "bold"),
            width=80,        # 这里改宽度，不要太小
            height=40,       # 关键：设为和输入框一致
            fg_color="#2563EB",    # 背景色
            hover_color="#0E2B88", # 悬停颜色
            text_color="white",    # 字体颜色
            corner_radius=12,      # 圆角半径
            command=self.send_follow_up_question
        )
        self.send_button.pack(pady=5)
        
        self.text_area = scrolledtext.ScrolledText(
            main_frame, 
            wrap=tk.WORD, 
            font=("微软雅黑", 12),
            bg="#F5F5F5", 
            fg="#333333",          
            insertbackground="white", 
            borderwidth=0, 
            highlightthickness=2,
            padx=40,
            pady=10
        )
        self.text_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.text_area.config(state=tk.DISABLED)
        self.text_area.tag_config(
            "user_tag", 
            foreground="#AD3430") 
        
        self.text_area.tag_config(
            "model_tag", 
            foreground="#194CBA" 
        )

        bold_font = ("微软雅黑", 12, "bold")
        self.text_area.tag_config("md_bold", font=bold_font)

        code_font = ("Consolas", 11) 
        self.text_area.tag_config(
            "md_code", 
            font=code_font, 
            background="#2D61BC", 
            foreground="#FFFFFF",
            lmargin1=20, lmargin2=20, 
            relief=tk.SOLID, borderwidth=1,
            wrap=tk.NONE 
        )
        self.text_area.tag_config(
            "md_list", 
            lmargin1=25, 
            lmargin2=25
        )
        self.disable_input()

    def process_initial_request(self):
        """通用处理函数，根据任务类型发送初始请求"""
        self.display_message("正在分析...\n")
        self.attributes('-topmost', True); self.focus_force(); self.attributes('-topmost', False)
        
        timeout_seconds = 12
        self.timeout_job = self.after(timeout_seconds * 1000, self.on_timeout)
        log(f"已设置 {timeout_seconds} 秒的API调用超时定时器。")

        def background_task():
            try:
                content_parts = [self.initial_prompt]
                
                # 根据任务类型准备请求内容
                if self.task_type == 'image':
                    image_path = self.task_data
                    if not os.path.exists(image_path):
                        raise FileNotFoundError(f"找不到截图文件: {image_path}")
                    self.loaded_image = Image.open(image_path)
                    content_parts.append(self.loaded_image)
                
                elif self.task_type == 'text':
                    clipboard_text = self.task_data
                    content_parts.append(clipboard_text)
                
                else:
                    raise ValueError(f"未知的任务类型: {self.task_type}")

                # 发送请求
                response = self.model.generate_content(
                    content_parts,
                    request_options={"timeout": timeout_seconds} 
                )
                result_text = response.text.strip()
                result_error = None

            except Exception as e:
                result_text = None
                result_error = e
            
            # 无论成功还是失败，取消超时定时器
            if self.timeout_job:
                self.after_cancel(self.timeout_job)
                self.timeout_job = None
                log("API调用已完成或失败，超时定时器已取消。")
            
            # 将结果调度回主线程更新UI
            self.after(0, lambda: self._update_ui(text=result_text, error=result_error))

        threading.Thread(target=background_task, daemon=True).start()
    
    def send_follow_up_question(self, event=None):
        question = self.entry.get().strip()
        if not question: return
        self.display_message(question, is_user=True)
        self.entry.delete(0, tk.END)
        self.disable_input()
        threading.Thread(target=self._send_and_display, args=(question,), daemon=True).start()

    def _send_and_display(self, question):
        try:
            # 网络操作
            response = self.chat_session.send_message(
                question,
                request_options={"timeout": 15}
            )            
            # 将结果调度回主线程
            self.after(0, self.display_message, response.text.strip(), False, True)
        
        except Exception as e:
            # 将错误调度回主线程
            self.after(0, self.display_message, f"\n发生错误: {e}")
        finally:
            # 将UI操作调度回主线程
            self.after(0, self.enable_input)
        
    def enable_input(self): self.entry.configure(state=tk.NORMAL); self.send_button.configure(state=tk.NORMAL)
    def disable_input(self): self.entry.configure(state=tk.DISABLED); self.send_button.configure(state=tk.DISABLED)
    def display_message(self, message, is_user=False, is_model=False):
        """
        在文本框中格式化并显示信息。
        如果是模型回复，则启动打字机效果。
        """
        # 如果有正在进行的打字机效果，先取消它
        if self.typewriter_job:
            self.after_cancel(self.typewriter_job)
            self.typewriter_job = None

        self.text_area.config(state=tk.NORMAL)
        
        if is_user:
            self.text_area.insert(tk.END, f"\n\n[用户说]: \n", "user_tag")
            self.text_area.insert(tk.END, f"{message}\n")
        elif is_model:
            self.text_area.insert(tk.END, f"\n[Gemini]: \n", "model_tag")
            if message:
                self.start_typewriter(message) #启动打字机
        else:
            self.text_area.insert(tk.END, message)
            
        self.text_area.see(tk.END)
        # 先不禁用文本框，等打字机结束后再禁用

    def start_typewriter(self, markdown_text):
        """解析Markdown，准备数据，并启动智能打字机效果"""
        import re
        
        # 1. 解析Markdown文本，生成带标签的片段列表 (segments)
        segments = []
        parts = re.split(r"(```.*?```)", markdown_text, flags=re.DOTALL)
        
        for part in parts:
            if part.startswith("```"):
                code_content = part.strip("`\n")
                segments.append(("\n" + code_content + "\n", "md_code"))
            else:
                for line in part.split('\n'):
                    list_match = re.match(r"^\s*\* (.*)", line)
                    if list_match:
                        content = list_match.group(1)
                        segments.append((f"• {content}\n", "md_list"))
                    else:
                        segments.append((line + "\n", None))

        # 2. 启动打字机效果
        self._typewriter_step(segments)

    def _typewriter_step(self, segments, segment_index=0, char_index=0):
        """智能打字机的核心函数，一次处理一“块”字符"""
        
        # --- 检查是否完成 ---
        if segment_index >= len(segments):
            # 所有片段都已显示完毕
            self.typewriter_job = None
            self.apply_bold_tags()
            self.text_area.config(state=tk.DISABLED)
            return

        # --- 获取当前要处理的片段 ---
        text, tag = segments[segment_index]
        
        # --- 核心优化：分块显示 ---
        chunk_size = 3 # 一次显示3个字符
        
        # 如果是代码块，一次性显示整块，因为它不需要打字机效果
        if tag == "md_code":
            chunk_size = len(text)
            
        end_of_chunk = min(char_index + chunk_size, len(text))
        chunk = text[char_index:end_of_chunk]

        # --- 插入带标签的块 ---
        if chunk:
            if tag:
                self.text_area.insert(tk.END, chunk, tag)
            else:
                self.text_area.insert(tk.END, chunk)
            self.text_area.see(tk.END)

        # --- 计算下一步 ---
        next_char_index = end_of_chunk
        next_segment_index = segment_index

        if next_char_index >= len(text):
            # 当前片段已显示完，移动到下一个片段
            next_segment_index += 1
            next_char_index = 0
            
        # --- 核心优化：动态延迟 ---
        delay = 2 # 基础延迟
        
        # 如果文本很长，加快后续速度
        total_len = sum(len(s[0]) for s in segments)
        if total_len > 300:
            # 已经显示了超过1/3后，速度翻倍（延迟减半）
            current_len = sum(len(s[0]) for s in segments[:segment_index]) + char_index
            if current_len > total_len / 3:
                delay = 1

        # --- 安排下一步 ---
        self.typewriter_job = self.after(
            delay, 
            self._typewriter_step, 
            segments, 
            next_segment_index, 
            next_char_index
        )

    def apply_bold_tags(self):
        """在文本完全显示后，查找并应用加粗标签"""
        import re
        content = self.text_area.get("1.0", tk.END)
        
        # 清理 ** 标记并应用加粗
        offset = 0
        for match in re.finditer(r"\*\*(.*?)\*\*", content):
            clean_text = match.group(1)
            
            start_index = self.text_area.index(f"1.0+{match.start() - offset}c")
            end_index = self.text_area.index(f"1.0+{match.end() - offset}c")
            
            self.text_area.delete(start_index, end_index)
            self.text_area.insert(start_index, clean_text, "md_bold")
            
            offset += 4 # 2个*号被删除，总共4个字符

    def _update_ui(self, text=None, error=None):
        """
        这个方法总是在主线程中被调用，用于安全地更新UI。
        """
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete('1.0', tk.END)
        self.text_area.config(state=tk.DISABLED)
        
        if error:
            log("update ui发生错误")
            # 如果有错误，显示错误信息
            error_message = f"发生错误: {error}"
            self.display_message(error_message)
            # 也可以在这里弹窗，效果更强烈
            messagebox.showerror("API 调用失败", error_message)
            # 失败后依然启用输入框，让用户可以复制错误或关闭窗口
            self.enable_input()
        
        elif text:
            # 如果成功，显示结果并初始化聊天
            self.display_message(text, is_model=True)
            
            # 动态构建聊天历史
            history_user_parts = [self.initial_prompt]
            if self.task_type == 'image' and self.loaded_image:
                history_user_parts.append(self.loaded_image)
            elif self.task_type == 'text':
                history_user_parts.append(self.task_data)

            self.chat_session = self.model.start_chat(history=[
                {'role': 'user', 'parts': history_user_parts},
                {'role': 'model', 'parts': [text]}
            ])
            self.enable_input()

# 主控制器 
class MainController:
    def __init__(self):
        log("[LOG-C1] MainController 初始化。")
        self.config_manager = ConfigManager()
        self.config = None
        self.gemini_model = None
        self.scaling_factor = 1.0
        self.current_pressed = set()
        self.hotkey_actions = {} 
        self.is_running_action = False
        self.root = None

    def on_press(self, key):
        # 如果有任务在运行，直接忽略任何按键，防止冲突
        if self.is_running_action:
            return
            
        try:
            normalized_key = keyboard.KeyCode.from_char(key.char.lower())
        except AttributeError:
            normalized_key = key
        
        self.current_pressed.add(normalized_key)

        # 遍历所有已注册的动作快捷键
        for action_name, key_set in self.hotkey_actions.items():
            if self.current_pressed == key_set:
                log(f"动作 '{action_name}' 的快捷键被触发。")
                if self.root:
                    self.root.after(0, self.trigger_action, action_name)
                break
            
    def on_release(self, key):
        """按键释放的监听回调，只负责清理 (最终绝对稳定版)"""
        # 释放任何一个键都重置当前按键组合状态
        self.current_pressed.clear()
        log(f"按键释放，重置快捷键状态。")

    def setup_from_config(self):
        """根据加载的配置初始化应用，失败则返回False"""
        # 提前设置代理，并获取返回的代理地址
        proxy_url = set_proxy(self.config.get("proxy_url", ""))

        model_name = self.config.get("model_name", "gemini-1.5-flash-latest")
        
        # 将获取到的代理地址传给 configure_gemini
        self.gemini_model = configure_gemini(
            api_key=self.config.get("api_key", ""), 
            model_name=model_name,
            proxy_url=proxy_url
        )

        if not self.gemini_model:
            self.show_error_and_exit(f"Gemini配置错误: API Key 无效、网络问题或模型名称 '{model_name}' 不正确。\n\n请检查 config.json 文件和代理设置。")
            return False

        # 先把 actions 从 config 中取出来
        actions = self.config.get("actions", {})
        if not actions:
            self.show_error_and_exit("配置文件中未找到 'actions' 配置项。")
            return False
            
        log("正在解析 actions...")
        for action_name, details in actions.items():
            hotkey_str = details.get("hotkey")
            if not hotkey_str:
                log(f"警告: 动作 '{action_name}' 没有配置 hotkey，将被忽略。")
                continue
            
            key_set = self.parse_hotkey(hotkey_str)
            if not key_set:
                self.show_error_and_exit(f"快捷键配置错误: 无法解析动作 '{action_name}' 的快捷键 '{hotkey_str}'。")
                return False
            
            self.hotkey_actions[action_name] = key_set
            log(f"  -> 已注册动作: '{action_name}', 快捷键: {hotkey_str}")

        if not self.hotkey_actions:
            self.show_error_and_exit("未成功注册任何有效的快捷键动作。")
            return False
            
        self.scaling_factor = get_screen_scaling_factor()
        return True

    def parse_hotkey(self, hotkey_str):
        """将字符串 'a+b+c' 解析为 pynput 按键集合 (最终修正版)"""
        if not isinstance(hotkey_str, str) or not hotkey_str: return set()
        
        key_map = {
            'ctrl': keyboard.Key.ctrl, 'alt': keyboard.Key.alt,
            'shift': keyboard.Key.shift, 'cmd': keyboard.Key.cmd, 'win': keyboard.Key.cmd
        }
        keys = set()
        
        parts = hotkey_str.lower().split('+')
        for part in parts:
            part = part.strip()
            if part in key_map:
                keys.add(key_map[part])
            elif len(part) == 1:
                keys.add(keyboard.KeyCode.from_char(part))
            else:
                log(f"无法识别的快捷键部分: '{part}'")
                return set() # 返回空集合表示解析失败
        
        return keys

    def trigger_action(self, action_name):
        """根据动作名称触发相应的流程"""
        if self.is_running_action:
            log("警告：当前已有任务在运行，本次触发被忽略。")
            return
        
        log(f"---------- 新任务开始 ({action_name}) ----------")
        self.is_running_action = True # 在流程开始时就设置标志
        set_proxy(self.config.get("proxy_url", ""))

        if action_name == "screenshot":
            self.start_screenshot_flow()
        elif action_name == "clipboard_text":
            self.start_clipboard_flow()
        else:
            log(f"错误: 未知的动作名称 '{action_name}'")
            self.is_running_action = False # 未知动作，重置标志

    def start_clipboard_flow(self):
        """处理剪贴板文本的流程"""
        try:
            clipboard_content = self.root.clipboard_get()
            if not clipboard_content.strip():
                messagebox.showinfo("提示", "剪贴板内容为空。")
                self.is_running_action = False # 流程结束，重置标志
                return
            
            action_config = self.config["actions"]["clipboard_text"]
            prompt = action_config.get("prompt", "请处理这段文本:") # 默认值
            
            log("成功获取剪贴板文本，准备显示结果窗口。")
            self.show_result_window(
                prompt=prompt, 
                task_type="text", 
                task_data=clipboard_content
            )

        except tk.TclError:
            messagebox.showinfo("提示", "无法从剪贴板获取文本内容。")
            self.is_running_action = False # 流程结束，重置标志
        except Exception as e:
            messagebox.showerror("错误", f"处理剪贴板时发生未知错误: {e}")
            log(f"处理剪贴板时发生未知错误: {e}")
            self.is_running_action = False # 流程结束，重置标志

    def run(self):
        """启动主程序"""
        log("[LOG-C3] MainController.run() 启动。")
        self.root = tk.Tk()
        self.root.withdraw()
        
        self.config = self.config_manager.load_config()

        if not self.config or not self.config.get("api_key"):
            self.show_error_and_exit(
                "配置文件 config.json 不存在或无效！\n\n"
                "请在程序同级目录下创建 config.json 文件，\n"
                "并填入您的 API Key 和其他配置。"
            )
            return

        if not self.setup_from_config():
            return
        
        log("Gemini助手已启动，在后台等待快捷键...")
        log("已注册的快捷键动作如下:")
        # 从 self.config 中读取 actions，以获取原始的 hotkey 字符串用于显示
        actions_config = self.config.get("actions", {})
        for name in self.hotkey_actions.keys():
            hotkey_str = actions_config.get(name, {}).get("hotkey", "未知")
            log(f"  -> {name}: {hotkey_str.upper()}")
        
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()
        
        self.root.mainloop()

    def show_error_and_exit(self, message):
        """显示一个错误消息框，然后退出程序"""
        log(f"启动错误: {message.replace(os.linesep, ' ')}")
        messagebox.showerror("启动错误", message)
        if self.root: self.root.destroy()

    def start_screenshot_flow(self):
        """处理截图的流程"""
        log("[LOG-C6] 准备创建 ScreenshotTaker 实例...")
        screenshot_path = os.path.join(self.config_manager.app_dir, "temp_screenshot.png")
        # 将截图路径作为额外信息传递给回调函数
        callback = lambda cancelled=False: self.screenshot_done(cancelled, screenshot_path)
        ScreenshotTaker(self.scaling_factor, callback, screenshot_path)
        log("[LOG-C7] ScreenshotTaker 实例创建完成。")
    
    def screenshot_done(self, cancelled=False, screenshot_path=None):
        if cancelled:
            self.is_running_action = False
            log("截图任务被取消。")
        elif screenshot_path:
            action_config = self.config["actions"]["screenshot"]
            prompt = action_config.get("prompt", "请描述这张图片:")
            self.show_result_window(
                prompt=prompt,
                task_type="image",
                task_data=screenshot_path
            )
        else:
            log("截图完成，但未提供截图路径。")
            self.is_running_action = False
        
    def show_result_window(self, prompt, task_type, task_data):
        log("[LOG-C8] show_result_window 被调用。")
        result_win = ResultWindow(
            model=self.gemini_model, 
            config_manager=self.config_manager,
            prompt=prompt,
            task_type=task_type,
            task_data=task_data
        )
        result_win.protocol("WM_DELETE_WINDOW", lambda: self.on_result_window_close(result_win))
        
    def on_result_window_close(self, window):
        self.is_running_action = False
        window.destroy()
        log("返回待机状态。")


if __name__ == "__main__":
    # 在创建任何Tkinter窗口之前，先声明进程的DPI感知级别
    # 这会告诉Windows不要对窗口进行DPI虚拟化
    try:
        ctypes.windll.shcore.SetProcessDpiAwarenessContext(-2)
        log("DPI感知级别已设置为 Per Monitor Aware。")
    except Exception as e:
        # 在一些旧系统上可能没有shcore.dll，回退到旧API
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            log("DPI感知级别已设置为 System Aware (旧版API)。")
        except Exception as e2:
            log(f"无法设置DPI感知级别: {e2}")

    # 安全地启动主程序
    controller = MainController()
    controller.run()
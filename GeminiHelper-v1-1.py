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

    # 1. 获取根 logger
    # 我们直接配置根 logger，这样所有地方调用 logging.info 都会生效
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # 设置日志记录的最低级别

    # 2. 清除任何可能已经存在的处理器，防止日志重复
    if logger.hasHandlers():
        logger.handlers.clear()

    # 3. 创建格式化器
    # 定义日志的格式：[时间戳][线程ID] 日志消息
    formatter = logging.Formatter('[%(asctime)s][Thread:%(thread)d] %(message)s', datefmt='%H:%M:%S')

    # 4. 创建并配置 StreamHandler (用于输出到控制台)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 5. 创建并配置 FileHandler (用于输出到文件)
    try:
        file_handler = logging.FileHandler(log_filepath, mode='w', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # 如果因为权限等问题无法创建日志文件，在控制台打印错误
        print(f"无法创建日志文件: {e}")

setup_logging()

# 一个全局的、易于使用的 log 函数
def log(message):
    """全局日志函数，使用 logging.info"""
    logging.info(message)

def set_proxy(config_proxy_url):
    """
    智能设置代理。
    优先级：用户在 config.json 中明确指定的代理 > 系统代理 > 无代理
    """
    final_proxy = None
    
    #检查用户是否在 config.json 中强制指定了代理
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

def configure_gemini(api_key, model_name): 
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name) 
        log(f"Gemini model '{model_name}' set successfully")
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
    def __init__(self, model, config_manager):
        super().__init__()
        self.model = model
        self.config_manager = config_manager

        self.config = self.config_manager.load_config() 
        self.initial_prompt = self.config.get("initial_prompt", "请描述这张图片,并将图片中字符（如果有）翻译成中文。") # 提供一个默认值

        self.screenshot_path = os.path.join(self.config_manager.app_dir, "temp_screenshot.png")
        self.chat_session = None
        self.loaded_image = None
        self.timeout_job = None
        self.typewriter_job = None 
        
        self.setup_ui()
        
        threading.Thread(target=self.process_image_and_get_response, daemon=True).start()

    def on_timeout(self):
        """当API调用超时时，由主线程的定时器调用"""
        # 检查一下，确保任务真的还在运行（防止极小概率的竞争）
        # 如果 self.timeout_job 为 None，说明任务已经正常完成了，直接返回
        if self.timeout_job is None:
            return
            
        log("API 调用超时！")
        # 直接调用更新函数来显示错误
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
            border_color="#B0B3B9"  # 边框颜色
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
            width=80,        # 宽度
            height=40,       # 和输入框一致
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

    def process_image_and_get_response(self):
        if not os.path.exists(self.screenshot_path):
            # 使用 lambda 包装
            self.after(0, lambda: self._update_ui(error="找不到截图文件。"))
            return

        # 在主线程里显示“正在分析”，这是安全的
        self.display_message("正在分析图片...\n")
        self.attributes('-topmost', True); self.focus_force(); self.attributes('-topmost', False)
        
        # 1. 设置一个15秒后会“爆炸”的定时器
        timeout_seconds = 12
        self.timeout_job = self.after(timeout_seconds * 1000, self.on_timeout)
        log(f"已设置 {timeout_seconds} 秒的API调用超时定时器。")

        # 2. 定义一个在后台线程中运行的真正的工作函数
        def background_task():
            try:
                self.loaded_image = Image.open(self.screenshot_path)
                # 我们依然保留库自带的timeout，作为第一道防线
                response = self.model.generate_content(
                    [self.initial_prompt, self.loaded_image],
                    request_options={"timeout": timeout_seconds} 
                )
                result_text = response.text.strip()
                result_error = None
            except Exception as e:
                result_text = None
                result_error = e
            
            # 3. 无论成功还是失败，工作完成后，先拆除“炸弹”
            if self.timeout_job:
                self.after_cancel(self.timeout_job)
                self.timeout_job = None
                log("API调用已完成，超时定时器已取消。")
            
            # 4. 将结果调度回主线程
            self.after(0, lambda: self._update_ui(text=result_text, error=result_error))

        # 5. 启动后台线程
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
        """解析Markdown，准备数据，并启动打字机效果"""
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
        char_list = []
        for text, tag in segments:
            for char in text:
                char_list.append((char, tag))
        
        # 启动递归调用
        self._typewriter_step(char_list)

    def _typewriter_step(self, char_list, index=0):
        """打字机的核心函数，一次处理一个字符"""
        if index < len(char_list):
            char, tag = char_list[index]
            
            # 插入带标签的字符
            if tag:
                self.text_area.insert(tk.END, char, tag)
            else:
                self.text_area.insert(tk.END, char)
            
            # 滚动到底部
            self.text_area.see(tk.END)
            delay = 6
            self.typewriter_job = self.after(delay, self._typewriter_step, char_list, index + 1)
        else:
            # 所有字符都已显示完毕
            self.typewriter_job = None
            # 重新处理加粗（在全部文本显示后处理）
            self.apply_bold_tags()
            self.text_area.config(state=tk.DISABLED) # 在这里才禁用文本框

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
            self.chat_session = self.model.start_chat(history=[
                {'role': 'user', 'parts': [self.initial_prompt, self.loaded_image]},
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
        self.hotkey_set = set()
        self.is_running_action = False
        self.root = None

    def on_press(self, key):
        try:
            normalized_key = keyboard.KeyCode.from_char(key.char.lower())
        except AttributeError:
            normalized_key = key
            
        if normalized_key in self.hotkey_set:
            self.current_pressed.add(normalized_key)

        if self.current_pressed == self.hotkey_set:
            log("[LOG-C2] 快捷键组合被正确按下。")
            
            if self.root:
                self.root.after(0, self.start_screenshot_flow)
            
    def on_release(self, key):
        """按键释放的监听回调，只负责清理 (最终绝对稳定版)"""
        
        try:
            normalized_key = keyboard.KeyCode.from_char(key.char.lower())
        except AttributeError:
            normalized_key = key

        if normalized_key in self.hotkey_set:
            try:
                self.current_pressed.clear()
                log(f"快捷键组合结束 (释放了 {normalized_key})，状态已重置。")
            except KeyError:
                pass

    def setup_from_config(self):
        """根据加载的配置初始化应用，失败则返回False"""
        #set_proxy(self.config.get("proxy_url", ""))
        model_name = self.config.get("model_name", "gemini-2.0-flash-latest")
        
        self.gemini_model = configure_gemini(self.config.get("api_key", ""), model_name)

        if not self.gemini_model:
            self.show_error_and_exit(f"Gemini配置错误: API Key 无效、网络问题或模型名称 '{model_name}' 不正确。\n\n请检查 config.json 文件。")
            return False
        
        self.gemini_model = configure_gemini(self.config.get("api_key", ""), model_name)
        if not self.gemini_model:
            self.show_error_and_exit(f"Gemini配置错误: API Key 无效或网络问题。\n\n请检查 config.json 文件。")
            return False

        self.hotkey_set = self.parse_hotkey(self.config.get("hotkey", ""))
        if not self.hotkey_set:
            self.show_error_and_exit(f"快捷键配置错误: 无法解析快捷键 '{self.config.get('hotkey', '')}'。\n\n请检查 config.json 文件中的格式 (例如: shift+cmd+d)。")
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
        log(f"快捷键: {self.config.get('hotkey', '未知').upper()}")
        
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()
        
        self.root.mainloop()

    def show_error_and_exit(self, message):
        """显示一个错误消息框，然后退出程序"""
        log(f"启动错误: {message.replace(os.linesep, ' ')}")
        messagebox.showerror("启动错误", message)
        if self.root: self.root.destroy()

    def start_screenshot_flow(self):
        if self.is_running_action:
            log("警告：当前已有任务在运行，本次触发被忽略。")
            return
        
        log("---------- 新任务开始，重新检查代理 ----------")
        set_proxy(self.config.get("proxy_url", ""))
        log("[LOG-C6] 准备创建 ScreenshotTaker 实例...")
        # 动态构建截图路径
        screenshot_path = os.path.join(self.config_manager.app_dir, "temp_screenshot.png")
        ScreenshotTaker(self.scaling_factor, self.screenshot_done, screenshot_path)
        log("[LOG-C7] ScreenshotTaker 实例创建完成。")
    
    def screenshot_done(self, cancelled=False):
        if cancelled:
            self.is_running_action = False
        else:
            self.show_result_window()
        
    def show_result_window(self):
        log("[LOG-C8] show_result_window 被调用。")
        result_win = ResultWindow(self.gemini_model, self.config_manager)
        result_win.protocol("WM_DELETE_WINDOW", lambda: self.on_result_window_close(result_win))
        
    def on_result_window_close(self, window):
        self.is_running_action = False
        window.destroy()
        log("返回待机状态。")


if __name__ == "__main__":
    # 创建任何Tkinter窗口之前，先声明进程的DPI感知级别
    # 告诉Windows不要对我们的窗口进行DPI虚拟化
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
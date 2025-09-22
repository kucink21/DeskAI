# core/controller.py

import tkinter as tk
from tkinter import messagebox
import os
from pynput import keyboard
import docx
import fitz
from PIL import Image
import threading
# 导入我们自己的模块
from features.floating_ball import FloatingBall
from features.tray_icon import TrayIcon
from .config_manager import ConfigManager
from .ui import ScreenshotTaker, ResultWindow
from .utils import log, set_proxy, configure_gemini, get_screen_scaling_factor

# 主控制器 
class MainController:
    def __init__(self, root):
        log("[LOG-C1] MainController 初始化。")
        self.config_manager = ConfigManager()
        self.config = None
        self.gemini_model = None
        self.scaling_factor = 1.0
        self.current_pressed = set()
        self.hotkey_actions = {} 
        self.is_running_action = False
        self.root = root
        self.floating_ball = None
        self.tray_icon = None

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
        #log(f"按键释放，重置快捷键状态。")

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
            self.show_error_and_exit(f"Gemini配置错误: API Key 无效、网络问题或模型名称 '{model_name}' 不正确。\n\n请检查 config.json 文件和代理设置。\n如果更新了API key，请重启程序以生效。")
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
            
    def create_widgets(self):
        """创建所有UI组件，如悬浮球和托盘图标"""
        self.floating_ball = FloatingBall(
            master=self.root,
            on_start_chat_callback=self.start_temporary_chat,
            on_hide_callback=self.hide_ball_to_tray,
            on_drop_callback=self.handle_drop_data # <--- 新增这一行
        )
        self.tray_icon = TrayIcon(
            on_show_callback=self.show_ball_from_tray,
            on_exit_callback=self.exit_app
        )

    def start_temporary_chat(self):
        """由悬浮球触发，启动一个临时的纯文本聊天"""
        if self.floating_ball:
            self.floating_ball.reset_idle_timer() 
        if self.is_running_action:
            log("警告：当前已有任务在运行，本次触发被忽略。")
            messagebox.showwarning("忙碌中", "请等待上一个任务完成。")
            return

        log("---------- 悬浮球任务开始（临时对话）----------")
        self.is_running_action = True
        
        # 这里的 prompt 只是为了启动对话，可以自定义
        prompt = "你好！"
        
        # task_data 为空，表示这是一个纯粹的、无上下文的对话开始
        self.show_result_window(
            prompt=prompt,
            task_type="text",
            task_data="" 
        )

    def hide_ball_to_tray(self):
        """隐藏悬浮球并显示托盘图标"""
        if self.floating_ball:
            self.floating_ball.reset_idle_timer()
        if self.floating_ball:
            self.floating_ball.hide()
        if self.tray_icon:
            self.tray_icon.start() # 仅在需要时启动托盘线程

    def show_ball_from_tray(self):
        """从托盘恢复悬浮球"""
        if self.tray_icon:
            self.tray_icon.stop()
            # pystray的stop是非阻塞的，需要一点时间来确保线程退出
            self.root.after(100, self._show_ball_action)
            
    def _show_ball_action(self):
        """确保在托盘退出后显示悬浮球"""
        if self.floating_ball:
            self.floating_ball.show()
            self.floating_ball.window.lift() # 确保窗口在最顶层
            self.floating_ball.window.focus_force()

    def exit_app(self):
        """干净地退出整个应用程序"""
        log("正在退出应用程序...")
        if self.tray_icon:
            self.tray_icon.stop()
        if self.floating_ball:
            self.floating_ball.destroy()
        if self.root:
            self.root.quit()
            self.root.destroy()
        log("应用程序已退出。")
        # 使用 os._exit(0) 确保所有线程都被强制终止
        os._exit(0)

    # 我们需要修改 show_error_and_exit
    def show_error_and_exit(self, message):
        """显示一个错误消息框，然后退出程序"""
        log(f"启动错误: {message.replace(os.linesep, ' ')}")
        # 错误可能在主循环开始前发生，此时 messagebox 可能无法正常显示
        # 创建一个临时root来显示错误
        temp_root = tk.Tk()
        temp_root.withdraw()
        messagebox.showerror("启动错误", message, parent=temp_root)
        temp_root.destroy()
        self.exit_app()
    def run(self):
        """启动主程序"""
        log("[LOG-C3] MainController.run() 启动。")
        # self.root = tk.Tk() <--- 删除
        # self.root.withdraw() <--- 删除
        
        self.config = self.config_manager.load_config()

        if not self.config or not self.config.get("api_key"):
            self.show_error_and_exit(
                "配置文件 config.json 不存在或无效！\n\n"
                "请在程序同级目录下创建 config.json 文件，\n"
                "并填入您的 API Key 和其他配置。\n"
                "API Key 可以在 https://aistudio.google.com/app/apikey 免费获取。\n"
                "如果更新了API key，请重启程序以生效。"
            )
            return

        if not self.setup_from_config():
            return

        log("正在创建悬浮球和系统托盘...")
        self.create_widgets()

        log("Gemini助手已启动，在后台等待快捷键...")
        log("已注册的快捷键动作如下:")
        actions_config = self.config.get("actions", {})
        for name in self.hotkey_actions.keys():
            hotkey_str = actions_config.get(name, {}).get("hotkey", "未知")
            log(f"  -> {name}: {hotkey_str.upper()}")
        
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()
        
        # 我们需要在 run 的最后确保 WM_DELETE_WINDOW 协议被设置
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.root.mainloop()


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

    def handle_drop_data(self, data):
        """
        拖放数据的总入口和调度中心。
        """
        if self.is_running_action:
            messagebox.showwarning("忙碌中", "请等待上一个任务完成。")
            return

        # 清理数据，移除可能的 {}
        cleaned_data = data.strip()
        if cleaned_data.startswith('{') and cleaned_data.endswith('}'):
            cleaned_data = cleaned_data[1:-1]

        # 判断是文件路径还是纯文本
        if os.path.exists(cleaned_data):
            self.process_dropped_files([cleaned_data])
        else:
            self.process_dropped_text(data)

    def process_dropped_text(self, text_content):
        """处理拖放的纯文本"""
        log("处理拖放的纯文本...")
        self.is_running_action = True
        
        action_config = self.config["actions"].get("clipboard_text", {})
        prompt = action_config.get("prompt", "请处理以下文本:")
        
        self.show_result_window(
            prompt=prompt,
            task_type="text",
            task_data=text_content
        )

    def process_dropped_files(self, filepaths):
        """处理拖放的文件列表，并根据文件类型分发任务。"""
        if not filepaths:
            return
            
        filepath = filepaths[0]
        log(f"处理拖放的文件: {filepath}")
        self.is_running_action = True

        ext = os.path.splitext(filepath)[1].lower()
        
        # --- 智能选择 Prompt 和处理方式 ---
        
        # 1. 优先检查是否是为 drop_handlers 特别定义的类型
        drop_handlers_config = self.config.get("drop_handlers", {})
        if ext in drop_handlers_config:
            handler_info = drop_handlers_config[ext]
            prompt = handler_info.get("prompt", f"请处理这个 {ext} 文件。")
            log(f"使用为 '{ext}' 类型定义的专属 prompt。")
            
            # 根据扩展名调用不同的处理函数
            if ext == ".docx":
                self.handle_docx_file(filepath, prompt)
            elif ext == ".pdf":
                self.handle_pdf_file(filepath, prompt)
            elif ext in [".py", ".js", ".html", ".css", ".java", ".cpp"]: # 可以把所有代码文件都归到这里
                self.handle_text_based_file(filepath, prompt)
            else: # 其他在 drop_handlers 中定义的、但没有特殊处理器的类型
                self.handle_text_based_file(filepath, prompt)
            return

        # 2. 如果没有专属定义，则回退到通用的旧逻辑
        if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.webp']:
            log("回退到通用的图片处理逻辑。")
            self.handle_dropped_image(filepath) # 复用 screenshot prompt
        
        elif ext in ['.txt', '.md', '.json']: # <-- 注意：.py 已从此列表移除
            log("回退到通用的文本文件处理逻辑。")
            self.handle_text_based_file(filepath, None) # 传入None，复用 clipboard prompt
        
        else:
            # 真正不支持的格式
            unsupported_message = f"不支持的文件类型: {ext}\n\n当前支持图片、文本和部分文档格式。"
            log(unsupported_message)
            self.is_running_action = False
            messagebox.showinfo("操作失败", unsupported_message)

    def handle_pdf_file(self, filepath, prompt):
        """
        具体处理 .pdf 文件的逻辑。
        采用图文混合模式，提取全部文本和页面截图。
        """
        log(f"正在处理PDF文件: {filepath}")
        
        # --- 创建一个后台线程来处理耗时的PDF解析 ---
        def pdf_processing_thread():
            try:
                doc = fitz.open(filepath)
                
                full_text = []
                page_images = []
                
                log(f"PDF共有 {len(doc)} 页。开始提取内容...")
                
                # 为了防止内容过长和处理时间过久，可以设置一个最大处理页数
                MAX_PAGES_TO_PROCESS = 50 
                pages_to_process = doc.page_count
                if pages_to_process > MAX_PAGES_TO_PROCESS:
                    log(f"警告：PDF页数过多，仅处理前 {MAX_PAGES_TO_PROCESS} 页。")
                    pages_to_process = MAX_PAGES_TO_PROCESS

                for i, page in enumerate(doc.load_page(page_num) for page_num in range(pages_to_process)):
                    # 1. 提取文本
                    full_text.append(page.get_text("text"))
                    
                    # 2. 渲染页面为图片
                    # 设置DPI以提高图片质量，150是个不错的折中值
                    pix = page.get_pixmap(dpi=150)
                    # 从pixmap的样本数据创建Pillow Image对象
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    page_images.append(img)
                    
                    log(f"  ...已处理第 {i+1}/{pages_to_process} 页")

                doc.close()

                # 将所有内容打包
                content = "\n".join(full_text)
                
                # 将任务调度回主线程以显示结果窗口
                # 注意：这里我们将图片列表和文本一起传递
                self.root.after(0, self.show_result_window_for_multimodal, 
                                prompt, "pdf_multimodal", (content, page_images))

            except Exception as e:
                log(f"解析 .pdf 文件失败: {filepath}, 错误: {e}")
                # 确保在主线程中显示错误并重置状态
                def show_error_and_reset():
                    messagebox.showerror("PDF解析失败", f"无法解析 .pdf 文件:\n{e}")
                    self.is_running_action = False
                self.root.after(0, show_error_and_reset)

        # 启动后台处理线程
        threading.Thread(target=pdf_processing_thread, daemon=True).start()

    def handle_text_based_file(self, filepath, prompt=None):
        """
        统一处理所有基于文本的文件（.txt, .py, .md 等）。
        如果 prompt 为 None，则复用剪贴板的 prompt。
        """
        if prompt is None:
            # 复用旧逻辑
            action_config = self.config["actions"].get("clipboard_text", {})
            prompt = action_config.get("prompt", "请分析以下文件内容:")
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            log(f"读取文件失败: {filepath}, 错误: {e}")
            messagebox.showerror("读取失败", f"无法读取文件内容:\n{e}")
            self.is_running_action = False
            return
            
        self.show_result_window(
            prompt=prompt,
            task_type="text",
            task_data=content
        )

    def handle_docx_file(self, filepath, prompt):
        """具体处理 .docx 文件的逻辑"""
        log(f"正在从 .docx 文件提取文本: {filepath}")
        try:
            doc = docx.Document(filepath)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            
            # (可选) 提取表格内容
            # for table in doc.tables:
            #     for row in table.rows:
            #         for cell in row.cells:
            #             full_text.append(cell.text)

            content = '\n'.join(full_text)

        except Exception as e:
            log(f"解析 .docx 文件失败: {filepath}, 错误: {e}")
            messagebox.showerror("解析失败", f"无法解析 .docx 文件:\n{e}")
            self.is_running_action = False
            return

        self.show_result_window(
            prompt=prompt,
            task_type="text", # docx内容也是文本
            task_data=content
        )

    def handle_dropped_image(self, filepath):
        """具体处理图片文件的逻辑"""
        action_config = self.config["actions"].get("screenshot", {})
        prompt = action_config.get("prompt", "请描述这张图片:")
        
        self.show_result_window(
            prompt=prompt,
            task_type="image_from_path",
            task_data=filepath
        )
    def show_result_window_for_multimodal(self, prompt, task_type, task_data_tuple):
        """专门为多模态任务（如PDF）调用结果窗口"""
        log("[LOG-C8-MM] show_result_window_for_multimodal 被调用。")
        result_win = ResultWindow(
            model=self.gemini_model, 
            config_manager=self.config_manager,
            prompt=prompt,
            task_type=task_type,
            task_data=task_data_tuple # task_data现在是一个元组 (text, [image1, image2, ...])
        )
        result_win.protocol("WM_DELETE_WINDOW", lambda: self.on_result_window_close(result_win))
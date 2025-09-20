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
import time 
import json 

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
        
def log(message):
    timestamp = time.strftime("%H:%M:%S", time.localtime())
    thread_id = threading.get_ident()
    print(f"[{timestamp}][Thread:{thread_id}] {message}")

def set_proxy(proxy_url): # <<--- 接收参数
    if proxy_url:
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        log(f"proxy set: {proxy_url}")
    else:
        log("no proxy set")

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
        
        self.setup_ui()
        
        threading.Thread(target=self.process_image_and_get_response, daemon=True).start()


    def setup_ui(self):
        self.title("Gemini 识别结果--你可以发送消息继续这个聊天")
        self.geometry("1200x1050")
        
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        input_frame = tk.Frame(main_frame)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        self.entry = tk.Entry(input_frame, font=("微软雅黑", 14))
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.entry.bind("<Return>", self.send_follow_up_question)

        self.send_button = tk.Button(input_frame, text="发送", font=("微软雅黑", 11), command=self.send_follow_up_question)
        self.send_button.pack(side=tk.RIGHT, padx=(10, 0), ipady=4, ipadx=5)
        
        self.text_area = scrolledtext.ScrolledText(
            main_frame, 
            wrap=tk.WORD, 
            font=("微软雅黑", 12),
            bg="#102A78", 
            fg="#ffffff",          
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
            foreground="#43BDF1") 
        
        self.text_area.tag_config(
            "model_tag", 
            foreground="#33EB43" 
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
            self.display_message("错误：找不到截图文件。")
            return

        self.display_message("正在分析图片...\n")
        self.attributes('-topmost', True); self.focus_force(); self.attributes('-topmost', False)
        
        try:
            self.loaded_image = Image.open(self.screenshot_path)
            response = self.model.generate_content([self.initial_prompt, self.loaded_image])
            initial_response_text = response.text.strip()
            
            self.text_area.config(state=tk.NORMAL); self.text_area.delete('1.0', tk.END); self.text_area.config(state=tk.DISABLED)
            self.display_message(initial_response_text, is_model=True)
            
            self.chat_session = self.model.start_chat(history=[
                {'role': 'user', 'parts': [self.initial_prompt, self.loaded_image]},
                {'role': 'model', 'parts': [initial_response_text]}
            ])
            self.enable_input()
        except Exception as e:
            self.display_message(f"\n发生错误: {e}")
    
    def send_follow_up_question(self, event=None):
        question = self.entry.get().strip()
        if not question: return
        self.display_message(question, is_user=True)
        self.entry.delete(0, tk.END)
        self.disable_input()
        threading.Thread(target=self._send_and_display, args=(question,), daemon=True).start()

    def _send_and_display(self, question):
        try:
            response = self.chat_session.send_message(question)
            
            self.display_message("", is_model=True) 
            self.apply_markdown(response.text.strip())

        except Exception as e: 
            self.display_message(f"\n发生错误: {e}")
        finally: 
            self.enable_input()
        
    def enable_input(self): self.entry.config(state=tk.NORMAL); self.send_button.config(state=tk.NORMAL)
    def disable_input(self): self.entry.config(state=tk.DISABLED); self.send_button.config(state=tk.DISABLED)
    def display_message(self, message, is_user=False, is_model=False):
        self.text_area.config(state=tk.NORMAL)
        
        if is_user:
            self.text_area.insert(tk.END, f"\n\n[用户说]: \n", "user_tag")
            self.text_area.insert(tk.END, f"{message}\n")
        elif is_model:
            self.text_area.insert(tk.END, f"\n[Gemini]: \n", "model_tag") 
            if message: 
                 self.apply_markdown(message)
        else:
            self.text_area.insert(tk.END, message)
            
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)


    def apply_markdown(self, markdown_text):
        """解析简单的Markdown并应用标签（最终优雅版）"""
        import re
        self.text_area.config(state=tk.NORMAL)

        parts = re.split(r"(```.*?```)", markdown_text, flags=re.DOTALL)
        
        for part in parts:
            if part.startswith("```"):
                code_content = part.strip("`\n")
                if not self.text_area.get(f"{self.text_area.index(tk.INSERT)} -1c", tk.INSERT) == "\n":
                    self.text_area.insert(tk.INSERT, "\n")
                
                self.text_area.insert(tk.INSERT, code_content, "md_code")
                self.text_area.insert(tk.INSERT, "\n")
            else:
                for line in part.split('\n'):
                    start_of_line = self.text_area.index(tk.INSERT)

                    list_match = re.match(r"^\s*\* (.*)", line)
                    if list_match:
                        content = list_match.group(1)
                        self.text_area.insert(tk.INSERT, f"• {content}")
                        self.text_area.tag_add("md_list", start_of_line, self.text_area.index(tk.INSERT))
                    else:
                        self.text_area.insert(tk.INSERT, line)

                    end_of_line = self.text_area.index(tk.INSERT)
                    line_text = self.text_area.get(start_of_line, end_of_line)
                    
                    offset = 0
                    for bold_match in re.finditer(r"\*\*(.*?)\*\*", line_text):
                        clean_text = bold_match.group(1)
                        
                        tag_start_index = self.text_area.index(f"{start_of_line}+{bold_match.start() - offset}c")
                        tag_end_index = self.text_area.index(f"{start_of_line}+{bold_match.end() - offset}c")
                        
                        self.text_area.delete(tag_start_index, tag_end_index)
                        self.text_area.insert(tag_start_index, clean_text, "md_bold")
                        
                        offset += 4

                    self.text_area.insert(tk.INSERT, "\n")

        self.text_area.config(state=tk.DISABLED)

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
        set_proxy(self.config.get("proxy_url", ""))
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
        if self.is_running_action: return
        self.is_running_action = True
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
    # 在创建任何Tkinter窗口之前，先声明进程的DPI感知级别
    # 这会告诉Windows不要对我们的窗口进行DPI虚拟化
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
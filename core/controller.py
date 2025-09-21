# core/controller.py

import tkinter as tk
from tkinter import messagebox
import os
from pynput import keyboard

# 导入我们自己的模块
from features.floating_ball import FloatingBall
from features.tray_icon import TrayIcon
from .config_manager import ConfigManager
from .ui import ScreenshotTaker, ResultWindow
from .utils import log, set_proxy, configure_gemini, get_screen_scaling_factor

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
            
    def create_widgets(self):
        """创建所有UI组件，如悬浮球和托盘图标"""
        self.floating_ball = FloatingBall(
            master=self.root,
            on_start_chat_callback=self.start_temporary_chat,
            on_hide_callback=self.hide_ball_to_tray
        )
        self.tray_icon = TrayIcon(
            on_show_callback=self.show_ball_from_tray,
            on_exit_callback=self.exit_app
        )
        # 首次不启动托盘，因为悬浮球是可见的

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
        log("正在创建悬浮球和系统托盘...")
        self.create_widgets()

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
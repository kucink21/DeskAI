# features/instructions_window.py

import tkinter as tk
import customtkinter as ctk
import os
import sys

class InstructionsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.transient(master)
        # self.grab_set() # 保持注释掉

        # --- 在这里添加最终的修复代码 ---
        # 从主题管理器获取标准的框架背景色
        default_frame_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        # 强制设置窗口的背景色，覆盖掉错误的默认值
        self.configure(fg_color=default_frame_color)
        # --- 修复代码结束 ---

        self.title("使用说明")
        self.geometry("700x600")

        # 确定说明文件的路径
        if getattr(sys, 'frozen', False):
            # 在打包后的环境中
            base_path = sys._MEIPASS
        else:
            # 在开发环境中
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        instructions_path = os.path.join(base_path, 'assets', 'instructions.md')

        # 创建一个文本框来显示内容
        textbox = ctk.CTkTextbox(
            self, 
            wrap="word", 
            font=("微软雅黑", 14),
            fg_color="#F8F8F8" # 深色背景
        )
        textbox.pack(fill="both", expand=True, padx=10, pady=10)

        try:
            with open(instructions_path, 'r', encoding='utf--8') as f:
                content = f.read()
            textbox.insert("1.0", content)
        except FileNotFoundError:
            textbox.insert("1.0", f"错误：找不到说明文件！\n\n请确保 'assets/instructions.md' 文件存在。")
        except Exception as e:
            textbox.insert("1.0", f"错误：无法读取说明文件。\n\n{e}")

        # 禁止编辑
        textbox.configure(state="disabled")

        # 添加一个关闭按钮
        close_button = ctk.CTkButton(self, text="关闭", command=self.destroy)
        close_button.pack(pady=10)
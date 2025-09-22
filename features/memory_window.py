# features/memory_window.py

import customtkinter as ctk
from tkinter import messagebox

class MemoryWindow(ctk.CTkToplevel):
    def __init__(self, master, current_memory, save_callback):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.title("编辑记忆库")
        self.geometry("600x500")

        # 设置背景色以修复可能的灰色蒙版问题
        default_frame_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        self.configure(fg_color=default_frame_color)

        self.initial_memory = current_memory
        self.save_callback = save_callback

        self.create_widgets()
        
        # 监听关闭事件
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        # 顶部说明标签
        info_label = ctk.CTkLabel(
            self, 
            text="在这里输入您的长期背景信息或短期任务上下文。\nAI会在每次处理请求时参考这些内容。\n比如：\n- 个人偏好：运动\n- 基础信息：我是一名计算机学生，在学习计算机视觉\n- 任务：我正在做一个python编程任务\n\n记忆库内容会被保存到memory.txt中。",
            font=("微软雅黑", 12),
            text_color="#888888",
            wraplength=550,
            justify="left"
        )
        info_label.pack(padx=20, pady=(10, 5), anchor="w")

        # 主文本编辑区
        self.textbox = ctk.CTkTextbox(self, wrap="word", font=("微软雅黑", 14))
        self.textbox.pack(fill="both", expand=True, padx=20, pady=5)
        self.textbox.insert("1.0", self.initial_memory)

        # 底部按钮区域
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(button_frame, text="保存并关闭", command=self.save_and_close).pack(side="right")
        ctk.CTkButton(button_frame, text="取消", command=self.on_close).pack(side="right", padx=10)

    def save_and_close(self):
        """保存并关闭窗口"""
        new_memory_content = self.textbox.get("1.0", "end-1c")
        if self.save_callback(new_memory_content): # 调用回调并检查是否成功
            self.destroy()
        else:
            messagebox.showerror("保存失败", "无法将记忆写入文件，请检查日志获取更多信息。")

    def on_close(self):
        """处理关闭窗口事件，检查是否有未保存的更改"""
        current_content = self.textbox.get("1.0", "end-1c")
        if current_content != self.initial_memory:
            # 弹出确认对话框
            response = messagebox.askyesnocancel(
                "未保存的更改",
                "您有未保存的更改，是否要保存？\n\n是 - 保存并关闭\n否 - 不保存并关闭\n取消 - 返回编辑",
                parent=self
            )
            if response is True: # 用户点击了“是”
                self.save_and_close()
            elif response is False: # 用户点击了“否”
                self.destroy()
            # 如果 response is None (用户点击了“取消”)，则什么也不做
        else:
            self.destroy()
# features/settings_window.py

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, current_config, models_config, save_callback):
        super().__init__(master)
        self.transient(master) # 保持在主窗口之上
        self.grab_set() # 模态窗口，阻止与其他窗口交互
        self.title("设置")
        self.geometry("800x700")

        self.config_data = current_config
        self.models_config = models_config
        self.save_callback = save_callback
        
        # 用于存储UI输入框控件的字典
        self.entries = {}
        self.placeholders = {
            ('api_key',): "在此处填写您的 Google AI API Key",
            ('proxy_url',): "留空则自动检测系统代理,否则填写完整的代理URL，例如: http://127.0.0.1:7890",
            ('model_name',): "例如: gemini-2.5-flash-lite",
            ('actions', 'screenshot', 'prompt'): "例如: 请描述这张截图...",
            ('actions', 'clipboard_text', 'prompt'): "例如: 将这段文字翻译成中文...",
            ('drop_handlers', '.pdf', 'prompt'): "例如: 总结这份PDF文档...",
            # 你可以为所有prompt都添加占位符
        }
        self.create_widgets()
        self.after(100, self.initialize_placeholders)

    def initialize_placeholders(self):
        """
        遍历所有文本框，如果它们应该显示占位符，
        就手动触发 <FocusOut> 事件来正确设置它们。
        """
        for widget_info in self.entries.values():
            if isinstance(widget_info, tuple) and len(widget_info) == 3:
                textbox, placeholder, state = widget_info
                # 如果它初始为空（即应该显示占位符）
                if state['is_placeholder']:
                    # 手动触发 <FocusOut> 事件
                    textbox.event_generate("<<FocusOut>>")
        
        # 将焦点设置到窗口本身，避免光标停在最后一个文本框里
        self.focus_set()

    def create_widgets(self):
        # 创建一个可滚动的框架
        scrollable_frame = ctk.CTkScrollableFrame(self, label_text="配置项")
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- 通用设置 ---
        ctk.CTkLabel(scrollable_frame, text="通用设置", font=("微软雅黑", 16, "bold")).pack(anchor="w", pady=(10, 5))
        # --- 新增：模型选择下拉菜单 ---
        ctk.CTkLabel(scrollable_frame, text="模型选择 (重启后生效)", font=("微软雅黑", 14, "bold")).pack(anchor="w", pady=(10, 5))
        
        model_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        model_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(model_frame, text="AI 提供商", width=120, anchor="w").pack(side="left")
        provider_names = list(self.models_config.get("providers", {}).keys())
        self.provider_combo = ctk.CTkComboBox(model_frame, values=provider_names, command=self.on_provider_selected)
        self.provider_combo.pack(side="left", padx=(10, 0))
        
        model_select_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
        model_select_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(model_select_frame, text="具体模型", width=120, anchor="w").pack(side="left")
        self.model_combo = ctk.CTkComboBox(model_select_frame, values=["请先选择提供商"])
        self.model_combo.pack(side="left", padx=(10, 0))
        
        # 初始化下拉菜单的显示值
        initial_provider = self.config_data.get("selected_provider", provider_names[0] if provider_names else "")
        self.provider_combo.set(initial_provider)
        self.on_provider_selected(initial_provider) # 手动触发一次，以填充模型列表
        
        initial_model = self.config_data.get("selected_model", "")
        if initial_model: self.model_combo.set(initial_model)
        # --- 新增代码结束 ---
        # --- 新增：独立的API Keys区域 ---
        ctk.CTkLabel(scrollable_frame, text="API Keys (重启后生效)", font=("微软雅黑", 16, "bold")).pack(anchor="w", pady=(20, 5))
        self.create_entry(scrollable_frame, "Google Gemini", ["api_keys", "google_gemini"])
        self.create_entry(scrollable_frame, "OpenAI", ["api_keys", "openai"])
        # (未来可以继续在这里添加其他厂商的Key输入框)
        # --- 新增代码结束 ---
        self.create_entry(scrollable_frame, "代理 URL", ["proxy_url"])
        proxy_info_label = ctk.CTkLabel(
            scrollable_frame, 
            text="                                    此项留空则自动检测系统代理, 否则填写完整的代理URL (例如: http://127.0.0.1:7890)",
            font=("微软雅黑", 12),
            text_color="#7F7E7E",
            wraplength=600, # 自动换行宽度
            justify="left"
        )
        proxy_info_label.pack(anchor="w", padx=10, pady=(3, 0))

        # --- 快捷键动作 Prompts ---
        ctk.CTkLabel(scrollable_frame, text="快捷键动作", font=("微软雅黑", 16, "bold")).pack(anchor="w", pady=(20, 5)) # 修改标题
        if "actions" in self.config_data:
            for action, details in self.config_data["actions"].items():
                # --- 为每个动作创建一个小容器 ---
                action_frame = ctk.CTkFrame(scrollable_frame)
                action_frame.pack(fill="x", pady=10)
                
                ctk.CTkLabel(action_frame, text=f"动作: {action}", font=("微软雅黑", 14, "bold")).pack(anchor="w", padx=10)
                
                # 创建快捷键输入框
                self.create_entry(action_frame, "  快捷键", ["actions", action, "hotkey"])
                
                # 创建 Prompt 文本框
                self.create_textbox(action_frame, "  提示词", ["actions", action, "prompt"])

        # --- 拖放动作 Prompts ---
        ctk.CTkLabel(scrollable_frame, text="拖放动作 Prompts", font=("微软雅黑", 16, "bold")).pack(anchor="w", pady=(20, 5))
        if "drop_handlers" in self.config_data:
            for ext, details in self.config_data["drop_handlers"].items():
                self.create_textbox(scrollable_frame, f"文件类型: {ext}", ["drop_handlers", ext, "prompt"])

        # --- 底部按钮 ---
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(button_frame, text="保存", command=self.save_settings).pack(side="right", padx=5)
        ctk.CTkButton(button_frame, text="取消", command=self.destroy).pack(side="right", padx=5)

    def on_provider_selected(self, selected_provider: str):
        """当用户选择了一个新的AI提供商时，更新具体模型的下拉列表"""
        provider_info = self.models_config.get("providers", {}).get(selected_provider)
        if provider_info:
            model_names = provider_info.get("models", [])
            self.model_combo.configure(values=model_names)
            if model_names:
                # 默认选中列表中的第一个模型
                self.model_combo.set(model_names[0])
        else:
            self.model_combo.configure(values=["无效的提供商"])
            self.model_combo.set("无效的提供商")

    def create_entry(self, parent, label_text, config_path):
        """创建一个单行输入框"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        
        label = ctk.CTkLabel(frame, text=label_text, width=120, anchor="w")
        label.pack(side="left", padx=(0, 10))

        value = self.get_config_value(config_path, "")
        
        path_tuple = tuple(config_path)
        placeholder_text = self.placeholders.get(path_tuple, None) 

        entry = ctk.CTkEntry(
            frame, 
            width=400,
            placeholder_text=placeholder_text 
        )

        entry.insert(0, value)
        entry.pack(side="left", fill="x", expand=True)
        
        self.entries[path_tuple] = entry

    def create_textbox(self, parent, label_text, config_path):
        """创建一个多行文本框，并使用状态标志模拟占位符行为"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        
        label = ctk.CTkLabel(frame, text=label_text, width=120, anchor="w")
        label.pack(side="left", padx=(0, 10), anchor="n")

        value = self.get_config_value(config_path, "")
        path_tuple = tuple(config_path)
        placeholder_text = self.placeholders.get(path_tuple, f"输入 {label_text} 的 Prompt...")
        placeholder_color = "#888888"
        default_text_color = ctk.ThemeManager.theme["CTkTextbox"]["text_color"]

        textbox = ctk.CTkTextbox(frame, height=100, wrap="word")

        state = {'is_placeholder': False}

        def on_focus_in(event):
            if state['is_placeholder']:
                textbox.delete("1.0", "end")
                textbox.configure(text_color=default_text_color)
                state['is_placeholder'] = False

        def on_focus_out(event):
            # strip() 确保只有空白字符的输入也被视为空
            if not textbox.get("1.0", "end-1c").strip():
                # 确保在插入占位符前是空的
                textbox.delete("1.0", "end") 
                textbox.configure(text_color=placeholder_color)
                textbox.insert("1.0", placeholder_text)
                state['is_placeholder'] = True

        textbox.bind("<FocusIn>", on_focus_in)
        textbox.bind("<FocusOut>", on_focus_out)

        # 初始化时只插入真实值，不处理占位符
        if value:
            textbox.insert("1.0", value)
            state['is_placeholder'] = False
        else:
            state['is_placeholder'] = True 
        
        textbox.pack(side="left", fill="x", expand=True)
        
        self.entries[path_tuple] = (textbox, placeholder_text, state)

    def get_config_value(self, path, default=""):
        """从嵌套字典中安全地获取值"""
        d = self.config_data
        for key in path:
            if isinstance(d, dict) and key in d:
                d = d[key]
            else:
                return default
        return d

    def save_settings(self):
        """收集UI中的数据，更新配置，并调用回调函数"""
        new_config = self.config_data.copy()
        new_config["selected_provider"] = self.provider_combo.get()
        new_config["selected_model"] = self.model_combo.get()
        for path_tuple, widget_info in self.entries.items():
            value = ""
            
            if isinstance(widget_info, ctk.CTkEntry):
                value = widget_info.get()
            
            elif isinstance(widget_info, tuple) and len(widget_info) == 3:
                textbox, placeholder, state = widget_info
                # 直接通过状态标志判断，而不是比较文本内容
                if state['is_placeholder']:
                    value = "" # 如果是占位符状态，保存空字符串
                else:
                    value = textbox.get("1.0", "end-1c")
            
            else:
                continue

            d = new_config
            for key in path_tuple[:-1]:
                d = d.setdefault(key, {})
            d[path_tuple[-1]] = value
        
        self.save_callback(new_config)
        
        messagebox.showinfo(
            "成功", 
            "设置已保存！\n\n"
            "提示：API Key、代理或快捷键的更改需要重启程序才能生效。"
        )
        self.destroy()
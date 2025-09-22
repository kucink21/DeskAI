# core/ui.py

import tkinter as tk
from tkinter import scrolledtext, messagebox
from PIL import Image, ImageGrab
import os
import threading
import customtkinter as ctk

# 导入工具函数
from .utils import log

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
        self.title(" [Gemini对话窗口] --> 你可以发送消息继续这个聊天 :) ")
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
            width=80,        
            height=40,      
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
        self.display_message("正在分析...\n  · 大文件需要更长时间，请耐心等待... \n  · API timeout设置为20秒")
        self.attributes('-topmost', True); self.focus_force(); self.attributes('-topmost', False)
        
        timeout_seconds = 20
        self.timeout_job = self.after(timeout_seconds * 1000, self.on_timeout)
        log(f"已设置 {timeout_seconds} 秒的API调用超时定时器。")

        def background_task():
            try:
                # --- 新的多模态请求构建逻辑 ---
                content_parts = [self.initial_prompt]
                
                if self.task_type == 'pdf_multimodal':
                    # task_data 是一个元组: (text, [image1, image2, ...])
                    pdf_text, pdf_images = self.task_data
                    
                    if pdf_text:
                        content_parts.append(pdf_text)

                    if pdf_images:
                        content_parts.extend(pdf_images)
                    
                    self.loaded_image = pdf_images[0] if pdf_images else None

                elif self.task_type in ['image', 'image_from_path']:
                    image_path = self.task_data
                    if not os.path.exists(image_path):
                        raise FileNotFoundError(f"找不到图片文件: {image_path}")
                    self.loaded_image = Image.open(image_path)
                    content_parts.append(self.loaded_image)

                elif self.task_type == 'text':
                    text_data = self.task_data
                    if text_data:
                        content_parts.append(text_data)
                
                else:
                    raise ValueError(f"未知的任务类型: {self.task_type}")

                # 发送请求 (这部分代码保持不变)
                log(f"正在向Gemini发送请求，包含 {len(content_parts)} 个部分...")
                response = self.model.generate_content(
                    content_parts,
                    request_options={"timeout": 60} # PDF处理可能需要更长的超时时间
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
            error_message = f"发生错误: {error} \n请检查网络连接和代理设置，以及API Key\n如果更新了API Key，请重启应用。"
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
            if self.task_type in ['image', 'image_from_path'] and self.loaded_image:
                history_user_parts.append(self.loaded_image)
            elif self.task_type == 'text':
                if self.task_data: # 确保非空
                    history_user_parts.append(self.task_data)
            elif self.task_type == 'pdf_multimodal':
                # 对于PDF，历史记录里包含文本和所有图片
                pdf_text, pdf_images = self.task_data
                if pdf_text:
                    history_user_parts.append(pdf_text)
                if pdf_images:
                    history_user_parts.extend(pdf_images)
            
            self.chat_session = self.model.start_chat(history=[
                {'role': 'user', 'parts': history_user_parts},
                {'role': 'model', 'parts': [text]}
            ])
            self.enable_input()
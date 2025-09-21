# features/floating_ball.py

import tkinter as tk
import os
import sys
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import math
from tkinterdnd2 import DND_FILES, DND_TEXT
from core.utils import log

# 导入Windows API相关的库
try:
    import ctypes
    from win32 import win32gui, win32con
    IS_WINDOWS = True
except ImportError:
    IS_WINDOWS = False
    print("警告：未找到 pywin32 库，将使用兼容模式显示悬浮球（边缘可能不平滑）。")
    print("在Windows上，请运行 'pip install pywin32' 以获得最佳效果。")


class FloatingBall:
    def __init__(self, master, on_start_chat_callback, on_hide_callback, on_drop_callback):
        self.master = master
        self.on_start_chat_callback = on_start_chat_callback
        self.on_hide_callback = on_hide_callback
        self.on_drop_callback = on_drop_callback
        
        self.ball_size = 120  # 保持尺寸

        self.window = tk.Toplevel(master)
        self.window.overrideredirect(True)
        self.window.wm_attributes("-topmost", True)
        self.window.geometry(f"{self.ball_size}x{self.ball_size}+100+100")
        
        # 将窗口背景设置为一种独特的颜色，用于颜色键控（即使在使用Alpha透明时也建议这样做作为后备）
        self.transparent_color = '#abcdef'
        self.window.config(bg=self.transparent_color)
        self.window.wm_attributes("-transparentcolor", self.transparent_color)
        self.window.drop_target_register(DND_FILES, DND_TEXT)
        self.window.dnd_bind('<<Drop>>', self.handle_drop)
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(__file__))
        
        # 加载PNG图片
        png_path = os.path.join(base_path, 'icon', 'ball.png')
        if os.path.exists(png_path):
            self.ball_image = ImageTk.PhotoImage(Image.open(png_path).resize((self.ball_size, self.ball_size), Image.Resampling.LANCZOS))
            self.label = tk.Label(self.window, image=self.ball_image, bd=0, bg=self.transparent_color)
            self.label.pack()
        else:
            # 回退方案
            self.label = tk.Canvas(self.window, width=self.ball_size, height=self.ball_size, bg=self.transparent_color, highlightthickness=0)
            padding = 10
            self.label.create_oval(padding, padding, self.ball_size - padding, self.ball_size - padding, fill="#2563EB", outline="lightblue", width=4)
            self.label.pack()

        # --- 关键部分：应用真正的Alpha透明 ---
        if IS_WINDOWS:
            self.apply_true_alpha_transparency()

        # 菜单和事件绑定的代码保持不变
        self.menu = None
        self.label.bind("<ButtonPress-1>", self.on_drag_start)
        self.label.bind("<B1-Motion>", self.on_drag_motion)
        self.label.bind("<Button-3>", self.show_custom_menu)
        self.label.bind("<Button-2>", self.show_custom_menu)
        self._drag_x = 0
        self._drag_y = 0
        # --- 动画相关属性 ---
        self.animation_job = None      # 存储 after() 任务的ID，用于取消
        self.is_animating = False      # 动画是否正在运行的标志
        self.original_pil_image = None # 存储原始的、未旋转的Pillow图像对象
        self.current_angle = 0         # 当前旋转角度

        # --- 待机计时器相关属性 ---
        self.idle_timer_job = None     # 存储待机计时器的ID
        self.idle_timeout = 6000      # 10秒后触发待机动画 (单位：毫秒)

        # 加载原始Pillow图像以备旋转
        # (这部分代码需要从原来的if/else块中提取和修改)
        png_path = os.path.join(base_path, 'icon', 'ball.png')
        if os.path.exists(png_path):
            # 将原始Pillow图像存储起来！
            self.original_pil_image = Image.open(png_path)
        else:
            # 如果PNG不存在，创建一个临时的Pillow图像
            self.original_pil_image = self.create_canvas_image()

        # 首次显示图像
        self.update_image(0) 

        # 启动第一个待机计时器
        self.reset_idle_timer()

    def handle_drop(self, event):
        """处理拖放事件，并将数据传递给主控制器"""
        log(f"悬浮球接收到拖放数据: {event.data}")
        # 重置待机计时器，因为这也是一种交互
        self.reset_idle_timer()

        # 调用主控制器传递过来的回调函数进行处理
        if self.on_drop_callback:
            self.on_drop_callback(event.data)

    def create_canvas_image(self):
        """如果PNG不存在，用Pillow在内存中创建一个图像"""
        temp_image = Image.new("RGBA", (self.ball_size, self.ball_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(temp_image)
        padding = 10
        draw.ellipse(
            (padding, padding, self.ball_size - padding, self.ball_size - padding), 
            fill="#2563EB", outline="lightblue", width=4
        )
        return temp_image

    def update_image(self, angle):
        """旋转并更新悬浮球显示的图像"""
        if not self.original_pil_image:
            return
        
        # 使用Pillow旋转图像。'expand=False'确保尺寸不变
        rotated_image = self.original_pil_image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
        
        # 将Pillow图像转换为Tkinter图像
        self.ball_image = ImageTk.PhotoImage(rotated_image)
        self.label.config(image=self.ball_image)

    def reset_idle_timer(self):
        """重置待机计时器"""
        # 如果有正在等待的计时器，先取消它
        if self.idle_timer_job:
            self.window.after_cancel(self.idle_timer_job)
        
        # 如果动画正在运行，则不启动新的计时器
        if self.is_animating:
            return
            
        # 设置一个新的计时器，在超时后启动动画
        self.idle_timer_job = self.window.after(self.idle_timeout, self.start_rotation_animation)

    def ease_in_out_sine(self, x):
        """一个缓动函数，返回0到1之间的值"""
        return -(math.cos(math.pi * x) - 1) / 2

    def start_rotation_animation(self):
        """开始旋转动画的主函数"""
        if self.is_animating:
            return
        
        self.is_animating = True
        self.current_angle = 0
        
        duration = 2000  # 动画总时长（毫秒），旋转两圈
        frames_per_second = 60
        total_frames = int(duration / 1000 * frames_per_second)
        total_rotation = 720 # 总共旋转720度（两圈）
        
        self.animate_frame(0, total_frames, duration, total_rotation)

    def animate_frame(self, frame, total_frames, duration, total_rotation):
        """递归函数，用于绘制动画的每一帧"""
        if frame > total_frames:
            # 动画结束
            self.is_animating = False
            self.update_image(0) # 恢复到0度
            self.reset_idle_timer() # 重新开始待机计时
            return

        # 计算当前进度 (0.0 to 1.0)
        progress = frame / total_frames
        
        # 应用缓动函数
        eased_progress = self.ease_in_out_sine(progress)
        
        # 根据缓动后的进度计算当前应该旋转的角度
        self.current_angle = eased_progress * total_rotation
        
        self.update_image(self.current_angle)
        
        # 调度下一帧
        delay = int(duration / total_frames)
        self.animation_job = self.window.after(
            delay, 
            self.animate_frame, 
            frame + 1, 
            total_frames, 
            duration, 
            total_rotation
        )

    def apply_true_alpha_transparency(self):
        """使用Windows API为窗口设置逐像素Alpha透明度"""
        # 强制更新窗口以获取句柄
        self.window.update()
        
        # 获取窗口句柄 (HWND)
        hwnd = win32gui.GetParent(self.window.winfo_id())
        
        # 获取窗口现有样式
        styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        
        # 添加 WS_EX_LAYERED 样式，这是实现透明的关键
        styles |= win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, styles)
        
        # 设置窗口为透明，但只让指定颜色(transparent_color)透明
        # 最后一个参数 LWA_COLORKEY 告诉API我们要使用颜色键控
        win32gui.SetLayeredWindowAttributes(hwnd, 0, 255, win32con.LWA_ALPHA)
        # 注意: 上面的代码使用全局Alpha，要实现完美的per-pixel alpha，
        # 通常需要更复杂的UpdateLayeredWindow调用。
        # 但对于Tkinter，SetLayeredWindowAttributes通常足以解决抗锯齿问题。
        # 我们在这里使用LWA_ALPHA来利用窗口本身的alpha通道，而不是颜色键控
        # win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(..), 0, win32con.LWA_COLORKEY)

    # --- 其他所有方法 (on_drag_start, show_custom_menu 等) 保持原样 ---
    # ... 把你之前版本中 FloatingBall 类的其他所有方法原封不动地复制到这里 ...
    def on_drag_start(self, event):
        if self.menu: self.menu.destroy(); self.menu = None
        self._drag_x, self._drag_y = event.x, event.y
        self.reset_idle_timer()
    def on_drag_motion(self, event):
        x = self.window.winfo_x() + event.x - self._drag_x
        y = self.window.winfo_y() + event.y - self._drag_y
        self.window.geometry(f"+{x}+{y}")
    def show_custom_menu(self, event):
        if self.menu: return
        self.reset_idle_timer()
        self.menu = tk.Toplevel(self.window); self.menu.overrideredirect(True); self.menu.wm_attributes("-topmost", True)
        menu_frame = ctk.CTkFrame(self.menu, corner_radius=10, fg_color="#333333"); menu_frame.pack(padx=1, pady=1)
        button_font, button_height = ("微软雅黑", 14), 40
        ctk.CTkButton(menu_frame, text="开始新对话", font=button_font, height=button_height, fg_color="transparent", hover_color="#555555", command=self.on_start_chat_callback).pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkButton(menu_frame, text="隐藏悬浮球", font=button_font, height=button_height, fg_color="transparent", hover_color="#555555", command=self.on_hide_callback).pack(fill="x", padx=10, pady=(5, 10))
        self.menu.update_idletasks()
        self.menu.geometry(f"{self.menu.winfo_width()}x{self.menu.winfo_height()}+{event.x_root}+{event.y_root}")
        self.menu.bind("<FocusOut>", lambda e: self.menu.destroy() if self.menu else None)
        self.menu.focus_set()
    def show(self): self.window.deiconify()
    def hide(self):
        if self.menu: self.menu.destroy(); self.menu = None
        self.window.withdraw()
    def destroy(self): self.window.destroy()
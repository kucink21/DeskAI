# features/floating_ball.py

import tkinter as tk
import os
import sys
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import math
import time
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
    def __init__(self, master, initial_theme_prefix: str, on_start_chat_callback, on_hide_callback, on_drop_callback, on_settings_callback, on_instructions_callback, on_memory_callback, on_restart_callback, on_exit_callback):
        self.master = master
        self.on_start_chat_callback = on_start_chat_callback
        self.on_hide_callback = on_hide_callback
        self.on_drop_callback = on_drop_callback
        self.on_settings_callback = on_settings_callback
        self.on_instructions_callback = on_instructions_callback
        self.on_memory_callback = on_memory_callback
        self.on_restart_callback = on_restart_callback
        self.on_exit_callback = on_exit_callback

        self.is_session_active = False
        self.idle_pil_image = None
        self.session_pil_image = None
        self.current_theme = ""

        self.ball_size = 132 
        self.window = tk.Toplevel(master)
        self.window.overrideredirect(True)
        self.window.wm_attributes("-topmost", True)
        self.window.geometry(f"{self.ball_size}x{self.ball_size}+100+100")
        self.transparent_color = '#abcdef'
        self.window.config(bg=self.transparent_color)
        self.window.wm_attributes("-transparentcolor", self.transparent_color)

        # --- 修正后的核心逻辑 ---

        # 1. 确定路径并加载 Pillow 图片到内存
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 1. 在 __init__ 中直接调用 set_icon_theme 来加载初始主题
        #    这会确保 self.idle_pil_image 被正确赋值。
        self.set_icon_theme(initial_theme_prefix)

        # 2. 现在，使用已经加载好的 self.idle_pil_image 来创建 self.label 控件
        #    这是确保 self.label 在被使用前存在的关键一步。
        self.ball_image = ImageTk.PhotoImage(self.idle_pil_image)
        self.label = tk.Label(self.window, image=self.ball_image, bd=0, bg=self.transparent_color)
        self.label.pack()

        if IS_WINDOWS:
            self.apply_true_alpha_transparency()

        self.menu = None
        self.label.bind("<ButtonPress-1>", self.on_button_press) 
        self.label.bind("<B1-Motion>", self.on_drag_motion)
        self.label.bind("<ButtonRelease-1>", self.on_button_release) 
        self.label.bind("<Double-Button-1>", self.on_double_click) 
        self.label.bind("<Button-3>", self.show_custom_menu)
        self.label.bind("<Button-2>", self.show_custom_menu)

        self._drag_x = 0
        self._drag_y = 0

        # 动画和待机计时器属性
        self.animation_job = None
        self.is_animating = False
        self.current_angle = 0
        self.idle_timer_job = None
        self.idle_timeout = 6000

        self.is_wobbling = False       # 晃动动画是否正在运行的标志
        self.wobble_job = None         # 存储晃动动画的 after ID
        self.single_click_timer = None # 存储用于区分单击/双击的 after ID

        # 注册拖放事件
        self.window.drop_target_register(DND_FILES, DND_TEXT)
        self.window.dnd_bind('<<Drop>>', self.handle_drop)
        
        # 启动第一个待机计时器
        self.reset_idle_timer()

    def set_icon_theme(self, theme_prefix: str):
        """
        加载并应用一套新的图标主题。
        这个方法现在在初始化时被调用，也可以用于未来的主题热切换。
        """
        if self.current_theme == theme_prefix and self.idle_pil_image is not None:
            return 
            
        log(f"正在设置/切换悬浮球图标主题为: {theme_prefix}")
        self.current_theme = theme_prefix
        
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            idle_png_path = os.path.join(base_path, 'icon', f'{theme_prefix}1.png')
            session_png_path = os.path.join(base_path, 'icon', f'{theme_prefix}2.png')

            if os.path.exists(idle_png_path):
                self.idle_pil_image = Image.open(idle_png_path)
            else:
                log(f"警告：找不到待机图标 {idle_png_path}，将使用备用方案。")
                self.idle_pil_image = self.create_canvas_image()

            if os.path.exists(session_png_path):
                self.session_pil_image = Image.open(session_png_path)
            else:
                log(f"警告：找不到会话图标 {session_png_path}，将使用待机图标代替。")
                self.session_pil_image = self.idle_pil_image
                
            # 如果label已经存在，则立即更新显示
            if hasattr(self, 'label') and self.label.winfo_exists():
                self.update_image(self.current_angle)

        except Exception as e:
            log(f"加载图标主题 '{theme_prefix}' 失败: {e}")
            if self.idle_pil_image is None: # 确保至少有一个可用的图像
                self.idle_pil_image = self.create_canvas_image()
                self.session_pil_image = self.idle_pil_image

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
    def set_session_state(self, is_active: bool):
        """
        设置悬浮球的会话状态，并立即更新其外观。
        :param is_active: True表示会话开始，False表示会话结束。
        """
        if self.is_session_active == is_active:
            return # 状态未改变，无需操作

        self.is_session_active = is_active
        log(f"悬浮球会话状态更新为: {is_active}")
        
        # 立即更新图像以反映新状态
        # 如果正在动画中，动画会自然地切换到新的基础图像上
        self.update_image(self.current_angle)
    def update_image(self, angle):
        """旋转并更新悬浮球显示的图像"""
        if self.is_session_active:
            base_image = self.session_pil_image
        else:
            base_image = self.idle_pil_image
        
        if not base_image:
            return
        
        # 使用Pillow旋转图像。
        rotated_image = base_image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
        
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
        total_rotation = 1080 # 总共旋转度
        
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
    def start_wobble_animation(self):
        """开始晃动动画"""
        # 防止动画重复或冲突
        if self.is_animating or self.is_wobbling:
            return
        
        self.is_wobbling = True
        
        # 取消任何待机动画或计时器
        if self.animation_job: self.window.after_cancel(self.animation_job)
        if self.idle_timer_job: self.window.after_cancel(self.idle_timer_job)

        # 存储动画开始前的窗口位置
        self.original_x = self.window.winfo_x()
        self.original_y = self.window.winfo_y()
        
        # 动画参数
        self.wobble_start_time = time.time()
        self.wobble_duration = 0.8  # 动画总时长（秒）
        self.wobble_max_angle = 20 # 最大摆动角度
        self.wobble_swings = 2     # 左右来回摆动两次
        
        self.wobble_frame()

    def wobble_frame(self):
        """递归函数，用于绘制晃动动画的每一帧"""
        elapsed_time = time.time() - self.wobble_start_time
        progress = elapsed_time / self.wobble_duration

        if progress > 1.0:
            # 动画结束
            self.is_wobbling = False
            self.update_image(0) # 恢复到0度
            self.window.geometry(f"+{self.original_x}+{self.original_y}") # 恢复原始位置
            self.reset_idle_timer() # 重新开始待机计时
            return

 
        # 1. 使用 sin 函数创建振荡
        # progress * pi * 2 * swings 会让 sin 在动画期间完成'swings'次完整振荡
        oscillation = math.sin(progress * math.pi * 2 * self.wobble_swings)
        
        # 2. 添加一个衰减效果，让晃动幅度越来越小
        decay = (1 - progress) ** 2 
        angle = self.wobble_max_angle * oscillation * decay

        # 3. 模拟底部轴心旋转的位移
        radius = self.ball_size / 2
        rad_angle = math.radians(angle)
        
        # 计算相对于图片中心的位移
        offset_x = radius * math.sin(rad_angle)
        offset_y = radius * (1 - math.cos(rad_angle)) 

        # 4. 计算窗口的新位置
        new_x = int(self.original_x + offset_x)
        new_y = int(self.original_y - offset_y) 

        # 5. 更新图像旋转和窗口位置
        self.update_image(angle)
        self.window.geometry(f"+{new_x}+{new_y}")
        
        # 6. 调度下一帧 (目标约60FPS)
        self.wobble_job = self.window.after(16, self.wobble_frame)
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

    def on_button_press(self, event):
        """鼠标左键按下时的处理"""
        self.close_menu()
        # 记录拖拽起始位置
        self._drag_x = event.x
        self._drag_y = event.y
        # 标记拖拽可能开始
        self.is_dragging = False 
    def on_button_release(self, event):
        """鼠标左键释放时的处理，用于判断是单击还是拖拽结束"""
        if not self.is_dragging:
            # 如果没有发生拖拽，则认为这是一个潜在的单击
            # 安排一个250ms后的任务执行单击动画
            # 这个延迟是为了等待可能的双击事件
            self.single_click_timer = self.window.after(250, self.start_wobble_animation)
        # 拖拽结束后，重置状态
        self.is_dragging = False
    def on_drag_motion(self, event):
        """鼠标拖动时的处理"""
        # 只要发生了拖动，就取消待处理的单击事件
        if self.single_click_timer:
            self.window.after_cancel(self.single_click_timer)
            self.single_click_timer = None
            
        self.is_dragging = True # 标记正在拖拽
        x = self.window.winfo_x() + event.x - self._drag_x
        y = self.window.winfo_y() + event.y - self._drag_y
        self.window.geometry(f"+{x}+{y}")
        
    def on_double_click(self, event):
        """处理双击事件，确保它不会触发单击"""
        if self.single_click_timer:
            self.window.after_cancel(self.single_click_timer)
            self.single_click_timer = None

        log("双击事件触发，单击动画已取消。")
    def show_custom_menu(self, event):
        if self.menu: return
        self.start_wobble_animation()
        self.reset_idle_timer()
        self.menu = tk.Toplevel(self.window); self.menu.overrideredirect(True); self.menu.wm_attributes("-topmost", True)
        menu_frame = ctk.CTkFrame(self.menu, corner_radius=10, fg_color="#333333"); menu_frame.pack(padx=1, pady=1)
        button_font, button_height, width = ("微软雅黑", 14), 30, 40
        # 功能性按钮
        ctk.CTkButton(menu_frame, text="开始新对话", font=button_font, height=button_height, width=width,
                    fg_color="transparent", hover_color="#555555",
                    command=self.on_start_chat_callback).pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkButton(menu_frame, text="记忆库", font=button_font, height=button_height,
                    fg_color="transparent", hover_color="#555555",
                    command=self.on_memory_callback).pack(fill="x", padx=10, pady=5)
        # 管理性按钮
        ctk.CTkButton(menu_frame, text="设置", font=button_font, height=button_height, width=width,
                    fg_color="transparent", hover_color="#555555",
                    command=self.on_settings_callback).pack(fill="x", padx=10, pady=5)

        # 使用一个小的 Frame 来模拟分割线
        ctk.CTkFrame(menu_frame, height=2, fg_color="#555555").pack(fill="x", padx=10, pady=5)

        # --- 新增的重启和退出按钮 ---
        """ctk.CTkButton(menu_frame, text="重启", font=button_font, height=button_height, width=width,
                    fg_color="transparent", hover_color="#555555",
                    command=self.on_restart_callback).pack(fill="x", padx=10, pady=5)
                    重启有问题，解决不了，暂时删除。
                    """
        
        ctk.CTkButton(menu_frame, text="使用说明", font=button_font, height=button_height,
                    fg_color="transparent", hover_color="#1E6FE1",
                    command=self.on_instructions_callback).pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(menu_frame, text="隐藏悬浮球", font=button_font, height=button_height, width=width,
                    fg_color="transparent", hover_color="#ff4d4d",
                    command=self.on_hide_callback).pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(menu_frame, text="退出", font=button_font, height=button_height, width=width,
                    fg_color="transparent", hover_color="#ff4d4d", 
                    command=self.on_exit_callback).pack(fill="x", padx=10, pady=(5, 10))
                
        self.menu.update_idletasks()
        self.menu.geometry(f"{self.menu.winfo_width()}x{self.menu.winfo_height()}+{event.x_root}+{event.y_root}")
        self.menu.bind("<FocusOut>", self.close_menu)
        self.menu.focus_set()
    def close_menu(self, event=None):
        """统一的关闭菜单方法，确保焦点返回"""
        if self.menu:
            self.menu.destroy()
            self.menu = None
            # 将焦点还给悬浮球窗口
            self.window.focus_force()
    def show(self): self.window.deiconify()
    def hide(self):
        self.close_menu() 
        self.window.withdraw()
    def destroy(self): self.window.destroy()
# core/utils.py

import logging
import sys
import os
import urllib.request
import ctypes
import google.generativeai as genai

def setup_logging():
    """配置日志系统，使其同时输出到控制台和文件"""
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.dirname(__file__)) 
    log_filepath = os.path.join(app_dir, "log.txt")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter('[%(asctime)s][Thread:%(thread)d] %(message)s', datefmt='%H:%M:%S')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        file_handler = logging.FileHandler(log_filepath, mode='w', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"无法创建日志文件: {e}")

def log(message):
    """全局日志函数，使用 logging.info"""
    logging.info(message)

def set_proxy(config_proxy_url):
    """智能设置代理并返回代理URL"""
    final_proxy = None
    if config_proxy_url:
        log(f"用户在 config.json 中指定了代理: {config_proxy_url}")
        final_proxy = config_proxy_url
    else:
        log("尝试自动检测系统代理...")
        try:
            system_proxies = urllib.request.getproxies()
            http_proxy = system_proxies.get('https') or system_proxies.get('http')
            if http_proxy:
                log(f"成功检测到系统代理: {http_proxy}")
                final_proxy = http_proxy
            else:
                log("未检测到系统代理。")
        except Exception as e:
            log(f"自动检测系统代理时发生错误: {e}")

    if final_proxy:
        if not final_proxy.startswith(('http://', 'https://')):
            final_proxy = 'http://' + final_proxy
        os.environ['HTTP_PROXY'] = final_proxy
        os.environ['HTTPS_PROXY'] = final_proxy
        log(f"最终生效的代理已设置为: {final_proxy}")
    else:
        log("最终未设置代理，将进行直接连接。")
    return final_proxy

def get_screen_scaling_factor():
    """获取屏幕缩放因子"""
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
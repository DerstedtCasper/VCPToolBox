#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台进度条弹窗
支持显示下载进度、速度、剩余时间等信息
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import os
import sys
from pathlib import Path


class ProgressDialog:
    """跨平台进度条弹窗"""
    
    def __init__(self, title="下载进度", width=500, height=200):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(f"{width}x{height}")
        self.root.resizable(False, False)
        
        # 居中显示
        self.center_window(width, height)
        
        # 设置窗口图标（如果存在）
        self.set_window_icon()
        
        # 初始化变量
        self.cancelled = False
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.last_downloaded = 0
        self.current_speed = 0
        
        # 创建界面
        self.create_widgets()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def center_window(self, width, height):
        """将窗口居中显示"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def set_window_icon(self):
        """设置窗口图标"""
        try:
            # 尝试设置图标
            icon_path = Path(__file__).parent.parent.parent / "VCPLogo.png"
            if icon_path.exists():
                # 在Windows上可以直接使用PNG
                if sys.platform == "win32":
                    self.root.iconbitmap(default=str(icon_path))
                else:
                    # 在其他平台上使用PhotoImage
                    icon = tk.PhotoImage(file=str(icon_path))
                    self.root.iconphoto(True, icon)
        except Exception:
            # 如果设置图标失败，忽略错误
            pass
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题标签
        self.title_label = ttk.Label(
            main_frame, 
            text="准备下载...", 
            font=("Arial", 12, "bold")
        )
        self.title_label.pack(pady=(0, 10))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(pady=(0, 10))
        
        # 进度信息框架
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 进度百分比
        self.percent_label = ttk.Label(info_frame, text="0%")
        self.percent_label.pack(side=tk.LEFT)
        
        # 下载速度
        self.speed_label = ttk.Label(info_frame, text="速度: 0 KB/s")
        self.speed_label.pack(side=tk.RIGHT)
        
        # 详细信息框架
        detail_frame = ttk.Frame(main_frame)
        detail_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 已下载/总大小
        self.size_label = ttk.Label(detail_frame, text="0 MB / 0 MB")
        self.size_label.pack(side=tk.LEFT)
        
        # 剩余时间
        self.time_label = ttk.Label(detail_frame, text="剩余时间: --:--")
        self.time_label.pack(side=tk.RIGHT)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # 取消按钮
        self.cancel_button = ttk.Button(
            button_frame,
            text="取消下载",
            command=self.cancel_download
        )
        self.cancel_button.pack(side=tk.RIGHT)
        
        # 最小化按钮
        self.minimize_button = ttk.Button(
            button_frame,
            text="最小化",
            command=self.minimize_window
        )
        self.minimize_button.pack(side=tk.RIGHT, padx=(0, 10))
    
    def update_progress(self, current, total, filename="", speed_bytes_per_sec=0):
        """更新进度信息"""
        if self.cancelled:
            return
        
        try:
            # 计算进度百分比
            if total > 0:
                progress = (current / total) * 100
                self.progress_var.set(progress)
                self.percent_label.config(text=f"{progress:.1f}%")
            else:
                self.progress_var.set(0)
                self.percent_label.config(text="0%")
            
            # 更新标题
            if filename:
                display_name = filename
                if len(display_name) > 50:
                    display_name = display_name[:47] + "..."
                self.title_label.config(text=f"下载: {display_name}")
            
            # 更新大小信息
            current_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.size_label.config(text=f"{current_mb:.1f} MB / {total_mb:.1f} MB")
            
            # 更新速度信息
            if speed_bytes_per_sec > 0:
                self.current_speed = speed_bytes_per_sec
                if speed_bytes_per_sec >= 1024 * 1024:  # MB/s
                    speed_text = f"速度: {speed_bytes_per_sec / (1024 * 1024):.1f} MB/s"
                else:  # KB/s
                    speed_text = f"速度: {speed_bytes_per_sec / 1024:.1f} KB/s"
                self.speed_label.config(text=speed_text)
                
                # 计算剩余时间
                if current > 0 and speed_bytes_per_sec > 0:
                    remaining_bytes = total - current
                    remaining_seconds = remaining_bytes / speed_bytes_per_sec
                    
                    if remaining_seconds < 60:
                        time_text = f"剩余时间: {int(remaining_seconds)}秒"
                    elif remaining_seconds < 3600:
                        minutes = int(remaining_seconds // 60)
                        seconds = int(remaining_seconds % 60)
                        time_text = f"剩余时间: {minutes}:{seconds:02d}"
                    else:
                        hours = int(remaining_seconds // 3600)
                        minutes = int((remaining_seconds % 3600) // 60)
                        time_text = f"剩余时间: {hours}:{minutes:02d}:00"
                    
                    self.time_label.config(text=time_text)
            
            # 更新界面
            self.root.update_idletasks()
            
        except Exception as e:
            print(f"更新进度时出错: {e}")
    
    def cancel_download(self):
        """取消下载"""
        self.cancelled = True
        self.cancel_button.config(text="正在取消...", state="disabled")
        self.title_label.config(text="正在取消下载...")
    
    def minimize_window(self):
        """最小化窗口"""
        self.root.iconify()
    
    def on_close(self):
        """窗口关闭事件"""
        self.cancel_download()
    
    def is_cancelled(self):
        """检查是否已取消"""
        return self.cancelled
    
    def show_completion(self, success=True, message=""):
        """显示完成状态"""
        if success:
            self.title_label.config(text="下载完成！")
            self.progress_var.set(100)
            self.percent_label.config(text="100%")
            self.cancel_button.config(text="关闭", state="normal")
            self.cancel_button.config(command=self.close_window)
        else:
            self.title_label.config(text=f"下载失败: {message}")
            self.cancel_button.config(text="关闭", state="normal")
            self.cancel_button.config(command=self.close_window)
        
        self.root.update_idletasks()
    
    def show_error(self, error_message):
        """显示错误信息"""
        self.show_completion(success=False, message=error_message)
    
    def close_window(self):
        """关闭窗口"""
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
    
    def run_in_thread(self):
        """在线程中运行GUI"""
        try:
            self.root.mainloop()
        except:
            pass


class ProgressCallback:
    """进度回调类，用于与missAV API集成"""
    
    def __init__(self, dialog, filename=""):
        self.dialog = dialog
        self.filename = filename
        self.last_time = time.time()
        self.last_downloaded = 0
        self.speed_samples = []
        self.max_samples = 10  # 保留最近10个速度样本用于平滑
    
    def __call__(self, current, total, **kwargs):
        """进度回调函数"""
        if self.dialog.is_cancelled():
            # 如果用户取消了下载，抛出异常来中断下载
            raise KeyboardInterrupt("用户取消下载")
        
        # 计算下载速度
        current_time = time.time()
        time_diff = current_time - self.last_time
        
        if time_diff >= 0.5:  # 每0.5秒更新一次速度
            bytes_diff = current - self.last_downloaded
            speed = bytes_diff / time_diff if time_diff > 0 else 0
            
            # 添加到速度样本中
            self.speed_samples.append(speed)
            if len(self.speed_samples) > self.max_samples:
                self.speed_samples.pop(0)
            
            # 计算平均速度（平滑处理）
            avg_speed = sum(self.speed_samples) / len(self.speed_samples)
            
            # 更新进度
            self.dialog.update_progress(current, total, self.filename, avg_speed)
            
            self.last_time = current_time
            self.last_downloaded = current
        else:
            # 即使不更新速度，也要更新进度条
            self.dialog.update_progress(current, total, self.filename, 0)


def create_progress_dialog(title="下载进度"):
    """创建进度对话框"""
    return ProgressDialog(title)


def test_progress_dialog():
    """测试进度对话框"""
    import random
    
    dialog = create_progress_dialog("测试下载")
    
    def simulate_download():
        """模拟下载过程"""
        total_size = 100 * 1024 * 1024  # 100MB
        current_size = 0
        
        while current_size < total_size and not dialog.is_cancelled():
            # 模拟下载速度变化
            chunk_size = random.randint(512 * 1024, 2 * 1024 * 1024)  # 0.5-2MB
            current_size = min(current_size + chunk_size, total_size)
            
            # 模拟网络速度
            speed = random.randint(1024 * 1024, 5 * 1024 * 1024)  # 1-5MB/s
            
            dialog.update_progress(current_size, total_size, "test_video.mp4", speed)
            time.sleep(0.1)
        
        if not dialog.is_cancelled():
            dialog.show_completion(True)
        else:
            dialog.show_completion(False, "用户取消")
    
    # 在后台线程中模拟下载
    download_thread = threading.Thread(target=simulate_download)
    download_thread.daemon = True
    download_thread.start()
    
    # 运行GUI
    dialog.run_in_thread()


if __name__ == "__main__":
    test_progress_dialog()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步下载任务的进度跟踪和回调模块
"""

import os
import json
import time
import requests
from pathlib import Path

class ProgressTracker:
    def __init__(self, plugin_name: str, task_id: str, video_title: str):
        self.plugin_name = plugin_name
        self.task_id = task_id
        self.video_title = video_title
        
        # 从环境变量获取回调URL和结果目录
        self.callback_base_url = os.getenv("CALLBACK_BASE_URL")
        self.results_dir = Path(os.getenv("VCP_ASYNC_RESULTS_DIR", "./VCPAsyncResults"))
        
        # 确保结果目录存在
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.status_file = self.results_dir / f"{self.plugin_name}-{self.task_id}.json"
        
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.last_downloaded = 0

    def _write_status(self, status: str, message: str, progress: float = 0.0, speed: float = 0.0, eta: str = "N/A"):
        """将格式化的消息写入状态文件"""
        
        # 构建一个适合AI直接读取的文本消息
        formatted_message = f"任务 '{self.video_title}' (ID: {self.task_id}):\n"
        formatted_message += f"状态: {status}\n"
        formatted_message += f"信息: {message}\n"
        if status == "running":
            formatted_message += f"进度: {progress:.1f}%\n"
            formatted_message += f"速度: {speed / (1024*1024):.2f} MB/s\n"
            formatted_message += f"预计剩余时间: {eta}"

        # VCP_ASYNC_RESULT 机制期望文件内容是一个JSON对象，其中包含一个 message 字段
        output_data = {
            "message": formatted_message
        }

        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error writing status file: {e}")

    def start(self):
        """标记任务开始"""
        self._write_status("running", "下载已开始...")

    def update(self, current_bytes: int, total_bytes: int):
        """更新下载进度"""
        current_time = time.time()
        time_diff = current_time - self.last_update_time
        
        if time_diff < 1 and current_bytes < total_bytes: # 每秒最多更新一次
            return

        bytes_diff = current_bytes - self.last_downloaded
        speed = bytes_diff / time_diff if time_diff > 0 else 0
        
        progress = (current_bytes / total_bytes) * 100 if total_bytes > 0 else 0
        
        eta = "N/A"
        if speed > 0:
            remaining_bytes = total_bytes - current_bytes
            remaining_seconds = remaining_bytes / speed
            eta = time.strftime('%H:%M:%S', time.gmtime(remaining_seconds))

        message = f"正在下载: {progress:.1f}% - {speed / (1024*1024):.2f} MB/s"
        self._write_status("running", message, progress, speed, eta)
        
        self.last_update_time = current_time
        self.last_downloaded = current_bytes

    def complete(self, file_path: str):
        """标记任务成功完成"""
        message = f"下载成功！文件已保存到: {file_path}"
        self._write_status("success", message, 100)
        self._send_callback("Succeed", {"filePath": file_path, "message": message})

    def error(self, error_message: str):
        """标记任务失败"""
        self._write_status("error", f"下载失败: {error_message}")
        self._send_callback("Failed", {"reason": error_message})

    def _send_callback(self, status: str, data: dict):
        """向服务器发送最终回调"""
        if not self.callback_base_url:
            print("Error: CALLBACK_BASE_URL not set. Cannot send callback.")
            return

        callback_url = f"{self.callback_base_url}/{self.plugin_name}/{self.task_id}"
        payload = {
            "status": status,
            "taskId": self.task_id,
            "data": data
        }
        
        try:
            requests.post(callback_url, json=payload, timeout=10)
        except Exception as e:
            print(f"Error sending callback to {callback_url}: {e}")

    def progress_callback_handler(self, current, total, **kwargs):
        """用于 missav_api 的回调处理器"""
        self.update(current, total)
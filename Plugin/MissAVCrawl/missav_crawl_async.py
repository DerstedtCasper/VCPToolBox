#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MissAVCrawl Asynchronous VCP Plugin
"""

import sys
import json
import os
import uuid
import threading
import traceback
from pathlib import Path

# 确保可以导入项目内的模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from missav_crawl import MissAVCrawler  # 复用已有的下载器逻辑
from progress_tracker import ProgressTracker

def download_task(url: str, quality: str, download_dir: str, downloader: str, tracker: ProgressTracker):
    """后台下载线程执行的函数"""
    try:
        tracker.start()
        
        # 初始化下载器
        # 注意：这里我们不使用带GUI的crawler，而是基础版
        crawler = MissAVCrawler()
        
        # 获取视频对象以获取标题等信息
        video = crawler.client.get_video(url)
        
        # 下载视频，并传入我们的进度回调处理器
        success = video.download(
            quality=quality or crawler.quality,
            downloader=downloader or crawler.downloader,
            path=download_dir or crawler.download_dir,
            callback=tracker.progress_callback_handler
        )

        if success:
            safe_title = crawler._sanitize_filename(video.title)
            file_path = Path(download_dir or crawler.download_dir) / f"{safe_title}.mp4"
            tracker.complete(str(file_path.absolute()))
        else:
            tracker.error("下载过程返回失败状态，请检查日志。")

    except Exception as e:
        tracker.error(f"下载线程出现异常: {str(e)}\n{traceback.format_exc()}")

def handle_async_download(request_data: dict):
    """处理异步下载请求"""
    url = request_data.get('url')
    if not url:
        # 立即返回错误给服务器
        print(json.dumps({"status": "error", "error": "Missing url parameter."}))
        return

    # 提取可选参数
    quality = request_data.get('quality')
    download_dir = request_data.get('download_dir')
    downloader = request_data.get('downloader')

    # 生成唯一的 taskId
    task_id = str(uuid.uuid4())
    
    # 尝试预获取视频标题用于tracker
    try:
        temp_crawler = MissAVCrawler()
        video_title = temp_crawler.client.get_video(url).title
    except Exception:
        video_title = "未知视频"

    # 立即返回初始响应
    initial_response = {
        "status": "success",
        "result": {
            "message": f"已开始在后台下载视频 '{video_title}'。任务ID: {task_id}。你可以使用占位符 `{{{{VCP_ASYNC_RESULT::MissAVCrawl::{task_id}}}}}` 来跟踪此任务的进度。",
            "taskId": task_id,
            "placeholder": f"{{{{VCP_ASYNC_RESULT::MissAVCrawl::{task_id}}}}}"
        }
    }
    print(json.dumps(initial_response))
    sys.stdout.flush() # 确保响应被立即发送

    # 启动后台下载线程
    tracker = ProgressTracker(plugin_name="MissAVCrawl", task_id=task_id, video_title=video_title)
    
    download_thread = threading.Thread(
        target=download_task,
        args=(url, quality, download_dir, downloader, tracker)
    )
    download_thread.daemon = True # 设置为守护线程，主进程可以立即退出
    download_thread.start()

def main():
    """主函数 - 用于直接测试"""
    try:
        input_data = sys.stdin.read().strip()
        if not input_data:
            print(json.dumps({"status": "error", "error": "No input data received for testing."}), file=sys.stderr)
            return

        request_data = json.loads(input_data)
        command = request_data.get('command')

        if command == "DownloadVideoAsync":
            handle_async_download(request_data)
        else:
            print(json.dumps({"status": "error", "error": f"This script only tests DownloadVideoAsync. Received: {command}"}))

    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"插件测试执行失败: {str(e)}",
            "traceback": traceback.format_exc()
        }
        print(json.dumps(error_response))

if __name__ == "__main__":
    main()
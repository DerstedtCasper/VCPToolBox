#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Async Handler - Fixed Version
处理异步下载请求的核心模块 - 修复版本
使用完全同步的方法避免事件循环问题
"""

import json
import os
import sys
import threading
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from .config import ASMRConfig
from .progress_manager import ProgressManager

def get_file_size_from_structure(file_structure: Dict, filename: str) -> int:
    """从文件结构中递归查找文件大小"""
    def search_structure(structure):
        for key, value in structure.items():
            if value.get("type") == "file" and key == filename:
                return value.get("size", 0)
            elif value.get("type") == "folder" and "children" in value:
                size = search_structure(value["children"])
                if size > 0:
                    return size
        return 0
    
    return search_structure(file_structure)

def handle_async_download(request_data: Dict[str, Any]):
    """处理异步下载请求"""
    try:
        work_id = request_data.get('work_id', '')
        if not work_id:
            result = {
                "status": "error",
                "error": "Work ID is required for download"
            }
            print(json.dumps(result, ensure_ascii=False))
            sys.stdout.flush()
            return
        
        # 获取目标路径参数（可选）
        target_path = request_data.get('target_path', '')
        
        # 移除音质选择参数，始终使用最佳音质
        quality = 'best'
        
        # 生成唯一的任务ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # 构建下载范围描述
        download_scope = "全部内容" if not target_path else f"指定路径: {target_path}"
        
        # 立即返回初始响应
        initial_response = {
            "status": "success",
            "result": f"ASMR作品下载任务已提交 (ID: {task_id})\n"
                     f"作品ID: {work_id}\n"
                     f"下载范围: {download_scope}\n"
                     f"音质: 自动选择最佳音质\n"
                     f"任务正在后台处理中，请耐心等待...\n"
                     f"请在你的回复中包含以下占位符原文：{{{{VCP_ASYNC_RESULT::ASMRTools::{task_id}}}}}",
            "messageForAI": f"ASMR下载任务已提交，任务ID为 {task_id}。请告知用户耐心等待，下载结果将通过通知推送。"
        }
        
        print(json.dumps(initial_response, ensure_ascii=False))
        sys.stdout.flush()
        
        # 启动后台下载线程
        callback_base_url = os.getenv("CALLBACK_BASE_URL")
        plugin_name_for_callback = os.getenv("PLUGIN_NAME_FOR_CALLBACK")
        
        # 总是启动后台任务，即使没有callback配置
        download_thread = threading.Thread(
            target=background_download_task,
            args=(task_id, work_id, quality, callback_base_url, plugin_name_for_callback, target_path)
        )
        download_thread.daemon = False  # 不设置为守护线程，让主进程等待
        download_thread.start()
        
        if not callback_base_url or not plugin_name_for_callback:
            print("Warning: Callback configuration missing", file=sys.stderr)
        
        # 给后台线程一些时间启动
        time.sleep(1)
            
    except Exception as e:
        result = {
            "status": "error",
            "error": f"Failed to start download task: {str(e)}"
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.stdout.flush()

def background_download_task(task_id: str, work_id: str, quality: str, callback_base_url: Optional[str], plugin_name: Optional[str], target_path: str = ""):
    """后台下载任务 - 完全同步版本"""
    try:
        # 运行同步下载
        result = perform_download_sync(task_id, work_id, quality, target_path)
        
        # 发送回调（如果配置了的话）
        if callback_base_url and plugin_name:
            callback_url = f"{callback_base_url}/{plugin_name}/{task_id}"
            
            try:
                response = requests.post(callback_url, json=result, timeout=30)
                response.raise_for_status()
                print(f"Callback sent successfully for task {task_id}", file=sys.stderr)
            except requests.exceptions.RequestException as e:
                print(f"Failed to send callback for task {task_id}: {e}", file=sys.stderr)
        else:
            print(f"Download task {task_id} completed, no callback configured", file=sys.stderr)
            
    except Exception as e:
        # 发送错误回调（如果配置了的话）
        error_result = {
            "requestId": task_id,
            "status": "Failed",
            "pluginName": "ASMRTools",
            "reason": str(e),
            "message": f"ASMR作品下载失败 (ID: {task_id}): {str(e)}"
        }
        
        if callback_base_url and plugin_name:
            callback_url = f"{callback_base_url}/{plugin_name}/{task_id}"
            try:
                response = requests.post(callback_url, json=error_result, timeout=30)
                response.raise_for_status()
            except:
                pass
        
        print(f"Download task {task_id} failed: {e}", file=sys.stderr)

def perform_download_sync(task_id: str, work_id: str, quality: str, target_path: str = "") -> Dict[str, Any]:
    """执行实际的下载任务 - 完全同步版本"""
    progress_manager = None
    
    try:
        # 初始化进度管理器
        plugin_dir = os.path.dirname(os.path.dirname(__file__))
        progress_manager = ProgressManager(plugin_dir)
        
        # 更新开始状态
        progress_manager.update_starting(task_id, work_id)
        
        config = ASMRConfig.from_env()
        if not config.validate():
            if progress_manager:
                progress_manager.update_failed(task_id, "Invalid configuration: username and password are required")
            return {
                "requestId": task_id,
                "status": "Failed",
                "pluginName": "ASMRTools",
                "reason": "Invalid configuration: username and password are required",
                "message": f"ASMR作品下载失败 (ID: {task_id}): 配置无效"
            }
        
        # 确保下载目录存在
        config.ensure_download_path()
        
        # 使用同步方式获取作品信息
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        })
        
        # 登录获取token
        login_url = "https://api.asmr-200.com/api/auth/me"
        if config.api_channel:
            login_url = f"https://{config.api_channel}/api/auth/me"
        
        login_data = {
            "name": config.username,
            "password": config.password
        }
        
        # 登录
        response = session.post(login_url, json=login_data, verify=False)
        if response.status_code != 200:
            if progress_manager:
                progress_manager.update_failed(task_id, f"Login failed: {response.status_code}")
            return {
                "requestId": task_id,
                "status": "Failed",
                "pluginName": "ASMRTools",
                "reason": f"Login failed: {response.status_code}",
                "message": f"ASMR作品下载失败 (ID: {task_id}): 登录失败"
            }
        
        resp_json = response.json()
        token = resp_json["token"]
        session.headers.update({
            "Authorization": f"Bearer {token}",
        })
        
        # 获取作品信息
        clean_work_id = work_id.replace('RJ', '').replace('VJ', '').replace('BJ', '')
        work_url = f"https://api.asmr-200.com/api/work/{clean_work_id}"
        if config.api_channel:
            work_url = f"https://{config.api_channel}/api/work/{clean_work_id}"
        
        work_response = session.get(work_url, verify=False)
        if work_response.status_code != 200:
            if progress_manager:
                progress_manager.update_failed(task_id, f"Work not found: {work_id}")
            return {
                "requestId": task_id,
                "status": "Failed",
                "pluginName": "ASMRTools",
                "reason": f"Work not found: {work_id}",
                "message": f"ASMR作品下载失败 (ID: {task_id}): 作品不存在"
            }
        
        work_info = work_response.json()
        
        # 获取音轨列表
        tracks_url = f"https://api.asmr-200.com/api/tracks/{clean_work_id}?v=2"
        if config.api_channel:
            tracks_url = f"https://{config.api_channel}/api/tracks/{clean_work_id}?v=2"
        
        tracks_response = session.get(tracks_url, verify=False)
        if tracks_response.status_code != 200:
            if progress_manager:
                progress_manager.update_failed(task_id, "No tracks found for this work", work_info)
            return {
                "requestId": task_id,
                "status": "Failed",
                "pluginName": "ASMRTools",
                "reason": "No tracks found for this work",
                "message": f"ASMR作品下载失败 (ID: {task_id}): 没有找到音轨文件"
            }
        
        tracks = tracks_response.json()
        
        # 使用同步下载器
        from .sync_downloader_simple import SyncDownloaderSimple
        
        downloader = SyncDownloaderSimple(config, session)
        
        # 提取所有文件信息
        all_files = downloader._extract_files_from_tracks(tracks)
        
        # 如果指定了目标路径，过滤文件
        if target_path:
            all_files = downloader._filter_files_by_path(all_files, target_path)
        
        total_files = len(all_files)
        
        # 构建文件结构信息
        file_structure = downloader._build_file_structure(tracks)
        
        # 更新准备状态
        if progress_manager:
            scope_msg = f" (指定路径: {target_path})" if target_path else ""
            progress_manager.update_preparing(task_id, work_info, total_files, file_structure)
        
        # 计算总文件大小
        total_bytes = 0
        file_sizes = {}
        for file_info in all_files:
            # 从文件结构中获取文件大小
            file_size = get_file_size_from_structure(file_structure, file_info.get("filename", ""))
            file_sizes[file_info.get("filename", "")] = file_size
            total_bytes += file_size
        
        # 进度回调函数
        completed_files = 0
        current_file = ""
        completed_files_list = []
        downloaded_bytes = 0
        
        def progress_callback(progress_info):
            nonlocal completed_files, current_file, completed_files_list, downloaded_bytes
            
            # 更新当前文件信息
            if progress_info.get("status") in ["complete", "skipped"]:
                completed_files += 1
                filename = progress_info.get("filename", "")
                if filename and filename not in completed_files_list:
                    completed_files_list.append(filename)
                    # 累加已下载的字节数
                    downloaded_bytes += file_sizes.get(filename, 0)
            elif progress_info.get("status") == "active":
                # 对于正在下载的文件，计算部分下载的字节数
                filename = progress_info.get("filename", "")
                completed_length = progress_info.get("completed_length", 0)
                
                # 计算已完成文件的总大小 + 当前文件的已下载部分
                temp_downloaded_bytes = sum(file_sizes.get(f, 0) for f in completed_files_list)
                temp_downloaded_bytes += completed_length
                downloaded_bytes = temp_downloaded_bytes
            
            if progress_info.get("filename"):
                current_file = progress_info["filename"]
            
            # 基于文件大小计算总体进度
            if total_bytes > 0:
                overall_progress = (downloaded_bytes / total_bytes) * 100
            else:
                # 如果没有大小信息，回退到文件数量计算
                overall_progress = (completed_files / total_files) * 100 if total_files > 0 else 0
            
            # 更新进度
            if progress_manager:
                progress_manager.update_download_progress(
                    task_id=task_id,
                    work_info=work_info,
                    progress_percent=overall_progress,
                    download_speed=progress_info.get("download_speed", 0),
                    completed_files=completed_files,
                    total_files=total_files,
                    current_file=current_file,
                    completed_files_list=completed_files_list,
                    downloaded_bytes=downloaded_bytes,
                    total_bytes=total_bytes
                )
        
        # 开始下载
        download_result = downloader.download_tracks(tracks, work_info, progress_callback, target_path)
        
        # 关闭session
        session.close()
        
        # 更新最终状态
        if download_result["success_count"] > 0:
            # 更新成功状态
            if progress_manager:
                progress_manager.update_success(task_id, work_info, download_result)
            
            message = f"ASMR作品下载完成 (ID: {task_id})\n"
            message += f"作品: [{work_id}] {download_result['work_title']}\n"
            message += f"下载目录: {download_result['download_dir']}\n"
            message += f"成功下载: {download_result['success_count']}/{download_result['total_tracks']} 个文件\n"
            
            if download_result["failed_count"] > 0:
                message += f"失败文件: {download_result['failed_count']} 个\n"
                message += f"失败列表: {', '.join(download_result['failed_downloads'])}\n"
            
            message += f"下载的文件:\n"
            for filename in download_result["completed_downloads"]:
                message += f"- {filename}\n"
            
            result = {
                "requestId": task_id,
                "status": "Succeed",
                "pluginName": "ASMRTools",
                "workId": work_id,
                "workTitle": download_result['work_title'],
                "downloadDir": download_result['download_dir'],
                "totalTracks": download_result['total_tracks'],
                "successCount": download_result['success_count'],
                "failedCount": download_result['failed_count'],
                "completedFiles": download_result["completed_downloads"],
                "failedFiles": download_result["failed_downloads"],
                "message": message
            }
        else:
            # 更新失败状态
            if progress_manager:
                progress_manager.update_failed(task_id, "All downloads failed", work_info)
            result = {
                "requestId": task_id,
                "status": "Failed",
                "pluginName": "ASMRTools",
                "reason": "All downloads failed",
                "failedFiles": download_result["failed_downloads"],
                "message": f"ASMR作品下载失败 (ID: {task_id}): 所有文件下载失败"
            }
        
        return result
            
    except Exception as e:
        # 更新失败状态
        if progress_manager:
            progress_manager.update_failed(task_id, str(e))
        
        return {
            "requestId": task_id,
            "status": "Failed",
            "pluginName": "ASMRTools",
            "reason": str(e),
            "message": f"ASMR作品下载失败 (ID: {task_id}): {str(e)}"
        }
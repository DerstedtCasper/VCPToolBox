#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Progress Manager
管理异步下载进度的实时更新
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

class ProgressManager:
    """进度管理器"""
    
    def __init__(self, plugin_dir: str):
        self.plugin_dir = Path(plugin_dir)
        # 使用VCP系统的全局VCPAsyncResults目录
        # 从插件目录向上找到VCP根目录
        vcp_root = self.plugin_dir.parent.parent  # Plugin/ASMRTools -> Plugin -> VCP根目录
        self.results_dir = vcp_root / "VCPAsyncResults"
        self.results_dir.mkdir(exist_ok=True)
        
        # 从配置中获取进度更新间隔
        from .config import ASMRConfig
        config = ASMRConfig.from_env()
        self.update_interval = config.progress_update_interval
        self.last_update_time = 0
        
        # ETA计算相关
        self._start_time = 0
        self._progress_history = []  # 存储进度历史用于更准确的ETA计算
        self._completed_files_list = []  # 存储已完成文件列表
        self._file_structure = {}  # 存储文件结构信息
    
    def update_progress(self, task_id: str, status: str, **kwargs) -> None:
        """更新任务进度"""
        try:
            # 使用扁平结构，确保格式一致
            progress_data = {
                "requestId": task_id,
                "status": status,
                "pluginName": "ASMRTools",
                "type": "asmr_download_status",
                "timestamp": time.time(),
                **kwargs
            }
            
            # 写入进度文件，使用ASMRTools-{task_id}格式
            progress_file = self.results_dir / f"ASMRTools-{task_id}.json"
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Failed to update progress for task {task_id}: {e}", file=sys.stderr)
    
    def update_download_progress(self, task_id: str, work_info: Dict, progress_percent: float, 
                               download_speed: int, completed_files: int, total_files: int,
                               current_file: str = "", completed_files_list: list = None,
                               downloaded_bytes: int = 0, total_bytes: int = 0) -> None:
        """更新下载进度"""
        current_time = time.time()
        
        # 更新已完成文件列表
        if completed_files_list:
            self._completed_files_list = completed_files_list.copy()
        
        # 记录进度历史用于ETA计算（每次都记录，但ETA计算会过滤）
        self._progress_history.append({
            "time": current_time,
            "progress": progress_percent,
            "completed_files": completed_files,
            "downloaded_bytes": downloaded_bytes,
            "total_bytes": total_bytes
        })
        
        # 只保留最近15个进度点（增加历史点数以提高ETA准确性）
        if len(self._progress_history) > 15:
            self._progress_history = self._progress_history[-15:]
        
        # 检查是否需要更新文件（根据配置的时间间隔，但ETA计算不受限制）
        should_update_file = current_time - self.last_update_time >= self.update_interval
        
        # 强制更新：如果进度有显著变化或者是第一次更新
        if abs(progress_percent - getattr(self, '_last_progress', 0)) > 1.0 or not hasattr(self, '_last_progress'):
            should_update_file = True
            self._last_progress = progress_percent
        
        # 格式化下载速度
        if download_speed > 1024 * 1024:  # MB/s
            speed_str = f"{download_speed / (1024 * 1024):.1f} MB/s"
        elif download_speed > 1024:  # KB/s
            speed_str = f"{download_speed / 1024:.1f} KB/s"
        else:  # B/s
            speed_str = f"{download_speed} B/s"
        
        # 改进的ETA计算
        eta_str = self._calculate_eta(progress_percent, current_time)
        
        # 格式化文件大小
        def format_bytes(bytes_val):
            if bytes_val >= 1024 * 1024 * 1024:  # GB
                return f"{bytes_val / (1024 * 1024 * 1024):.1f} GB"
            elif bytes_val >= 1024 * 1024:  # MB
                return f"{bytes_val / (1024 * 1024):.1f} MB"
            elif bytes_val >= 1024:  # KB
                return f"{bytes_val / 1024:.1f} KB"
            else:
                return f"{bytes_val} B"
        
        # 构建更详细的消息
        message = f"🎵 正在下载ASMR作品: {work_info.get('title', 'Unknown')}\n"
        message += f"📊 进度: {progress_percent:.1f}% ({completed_files}/{total_files} 文件)\n"
        
        # 添加文件大小信息
        if total_bytes > 0:
            message += f"💾 大小: {format_bytes(downloaded_bytes)}/{format_bytes(total_bytes)}\n"
        
        message += f"⚡ 速度: {speed_str}\n"
        message += f"⏱️ 预计剩余: {eta_str}\n"
        if current_file:
            message += f"📁 当前文件: {current_file}\n"
        
        # 添加已完成文件的简要列表（最多显示3个最新的）
        if self._completed_files_list:
            recent_files = self._completed_files_list[-3:] if len(self._completed_files_list) > 3 else self._completed_files_list
            message += f"✅ 最近完成: {', '.join(recent_files)}"
            if len(self._completed_files_list) > 3:
                message += f" (共{len(self._completed_files_list)}个)"
        
        # 只在需要时更新文件
        if should_update_file:
            self.last_update_time = current_time
            
            self.update_progress(
                task_id=task_id,
                status="Downloading",
                workId=work_info.get('source_id', ''),
                workTitle=work_info.get('title', 'Unknown Work'),
                progress=progress_percent,
                downloadSpeed=speed_str,
                eta=eta_str,
                completedFiles=completed_files,
                totalFiles=total_files,
                currentFile=current_file,
                completedFilesList=self._completed_files_list,
                fileStructure=self._file_structure,
                downloadedBytes=downloaded_bytes,
                totalBytes=total_bytes,
                message=message
            )
    
    def _calculate_eta(self, current_progress: float, current_time: float) -> str:
        """计算更准确的ETA - 基于字节大小"""
        if current_progress <= 0 or current_progress >= 100:
            return "--:--"
        
        if len(self._progress_history) < 2:
            return "--:--"
        
        try:
            # 使用最近的进度点计算平均速度，优先使用字节数据
            recent_history = self._progress_history[-min(8, len(self._progress_history)):]
            
            if len(recent_history) < 2:
                return "--:--"
            
            # 计算总的时间差异
            total_time_diff = recent_history[-1]["time"] - recent_history[0]["time"]
            
            # 降低时间间隔要求，允许更快的ETA计算
            if total_time_diff < 3:  # 至少3秒的时间间隔
                return "--:--"
            
            # 优先使用字节数据计算ETA
            if (recent_history[-1].get("total_bytes", 0) > 0 and 
                recent_history[-1].get("downloaded_bytes", 0) > 0):
                
                # 基于字节的ETA计算
                bytes_diff = recent_history[-1]["downloaded_bytes"] - recent_history[0]["downloaded_bytes"]
                
                if bytes_diff > 0:
                    # 计算字节下载速度（字节/秒）
                    bytes_per_second = bytes_diff / total_time_diff
                    remaining_bytes = recent_history[-1]["total_bytes"] - recent_history[-1]["downloaded_bytes"]
                    
                    if remaining_bytes > 0:
                        eta_seconds = int(remaining_bytes / bytes_per_second)
                    else:
                        return "00:00"
                else:
                    # 如果字节数据不可用，回退到百分比计算
                    return self._calculate_eta_by_progress(recent_history, current_progress, total_time_diff)
            else:
                # 如果字节数据不可用，回退到百分比计算
                return self._calculate_eta_by_progress(recent_history, current_progress, total_time_diff)
            
            # 应用平滑因子，避免ETA跳跃过大
            if hasattr(self, '_last_eta_seconds') and self._last_eta_seconds > 0:
                # 如果新ETA与上次相差太大，使用加权平均
                if abs(eta_seconds - self._last_eta_seconds) > self._last_eta_seconds * 0.4:
                    eta_seconds = int(0.7 * self._last_eta_seconds + 0.3 * eta_seconds)
            
            self._last_eta_seconds = eta_seconds
            
            # 限制ETA显示范围，避免显示过大的数值
            if eta_seconds > 7200:  # 超过2小时
                return ">2h"
            elif eta_seconds > 3600:  # 超过1小时
                hours = eta_seconds // 3600
                minutes = (eta_seconds % 3600) // 60
                return f"{hours}h{minutes:02d}m"
            else:
                minutes = eta_seconds // 60
                seconds = eta_seconds % 60
                return f"{minutes:02d}:{seconds:02d}"
                
        except Exception as e:
            print(f"ETA calculation error: {e}", file=sys.stderr)
            return "--:--"
    
    def _calculate_eta_by_progress(self, recent_history, current_progress, total_time_diff):
        """基于进度百分比的ETA计算（备用方法）"""
        try:
            total_progress_diff = recent_history[-1]["progress"] - recent_history[0]["progress"]
            
            if total_progress_diff <= 0:
                return "--:--"
            
            # 计算进度变化率（每秒进度百分比）
            progress_rate = total_progress_diff / total_time_diff
            remaining_progress = 100 - current_progress
            
            if progress_rate <= 0:
                return "--:--"
            
            eta_seconds = int(remaining_progress / progress_rate)
            
            # 限制显示范围
            if eta_seconds > 7200:
                return ">2h"
            elif eta_seconds > 3600:
                hours = eta_seconds // 3600
                minutes = (eta_seconds % 3600) // 60
                return f"{hours}h{minutes:02d}m"
            else:
                minutes = eta_seconds // 60
                seconds = eta_seconds % 60
                return f"{minutes:02d}:{seconds:02d}"
                
        except Exception:
            return "--:--"
    
    def update_success(self, task_id: str, work_info: Dict, download_result: Dict) -> None:
        """更新成功状态"""
        message = f"ASMR作品下载完成: {work_info.get('title', 'Unknown')}\n"
        message += f"成功下载: {download_result['success_count']}/{download_result['total_tracks']} 个文件\n"
        message += f"下载目录: {download_result['download_dir']}"
        
        self.update_progress(
            task_id=task_id,
            status="Succeed",
            workId=work_info.get('source_id', ''),
            workTitle=work_info.get('title', 'Unknown Work'),
            progress=100.0,
            completedFiles=download_result['success_count'],
            totalFiles=download_result['total_tracks'],
            downloadDir=download_result['download_dir'],
            completedFilesList=download_result['completed_downloads'],
            failedFilesList=download_result['failed_downloads'],
            message=message
        )
    
    def update_failed(self, task_id: str, reason: str, work_info: Optional[Dict] = None) -> None:
        """更新失败状态"""
        message = f"ASMR作品下载失败 (ID: {task_id}): {reason}"
        
        update_data = {
            "task_id": task_id,
            "status": "Failed",
            "reason": reason,
            "message": message
        }
        
        if work_info:
            update_data.update({
                "workId": work_info.get('source_id', ''),
                "workTitle": work_info.get('title', 'Unknown Work')
            })
        
        self.update_progress(**update_data)
    
    def update_starting(self, task_id: str, work_id: str) -> None:
        """更新开始状态"""
        self._start_time = time.time()
        self._progress_history = []
        self._completed_files_list = []
        self._file_structure = {}
        self._last_eta_seconds = 0  # 重置ETA历史
        
        self.update_progress(
            task_id=task_id,
            status="Starting",
            workId=work_id,
            progress=0.0,
            eta="--:--",
            completedFiles=0,
            totalFiles=0,
            currentFile="",
            completedFilesList=[],
            fileStructure={},
            message=f"🚀 正在准备下载ASMR作品: {work_id}"
        )
    
    def update_preparing(self, task_id: str, work_info: Dict, total_files: int, file_structure: Dict = None) -> None:
        """更新准备状态"""
        if file_structure:
            self._file_structure = file_structure
            
        message = f"📋 正在准备下载: {work_info.get('title', 'Unknown')}\n"
        message += f"📁 找到 {total_files} 个文件"
        
        if file_structure:
            message += f"\n🗂️ 文件结构已分析完成"
        
        self.update_progress(
            task_id=task_id,
            status="Preparing",
            workId=work_info.get('source_id', ''),
            workTitle=work_info.get('title', 'Unknown Work'),
            progress=5.0,
            totalFiles=total_files,
            fileStructure=self._file_structure,
            message=message
        )
    
    def cleanup_progress_file(self, task_id: str) -> None:
        """清理进度文件（可选）"""
        try:
            progress_file = self.results_dir / f"ASMRTools-{task_id}.json"
            if progress_file.exists():
                # 可以选择删除或保留文件
                # progress_file.unlink()
                pass
        except Exception as e:
            print(f"Failed to cleanup progress file for task {task_id}: {e}", file=sys.stderr)

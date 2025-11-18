#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync Downloader Simple
简化的同步下载器，使用已有的requests session
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable

class SyncDownloaderSimple:
    """简化的同步下载器"""
    
    def __init__(self, config, session):
        self.config = config
        self.session = session
        
    def _extract_files_from_tracks(self, tracks: List[Dict], base_path: str = "") -> List[Dict]:
        """递归提取所有文件从嵌套的音轨结构"""
        files = []
        
        for track in tracks:
            if track.get("type") == "folder":
                # 如果是文件夹，递归处理子项
                track_title = track.get("title", "Unknown Folder")
                children = track.get("children", [])
                folder_path = f"{base_path}/{self._sanitize_filename(track_title)}" if base_path else self._sanitize_filename(track_title)
                files.extend(self._extract_files_from_tracks(children, folder_path))
            else:
                # 如果是文件，添加到列表
                file_info = {
                    "title": track.get("title", "Unknown File"),
                    "mediaDownloadUrl": track.get("mediaDownloadUrl", ""),
                    "path": base_path,
                    "filename": self._sanitize_filename(track.get("title", "Unknown File")),
                    "size": track.get("size", 0)  # 添加文件大小信息
                }
                files.append(file_info)
        
        return files
    
    def _build_file_structure(self, tracks: List[Dict], base_path: str = "") -> Dict:
        """构建文件结构树用于显示"""
        structure = {}
        
        for track in tracks:
            if track.get("type") == "folder":
                track_title = track.get("title", "Unknown Folder")
                children = track.get("children", [])
                folder_name = self._sanitize_filename(track_title)
                
                # 递归构建子结构
                child_structure = self._build_file_structure(children, f"{base_path}/{folder_name}" if base_path else folder_name)
                structure[folder_name] = {
                    "type": "folder",
                    "children": child_structure,
                    "file_count": self._count_files_in_structure(child_structure)
                }
            else:
                filename = self._sanitize_filename(track.get("title", "Unknown File"))
                structure[filename] = {
                    "type": "file",
                    "size": track.get("size", 0),
                    "url": track.get("mediaDownloadUrl", "")
                }
        
        return structure
    
    def _count_files_in_structure(self, structure: Dict) -> int:
        """计算结构中的文件数量"""
        count = 0
        for item in structure.values():
            if item["type"] == "file":
                count += 1
            elif item["type"] == "folder":
                count += item.get("file_count", 0)
        return count
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不合法字符"""
        import re
        # 移除或替换不合法字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip('. ')
        return filename if filename else "unnamed_file"
    
    def _filter_files_by_path(self, all_files: List[Dict], target_path: str) -> List[Dict]:
        """根据目标路径过滤文件"""
        filtered_files = []
        
        # 标准化目标路径（移除开头和结尾的斜杠）
        target_path = target_path.strip('/')
        
        for file_info in all_files:
            file_path = file_info.get("path", "")
            filename = file_info.get("filename", "")
            
            # 构建完整的文件路径
            if file_path:
                full_path = f"{file_path}/{filename}"
            else:
                full_path = filename
            
            # 检查是否匹配目标路径
            if self._path_matches(full_path, target_path):
                filtered_files.append(file_info)
        
        return filtered_files
    
    def _path_matches(self, file_path: str, target_path: str) -> bool:
        """检查文件路径是否匹配目标路径"""
        # 标准化路径
        file_path = file_path.strip('/')
        target_path = target_path.strip('/')
        
        # 如果目标路径为空，匹配所有文件
        if not target_path:
            return True
        
        # 精确匹配文件
        if file_path == target_path:
            return True
        
        # 检查是否在目标文件夹内
        if file_path.startswith(target_path + '/'):
            return True
        
        # 检查是否匹配文件夹
        file_dir = '/'.join(file_path.split('/')[:-1]) if '/' in file_path else ""
        if file_dir == target_path:
            return True
        
        return False
    
    def download_single_file(self, file_info: Dict, download_dir: Path, 
                           progress_callback: Optional[Callable] = None) -> bool:
        """下载单个文件"""
        try:
            url = file_info.get("mediaDownloadUrl", "")
            if not url:
                print(f"No download URL for file: {file_info.get('filename', 'Unknown')}")
                return False
            
            # 创建完整的文件路径
            file_path = file_info.get("path", "")
            filename = file_info.get("filename", "unknown_file")
            
            if file_path:
                full_dir = download_dir / file_path
                full_dir.mkdir(parents=True, exist_ok=True)
                full_file_path = full_dir / filename
            else:
                full_file_path = download_dir / filename
            
            # 如果文件已存在且大小合理，跳过下载
            if full_file_path.exists() and full_file_path.stat().st_size > 0:
                print(f"File already exists, skipping: {filename}")
                if progress_callback:
                    progress_callback({
                        "filename": filename,
                        "status": "skipped",  # 使用skipped状态而不是complete
                        "completed_length": full_file_path.stat().st_size,
                        "total_length": full_file_path.stat().st_size,
                        "download_speed": 0,
                        "progress_percent": 100
                    })
                return True
            
            print(f"Downloading: {filename}")
            
            # 开始下载，使用更大的chunk_size和timeout
            response = self.session.get(url, stream=True, verify=False, timeout=60)
            if response.status_code != 200:
                print(f"HTTP {response.status_code} for {filename}: {url}")
                return False
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            start_time = time.time()
            last_progress_time = 0
            
            # 创建文件并写入数据，使用更大的chunk_size提高性能
            with open(full_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):  # 64KB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 计算下载速度和进度
                        current_time = time.time()
                        elapsed_time = current_time - start_time
                        download_speed = int(downloaded_size / elapsed_time) if elapsed_time > 0 else 0
                        progress_percent = (downloaded_size / total_size * 100) if total_size > 0 else 0
                        
                        # 减少进度回调频率，只每2秒更新一次
                        if progress_callback and (current_time - last_progress_time >= 2.0):
                            progress_callback({
                                "filename": filename,
                                "status": "active",
                                "completed_length": downloaded_size,
                                "total_length": total_size,
                                "download_speed": download_speed,
                                "progress_percent": progress_percent
                            })
                            last_progress_time = current_time
            
            # 下载完成回调
            if progress_callback:
                progress_callback({
                    "filename": filename,
                    "status": "complete",
                    "completed_length": downloaded_size,
                    "total_length": total_size,
                    "download_speed": 0,
                    "progress_percent": 100
                })
            
            print(f"Downloaded successfully: {filename} ({downloaded_size} bytes)")
            return True
            
        except Exception as e:
            print(f"Download failed for {file_info.get('filename', 'Unknown')}: {e}")
            return False
    
    def download_tracks(self, tracks: List[Dict], work_info: Dict, 
                       progress_callback: Optional[Callable] = None, target_path: str = "") -> Dict:
        """下载作品的所有音轨"""
        work_id = work_info.get("source_id", "unknown")
        work_title = work_info.get("title", "Unknown Work")
        
        # 创建下载目录
        safe_title = self._sanitize_filename(work_title)
        download_dir = Path(self.config.download_path) / "asmr" / f"{work_id} - {safe_title}"
        download_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Download directory: {download_dir}")
        
        # 提取所有文件
        all_files = self._extract_files_from_tracks(tracks)
        
        # 如果指定了目标路径，过滤文件
        if target_path:
            filtered_files = self._filter_files_by_path(all_files, target_path)
            print(f"Found {len(all_files)} total files, filtering to {len(filtered_files)} files for path: {target_path}")
            all_files = filtered_files
        else:
            print(f"Found {len(all_files)} files to download")
        
        # 下载统计
        completed_downloads = []
        failed_downloads = []
        
        # 顺序下载所有文件
        for file_info in all_files:
            success = self.download_single_file(file_info, download_dir, progress_callback)
            if success:
                completed_downloads.append(file_info.get("filename", "unknown"))
            else:
                failed_downloads.append(file_info.get("filename", "unknown"))
        
        # 统计结果
        success_count = len(completed_downloads)
        failed_count = len(failed_downloads)
        
        return {
            "work_title": work_title,
            "download_dir": str(download_dir),
            "total_tracks": len(all_files),
            "success_count": success_count,
            "failed_count": failed_count,
            "completed_downloads": completed_downloads,
            "failed_downloads": failed_downloads
        }
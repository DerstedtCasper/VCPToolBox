#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MissAVCrawl VCP Plugin with Progress Dialog
基于 missAV API 的视频下载工具，支持进度条弹窗显示
"""

import sys
import json
import os
import traceback
import threading
import time
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import logging

# 导入进度条对话框
try:
    from progress_dialog import ProgressDialog, ProgressCallback
    PROGRESS_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入进度条模块: {e}", file=sys.stderr)
    PROGRESS_AVAILABLE = False


# 导入 missAV API 相关模块
def import_missav_api():
    """导入 missAV API 模块"""
    import_errors = []
    
    # 方法1: 尝试导入已安装的 missAV_api 包
    try:
        from missav_api import Client
        from base_api.modules.progress_bars import Callback
        return Client, Callback, "pip安装的missAV_api包"
    except ImportError as e:
        import_errors.append(f"pip包导入失败: {str(e)}")
    
    # 方法2: 尝试导入 eaf_base_api 和本地 missAV API
    try:
        from base_api import BaseCore
        from base_api.modules.progress_bars import Callback
        
        # 导入本地的 missAV API 代码
        current_dir = Path(__file__).parent
        missav_api_path = current_dir / "missav_api_core"
        
        if missav_api_path.exists():
            sys.path.insert(0, str(missav_api_path))
            from missav_api import Client
            return Client, Callback, f"本地源码导入: {missav_api_path}"
        else:
            raise ImportError(f"本地 missAV API 路径不存在: {missav_api_path}")
            
    except ImportError as e:
        import_errors.append(f"本地源码导入失败: {str(e)}")
    
    # 如果都失败了，抛出详细错误
    error_msg = "无法导入 missAV API 模块。尝试的方法:\n" + "\n".join(import_errors)
    raise ImportError(error_msg)


class MissAVCrawlerWithProgress:
    """MissAV 视频下载器（带进度条）"""
    
    def __init__(self):
        self.download_dir = os.getenv('MISSAV_DOWNLOAD_DIR', './downloads')
        self.quality = os.getenv('MISSAV_QUALITY', 'best')
        self.downloader = os.getenv('MISSAV_DOWNLOADER', 'threaded')
        self.proxy = os.getenv('MISSAV_PROXY', '')
        self.show_progress = os.getenv('MISSAV_SHOW_PROGRESS', 'true').lower() == 'true'
        
        # 确保下载目录存在
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
        
        # 初始化 missAV 客户端
        try:
            self.Client, self.Callback, import_source = import_missav_api()
            
            # 静默初始化客户端，避免日志输出
            stdout_backup = sys.stdout
            stderr_backup = sys.stderr
            
            try:
                sys.stdout = StringIO()
                sys.stderr = StringIO()
                self.client = self.Client()
            finally:
                sys.stdout = stdout_backup
                sys.stderr = stderr_backup
                
            self.import_info = f"成功导入 missAV API: {import_source}"
        except Exception as e:
            self.import_info = f"导入 missAV API 失败: {str(e)}"
            raise
    
    def get_video_info(self, url: str) -> dict:
        """获取视频信息"""
        try:
            # 重定向stdout和stderr，避免任何输出干扰JSON响应
            stdout_backup = sys.stdout
            stderr_backup = sys.stderr
            
            try:
                # 将stdout和stderr重定向到StringIO，捕获所有输出
                sys.stdout = StringIO()
                sys.stderr = StringIO()
                
                video = self.client.get_video(url)
                
                info = {
                    "title": video.title,
                    "video_code": video.video_code,
                    "publish_date": video.publish_date,
                    "thumbnail": video.thumbnail,
                    "m3u8_url": video.m3u8_base_url,
                    "url": url
                }
                
            finally:
                # 恢复stdout和stderr
                sys.stdout = stdout_backup
                sys.stderr = stderr_backup
            
            return {
                "success": True,
                "info": info,
                "message": "成功获取视频信息"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"获取视频信息失败: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    def silent_callback(self, current, total, speed=None):
        """静默的进度回调函数，不输出到stdout"""
        # 什么都不做，避免输出干扰JSON响应
        pass
    
    def download_video_with_progress(self, url: str, quality: str = None, 
                                   download_dir: str = None, downloader: str = None,
                                   show_progress: bool = None) -> dict:
        """下载视频（带进度条）"""
        try:
            # 使用传入的参数或默认配置
            quality = quality or self.quality
            download_dir = download_dir or self.download_dir
            downloader = downloader or self.downloader
            show_progress = show_progress if show_progress is not None else self.show_progress
            
            # 确保下载目录存在
            Path(download_dir).mkdir(parents=True, exist_ok=True)
            
            # 获取视频对象
            video = self.client.get_video(url)
            
            # 获取视频信息
            video_info = {
                "title": video.title,
                "video_code": video.video_code,
                "publish_date": video.publish_date
            }
            
            # 创建进度对话框
            progress_dialog = None
            progress_callback = None
            download_cancelled = False
            
            if show_progress and PROGRESS_AVAILABLE:
                try:
                    progress_dialog = ProgressDialog(f"下载视频: {video.title}")
                    progress_callback = ProgressCallback(progress_dialog, video.title)
                    
                    # 在后台线程中运行GUI
                    gui_thread = threading.Thread(target=progress_dialog.run_in_thread)
                    gui_thread.daemon = True
                    gui_thread.start()
                    
                    # 等待GUI初始化
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"创建进度对话框失败: {e}", file=sys.stderr)
                    progress_dialog = None
                    progress_callback = None
            
            # 重定向stdout和stderr，避免进度条输出干扰JSON响应
            stdout_backup = sys.stdout
            stderr_backup = sys.stderr
            
            try:
                # 将stdout和stderr重定向到StringIO，捕获所有输出
                sys.stdout = StringIO()
                sys.stderr = StringIO()
                
                # 选择回调函数
                callback = progress_callback if progress_callback else self.silent_callback
                
                # 下载视频
                success = video.download(
                    quality=quality,
                    downloader=downloader,
                    path=download_dir,
                    callback=callback
                )
                
            except KeyboardInterrupt:
                # 用户取消下载
                download_cancelled = True
                success = False
            finally:
                # 恢复stdout和stderr
                sys.stdout = stdout_backup
                sys.stderr = stderr_backup
            
            # 更新进度对话框状态
            if progress_dialog:
                if download_cancelled:
                    progress_dialog.show_completion(False, "用户取消下载")
                elif success:
                    progress_dialog.show_completion(True)
                else:
                    progress_dialog.show_completion(False, "下载失败")
                
                # 等待用户关闭对话框或自动关闭
                time.sleep(2)
                try:
                    progress_dialog.close_window()
                except:
                    pass
            
            if download_cancelled:
                return {
                    "success": False,
                    "video_info": video_info,
                    "error": "下载被用户取消"
                }
            
            if success:
                # 构建文件路径
                safe_title = self._sanitize_filename(video.title)
                file_path = Path(download_dir) / f"{safe_title}.mp4"
                
                return {
                    "success": True,
                    "video_info": video_info,
                    "file_path": str(file_path),
                    "download_dir": download_dir,
                    "quality": quality,
                    "message": f"视频下载成功: {video.title}"
                }
            else:
                return {
                    "success": False,
                    "video_info": video_info,
                    "error": "下载失败，请检查网络连接或视频URL"
                }
                
        except Exception as e:
            # 如果有进度对话框，显示错误
            if 'progress_dialog' in locals() and progress_dialog:
                progress_dialog.show_error(str(e))
                time.sleep(2)
                try:
                    progress_dialog.close_window()
                except:
                    pass
            
            return {
                "success": False,
                "error": f"下载视频失败: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    def download_video(self, url: str, quality: str = None, download_dir: str = None, 
                      downloader: str = None) -> dict:
        """下载视频（兼容原版接口）"""
        return self.download_video_with_progress(url, quality, download_dir, downloader, False)
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不安全字符"""
        import re
        # 移除或替换不安全的字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除前后空格
        filename = filename.strip()
        # 限制长度
        if len(filename) > 200:
            filename = filename[:200]
        return filename


def process_request(request_data: dict) -> dict:
    """处理请求"""
    try:
        command = request_data.get('command', '').strip()
        
        if not command:
            return {
                "status": "error",
                "error": "缺少 command 参数"
            }
        
        # 初始化爬虫
        crawler = MissAVCrawlerWithProgress()
        
        if command == "GetVideoInfo":
            url = request_data.get('url', '').strip()
            if not url:
                return {
                    "status": "error",
                    "error": "缺少 url 参数"
                }
            
            result = crawler.get_video_info(url)
            
            if result["success"]:
                info = result["info"]
                response_text = f"""### MissAV 视频信息 ###

标题: {info['title']}
视频代码: {info['video_code']}
发布日期: {info['publish_date']}
缩略图: {info['thumbnail']}
M3U8 URL: {info['m3u8_url']}
原始URL: {info['url']}

视频信息获取成功！"""
                
                return {
                    "status": "success",
                    "result": response_text
                }
            else:
                return {
                    "status": "error",
                    "error": result["error"]
                }
        
        elif command == "DownloadVideo":
            url = request_data.get('url', '').strip()
            if not url:
                return {
                    "status": "error",
                    "error": "缺少 url 参数"
                }
            
            quality = request_data.get('quality', '').strip()
            download_dir = request_data.get('download_dir', '').strip()
            downloader = request_data.get('downloader', '').strip()
            
            result = crawler.download_video(
                url=url,
                quality=quality if quality else None,
                download_dir=download_dir if download_dir else None,
                downloader=downloader if downloader else None
            )
            
            if result["success"]:
                info = result["video_info"]
                response_text = f"""### MissAV 视频下载完成 ###

标题: {info['title']}
视频代码: {info['video_code']}
发布日期: {info['publish_date']}
文件路径: {result['file_path']}
下载目录: {result['download_dir']}
视频质量: {result['quality']}

视频下载成功！文件已保存到指定目录。"""
                
                return {
                    "status": "success",
                    "result": response_text
                }
            else:
                error_msg = result.get("error", "未知错误")
                if "video_info" in result:
                    info = result["video_info"]
                    error_msg += f"\n视频信息: {info['title']} ({info['video_code']})"
                
                return {
                    "status": "error",
                    "error": error_msg
                }
        
        elif command == "DownloadVideoWithProgress":
            url = request_data.get('url', '').strip()
            if not url:
                return {
                    "status": "error",
                    "error": "缺少 url 参数"
                }
            
            quality = request_data.get('quality', '').strip()
            download_dir = request_data.get('download_dir', '').strip()
            downloader = request_data.get('downloader', '').strip()
            show_progress = request_data.get('show_progress', True)
            
            result = crawler.download_video_with_progress(
                url=url,
                quality=quality if quality else None,
                download_dir=download_dir if download_dir else None,
                downloader=downloader if downloader else None,
                show_progress=show_progress
            )
            
            if result["success"]:
                info = result["video_info"]
                response_text = f"""### MissAV 视频下载完成（带进度条）###

标题: {info['title']}
视频代码: {info['video_code']}
发布日期: {info['publish_date']}
文件路径: {result['file_path']}
下载目录: {result['download_dir']}
视频质量: {result['quality']}

视频下载成功！文件已保存到指定目录。
进度条已显示下载过程。"""
                
                return {
                    "status": "success",
                    "result": response_text
                }
            else:
                error_msg = result.get("error", "未知错误")
                if "video_info" in result:
                    info = result["video_info"]
                    error_msg += f"\n视频信息: {info['title']} ({info['video_code']})"
                
                return {
                    "status": "error",
                    "error": error_msg
                }
        
        else:
            return {
                "status": "error",
                "error": f"未知命令: {command}"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "error": f"处理请求时发生错误: {str(e)}",
            "traceback": traceback.format_exc()
        }


def main():
    """主函数"""
    try:
        # 读取标准输入
        input_data = sys.stdin.read().strip()
        
        if not input_data:
            result = {
                "status": "error",
                "error": "没有接收到输入数据"
            }
        else:
            try:
                # 解析JSON输入
                request_data = json.loads(input_data)
                result = process_request(request_data)
            except json.JSONDecodeError as e:
                result = {
                    "status": "error",
                    "error": f"JSON解析失败: {str(e)}"
                }
    
    except Exception as e:
        result = {
            "status": "error",
            "error": f"插件执行失败: {str(e)}",
            "traceback": traceback.format_exc()
        }
    
    # 输出结果
    print(json.dumps(result, ensure_ascii=False), file=sys.stdout)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
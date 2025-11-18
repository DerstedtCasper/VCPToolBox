#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MissAVCrawl VCP Plugin
基于 missAV API 的视频下载工具
"""

import sys
import json
import os
import traceback
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import logging

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


class MissAVCrawler:
    """MissAV 视频下载器"""
    
    def __init__(self):
        self.download_dir = os.getenv('MISSAV_DOWNLOAD_DIR', './downloads')
        self.quality = os.getenv('MISSAV_QUALITY', 'best')
        self.downloader = os.getenv('MISSAV_DOWNLOADER', 'threaded')
        self.proxy = os.getenv('MISSAV_PROXY', '')
        
        # 确保下载目录存在
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
        
        # 尝试初始化 missAV 客户端
        self.client = None
        self.Client = None
        self.Callback = None
        
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
            self.api_available = True
        except Exception as e:
            self.import_info = f"导入 missAV API 失败: {str(e)}"
            self.api_available = False
            # 不再抛出异常，允许插件继续工作
    
    def get_video_info(self, url: str) -> dict:
        """获取视频信息"""
        if not self.api_available or not self.client:
            return {
                "success": False,
                "error": "missAV API 不可用，无法获取视频信息"
            }
            
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
    
    def search_videos(self, keyword: str, page: int = 1, sort: str = None, 
                     include_cover: bool = True, include_title: bool = True,
                     max_results: int = 20, max_pages: int = 1) -> dict:
        """
        增强版搜索视频功能
        
        Args:
            keyword: 搜索关键词
            page: 起始页码（从1开始）
            sort: 排序方式 - saved(收藏数), today_views(日流量), weekly_views(周流量), 
                  monthly_views(月流量), views(总流量), updated(最近更新), released_at(发行日期)
            include_cover: 是否返回视频封面图片URL
            include_title: 是否返回视频完整标题
            max_results: 每页最大结果数量
            max_pages: 最大搜索页数
        """
        if not self.api_available or not self.client:
            return {
                "success": False,
                "keyword": keyword,
                "page": page,
                "error": "missAV API 不可用，无法搜索视频",
                "results": []
            }
            
        try:
            # 重定向stdout和stderr，避免任何输出干扰JSON响应
            stdout_backup = sys.stdout
            stderr_backup = sys.stderr
            
            try:
                # 将stdout和stderr重定向到StringIO，捕获所有输出
                sys.stdout = StringIO()
                sys.stderr = StringIO()
                
                # 使用增强版客户端搜索视频，带重试机制
                result = self.client.search_videos_enhanced_with_retry(
                    keyword=keyword, 
                    page=page, 
                    sort=sort,
                    include_cover=include_cover,
                    include_title=include_title,
                    max_results=max_results,
                    max_pages=max_pages
                )
                
            finally:
                # 恢复stdout和stderr
                sys.stdout = stdout_backup
                sys.stderr = stderr_backup
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "keyword": keyword,
                "page": page,
                "error": f"搜索视频失败: {str(e)}",
                "results": [],
                "traceback": traceback.format_exc()
            }
    
    def get_hot_videos(self, category: str = "daily", page: int = 1) -> dict:
        """获取热榜视频"""
        if not self.api_available or not self.client:
            return {
                "success": False,
                "category": category,
                "page": page,
                "error": "missAV API 不可用，无法获取热榜视频",
                "results": []
            }
            
        try:
            # 重定向stdout和stderr，避免任何输出干扰JSON响应
            stdout_backup = sys.stdout
            stderr_backup = sys.stderr
            
            try:
                # 将stdout和stderr重定向到StringIO，捕获所有输出
                sys.stdout = StringIO()
                sys.stderr = StringIO()
                
                # 使用客户端获取热榜视频
                result = self.client.get_hot_videos(category, page)
                
            finally:
                # 恢复stdout和stderr
                sys.stdout = stdout_backup
                sys.stderr = stderr_backup
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "category": category,
                "page": page,
                "error": f"获取热榜失败: {str(e)}",
                "results": [],
                "traceback": traceback.format_exc()
            }
    
    def download_video(self, url: str, quality: str = None, download_dir: str = None, 
                      downloader: str = None) -> dict:
        """下载视频"""
        if not self.api_available or not self.client:
            return {
                "success": False,
                "error": "missAV API 不可用，无法下载视频"
            }
            
        try:
            # 使用传入的参数或默认配置
            quality = quality or self.quality
            download_dir = download_dir or self.download_dir
            downloader = downloader or self.downloader
            
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
            
            # 重定向stdout和stderr，避免进度条输出干扰JSON响应
            stdout_backup = sys.stdout
            stderr_backup = sys.stderr
            
            try:
                # 将stdout和stderr重定向到StringIO，捕获所有输出
                sys.stdout = StringIO()
                sys.stderr = StringIO()
                
                # 下载视频，使用静默回调
                success = video.download(
                    quality=quality,
                    downloader=downloader,
                    path=download_dir,
                    callback=self.silent_callback
                )
                
            finally:
                # 恢复stdout和stderr
                sys.stdout = stdout_backup
                sys.stderr = stderr_backup
            
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
            return {
                "success": False,
                "error": f"下载视频失败: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
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
        crawler = MissAVCrawler()
        
        if command == "GetVideoInfo":
            url = request_data.get('url', '') or ''
            if isinstance(url, str):
                url = url.strip()
            else:
                url = str(url).strip() if url is not None else ''
            if not url:
                return {
                    "status": "error",
                    "error": "缺少 url 参数"
                }
            
            result = crawler.get_video_info(url)
            
            if result["success"]:
                info = result["info"]
                response_text = f"""### MissAV 视频信息 ###

标题**: {info['title']}
视频代码**: {info['video_code']}
发布日期**: {info['publish_date']}
缩略图**: {info['thumbnail']}
M3U8 URL**: {info['m3u8_url']}
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
            url = request_data.get('url', '') or ''
            if isinstance(url, str):
                url = url.strip()
            else:
                url = str(url).strip() if url is not None else ''
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
        
        elif command == "SearchVideos":
            keyword = request_data.get('keyword', '') or ''
            if isinstance(keyword, str):
                keyword = keyword.strip()
            else:
                keyword = str(keyword).strip() if keyword is not None else ''
            if not keyword:
                return {
                    "status": "error",
                    "error": "缺少 keyword 参数"
                }
            
            # 处理页码参数
            page = request_data.get('page', 1)
            try:
                page = int(page) if page else 1
                if page < 1:
                    page = 1
            except (ValueError, TypeError):
                page = 1
            
            # 处理排序参数
            sort = request_data.get('sort', '').strip()
            valid_sorts = ['saved', 'today_views', 'weekly_views', 'monthly_views', 'views', 'updated', 'released_at']
            if sort and sort not in valid_sorts:
                sort = None
            
            # 处理封面图片参数
            include_cover = request_data.get('include_cover', True)
            if isinstance(include_cover, str):
                include_cover = include_cover.lower() in ['true', '1', 'yes', 'on']
            
            # 处理标题参数
            include_title = request_data.get('include_title', True)
            if isinstance(include_title, str):
                include_title = include_title.lower() in ['true', '1', 'yes', 'on']
            
            # 处理最大结果数参数
            max_results = request_data.get('max_results', 20)
            try:
                max_results = int(max_results) if max_results else 20
                if max_results < 1:
                    max_results = 20
                elif max_results > 100:
                    max_results = 100
            except (ValueError, TypeError):
                max_results = 20
            
            # 处理最大页数参数
            max_pages = request_data.get('max_pages', 1)
            try:
                max_pages = int(max_pages) if max_pages else 1
                if max_pages < 1:
                    max_pages = 1
                elif max_pages > 10:
                    max_pages = 10
            except (ValueError, TypeError):
                max_pages = 1
            
            result = crawler.search_videos(
                keyword=keyword, 
                page=page, 
                sort=sort,
                include_cover=include_cover,
                include_title=include_title,
                max_results=max_results,
                max_pages=max_pages
            )
            
            if result["success"]:
                results = result["results"]
                
                # 构建排序说明
                sort_desc = ""
                if sort:
                    sort_names = {
                        'saved': '收藏数',
                        'today_views': '日流量',
                        'weekly_views': '周流量',
                        'monthly_views': '月流量',
                        'views': '总流量',
                        'updated': '最近更新',
                        'released_at': '发行日期'
                    }
                    sort_desc = f"排序方式: {sort_names.get(sort, sort)}\n"
                
                response_text = f"""### MissAV 增强搜索结果 ###

搜索关键词: {keyword}
页码范围: {page} - {page + max_pages - 1}
{sort_desc}找到视频数量: {result['total_count']}
实际页数: {result.get('actual_pages', 1)}

"""
                
                if results:
                    response_text += "搜索结果:\n\n"
                    display_count = min(len(results), 15)  # 最多显示15个结果
                    
                    for i, video in enumerate(results[:display_count], 1):
                        response_text += f"{i}. **{video['title']}**\n"
                        response_text += f"   视频代码: {video['video_code']}\n"
                        response_text += f"   链接: {video['url']}\n"
                        
                        if include_cover and video.get('thumbnail'):
                            response_text += f"   封面图片: {video['thumbnail']}\n"
                        
                        if include_title and video.get('full_title') and video.get('full_title') != video.get('title'):
                            response_text += f"   完整标题: {video['full_title']}\n"
                        
                        if video.get('publish_date'):
                            response_text += f"   发布日期: {video['publish_date']}\n"
                        
                        if video.get('views'):
                            response_text += f"   观看次数: {video['views']}\n"
                        
                        response_text += "\n"
                    
                    if len(results) > display_count:
                        response_text += f"... 还有 {len(results) - display_count} 个结果未显示\n"
                else:
                    response_text += "未找到相关视频。\n"
                
                response_text += "\n搜索完成！"
                
                return {
                    "status": "success",
                    "result": response_text
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("error", "搜索失败")
                }
        
        elif command == "GetHotVideos":
            category = request_data.get('category', 'daily') or 'daily'
            if isinstance(category, str):
                category = category.strip().lower()
            else:
                category = str(category).strip().lower() if category is not None else 'daily'
            
            # 验证分类参数
            valid_categories = ['daily', 'weekly', 'monthly', 'new', 'popular', 'trending']
            if category not in valid_categories:
                category = 'daily'
            
            page = request_data.get('page', 1)
            try:
                page = int(page) if page else 1
                if page < 1:
                    page = 1
            except (ValueError, TypeError):
                page = 1
            
            # 尝试使用原有的热榜功能，如果失败则使用独立热榜
            result = None
            
            # 如果crawler可用，尝试使用原有功能
            if crawler and hasattr(crawler, 'get_hot_videos'):
                try:
                    result = crawler.get_hot_videos(category, page)
                    
                    # 如果原有功能失败或返回空结果，使用独立热榜
                    if not result.get("success") or not result.get("results"):
                        result = None
                        
                except Exception:
                    result = None
            
            # 如果原有功能不可用，使用独立热榜功能
            if result is None:
                try:
                    from standalone_hot_videos import StandaloneMissAVHotVideos
                    standalone_hot_videos = StandaloneMissAVHotVideos()
                    result = standalone_hot_videos.get_hot_videos(category, page)
                except Exception as standalone_error:
                    # 如果独立热榜也失败，返回错误
                    return {
                        "status": "error",
                        "error": f"热榜功能不可用: {str(standalone_error)}"
                    }
            
            if result["success"]:
                results = result["results"]
                category_name = {
                    'daily': '每日热门',
                    'weekly': '每周热门', 
                    'monthly': '每月热门',
                    'new': '最新视频',
                    'popular': '最受欢迎',
                    'trending': '趋势视频'
                }.get(category, '热门视频')
                
                response_text = f"""### MissAV {category_name} ###

分类: {category_name}
页码: {page}
视频数量: {result['total_count']}

"""
                
                if results:
                    response_text += "热榜视频:\n\n"
                    for i, video in enumerate(results[:15], 1):  # 最多显示15个结果
                        response_text += f"{i}. **{video['title']}**\n"
                        response_text += f"   视频代码: {video['video_code']}\n"
                        response_text += f"   链接: {video['url']}\n"
                        if video.get('thumbnail'):
                            response_text += f"   缩略图: {video['thumbnail']}\n"
                        if video.get('duration'):
                            response_text += f"   时长: {video['duration']}\n"
                        if video.get('publish_date'):
                            response_text += f"   发布日期: {video['publish_date']}\n"
                        response_text += "\n"
                    
                    if len(results) > 15:
                        response_text += f"... 还有 {len(results) - 15} 个视频未显示\n"
                else:
                    response_text += "暂无热榜视频。\n"
                
                # 添加数据源信息
                if result.get("source") == "generated_data" or result.get("source") == "mock_data":
                    response_text += f"\n💡 {result.get('note', '当前显示的是高质量模拟数据')}\n"
                
                response_text += "\n热榜获取完成！"
                
                return {
                    "status": "success",
                    "result": response_text
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("error", "获取热榜失败")
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
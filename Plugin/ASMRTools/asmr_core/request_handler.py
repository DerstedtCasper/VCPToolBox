#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Request Handler
处理同步请求的核心模块
"""

import asyncio
import json
from typing import Dict, Any

from .config import ASMRConfig
from .asmr_api import ASMRAPIClient

def format_bytes(bytes_val: int) -> str:
    """格式化字节数"""
    if bytes_val >= 1024 * 1024 * 1024:  # GB
        return f"{bytes_val / (1024 * 1024 * 1024):.1f} GB"
    elif bytes_val >= 1024 * 1024:  # MB
        return f"{bytes_val / (1024 * 1024):.1f} MB"
    elif bytes_val >= 1024:  # KB
        return f"{bytes_val / 1024:.1f} KB"
    else:
        return f"{bytes_val} B"

def format_file_structure(structure: Dict, indent: str = "") -> str:
    """格式化文件结构为树状显示"""
    result = ""
    items = list(structure.items())
    
    for i, (name, item) in enumerate(items):
        is_last = i == len(items) - 1
        current_indent = "└── " if is_last else "├── "
        
        if item.get("type") == "folder":
            file_count = item.get("file_count", 0)
            result += f"{indent}{current_indent}📁 {name}/ ({file_count} 文件)\n"
            
            # 递归显示子项
            if "children" in item:
                next_indent = indent + ("    " if is_last else "│   ")
                result += format_file_structure(item["children"], next_indent)
        else:
            file_size = item.get("size", 0)
            result += f"{indent}{current_indent}📄 {name} ({format_bytes(file_size)})\n"
    
    return result

def process_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """处理同步请求"""
    try:
        command = request_data.get('command')
        
        if command == "SearchWorks":
            return asyncio.run(handle_search_works(request_data))
        elif command == "GetWorkInfo":
            return asyncio.run(handle_get_work_info(request_data))
        elif command == "GetRecommendations":
            return asyncio.run(handle_get_recommendations(request_data))
        elif command == "GetPopularWorks":
            return asyncio.run(handle_get_popular_works(request_data))
        else:
            return {
                "status": "error",
                "error": f"Unknown command: {command}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": f"Request processing failed: {str(e)}"
        }

async def handle_search_works(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """处理搜索作品请求"""
    try:
        config = ASMRConfig.from_env()
        if not config.validate():
            return {
                "status": "error",
                "error": "Invalid configuration: username and password are required"
            }
        
        keyword = request_data.get('keyword', '')
        if not keyword:
            return {
                "status": "error",
                "error": "Keyword is required for search"
            }
        
        # 解析过滤器参数
        filters = {}
        if 'tags' in request_data and request_data['tags']:
            filters['tags'] = request_data['tags']
        if 'no_tags' in request_data and request_data['no_tags']:
            filters['no_tags'] = request_data['no_tags']
        if 'circle' in request_data and request_data['circle']:
            filters['circle'] = request_data['circle']
        if 'age' in request_data and request_data['age']:
            filters['age'] = request_data['age']
        
        limit = int(request_data.get('limit', 20))
        
        async with ASMRAPIClient(config) as client:
            works = await client.search_works(keyword, **filters)
            
            # 限制返回结果数量
            if limit > 0:
                works = works[:limit]
            
            # 格式化结果
            formatted_works = []
            for work in works:
                # 获取社团名称
                circle_name = ""
                if work.get("circle"):
                    circle_name = work["circle"].get("name", "")
                elif work.get("circle_name"):
                    circle_name = work["circle_name"]
                
                # 构建DLSite链接
                dlsite_url = ""
                asmr_one_url = ""
                if work.get("source_id"):
                    work_id = work["source_id"]
                    dlsite_url = f"https://www.dlsite.com/maniax/work/=/product_id/{work_id}.html"
                    asmr_one_url = f"https://asmr.one/work/{work_id}"
                
                formatted_work = {
                    "id": work.get("source_id", ""),
                    "title": work.get("title", ""),
                    "circle_name": circle_name,
                    "release_date": work.get("release", ""),
                    "age_category": work.get("age_category_string", ""),
                    "has_subtitle": work.get("has_subtitle", False),
                    "rating": work.get("rate_average_2dp", 0),
                    "review_count": work.get("review_count", 0),
                    "price": work.get("price", 0),
                    "tags": [tag.get("name", "") for tag in work.get("tags", [])],
                    "vas": [va.get("name", "") for va in work.get("vas", [])],
                    "cover_url": work.get("mainCoverUrl", ""),
                    "thumbnail_url": work.get("thumbnailCoverUrl", ""),
                    "dlsite_url": dlsite_url,
                    "asmr_one_url": asmr_one_url
                }
                formatted_works.append(formatted_work)
            
            result_text = f"搜索关键词: {keyword}\n"
            result_text += f"找到 {len(formatted_works)} 个作品:\n\n"
            
            for i, work in enumerate(formatted_works, 1):
                result_text += f"{i}. [{work['id']}] {work['title']}\n"
                result_text += f"   社团: {work['circle_name']}\n"
                result_text += f"   发布日期: {work['release_date']}\n"
                result_text += f"   评分: {work['rating']:.2f} ({work['review_count']}评价)\n"
                result_text += f"   价格: {work['price']}円\n"
                result_text += f"   年龄分级: {work['age_category']}\n"
                result_text += f"   字幕: {'有' if work['has_subtitle'] else '无'}\n"
                if work['cover_url']:
                    result_text += f"   封面图片: {work['cover_url']}\n"
                if work['asmr_one_url']:
                    result_text += f"   ASMR.one链接: {work['asmr_one_url']}\n"
                if work['dlsite_url']:
                    result_text += f"   DLSite链接: {work['dlsite_url']}\n"
                if work['tags']:
                    result_text += f"   标签: {', '.join(work['tags'][:5])}\n"
                if work['vas']:
                    result_text += f"   声优: {', '.join(work['vas'][:3])}\n"
                result_text += "\n"
            
            return {
                "status": "success",
                "result": result_text
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": f"Search failed: {str(e)}"
        }

async def handle_get_work_info(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """处理获取作品信息请求"""
    try:
        config = ASMRConfig.from_env()
        if not config.validate():
            return {
                "status": "error",
                "error": "Invalid configuration: username and password are required"
            }
        
        work_id = request_data.get('work_id', '')
        if not work_id:
            return {
                "status": "error",
                "error": "Work ID is required"
            }
        
        async with ASMRAPIClient(config) as client:
            work_info = await client.get_work_info(work_id)
            
            if not work_info:
                return {
                    "status": "error",
                    "error": f"Work not found: {work_id}"
                }
            
            # 获取音轨信息
            tracks = await client.get_work_tracks(work_id)
            
            # 格式化结果
            result_text = f"作品信息: {work_id}\n\n"
            result_text += f"标题: {work_info.get('title', 'N/A')}\n"
            
            # 获取社团名称
            circle_name = "N/A"
            if work_info.get("circle"):
                circle_name = work_info["circle"].get("name", "N/A")
            elif work_info.get("circle_name"):
                circle_name = work_info["circle_name"]
            result_text += f"社团: {circle_name}\n"
            result_text += f"发布日期: {work_info.get('release', 'N/A')}\n"
            result_text += f"年龄分级: {work_info.get('age_category_string', 'N/A')}\n"
            result_text += f"评分: {work_info.get('rate_average_2dp', 0):.2f} ({work_info.get('review_count', 0)}评价)\n"
            result_text += f"价格: {work_info.get('price', 0)}円\n"
            result_text += f"销量: {work_info.get('dl_count', 0)}\n"
            result_text += f"字幕: {'有' if work_info.get('has_subtitle') else '无'}\n"
            
            # 添加封面图片信息
            if work_info.get('mainCoverUrl'):
                result_text += f"封面图片: {work_info.get('mainCoverUrl')}\n"
            if work_info.get('thumbnailCoverUrl'):
                result_text += f"缩略图: {work_info.get('thumbnailCoverUrl')}\n"
            
            # 添加网址链接
            if work_info.get('source_id'):
                work_id_for_url = work_info['source_id']
                result_text += f"ASMR.one链接: https://asmr.one/work/{work_id_for_url}\n"
                result_text += f"DLSite链接: https://www.dlsite.com/maniax/work/=/product_id/{work_id_for_url}.html\n"
            
            # 标签信息
            tags = work_info.get('tags', [])
            if tags:
                result_text += f"标签: {', '.join([tag.get('name', '') for tag in tags])}\n"
            
            # 声优信息
            vas = work_info.get('vas', [])
            if vas:
                result_text += f"声优: {', '.join([va.get('name', '') for va in vas])}\n"
            
            # 文件结构和大小信息
            if tracks:
                # 构建文件结构
                from .sync_downloader_simple import SyncDownloaderSimple
                
                # 创建一个临时的下载器实例来构建文件结构
                temp_config = ASMRConfig.from_env()
                temp_downloader = SyncDownloaderSimple(temp_config, None)
                
                # 提取所有文件信息
                all_files = temp_downloader._extract_files_from_tracks(tracks)
                file_structure = temp_downloader._build_file_structure(tracks)
                
                # 计算总大小
                total_size = sum(file_info.get('size', 0) for file_info in all_files)
                
                result_text += f"\n📊 文件统计:\n"
                result_text += f"文件总数: {len(all_files)} 个\n"
                result_text += f"总大小: {format_bytes(total_size)}\n"
                
                # 显示文件结构
                result_text += f"\n📁 文件结构:\n"
                result_text += format_file_structure(file_structure, "")
                
                # 显示最大的几个文件
                if all_files:
                    sorted_files = sorted(all_files, key=lambda x: x.get('size', 0), reverse=True)
                    largest_files = sorted_files[:5]
                    
                    result_text += f"\n📈 最大的文件:\n"
                    for i, file_info in enumerate(largest_files, 1):
                        file_size = file_info.get('size', 0)
                        percentage = (file_size / total_size * 100) if total_size > 0 else 0
                        result_text += f"{i}. {file_info.get('filename', 'Unknown')} - {format_bytes(file_size)} ({percentage:.1f}%)\n"
            
            # 简介
            if work_info.get('intro'):
                result_text += f"\n简介:\n{work_info.get('intro')}\n"
            
            return {
                "status": "success",
                "result": result_text
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": f"Get work info failed: {str(e)}"
        }

async def handle_get_recommendations(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """处理获取推荐作品请求"""
    try:
        config = ASMRConfig.from_env()
        if not config.validate():
            return {
                "status": "error",
                "error": "Invalid configuration: username and password are required"
            }
        
        limit = int(request_data.get('limit', 10))
        
        async with ASMRAPIClient(config) as client:
            works = await client.get_recommendations()
            
            if limit > 0:
                works = works[:limit]
            
            result_text = f"推荐作品 ({len(works)}个):\n\n"
            
            for i, work in enumerate(works, 1):
                # 获取社团名称
                circle_name = ""
                if work.get("circle"):
                    circle_name = work["circle"].get("name", "")
                elif work.get("circle_name"):
                    circle_name = work["circle_name"]
                
                result_text += f"{i}. [{work.get('source_id', '')}] {work.get('title', '')}\n"
                result_text += f"   社团: {circle_name}\n"
                result_text += f"   评分: {work.get('rate_average_2dp', 0):.2f}\n"
                result_text += f"   价格: {work.get('price', 0)}円\n"
                if work.get('mainCoverUrl'):
                    result_text += f"   封面图片: {work.get('mainCoverUrl')}\n"
                if work.get('source_id'):
                    work_id = work['source_id']
                    result_text += f"   ASMR.one链接: https://asmr.one/work/{work_id}\n"
                    result_text += f"   DLSite链接: https://www.dlsite.com/maniax/work/=/product_id/{work_id}.html\n"
                result_text += "\n"
            
            return {
                "status": "success",
                "result": result_text
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": f"Get recommendations failed: {str(e)}"
        }

async def handle_get_popular_works(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """处理获取热门作品请求"""
    try:
        config = ASMRConfig.from_env()
        if not config.validate():
            return {
                "status": "error",
                "error": "Invalid configuration: username and password are required"
            }
        
        limit = int(request_data.get('limit', 10))
        
        async with ASMRAPIClient(config) as client:
            works = await client.get_popular_works()
            
            if limit > 0:
                works = works[:limit]
            
            result_text = f"热门作品 ({len(works)}个):\n\n"
            
            for i, work in enumerate(works, 1):
                # 获取社团名称
                circle_name = ""
                if work.get("circle"):
                    circle_name = work["circle"].get("name", "")
                elif work.get("circle_name"):
                    circle_name = work["circle_name"]
                
                result_text += f"{i}. [{work.get('source_id', '')}] {work.get('title', '')}\n"
                result_text += f"   社团: {circle_name}\n"
                result_text += f"   评分: {work.get('rate_average_2dp', 0):.2f}\n"
                result_text += f"   下载量: {work.get('dl_count', 0)}\n"
                result_text += f"   价格: {work.get('price', 0)}円\n"
                if work.get('mainCoverUrl'):
                    result_text += f"   封面图片: {work.get('mainCoverUrl')}\n"
                if work.get('source_id'):
                    work_id = work['source_id']
                    result_text += f"   ASMR.one链接: https://asmr.one/work/{work_id}\n"
                    result_text += f"   DLSite链接: https://www.dlsite.com/maniax/work/=/product_id/{work_id}.html\n"
                result_text += "\n"
            
            return {
                "status": "success",
                "result": result_text
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": f"Get popular works failed: {str(e)}"
        }
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MissAV 搜索功能实现分析和测试
"""

import sys
import re
import requests
from pathlib import Path
from urllib.parse import quote, urljoin
from typing import List, Dict, Optional

# 添加当前目录到 Python 路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "missav_api_core"))

from consts import HEADERS


class MissAVSearcher:
    """MissAV 搜索器"""
    
    def __init__(self):
        self.base_url = "https://missav.ws"
        self.headers = HEADERS.copy()
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_videos(self, keyword: str, page: int = 1) -> Dict:
        """
        搜索视频
        
        Args:
            keyword: 搜索关键词
            page: 页码（从1开始）
            
        Returns:
            包含搜索结果的字典
        """
        try:
            # 构造搜索URL
            search_url = f"{self.base_url}/search/{quote(keyword)}"
            if page > 1:
                search_url += f"?page={page}"
            
            print(f"搜索URL: {search_url}")
            
            # 发送请求
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            # 解析搜索结果
            results = self._parse_search_results(response.text, keyword)
            
            return {
                "success": True,
                "keyword": keyword,
                "page": page,
                "results": results,
                "total_count": len(results),
                "message": f"找到 {len(results)} 个相关视频"
            }
            
        except Exception as e:
            return {
                "success": False,
                "keyword": keyword,
                "page": page,
                "error": f"搜索失败: {str(e)}",
                "results": []
            }
    
    def _parse_search_results(self, html_content: str, keyword: str) -> List[Dict]:
        """解析搜索结果页面"""
        results = []
        
        try:
            # 搜索视频卡片的正则表达式模式
            # 基于常见的视频网站结构，寻找包含链接、标题、缩略图的模式
            
            # 模式1: 寻找视频链接
            video_link_pattern = r'<a[^>]*href="([^"]*)"[^>]*>.*?</a>'
            video_links = re.findall(video_link_pattern, html_content, re.DOTALL)
            
            # 过滤出视频页面链接（通常包含视频代码）
            video_urls = []
            for link in video_links:
                if self._is_video_url(link):
                    if link.startswith('/'):
                        link = urljoin(self.base_url, link)
                    video_urls.append(link)
            
            # 移除重复链接
            video_urls = list(set(video_urls))
            
            # 为每个视频URL提取更多信息
            for url in video_urls[:20]:  # 限制最多20个结果
                video_info = self._extract_video_info_from_url(url, html_content)
                if video_info:
                    results.append(video_info)
            
            # 如果上述方法没有找到结果，尝试其他解析方法
            if not results:
                results = self._parse_alternative_format(html_content)
            
        except Exception as e:
            print(f"解析搜索结果时出错: {str(e)}")
        
        return results
    
    def _is_video_url(self, url: str) -> bool:
        """判断是否是视频页面URL"""
        # 视频URL通常包含视频代码模式
        video_patterns = [
            r'/[a-zA-Z]+-\d+',  # 如 /abc-123
            r'/[a-zA-Z0-9]+-[a-zA-Z0-9]+',  # 如 /ofje-505
            r'/\d+',  # 纯数字
        ]
        
        for pattern in video_patterns:
            if re.search(pattern, url):
                return True
        
        # 排除非视频页面
        exclude_patterns = [
            '/search/', '/category/', '/tag/', '/actress/',
            '/studio/', '/series/', '/page/', '/login',
            '/register', '/contact', '/about', '.css', '.js',
            '.png', '.jpg', '.gif', '.ico'
        ]
        
        for exclude in exclude_patterns:
            if exclude in url:
                return False
        
        return False
    
    def _extract_video_info_from_url(self, url: str, html_content: str) -> Optional[Dict]:
        """从URL和HTML内容中提取视频信息"""
        try:
            # 从URL提取视频代码
            video_code = self._extract_video_code_from_url(url)
            
            # 在HTML中查找对应的视频信息
            video_info = {
                "url": url,
                "video_code": video_code,
                "title": "",
                "thumbnail": "",
                "duration": "",
                "publish_date": ""
            }
            
            # 尝试从HTML中提取标题
            title_patterns = [
                rf'<[^>]*href="{re.escape(url)}"[^>]*>([^<]+)</a>',
                rf'<[^>]*title="([^"]*)"[^>]*href="{re.escape(url)}"',
                rf'alt="([^"]*)"[^>]*.*?href="{re.escape(url)}"'
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    video_info["title"] = match.group(1).strip()
                    break
            
            # 如果没有找到标题，使用视频代码作为标题
            if not video_info["title"]:
                video_info["title"] = video_code or "未知标题"
            
            # 尝试提取缩略图
            thumbnail_patterns = [
                rf'<img[^>]*src="([^"]*)"[^>]*.*?href="{re.escape(url)}"',
                rf'href="{re.escape(url)}"[^>]*.*?<img[^>]*src="([^"]*)"'
            ]
            
            for pattern in thumbnail_patterns:
                match = re.search(pattern, html_content, re.DOTALL)
                if match:
                    thumbnail = match.group(1)
                    if thumbnail.startswith('/'):
                        thumbnail = urljoin(self.base_url, thumbnail)
                    video_info["thumbnail"] = thumbnail
                    break
            
            return video_info
            
        except Exception as e:
            print(f"提取视频信息时出错: {str(e)}")
            return None
    
    def _extract_video_code_from_url(self, url: str) -> str:
        """从URL中提取视频代码"""
        # 从URL路径中提取视频代码
        path = url.split('/')[-1]
        
        # 移除查询参数
        if '?' in path:
            path = path.split('?')[0]
        
        return path
    
    def _parse_alternative_format(self, html_content: str) -> List[Dict]:
        """尝试其他格式的解析方法"""
        results = []
        
        try:
            # 方法1: 寻找包含视频信息的JSON数据
            json_pattern = r'<script[^>]*>.*?(\{.*?"videos".*?\}).*?</script>'
            json_matches = re.findall(json_pattern, html_content, re.DOTALL)
            
            for json_str in json_matches:
                try:
                    import json
                    data = json.loads(json_str)
                    if 'videos' in data:
                        for video in data['videos']:
                            results.append({
                                "url": video.get('url', ''),
                                "video_code": video.get('code', ''),
                                "title": video.get('title', ''),
                                "thumbnail": video.get('thumbnail', ''),
                                "duration": video.get('duration', ''),
                                "publish_date": video.get('date', '')
                            })
                except:
                    continue
            
            # 方法2: 基于常见的HTML结构模式
            if not results:
                # 寻找视频卡片容器
                card_pattern = r'<div[^>]*class="[^"]*video[^"]*"[^>]*>(.*?)</div>'
                cards = re.findall(card_pattern, html_content, re.DOTALL | re.IGNORECASE)
                
                for card in cards:
                    # 从每个卡片中提取信息
                    url_match = re.search(r'href="([^"]*)"', card)
                    title_match = re.search(r'title="([^"]*)"', card)
                    img_match = re.search(r'src="([^"]*)"', card)
                    
                    if url_match:
                        url = url_match.group(1)
                        if url.startswith('/'):
                            url = urljoin(self.base_url, url)
                        
                        if self._is_video_url(url):
                            results.append({
                                "url": url,
                                "video_code": self._extract_video_code_from_url(url),
                                "title": title_match.group(1) if title_match else "",
                                "thumbnail": img_match.group(1) if img_match else "",
                                "duration": "",
                                "publish_date": ""
                            })
            
        except Exception as e:
            print(f"备用解析方法出错: {str(e)}")
        
        return results


def test_search_functionality():
    """测试搜索功能"""
    print("=== 测试 MissAV 搜索功能 ===")
    
    searcher = MissAVSearcher()
    
    # 测试搜索
    test_keywords = ["OFJE", "SSIS", "STARS"]
    
    for keyword in test_keywords:
        print(f"\n搜索关键词: {keyword}")
        result = searcher.search_videos(keyword)
        
        if result["success"]:
            print(f"✅ 搜索成功，找到 {result['total_count']} 个结果")
            
            # 显示前3个结果
            for i, video in enumerate(result["results"][:3]):
                print(f"  {i+1}. {video['title']}")
                print(f"     URL: {video['url']}")
                print(f"     代码: {video['video_code']}")
                if video['thumbnail']:
                    print(f"     缩略图: {video['thumbnail'][:50]}...")
        else:
            print(f"❌ 搜索失败: {result['error']}")


def analyze_test_video():
    """分析测试视频页面结构"""
    print("\n=== 分析测试视频页面结构 ===")
    
    test_url = "https://missav.ws/ofje-505"
    
    try:
        response = requests.get(test_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        content = response.text
        
        print(f"页面长度: {len(content)} 字符")
        
        # 分析页面结构
        print("\n页面结构分析:")
        
        # 查找标题
        title_patterns = [
            r'<title>([^<]+)</title>',
            r'<h1[^>]*>([^<]+)</h1>',
            r'<h2[^>]*>([^<]+)</h2>'
        ]
        
        for pattern in title_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                print(f"  标题模式 '{pattern}': {matches[:3]}")
        
        # 查找视频代码
        code_patterns = [
            r'OFJE-505',
            r'ofje-505',
            r'[A-Z]+-\d+',
            r'[a-z]+-\d+'
        ]
        
        for pattern in code_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                print(f"  代码模式 '{pattern}': {len(matches)} 个匹配")
        
        # 查找链接结构
        link_pattern = r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
        links = re.findall(link_pattern, content)
        
        video_links = [link for link in links if 'ofje' in link[0].lower() or 'ssis' in link[0].lower()]
        print(f"  相关视频链接: {len(video_links)} 个")
        
        if video_links:
            for i, (url, text) in enumerate(video_links[:3]):
                print(f"    {i+1}. {url} -> {text[:30]}...")
        
    except Exception as e:
        print(f"❌ 分析失败: {str(e)}")


if __name__ == "__main__":
    # 分析测试视频页面
    analyze_test_video()
    
    # 测试搜索功能
    test_search_functionality()
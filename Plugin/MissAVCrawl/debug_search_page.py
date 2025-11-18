#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试搜索页面结构
"""

import sys
import re
import requests
from pathlib import Path
from urllib.parse import quote

# 添加当前目录到 Python 路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "missav_api_core"))

from consts import HEADERS


def analyze_search_page_structure():
    """分析搜索页面的实际结构"""
    print("=== 分析搜索页面结构 ===")
    
    # 测试不同的搜索URL格式
    base_url = "https://missav.ws"
    test_keywords = ["OFJE-505", "SSIS"]
    
    for keyword in test_keywords:
        print(f"\n--- 分析关键词: {keyword} ---")
        
        # 尝试不同的搜索URL格式
        search_urls = [
            f"{base_url}/search/{quote(keyword)}",
            f"{base_url}/search?q={quote(keyword)}",
            f"{base_url}/cn/search/{quote(keyword)}",
            f"{base_url}/en/search/{quote(keyword)}",
        ]
        
        for search_url in search_urls:
            print(f"\n测试URL: {search_url}")
            
            try:
                response = requests.get(search_url, headers=HEADERS, timeout=30)
                print(f"状态码: {response.status_code}")
                
                if response.status_code == 200:
                    content = response.text
                    print(f"页面长度: {len(content)} 字符")
                    
                    # 分析页面结构
                    analyze_page_content(content, keyword)
                    break  # 找到有效页面就停止
                    
            except Exception as e:
                print(f"请求失败: {str(e)}")


def analyze_page_content(content: str, keyword: str):
    """分析页面内容结构"""
    print("\n页面内容分析:")
    
    # 1. 查找可能的视频容器
    container_patterns = [
        r'<div[^>]*class="[^"]*(?:video|item|card|result)[^"]*"[^>]*>',
        r'<article[^>]*class="[^"]*(?:video|item)[^"]*"[^>]*>',
        r'<li[^>]*class="[^"]*(?:video|item)[^"]*"[^>]*>',
    ]
    
    for pattern in container_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            print(f"  找到容器模式 '{pattern}': {len(matches)} 个")
            if matches:
                print(f"    示例: {matches[0][:100]}...")
    
    # 2. 查找所有链接
    all_links = re.findall(r'href="([^"]*)"', content)
    print(f"  总链接数: {len(all_links)}")
    
    # 3. 分析链接类型
    video_like_links = []
    other_links = []
    
    for link in all_links:
        if any(pattern in link.lower() for pattern in [
            keyword.lower(), 'ssis', 'ofje', 'stars'
        ]):
            video_like_links.append(link)
        else:
            other_links.append(link)
    
    print(f"  可能的视频链接: {len(video_like_links)}")
    print(f"  其他链接: {len(other_links)}")
    
    # 4. 显示可能的视频链接
    if video_like_links:
        print("\n  可能的视频链接示例:")
        for i, link in enumerate(video_like_links[:10]):
            print(f"    {i+1}. {link}")
    
    # 5. 显示其他链接的类型分布
    if other_links:
        print("\n  其他链接类型分析:")
        link_types = {}
        for link in other_links[:50]:  # 只分析前50个
            if '/search/' in link:
                link_types['搜索'] = link_types.get('搜索', 0) + 1
            elif '/category/' in link or '/tag/' in link:
                link_types['分类'] = link_types.get('分类', 0) + 1
            elif '/actress/' in link:
                link_types['演员'] = link_types.get('演员', 0) + 1
            elif any(ext in link for ext in ['.css', '.js', '.woff', '.png', '.jpg']):
                link_types['资源文件'] = link_types.get('资源文件', 0) + 1
            elif 'uncensored' in link or 'subtitle' in link or 'hot' in link:
                link_types['分类页面'] = link_types.get('分类页面', 0) + 1
            else:
                link_types['其他'] = link_types.get('其他', 0) + 1
        
        for link_type, count in link_types.items():
            print(f"    {link_type}: {count}")
    
    # 6. 查找可能的视频代码模式
    print("\n  视频代码模式分析:")
    video_code_patterns = [
        r'[A-Z]{2,6}-\d{2,4}',
        r'\d{2,4}[A-Z]{2,6}-\d{2,4}',
        r'FC2-PPV-\d{6,8}',
    ]
    
    for pattern in video_code_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            unique_matches = list(set(matches))
            print(f"    模式 '{pattern}': {len(unique_matches)} 个唯一匹配")
            for match in unique_matches[:5]:
                print(f"      - {match}")


def test_improved_url_filtering():
    """测试改进后的URL过滤"""
    print("\n=== 测试改进后的URL过滤 ===")
    
    from missav_api import Client
    client = Client()
    
    # 从实际搜索结果中提取的URL示例
    test_urls = [
        "/san-374-uncensored-leak",
        "/laby-003", 
        "/san-376-uncensored-leak",
        "/halant-v8-latin-500.woff2",
        "/uncensored-leak",
        "/monthly-hot",
        "/sdam-148-uncensored-leak",
        "/dm621/uncensored-leak",
        "/laby-003-uncensored-leak",
        "/chinese-subtitle",
        "/ofje-505",  # 这个应该被识别为视频
        "/ssis-950",  # 这个应该被识别为视频
    ]
    
    print("URL过滤测试:")
    for url in test_urls:
        is_video = client._is_video_url(url)
        status = "✅ 视频" if is_video else "❌ 非视频"
        print(f"  {status} {url}")


def main():
    """主函数"""
    print("搜索页面结构调试工具")
    print("=" * 50)
    
    # 分析搜索页面结构
    analyze_search_page_structure()
    
    # 测试URL过滤
    test_improved_url_filtering()
    
    print("\n" + "=" * 50)
    print("调试完成！")


if __name__ == "__main__":
    main()
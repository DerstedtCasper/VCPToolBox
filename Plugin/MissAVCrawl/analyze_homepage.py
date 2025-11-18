#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析 MissAV 首页结构，为热榜功能做准备
"""

import sys
import re
import requests
from pathlib import Path

# 添加当前目录到 Python 路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "missav_api_core"))

from consts import HEADERS


def analyze_homepage_structure():
    """分析首页结构"""
    print("=== 分析 MissAV 首页结构 ===")
    
    homepage_urls = [
        "https://missav.ws/dm22/en",
        "https://missav.ws/",
        "https://missav.ws/en",
        "https://missav.ws/cn"
    ]
    
    for url in homepage_urls:
        print(f"\n--- 分析 {url} ---")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text
                print(f"页面长度: {len(content)} 字符")
                
                # 分析页面结构
                analyze_page_structure(content, url)
                break  # 找到可用页面就停止
                
        except Exception as e:
            print(f"请求失败: {str(e)}")


def analyze_page_structure(content: str, url: str):
    """分析页面结构"""
    print("\n页面结构分析:")
    
    # 1. 查找可能的热榜容器
    hot_patterns = [
        r'<div[^>]*class="[^"]*(?:hot|popular|trending|featured)[^"]*"[^>]*>',
        r'<section[^>]*class="[^"]*(?:hot|popular|trending)[^"]*"[^>]*>',
        r'<h[1-6][^>]*>.*?(?:热门|Hot|Popular|Trending).*?</h[1-6]>',
        r'<div[^>]*id="[^"]*(?:hot|popular|trending)[^"]*"[^>]*>',
    ]
    
    for pattern in hot_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
        if matches:
            print(f"  找到热榜容器模式: {len(matches)} 个")
            for i, match in enumerate(matches[:3]):
                print(f"    {i+1}. {match[:100]}...")
    
    # 2. 查找视频卡片结构
    card_patterns = [
        r'<div[^>]*class="[^"]*(?:video|item|card|movie)[^"]*"[^>]*>',
        r'<article[^>]*class="[^"]*(?:video|item|movie)[^"]*"[^>]*>',
        r'<a[^>]*class="[^"]*(?:video|item|movie)[^"]*"[^>]*href="[^"]*"[^>]*>',
    ]
    
    total_cards = 0
    for pattern in card_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            print(f"  视频卡片模式 '{pattern[:30]}...': {len(matches)} 个")
            total_cards += len(matches)
    
    print(f"  总视频卡片数: {total_cards}")
    
    # 3. 提取所有视频链接
    video_links = extract_video_links(content)
    print(f"  提取到的视频链接: {len(video_links)} 个")
    
    if video_links:
        print("  视频链接示例:")
        for i, link in enumerate(video_links[:10]):
            print(f"    {i+1}. {link}")
    
    # 4. 分析页面标题和描述
    title_match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
    if title_match:
        print(f"  页面标题: {title_match.group(1)}")
    
    # 5. 查找可能的分类或标签
    category_patterns = [
        r'<a[^>]*href="[^"]*(?:category|tag|genre)[^"]*"[^>]*>([^<]+)</a>',
        r'<span[^>]*class="[^"]*(?:category|tag|genre)[^"]*"[^>]*>([^<]+)</span>',
    ]
    
    for pattern in category_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            print(f"  分类标签: {matches[:10]}")
            break


def extract_video_links(content: str) -> list:
    """提取视频链接"""
    # 提取所有链接
    all_links = re.findall(r'href="([^"]*)"', content)
    
    # 过滤出可能的视频链接
    video_links = []
    video_patterns = [
        r'^/[A-Z]{2,6}-\d{2,4}$',
        r'^/[A-Z]{2,6}-\d{2,4}(-[a-z-]+)?$',
        r'^/\d{2,4}[A-Z]{2,6}-\d{2,4}$',
        r'^/FC2-PPV-\d{6,8}$',
        r'^/[A-Z]{1,4}\d{2,4}$',
    ]
    
    for link in all_links:
        # 移除查询参数
        clean_link = link.split('?')[0]
        
        # 检查是否匹配视频模式
        for pattern in video_patterns:
            if re.match(pattern, clean_link, re.IGNORECASE):
                video_links.append(link)
                break
    
    return list(set(video_links))  # 去重


def analyze_video_card_structure():
    """分析视频卡片的详细结构"""
    print("\n=== 分析视频卡片结构 ===")
    
    try:
        response = requests.get("https://missav.ws/dm22/en", headers=HEADERS, timeout=30)
        if response.status_code != 200:
            print("无法获取首页内容")
            return
        
        content = response.text
        
        # 查找包含视频链接的区域
        video_links = extract_video_links(content)
        
        if video_links:
            # 分析第一个视频链接周围的HTML结构
            first_link = video_links[0]
            print(f"分析视频链接: {first_link}")
            
            # 查找包含该链接的HTML片段
            link_pattern = re.escape(first_link)
            context_pattern = rf'(.{{0,500}}href="{link_pattern}"[^>]*>.*?</a>.{{0,500}})'
            
            match = re.search(context_pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                context = match.group(1)
                print("视频卡片HTML结构:")
                print(context[:800] + "..." if len(context) > 800 else context)
                
                # 分析结构元素
                analyze_card_elements(context)
    
    except Exception as e:
        print(f"分析失败: {str(e)}")


def analyze_card_elements(html_fragment: str):
    """分析卡片元素"""
    print("\n卡片元素分析:")
    
    # 查找图片
    img_matches = re.findall(r'<img[^>]*src="([^"]*)"[^>]*>', html_fragment, re.IGNORECASE)
    if img_matches:
        print(f"  图片: {len(img_matches)} 个")
        for img in img_matches[:3]:
            print(f"    - {img}")
    
    # 查找标题
    title_patterns = [
        r'<h[1-6][^>]*>([^<]+)</h[1-6]>',
        r'title="([^"]*)"',
        r'alt="([^"]*)"',
    ]
    
    for pattern in title_patterns:
        matches = re.findall(pattern, html_fragment, re.IGNORECASE)
        if matches:
            print(f"  标题模式 '{pattern[:20]}...': {matches[:3]}")
    
    # 查找时长、日期等信息
    info_patterns = [
        r'(\d{1,2}:\d{2}:\d{2})',  # 时长格式
        r'(\d{4}-\d{2}-\d{2})',   # 日期格式
        r'(\d{1,2}:\d{2})',       # 简短时长
    ]
    
    for pattern in info_patterns:
        matches = re.findall(pattern, html_fragment)
        if matches:
            print(f"  信息模式 '{pattern}': {matches[:3]}")


def main():
    """主函数"""
    print("MissAV 首页结构分析工具")
    print("=" * 50)
    
    # 分析首页结构
    analyze_homepage_structure()
    
    # 分析视频卡片结构
    analyze_video_card_structure()
    
    print("\n" + "=" * 50)
    print("分析完成！")


if __name__ == "__main__":
    main()
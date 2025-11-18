#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASMR API Client
基于ASMRManager的API客户端实现
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, TypeVar
from aiohttp import ClientConnectorError, ClientSession
from aiohttp.connector import TCPConnector

from .config import ASMRConfig

T = TypeVar("T", bound="ASMRAPIClient")

class ASMRAPIClient:
    """ASMR.one API客户端"""
    
    def __init__(self, config: ASMRConfig):
        self.config = config
        self.base_api_url = "https://api.asmr-200.com/api/"
        self.headers = {
            "User-Agent": "ASMRTools-VCP (https://github.com/lioensky/VCPToolBox)",
        }
        self._session: Optional[ClientSession] = None
        self.recommender_uuid: str = ""
        
        # 设置API频道
        if config.api_channel:
            self.base_api_url = f"https://{config.api_channel}/api/"

    async def __aenter__(self):
        """异步上下文管理器入口"""
        import ssl
        # 创建SSL上下文，跳过证书验证
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = TCPConnector(limit=10, ssl=ssl_context)
        self._session = ClientSession(connector=connector)
        await self.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self._session:
            await self._session.close()

    async def login(self) -> bool:
        """登录ASMR.one"""
        try:
            async with self._session.post(
                self.base_api_url + "auth/me",
                json={"name": self.config.username, "password": self.config.password},
                headers=self.headers,
                proxy=self.config.proxy,
            ) as resp:
                if resp.status != 200:
                    return False
                    
                resp_json = await resp.json()
                token = resp_json["token"]
                self.headers.update({
                    "Authorization": f"Bearer {token}",
                })
                self.recommender_uuid = resp_json["user"]["recommenderUuid"]
                return True
        except Exception as e:
            print(f"Login failed: {e}")
            return False

    async def get(self, route: str, params: Optional[Dict] = None, max_retry: int = 3) -> Optional[Any]:
        """GET请求"""
        retry = 0
        while retry <= max_retry:
            try:
                async with self._session.get(
                    self.base_api_url + route,
                    headers=self.headers,
                    proxy=self.config.proxy,
                    params=params,
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        print(f"Request failed with status {resp.status} for route: {route}")
                        return None
            except Exception as e:
                print(f"Request {route} failed: {e}")
                if retry >= max_retry:
                    return None
                retry += 1
                await asyncio.sleep(2)
        return None

    async def post(self, route: str, data: Optional[Dict] = None, max_retry: int = 3) -> Optional[Any]:
        """POST请求"""
        retry = 0
        while retry <= max_retry:
            try:
                async with self._session.post(
                    self.base_api_url + route,
                    headers=self.headers,
                    proxy=self.config.proxy,
                    json=data,
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        print(f"Request failed with status {resp.status}")
                        return None
            except Exception as e:
                print(f"Request {route} failed: {e}")
                if retry >= max_retry:
                    return None
                retry += 1
                await asyncio.sleep(2)
        return None

    async def search_works(self, keyword: str, **filters) -> List[Dict]:
        """搜索作品"""
        # 构建搜索内容
        search_filters = []
        
        # 添加关键词
        if keyword:
            search_filters.append(keyword)
            
        # 添加标签过滤器
        if "tags" in filters and filters["tags"]:
            tags = filters["tags"].split(",") if isinstance(filters["tags"], str) else filters["tags"]
            for tag in tags:
                search_filters.append(f"$tag:{tag.strip()}$")
                
        if "no_tags" in filters and filters["no_tags"]:
            no_tags = filters["no_tags"].split(",") if isinstance(filters["no_tags"], str) else filters["no_tags"]
            for tag in no_tags:
                search_filters.append(f"$-tag:{tag.strip()}$")
                
        # 添加其他过滤器
        if "circle" in filters and filters["circle"]:
            search_filters.append(f"$circle:{filters['circle']}$")
        if "age" in filters and filters["age"]:
            search_filters.append(f"$age:{filters['age']}$")
            
        # 构建搜索字符串
        search_content = " ".join(search_filters).replace("/", "%2F")
        
        # 搜索参数
        params = {
            "page": "1",
            "subtitle": "0",
            "order": "create_date",
            "sort": "desc"
        }
        
        # 使用搜索端点
        result = await self.get(f"search/{search_content}", params)
        if result and "works" in result:
            return result["works"]
        return []

    async def get_work_info(self, work_id: str) -> Optional[Dict]:
        """获取作品详细信息"""
        # 移除RJ/VJ/BJ前缀，只保留数字
        clean_id = work_id.upper()
        if clean_id.startswith(('RJ', 'VJ', 'BJ')):
            clean_id = clean_id[2:]
            
        result = await self.get(f"work/{clean_id}")
        return result

    async def get_recommendations(self, page: int = 1) -> List[Dict]:
        """获取推荐作品"""
        data = {
            "keyword": " ",
            "recommenderUuid": self.recommender_uuid,
            "page": page,
            "subtitle": 0,
            "order": "create_date",
            "sort": "desc"
        }
        result = await self.post("recommender/recommend-for-user", data)
        if result and "works" in result:
            return result["works"]
        return []

    async def get_popular_works(self, page: int = 1) -> List[Dict]:
        """获取热门作品"""
        data = {
            "keyword": " ",
            "recommenderUuid": self.recommender_uuid,
            "page": page,
            "subtitle": 0,
            "order": "create_date",
            "sort": "desc"
        }
        result = await self.post("recommender/popular", data)
        if result and "works" in result:
            return result["works"]
        return []

    async def get_work_tracks(self, work_id: str) -> List[Dict]:
        """获取作品音轨列表"""
        clean_id = work_id.upper()
        if clean_id.startswith(('RJ', 'VJ', 'BJ')):
            clean_id = clean_id[2:]
            
        result = await self.get(f"tracks/{clean_id}", params={"v": 2})
        if result:
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                if "error" in result:
                    print(f"Error getting tracks: {result['error']}")
                    return []
                elif "tracks" in result:
                    return result["tracks"]
        return []
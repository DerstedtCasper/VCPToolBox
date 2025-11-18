#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络请求配置
"""

import os
from pathlib import Path

# 默认配置
DEFAULT_CONFIG = {
    # 重试配置
    "MAX_RETRIES": 3,
    "RETRY_DELAY": 1,  # 秒
    "EXPONENTIAL_BACKOFF": True,
    
    # 超时配置
    "REQUEST_TIMEOUT": 30,  # 秒
    "CONNECT_TIMEOUT": 10,  # 秒
    
    # 连接池配置
    "POOL_CONNECTIONS": 10,
    "POOL_MAXSIZE": 10,
    
    # 用户代理轮换
    "ROTATE_USER_AGENT": False,
    
    # 调试模式
    "DEBUG_NETWORK": False
}

# 用户代理列表
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]


class NetworkConfig:
    """网络配置管理器"""
    
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self._load_from_env()
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        env_mappings = {
            "MISSAV_MAX_RETRIES": "MAX_RETRIES",
            "MISSAV_RETRY_DELAY": "RETRY_DELAY",
            "MISSAV_REQUEST_TIMEOUT": "REQUEST_TIMEOUT",
            "MISSAV_CONNECT_TIMEOUT": "CONNECT_TIMEOUT",
            "MISSAV_DEBUG_NETWORK": "DEBUG_NETWORK"
        }
        
        for env_key, config_key in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                # 类型转换
                if config_key in ["MAX_RETRIES", "RETRY_DELAY", "REQUEST_TIMEOUT", "CONNECT_TIMEOUT", "POOL_CONNECTIONS", "POOL_MAXSIZE"]:
                    try:
                        self.config[config_key] = int(env_value)
                    except ValueError:
                        pass
                elif config_key in ["EXPONENTIAL_BACKOFF", "ROTATE_USER_AGENT", "DEBUG_NETWORK"]:
                    self.config[config_key] = env_value.lower() in ['true', '1', 'yes', 'on']
                else:
                    self.config[config_key] = env_value
    
    def get(self, key: str, default=None):
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """设置配置值"""
        self.config[key] = value
    
    def get_user_agent(self, index: int = 0):
        """获取用户代理"""
        if self.config["ROTATE_USER_AGENT"]:
            import random
            return random.choice(USER_AGENTS)
        else:
            return USER_AGENTS[index % len(USER_AGENTS)]
    
    def get_retry_delay(self, attempt: int):
        """获取重试延迟时间"""
        base_delay = self.config["RETRY_DELAY"]
        if self.config["EXPONENTIAL_BACKOFF"]:
            return base_delay * (2 ** attempt)
        else:
            return base_delay
    
    def debug_print(self, message: str):
        """调试输出"""
        if self.config["DEBUG_NETWORK"]:
            print(f"[NetworkDebug] {message}")


# 全局配置实例
network_config = NetworkConfig()
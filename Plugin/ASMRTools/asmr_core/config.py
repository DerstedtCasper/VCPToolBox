#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASMR Tools Configuration
基于环境变量的配置管理
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

def load_env_file(env_file_path: str):
    """加载.env文件到环境变量"""
    if not os.path.exists(env_file_path):
        return
    
    with open(env_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # 只有当环境变量不存在时才设置
                if key not in os.environ:
                    os.environ[key] = value

@dataclass
class ASMRConfig:
    """ASMR工具配置类"""
    username: str
    password: str
    download_path: str
    proxy: Optional[str] = None
    api_channel: Optional[str] = None
    aria2_host: str = "http://localhost"
    aria2_port: int = 6800
    aria2_secret: str = ""
    progress_update_interval: int = 30

    @classmethod
    def from_env(cls) -> 'ASMRConfig':
        """从环境变量创建配置"""
        # 尝试加载config.env文件
        current_dir = Path(__file__).parent.parent
        config_file = current_dir / 'config.env'
        load_env_file(str(config_file))
        
        return cls(
            username=os.getenv('ASMR_USERNAME', ''),
            password=os.getenv('ASMR_PASSWORD', ''),
            download_path=os.getenv('ASMR_DOWNLOAD_PATH', './downloads/asmr'),
            proxy=os.getenv('ASMR_PROXY') or None,
            api_channel=os.getenv('ASMR_API_CHANNEL') or None,
            aria2_host=os.getenv('ARIA2_HOST', 'http://localhost'),
            aria2_port=int(os.getenv('ARIA2_PORT', '6800')),
            aria2_secret=os.getenv('ARIA2_SECRET', ''),
            progress_update_interval=int(os.getenv('ASMR_PROGRESS_UPDATE_INTERVAL', '30'))
        )

    def validate(self) -> bool:
        """验证配置是否有效"""
        if not self.username or not self.password:
            return False
        return True

    def ensure_download_path(self):
        """确保下载目录存在"""
        Path(self.download_path).mkdir(parents=True, exist_ok=True)
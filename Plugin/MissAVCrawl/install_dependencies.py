#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MissAVCrawl Plugin 依赖安装脚本
"""

import subprocess
import sys
import os
from pathlib import Path

def install_package(package_name):
    """安装Python包"""
    try:
        print(f"正在安装 {package_name}...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", package_name], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {package_name} 安装成功")
            return True
        else:
            print(f"❌ {package_name} 安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 安装 {package_name} 时发生错误: {str(e)}")
        return False

def check_package(package_name):
    """检查包是否已安装"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def main():
    """主函数"""
    print("MissAVCrawl Plugin 依赖检查和安装")
    print("=" * 50)
    
    # 必需的包列表
    required_packages = [
        "eaf_base_api",
        "requests",
        "urllib3"
    ]
    
    # 检查和安装依赖
    all_installed = True
    for package in required_packages:
        if check_package(package.replace("-", "_")):
            print(f"✅ {package} 已安装")
        else:
            print(f"⚠️  {package} 未安装，正在安装...")
            if not install_package(package):
                all_installed = False
    
    print("\n" + "=" * 50)
    
    if all_installed:
        print("🎉 所有依赖安装完成！")
        print("\n现在可以使用 MissAVCrawl 插件了。")
        print("使用方法请参考 README.md 文件。")
    else:
        print("❌ 部分依赖安装失败，请手动安装：")
        for package in required_packages:
            print(f"  pip install {package}")
    
    # 检查 missAV API 核心源码
    current_dir = Path(__file__).parent
    missav_api_path = current_dir / "missav_api_core"
    
    print(f"\n检查 missAV API 核心源码...")
    if missav_api_path.exists():
        core_files = ["__init__.py", "missav_api.py", "consts.py"]
        missing_files = [f for f in core_files if not (missav_api_path / f).exists()]
        
        if not missing_files:
            print(f"✅ missAV API 核心源码完整: {missav_api_path}")
        else:
            print(f"⚠️  missAV API 核心源码不完整，缺少文件: {missing_files}")
    else:
        print(f"⚠️  missAV API 核心源码不存在: {missav_api_path}")
        print("请确保 missav_api_core 目录及其文件已正确安装。")

if __name__ == "__main__":
    main()
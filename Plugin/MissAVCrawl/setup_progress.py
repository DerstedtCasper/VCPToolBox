#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MissAV 进度条插件安装和设置脚本
"""

import os
import sys
import shutil
import platform
from pathlib import Path


def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 6):
        print("❌ 错误: 需要 Python 3.6 或更高版本")
        print(f"   当前版本: Python {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python 版本检查通过: {version.major}.{version.minor}.{version.micro}")
    return True


def check_tkinter():
    """检查 tkinter 是否可用"""
    try:
        import tkinter as tk
        # 尝试创建一个隐藏的测试窗口
        root = tk.Tk()
        root.withdraw()  # 隐藏窗口
        root.destroy()
        print("✅ tkinter 模块检查通过")
        return True
    except ImportError:
        print("❌ 错误: tkinter 模块不可用")
        return False
    except Exception as e:
        print(f"⚠️  警告: tkinter 测试失败: {e}")
        print("   这可能是因为没有图形界面环境，但模块本身可能可用")
        return True


def install_tkinter_guide():
    """显示 tkinter 安装指南"""
    system = platform.system().lower()
    
    print("\n📋 tkinter 安装指南:")
    
    if system == "linux":
        print("Linux 系统:")
        print("  Ubuntu/Debian: sudo apt-get install python3-tk")
        print("  CentOS/RHEL:   sudo yum install tkinter")
        print("  Arch Linux:    sudo pacman -S tk")
        print("  Fedora:        sudo dnf install python3-tkinter")
    
    elif system == "darwin":  # macOS
        print("macOS 系统:")
        print("  如果使用 Homebrew 安装的 Python:")
        print("    brew install python-tk")
        print("  或者重新安装 Python:")
        print("    brew reinstall python")
    
    elif system == "windows":
        print("Windows 系统:")
        print("  tkinter 通常随 Python 一起安装")
        print("  如果缺失，请重新安装 Python 并确保勾选 'tcl/tk and IDLE' 选项")
    
    else:
        print(f"  未知系统: {system}")
        print("  请查阅您的系统文档来安装 tkinter")


def create_config_file():
    """创建配置文件"""
    config_path = Path("config.env")
    example_path = Path("config.env.example")
    
    if config_path.exists():
        print("✅ 配置文件已存在: config.env")
        return True
    
    if example_path.exists():
        try:
            shutil.copy(example_path, config_path)
            print("✅ 已创建配置文件: config.env")
            return True
        except Exception as e:
            print(f"❌ 创建配置文件失败: {e}")
            return False
    else:
        # 创建基本配置文件
        config_content = """# MissAV 下载器配置文件
MISSAV_DOWNLOAD_DIR=./downloads
MISSAV_QUALITY=best
MISSAV_DOWNLOADER=threaded
MISSAV_PROXY=
MISSAV_SHOW_PROGRESS=true
"""
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            print("✅ 已创建基本配置文件: config.env")
            return True
        except Exception as e:
            print(f"❌ 创建配置文件失败: {e}")
            return False


def create_download_directory():
    """创建下载目录"""
    download_dir = Path("./downloads")
    
    try:
        download_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ 下载目录已准备: {download_dir.absolute()}")
        return True
    except Exception as e:
        print(f"❌ 创建下载目录失败: {e}")
        return False


def test_progress_dialog():
    """测试进度对话框"""
    try:
        from progress_dialog import ProgressDialog
        print("✅ 进度对话框模块导入成功")
        
        # 询问是否运行测试
        response = input("\n🤔 是否运行进度条测试? (y/N): ").strip().lower()
        if response in ['y', 'yes']:
            print("🚀 启动进度条测试...")
            os.system(f"{sys.executable} test_progress.py basic")
        
        return True
    except ImportError as e:
        print(f"❌ 进度对话框模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"⚠️  进度对话框测试出现问题: {e}")
        return True


def check_dependencies():
    """检查依赖"""
    print("\n📦 检查依赖模块...")
    
    required_modules = [
        ('json', '内置模块'),
        ('threading', '内置模块'),
        ('pathlib', '内置模块'),
        ('time', '内置模块'),
    ]
    
    optional_modules = [
        ('requests', 'HTTP 请求库'),
        ('urllib3', 'HTTP 客户端库'),
    ]
    
    all_good = True
    
    for module, description in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module} - {description}")
        except ImportError:
            print(f"  ❌ {module} - {description} (缺失)")
            all_good = False
    
    for module, description in optional_modules:
        try:
            __import__(module)
            print(f"  ✅ {module} - {description}")
        except ImportError:
            print(f"  ⚠️  {module} - {description} (可选，用于 missAV API)")
    
    return all_good


def main():
    """主安装函数"""
    print("🎯 MissAV 进度条插件安装向导")
    print("=" * 50)
    
    # 检查 Python 版本
    if not check_python_version():
        sys.exit(1)
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请安装缺失的模块")
        sys.exit(1)
    
    # 检查 tkinter
    tkinter_ok = check_tkinter()
    if not tkinter_ok:
        install_tkinter_guide()
        print("\n⚠️  请安装 tkinter 后重新运行此脚本")
        sys.exit(1)
    
    # 创建配置文件
    if not create_config_file():
        sys.exit(1)
    
    # 创建下载目录
    if not create_download_directory():
        sys.exit(1)
    
    # 测试进度对话框
    if not test_progress_dialog():
        print("\n⚠️  进度对话框测试失败，但安装可以继续")
    
    print("\n🎉 安装完成!")
    print("\n📋 使用说明:")
    print("1. 编辑 config.env 文件来自定义配置")
    print("2. 使用 DownloadVideoWithProgress 命令来下载视频")
    print("3. 运行 'python test_progress.py' 来测试功能")
    print("4. 查看 README_Progress.md 获取详细文档")
    
    print("\n🔧 配置建议:")
    print("- 设置合适的下载目录路径")
    print("- 根据网络情况选择视频质量")
    print("- 如需代理，请在配置文件中设置")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 安装过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
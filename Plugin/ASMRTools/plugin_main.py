#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASMRTools VCP Plugin - Main Entry Point
基于ASMRManager的VCP异步插件入口
"""

import sys
import json
import traceback
import os
from pathlib import Path

# 确保可以导入本地模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """插件主入口函数"""
    try:
        # 读取标准输入
        input_data = sys.stdin.read().strip()
        
        if not input_data:
            result = {
                "status": "error",
                "error": "No input data received by the plugin."
            }
        else:
            # 解析JSON输入
            request_data = json.loads(input_data)
            command = request_data.get('command')

            if not command:
                result = {
                    "status": "error",
                    "error": "Missing 'command' in request data."
                }
            elif command == "DownloadWorkAsync":
                # 异步下载命令
                from asmr_core.async_handler_fixed import handle_async_download
                handle_async_download(request_data)
                return  # 异步命令直接返回，不输出JSON
            else:
                # 同步命令
                from asmr_core.request_handler import process_request
                result = process_request(request_data)

    except json.JSONDecodeError as e:
        result = {
            "status": "error",
            "error": f"Failed to parse input JSON: {str(e)}"
        }
    except Exception as e:
        result = {
            "status": "error",
            "error": f"An unexpected error occurred: {str(e)}",
            "traceback": traceback.format_exc()
        }

    # 输出结果到标准输出
    print(json.dumps(result, ensure_ascii=False))
    sys.stdout.flush()

if __name__ == "__main__":
    main()
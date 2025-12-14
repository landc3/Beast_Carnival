#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启动脚本
"""
import uvicorn
import webbrowser
import threading
import time
import subprocess
import os
import sys
from pathlib import Path
from config import config

def start_frontend():
    """启动前端服务器"""
    # 获取项目根目录
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    frontend_dir = project_root / "frontend"
    
    if not frontend_dir.exists():
        print(f"警告: 前端目录不存在: {frontend_dir}")
        return
    
    # 检查是否已安装依赖
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("前端依赖未安装，正在安装...")
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=str(frontend_dir),
                check=False,
                shell=True
            )
        except Exception as e:
            print(f"安装前端依赖失败: {e}")
            return
    
    # 启动前端服务器
    print("正在启动前端服务器...")
    try:
        subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(frontend_dir),
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("前端服务器已启动")
    except Exception as e:
        print(f"启动前端服务器失败: {e}")

def open_browser():
    """延迟打开浏览器"""
    time.sleep(5)  # 等待前端服务器启动
    frontend_url = "http://localhost:4399"
    webbrowser.open(frontend_url)
    print(f"\n浏览器已自动打开: {frontend_url}")

if __name__ == "__main__":
    # 启动前端服务器
    frontend_thread = threading.Thread(target=start_frontend, daemon=True)
    frontend_thread.start()
    
    # 在后台线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )


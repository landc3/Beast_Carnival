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

def check_redis():
    """检查Redis是否可用"""
    try:
        import redis
        r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB, socket_connect_timeout=2)
        r.ping()
        print("✓ Redis连接正常")
        return True
    except Exception as e:
        print(f"✗ Redis连接失败: {e}")
        print(f"  请确保Redis服务正在运行 (host={config.REDIS_HOST}, port={config.REDIS_PORT})")
        print("  Windows: redis-server")
        print("  Linux/Mac: sudo systemctl start redis 或 redis-server")
        return False

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

def check_port(port):
    """检查端口是否被占用"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        if result == 0:
            return True  # 端口被占用
        return False
    except Exception:
        return False

if __name__ == "__main__":
    # 设置环境变量，禁用 Python 缓冲，确保日志立即输出
    import os
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    # 强制刷新 stdout 和 stderr
    import sys
    sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
    sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None
    
    print("=" * 50)
    print("Beast Carnival 启动中...")
    print("=" * 50)
    
    # 检查端口是否被占用
    print(f"\n[0/4] 检查端口 {config.PORT} 是否可用...")
    if check_port(config.PORT):
        print(f"⚠ 警告: 端口 {config.PORT} 已被占用")
        print(f"   这可能导致连接问题。请关闭其他使用该端口的程序。")
        print(f"   如果这是预期的（例如之前的实例），可以继续运行。")
    else:
        print(f"✓ 端口 {config.PORT} 可用")
    
    # 检查Redis
    print(f"\n[1/4] 检查Redis连接...")
    if not check_redis():
        print("\n启动失败：Redis未运行")
        sys.exit(1)
    
    # 启动前端服务器
    print(f"\n[2/4] 启动前端服务器...")
    frontend_thread = threading.Thread(target=start_frontend, daemon=True)
    frontend_thread.start()
    
    # 在后台线程中打开浏览器
    print(f"\n[3/4] 准备打开浏览器...")
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    print(f"\n[4/4] 启动后端服务器...")
    
    print(f"\n后端服务: http://{config.HOST}:{config.PORT}")
    print(f"前端服务: http://localhost:4399")
    print("=" * 50)
    print("\n正在启动后端服务器...\n")
    
    # 配置 uvicorn 日志，确保能看到所有日志
    # 创建自定义日志配置，确保访问日志正确输出
    import logging.config
    
    # 在 uvicorn 启动前，先配置日志，确保所有模块的日志都能输出
    # 这很重要，因为 reload=True 时可能会重新加载模块
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 确保所有服务模块的 logger 都配置正确
    for module_name in ['services.werewolf_service', 'services.ai_service', 'services.redis_service', 
                        'services.character_service', 'services.event_service', 'services', 'main']:
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(logging.INFO)
        module_logger.propagate = True
        # 确保有 handler
        if not module_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            module_logger.addHandler(handler)
    
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,  # 不禁用现有 logger，保留 main.py 中的配置
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": None,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(client_addr)s "%(request_line)s" %(status_code)s',
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "detailed": {
                "formatter": "detailed",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
            # 添加其他模块的 logger 配置，确保日志能输出
            # 注意：propagate=True 允许日志向上传播到根 logger（main.py 中配置的）
            "services.werewolf_service": {"handlers": ["detailed"], "level": "INFO", "propagate": True},
            "services.ai_service": {"handlers": ["detailed"], "level": "INFO", "propagate": True},
            "services.redis_service": {"handlers": ["detailed"], "level": "INFO", "propagate": True},
            "services.character_service": {"handlers": ["detailed"], "level": "INFO", "propagate": True},
            "services.event_service": {"handlers": ["detailed"], "level": "INFO", "propagate": True},
            "main": {"handlers": ["detailed"], "level": "INFO", "propagate": True},
        },
    }
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="info",
        access_log=True,  # 确保访问日志启用
        log_config=log_config  # 使用自定义日志配置
    )


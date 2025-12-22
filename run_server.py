#!/usr/bin/env python3
"""
服务器启动入口
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.server import StockRequestHandler
from src.config import PORT
import socketserver

if __name__ == "__main__":
    # 允许地址重用，避免重启时由"Address already in use"错误
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), StockRequestHandler) as httpd:
        print(f"股票后端服务器运行在 http://localhost:{PORT}")
        httpd.serve_forever()


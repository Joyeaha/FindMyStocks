#!/usr/bin/env python3
"""
股票数据后端服务器
主服务器负责路由分发，将请求转发到对应的处理器
"""

import http.server
import socketserver
import json

from . import config
from .static_handler import StaticFileHandler
from .api.api_handler import StockAPIHandler
from .utils import log_message, send_error_response


class StockRequestHandler(http.server.BaseHTTPRequestHandler):
    """股票数据请求处理器（路由分发）"""
    
    def do_POST(self) -> None:
        """处理 POST 请求（业务 API）"""
        # 读取请求体
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                request_params = json.loads(post_data.decode('utf-8'))
            else:
                request_params = {}
        except (json.JSONDecodeError, ValueError) as e:
            log_message(f"解析请求参数失败: {e}")
            send_error_response(400, "Invalid JSON body", self)
            return
        
        # 路由到业务 API 处理器
        StockAPIHandler.handle_post(request_params, self)
    
    def do_GET(self) -> None:
        """处理 GET 请求（静态文件服务）"""
        # 路由到静态文件处理器
        if not StaticFileHandler.handle_get(self.path, self):
            send_error_response(404, "Not found", self)
    
    def do_OPTIONS(self) -> None:
        """处理 OPTIONS 请求（CORS 预检）"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


if __name__ == "__main__":
    # 允许地址重用，避免重启时由"Address already in use"错误
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", config.PORT), StockRequestHandler) as httpd:
        log_message(f"股票后端服务器运行在 http://localhost:{config.PORT}")
        httpd.serve_forever()

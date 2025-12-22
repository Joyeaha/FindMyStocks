#!/usr/bin/env python3
"""
静态文件服务处理器
负责处理 HTML 和静态资源（CSS、JS 等）的请求
"""

import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING

from . import config
from .utils import log_message, send_error_response

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler


class StaticFileHandler:
    """静态文件处理器"""
    
    @staticmethod
    def get_static_dir() -> Path:
        """获取静态文件目录"""
        return Path(config.BASE_DIR) / 'static'
    
    @staticmethod
    def get_html_file() -> Path:
        """获取 HTML 文件路径"""
        return Path(config.BASE_DIR) / 'index.html'
    
    @staticmethod
    def handle_get(path: str, request_handler: 'BaseHTTPRequestHandler') -> bool:
        """
        处理 GET 请求
        
        Args:
            path: 请求路径
            request_handler: HTTP 请求处理器实例
        
        Returns:
            是否成功处理请求
        """
        # 移除查询参数
        clean_path = path.split('?')[0]
        
        # 处理根路径，返回 index.html
        if clean_path == '/' or clean_path == '/index.html':
            StaticFileHandler.serve_file(
                StaticFileHandler.get_html_file(),
                'text/html',
                request_handler
            )
            return True
        
        # 处理静态文件
        if clean_path.startswith('/static/'):
            file_path = StaticFileHandler.get_static_dir() / clean_path[8:]  # 移除 '/static/' 前缀
            if file_path.exists() and file_path.is_file():
                # 确定 MIME 类型
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if not mime_type:
                    if file_path.suffix == '.js':
                        mime_type = 'application/javascript'
                    elif file_path.suffix == '.css':
                        mime_type = 'text/css'
                    else:
                        mime_type = 'application/octet-stream'
                
                StaticFileHandler.serve_file(file_path, mime_type, request_handler)
                return True
        
        return False
    
    @staticmethod
    def serve_file(file_path: Path, content_type: str, request_handler: 'BaseHTTPRequestHandler') -> None:
        """
        提供静态文件服务
        
        Args:
            file_path: 文件路径
            content_type: 内容类型
            request_handler: HTTP 请求处理器实例
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            request_handler.send_response(200)
            request_handler.send_header('Content-Type', content_type)
            request_handler.send_header('Content-Length', str(len(content)))
            request_handler.send_header('Access-Control-Allow-Origin', '*')
            # 缓存静态资源
            if content_type.startswith('application/javascript') or content_type == 'text/css':
                request_handler.send_header('Cache-Control', 'public, max-age=31536000')  # 1年缓存
            request_handler.end_headers()
            request_handler.wfile.write(content)
        except IOError as e:
            log_message(f"读取文件失败: {e}")
            send_error_response(500, "Internal Server Error", request_handler)


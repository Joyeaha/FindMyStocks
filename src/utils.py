#!/usr/bin/env python3
"""
工具函数模块
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler


def get_current_date() -> str:
    """获取当前日期字符串，格式为 'YYYY-MM-DD'"""
    return time.strftime('%Y-%m-%d')


def get_current_datetime() -> str:
    """获取当前日期时间字符串，格式为 'YYYY-MM-DD HH:MM:SS'"""
    return time.strftime('%Y-%m-%d %H:%M:%S')


def format_timestamp(timestamp: float) -> str:
    """将时间戳格式化为日期时间字符串"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def log_message(message: str) -> None:
    """格式化日志消息"""
    print(f"[{get_current_datetime()}] {message}")


def send_error_response(code: int, message: str, request_handler: 'BaseHTTPRequestHandler') -> None:
    """
    向前端返回错误响应
    
    Args:
        code: HTTP 状态码
        message: 错误消息
        request_handler: HTTP 请求处理器实例
    """
    request_handler.send_response(code)
    request_handler.send_header('Content-Type', 'application/json')
    request_handler.send_header('Access-Control-Allow-Origin', '*')
    request_handler.end_headers()
    request_handler.wfile.write(json.dumps({"error": message}).encode('utf-8'))


def send_json_response(data: Dict[str, Any], request_handler: 'BaseHTTPRequestHandler') -> None:
    """
    向前端返回 JSON 响应
    
    Args:
        data: 要返回的数据字典
        request_handler: HTTP 请求处理器实例
    """
    request_handler.send_response(200)
    request_handler.send_header('Content-Type', 'application/json')
    request_handler.send_header('Access-Control-Allow-Origin', '*')
    request_handler.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
    request_handler.send_header('Access-Control-Allow-Headers', 'Content-Type')
    request_handler.end_headers()
    request_handler.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))


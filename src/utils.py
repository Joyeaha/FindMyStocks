#!/usr/bin/env python3
"""
工具函数模块
"""

import time
from datetime import datetime
from typing import Optional


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


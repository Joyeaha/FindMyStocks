#!/usr/bin/env python3
"""
数据缓存管理模块
提供缓存数据的读取、保存和过期清理功能（支持基本面和财报数据）
"""

import json
import os
from typing import Optional, Dict, Any, List

from .. import config
from ..utils import log_message, format_timestamp


def _load_cache(cache_file: str) -> Dict[str, Any]:
    """加载缓存文件"""
    if not os.path.exists(cache_file):
        return {}
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        log_message(f"读取缓存文件失败: {e}")
        return {}


def _save_cache(cache_data: Dict[str, Any], cache_file: str) -> None:
    """保存缓存文件"""
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        log_message(f"保存缓存文件失败: {e}")
        raise


def _clean_expired_cache(cache_data: Dict[str, Any], cache_file: str) -> Dict[str, Any]:
    """清理过期数据"""
    import time
    current_timestamp = time.time()
    expired_dates = []
    
    for cache_date, cache_value in cache_data.items():
        if isinstance(cache_value, dict) and 'expireAt' in cache_value:
            expire_at = cache_value.get('expireAt')
            if expire_at and expire_at < current_timestamp:
                expired_dates.append(cache_date)
    
    if expired_dates:
        for expired_date in expired_dates:
            del cache_data[expired_date]
        log_message(f"清理了 {len(expired_dates)} 个过期的缓存数据: {expired_dates}")
        _save_cache(cache_data, cache_file)
    
    return cache_data


def get_cache(date: str, metrics_list: List[str], cache_file: str) -> Optional[Dict[str, Any]]:
    """
    从缓存文件中读取指定日期的数据
    返回缓存数据，如果不存在、已过期或 metricsList 不匹配则返回 None
    同时清理所有过期数据
    
    Args:
        date: 日期字符串，格式为 'YYYY-MM-DD'
        metrics_list: 请求的指标列表
        cache_file: 缓存文件路径
    
    Returns:
        缓存的数据，如果不存在、已过期或 metricsList 不匹配则返回 None
    """
    cache_data = _load_cache(cache_file)
    if not cache_data:
        return None
    
    # 清理过期数据
    cache_data = _clean_expired_cache(cache_data, cache_file)
    
    # 检查指定日期的数据是否存在且未过期
    cached_value = cache_data.get(date)
    if not cached_value:
        return None
    
    # 兼容新旧格式：如果是新格式（包含 expireAt），提取 data 字段；否则直接返回
    if isinstance(cached_value, dict) and 'expireAt' in cached_value:
        import time
        expire_at = cached_value.get('expireAt')
        if expire_at and expire_at < time.time():
            log_message(f"缓存数据已过期，日期: {date}")
            return None
        
        # 检查 metricsList
        cached_metrics_list = cached_value.get('metricsList')
        if not cached_metrics_list:
            # 旧缓存没有 metricsList，需要重新请求
            log_message(f"缓存数据缺少 metricsList，日期: {date}")
            return None
        
        # 检查缓存的 metricsList 是否包含请求的所有指标
        cached_metrics_set = set(cached_metrics_list)
        requested_metrics_set = set(metrics_list)
        
        if not requested_metrics_set.issubset(cached_metrics_set):
            log_message(f"缓存数据的 metricsList 不包含请求的指标，日期: {date}, 缓存: {cached_metrics_list}, 请求: {metrics_list}")
            return None
        
        return cached_value.get('data')
    
    # 旧格式，没有 metricsList，需要重新请求
    log_message(f"缓存数据格式过旧（缺少 metricsList），日期: {date}")
    return None


def save_cache(date: str, data: Dict[str, Any], metrics_list: List[str], cache_file: str, expire_days: int) -> None:
    """
    按日期保存数据到缓存文件
    添加过期时间（使用后的指定天数）和 metricsList
    
    Args:
        date: 日期字符串，格式为 'YYYY-MM-DD'
        data: 要缓存的数据
        metrics_list: 指标列表
        cache_file: 缓存文件路径
        expire_days: 过期天数
    
    Raises:
        IOError: 保存文件失败
    """
    import time
    
    cache_data = _load_cache(cache_file)
    
    # 计算过期时间（当前时间 + 过期天数）
    expire_at = time.time() + (expire_days * 24 * 60 * 60)
    
    # 包装数据，添加过期时间和 metricsList
    cache_entry = {
        "data": data,
        "metricsList": metrics_list,
        "expireAt": expire_at,
        "savedAt": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 以日期为 key 更新缓存
    cache_data[date] = cache_entry
    
    # 保存到文件
    _save_cache(cache_data, cache_file)
    expire_date_str = format_timestamp(expire_at)
    log_message(f"已保存数据到缓存，日期: {date}, metricsList: {metrics_list}, 过期时间: {expire_date_str}")

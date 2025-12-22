#!/usr/bin/env python3
"""
基本面数据获取模块
提供从理杏仁API获取股票基本面数据的功能
"""

import json
import urllib.request
import urllib.error
import gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple, Optional

from .. import config
from ..utils import log_message


def request_api(url: str, payload: Dict[str, Any]) -> bytes:
    """
    向理杏仁API发送请求
    
    Args:
        url: API 地址
        payload: 请求参数（字典）
    
    Returns:
        响应数据的字节流
    
    Raises:
        urllib.error.HTTPError: HTTP 错误
        Exception: 其他请求错误
    """
    request_data = json.dumps(payload).encode('utf-8')
    retry_delay = config.INITIAL_RETRY_DELAY
    
    for attempt in range(config.MAX_RETRIES):
        try:
            req = urllib.request.Request(url, data=request_data, headers={
                'Content-Type': 'application/json',
                'Accept-Encoding': 'gzip'
            })
            
            response = urllib.request.urlopen(req)
            response_data = response.read()
            
            # 处理gzip解压
            if response.info().get('Content-Encoding') == 'gzip':
                try:
                    response_data = gzip.decompress(response_data)
                    log_message("已解压gzip响应数据")
                except Exception as e:
                    log_message(f"解压gzip数据失败: {e}")

            return response_data
            
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < config.MAX_RETRIES - 1:
                log_message(f"API限流 (429), {retry_delay}秒后重试 (第{attempt+1}次)...")
                import time
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            
            # 尝试读取理杏仁API返回的错误信息
            error_message = None
            try:
                error_body = e.read()
                # 处理gzip解压
                if e.headers.get('Content-Encoding') == 'gzip':
                    try:
                        error_body = gzip.decompress(error_body)
                    except Exception:
                        pass
                
                # 尝试解析JSON错误响应
                try:
                    error_data = json.loads(error_body.decode('utf-8'))
                    # 理杏仁API可能返回的错误字段：message, error, msg等
                    error_message = (
                        error_data.get('message') or 
                        error_data.get('error') or 
                        error_data.get('msg') or 
                        error_body.decode('utf-8', errors='ignore')
                    )
                except (json.JSONDecodeError, UnicodeDecodeError):
                    error_message = error_body.decode('utf-8', errors='ignore') or str(e)
            except Exception:
                error_message = str(e)
            
            # 创建一个包含理杏仁错误信息的异常
            api_error = Exception(f"理杏仁API错误: {error_message or f'HTTP {e.code}'}")
            api_error.api_error_message = error_message or f'HTTP {e.code}'
            raise api_error
        except Exception as e:
            if attempt == config.MAX_RETRIES - 1:
                raise
            log_message(f"请求失败，重试中: {e}")
            import time
            time.sleep(retry_delay)
            retry_delay *= 2


def _fetch_single_batch(
    batch: List[str],
    batch_num: int,
    total_batches: int,
    date: str,
    metrics_list: List[str]
) -> Tuple[int, List[Dict[str, Any]], List[str], Optional[Exception]]:
    """
    处理单个批次的基本面数据请求
    
    Args:
        batch: 股票代码列表（最多100个）
        batch_num: 批次号
        total_batches: 总批次数
        date: 日期字符串
        metrics_list: 指标列表
    
    Returns:
        (batch_num, batch_data, missing_codes, error)
    """
    payload = {
        "token": config.TOKEN,
        "stockCodes": batch,
        "date": date,
        "metricsList": metrics_list
    }
    
    try:
        log_message(f"请求第 {batch_num}/{total_batches} 批，股票数量: {len(batch)}")
        log_message(payload)
        response_data = json.loads(request_api(config.HK_FUNDAMENTAL_URL, payload))
        
        batch_data = response_data.get('data', [])
        missing_codes = []
        if len(batch_data) != len(batch):
            received_codes = {item.get('stockCode') for item in batch_data if item.get('stockCode')}
            missing_codes = list(set(batch) - received_codes)
        
        log_message(f"第 {batch_num} 批获取成功，数据量: {len(batch_data)}")
        return (batch_num, batch_data, missing_codes, None)
    except Exception as e:
        log_message(f"第 {batch_num} 批请求失败: {e}")
        return (batch_num, [], [], e)


def batch_fetch_fundamental_data(
    stock_codes: List[str],
    date: str,
    metrics_list: List[str]
) -> Dict[str, Any]:
    """
    按每100个股票代码一组分批并行请求基本面数据
    
    Args:
        stock_codes: 股票代码列表
        date: 日期字符串，格式为 'YYYY-MM-DD'
        metrics_list: 指标列表
    
    Returns:
        包含 total 和 data 的字典
    
    Raises:
        Exception: 如果所有批次都失败
    """
    if not stock_codes:
        return {"total": 0, "data": []}
    
    all_data = []
    missing_codes = []
    total_batches = (len(stock_codes) + config.BATCH_SIZE - 1) // config.BATCH_SIZE
    failed_batches = []
    
    log_message(f"开始并行批量获取基本面数据，共 {len(stock_codes)} 个股票，分 {total_batches} 批")

    # 准备所有批次
    batches = [
        (stock_codes[i:i+config.BATCH_SIZE], i // config.BATCH_SIZE + 1)
        for i in range(0, len(stock_codes), config.BATCH_SIZE)
    ]
    
    # 使用线程池并行执行所有批次请求
    max_workers = min(config.MAX_WORKERS, total_batches)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_batch = {
            executor.submit(_fetch_single_batch, batch, batch_num, total_batches, date, metrics_list): batch_num
            for batch, batch_num in batches
        }
        
        # 收集结果
        results = {}
        for future in as_completed(future_to_batch):
            batch_num, batch_data, batch_missing, error = future.result()
            results[batch_num] = (batch_data, batch_missing, error)
            
            if error:
                failed_batches.append(batch_num)
    
    # 按批次号排序合并数据（保持顺序）
    sorted_results = sorted(results.items())
    for batch_num, (batch_data, batch_missing, error) in sorted_results:
        if not error:
            all_data.extend(batch_data)
            missing_codes.extend(batch_missing)
    
    if failed_batches:
        log_message(f"警告: 有 {len(failed_batches)} 批请求失败: {failed_batches}")
    
    if len(failed_batches) == total_batches:
        raise Exception("所有批次请求都失败了")
    
    log_message(f"批量获取完成，总共获取 {len(all_data)} 条基本面数据，缺失股票数量: {len(missing_codes)}，缺失股票: {missing_codes}")
    
    return {
        "total": len(all_data),
        "data": all_data
    }

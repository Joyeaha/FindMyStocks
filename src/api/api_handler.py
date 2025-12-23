#!/usr/bin/env python3
"""
股票业务 API 处理器
负责处理所有业务相关的 API 请求
"""

import json
import os
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, TYPE_CHECKING

from .. import config
from . import data_cache
from . import data_fetcher
from . import stock_filter
from . import filter_config
from ..utils import log_message, get_current_date, send_error_response, send_json_response


def extract_nested_field_value(obj: Dict[str, Any], field_key: str) -> Any:
    """
    从嵌套对象中提取字段值
    
    例如：字段 "y.m.roe.t" 从 {y: {m: {roe: {t: 0.2038}}}} 中提取 0.2038
    
    Args:
        obj: 嵌套对象
        field_key: 字段key，使用点号分隔，如 "y.m.roe.t"
    
    Returns:
        字段值，如果不存在则返回 None
    """
    if not obj or not field_key:
        return None
    
    keys = field_key.split('.')
    value = obj
    
    for key in keys:
        if value and isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    
    return value


def process_fs_data(fs_data: Dict[str, Any], fs_metrics_list: list) -> Dict[str, Any]:
    """
    处理财报数据，提取嵌套字段值到顶层
    
    Args:
        fs_data: 财报数据对象
        fs_metrics_list: 财报指标列表
    
    Returns:
        处理后的数据对象，包含原始数据和提取的字段值
    """
    if not fs_data or not fs_metrics_list:
        return fs_data
    
    # 创建新对象，包含原始数据和提取的字段值
    processed_data = fs_data.copy()
    
    # 提取每个字段的值
    for field_key in fs_metrics_list:
        if not field_key:
            continue
        value = extract_nested_field_value(fs_data, field_key)
        if value is not None:
            processed_data[field_key] = value
    
    return processed_data

if TYPE_CHECKING:
    from http.server import BaseHTTPRequestHandler


class StockAPIHandler:
    """股票业务 API 处理器"""
    
    @staticmethod
    def handle_hk_stocks_info() -> Optional[list]:
        """
        功能：获取所有港股股票基础信息（股票代码和股票名称）
        
        Returns:
            股票信息列表，每个元素包含 stockCode 和 stockName，如果失败则返回 None
        """
        today = get_current_date()
        
        # 尝试从缓存读取
        if os.path.exists(config.HK_STOCKS_CACHE_FILE):
            try:
                with open(config.HK_STOCKS_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                    if cached.get('date') == today:
                        log_message("使用缓存的港股股票信息数据")
                        return cached.get('data')
            except (json.JSONDecodeError, IOError) as e:
                log_message(f"读取缓存失败: {e}")

        # 从 API 获取
        payload = {
            "token": config.TOKEN,
            "fsTableType": "non_financial"
        }
        log_message("处理请求: 获取港股股票信息")
        
        try:
            response_data = json.loads(data_fetcher.request_api(config.HK_COMPANY_URL, payload))
            total = response_data.get('total', 0)
            log_message(f"请求到所有公司数据，公司数量: {total}")
            
            company_list = response_data.get('data', [])
            # 提取股票代码和股票名称
            stocks_info = []
            for company in company_list:
                stock_code = company.get('stockCode')
                if stock_code:
                    stock_name = company.get('name') or company.get('nameCn') or company.get('stockName') or stock_code
                    stocks_info.append({
                        'stockCode': stock_code,
                        'stockName': stock_name
                    })

            # 保存到缓存
            try:
                data_to_cache = {
                    "date": today,
                    "data": stocks_info
                }
                with open(config.HK_STOCKS_CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data_to_cache, f, ensure_ascii=False, indent=2)
                log_message(f"已更新缓存文件: {config.HK_STOCKS_CACHE_FILE}")
            except IOError as e:
                log_message(f"写入缓存失败: {e}")
            
            return stocks_info
        except Exception as e:
            log_message(f"请求港股股票信息失败: {e}")
            return None
    
    @staticmethod
    def _get_stock_name_mapping() -> Dict[str, str]:
        """
        获取股票代码到股票名称的映射字典
        
        Returns:
            股票代码到股票名称的映射字典
        """
        stocks_info = StockAPIHandler.handle_hk_stocks_info()
        if not stocks_info:
            return {}
        return {stock.get('stockCode'): stock.get('stockName', '') for stock in stocks_info if stock.get('stockCode')}
    
    @staticmethod
    def _get_stock_codes() -> Optional[list]:
        """
        获取所有港股股票代码列表（从股票信息中提取）
        
        Returns:
            股票代码列表，如果失败则返回 None
        """
        stocks_info = StockAPIHandler.handle_hk_stocks_info()
        if not stocks_info:
            return None
        return [stock.get('stockCode') for stock in stocks_info if stock.get('stockCode')]
    
    @staticmethod
    def get_stock_fundamentals(stock_codes: list, metrics_list: list, date: str) -> Dict[str, Any]:
        """
        功能：获取指定股票的基本面数据
        
        Args:
            stock_codes: 股票代码列表
            metrics_list: 指标列表
            date: 日期字符串
        
        Returns:
            包含股票基本面数据的字典
        """
        payload = {
            "token": config.TOKEN,
            "stockCodes": stock_codes,
            "metricsList": metrics_list,
            "date": date
        }
        
        log_message(f"接口一：获取指定股票基本面数据 - 股票={stock_codes}, 指标={metrics_list}, 日期={date}")
        
        try:
            response_data = data_fetcher.request_api(config.HK_FUNDAMENTAL_URL, payload)
            result = json.loads(response_data)
            
            # 检查理杏仁API返回的错误
            # 如果响应中有data字段，说明是成功响应（即使有message字段也是成功的）
            # 只有当没有data字段，但有error或message字段时，才是错误
            if 'data' not in result:
                error_msg = None
                if 'error' in result:
                    error_value = result.get('error')
                    # 只有当error字段存在且值不是"success"时才是错误
                    if error_value and str(error_value).lower() != 'success':
                        error_msg = str(error_value)
                elif 'message' in result:
                    message_value = result.get('message')
                    if message_value and str(message_value).lower() != 'success':
                        error_msg = str(message_value)
                
                if error_msg:
                    api_error = Exception(f"理杏仁API错误: {error_msg}")
                    api_error.api_error_message = error_msg
                    raise api_error
            
            # 为每个股票添加 stockName 字段
            stock_name_mapping = StockAPIHandler._get_stock_name_mapping()
            stocks_data = result.get('data', [])
            for stock in stocks_data:
                stock_code = stock.get('stockCode')
                if stock_code and stock_code in stock_name_mapping:
                    stock['stockName'] = stock_name_mapping[stock_code]
                elif not stock.get('stockName'):
                    stock['stockName'] = stock_code or ''
            
            return result
        except Exception as e:
            log_message(f"获取股票基本面数据失败: {e}")
            # 如果异常包含理杏仁API的错误信息，保留它
            if hasattr(e, 'api_error_message'):
                raise
            # 否则包装成通用错误
            raise Exception(f"获取股票基本面数据失败: {str(e)}")
    
    @staticmethod
    def get_stock_fs_data(stock_codes: list, metrics_list: list, date: str) -> Dict[str, Any]:
        """
        功能：获取指定股票的财报数据
        
        Args:
            stock_codes: 股票代码列表
            metrics_list: 指标列表
            date: 日期字符串
        
        Returns:
            包含股票财报数据的字典
        """
        payload = {
            "token": config.TOKEN,
            "stockCodes": stock_codes,
            "metricsList": metrics_list,
            "date": date
        }
        
        log_message(f"接口一：获取指定股票财报数据 - 股票={stock_codes}, 指标={metrics_list}, 日期={date}")
        
        try:
            response_data = data_fetcher.request_api(config.HK_FS_URL, payload)
            result = json.loads(response_data)
            
            # 检查理杏仁API返回的错误
            # 如果响应中有data字段，说明是成功响应（即使有message字段也是成功的）
            # 只有当没有data字段，但有error或message字段时，才是错误
            if 'data' not in result:
                error_msg = None
                if 'error' in result:
                    error_value = result.get('error')
                    # 只有当error字段存在且值不是"success"时才是错误
                    if error_value and str(error_value).lower() != 'success':
                        error_msg = str(error_value)
                elif 'message' in result:
                    message_value = result.get('message')
                    if message_value and str(message_value).lower() != 'success':
                        error_msg = str(message_value)
                
                if error_msg:
                    api_error = Exception(f"理杏仁API错误: {error_msg}")
                    api_error.api_error_message = error_msg
                    raise api_error
            
            # 为每个股票添加 stockName 字段
            stock_name_mapping = StockAPIHandler._get_stock_name_mapping()
            stocks_data = result.get('data', [])
            for stock in stocks_data:
                stock_code = stock.get('stockCode')
                if stock_code and stock_code in stock_name_mapping:
                    stock['stockName'] = stock_name_mapping[stock_code]
                elif not stock.get('stockName'):
                    stock['stockName'] = stock_code or ''
            
            return result
        except Exception as e:
            log_message(f"获取股票财报数据失败: {e}")
            # 如果异常包含理杏仁API的错误信息，保留它
            if hasattr(e, 'api_error_message'):
                raise
            # 否则包装成通用错误
            raise Exception(f"获取股票财报数据失败: {str(e)}")
    
    @staticmethod
    def get_stock_data(stock_codes: list, metrics_list: Dict[str, list], date: str, fs_date: Optional[str] = None) -> Dict[str, Any]:
        """
        功能：获取指定股票的数据（支持基本面数据和财报数据）
        
        Args:
            stock_codes: 股票代码列表
            metrics_list: 指标列表对象，格式为 {fundamental: [...], fs: [...]}
            date: 日期字符串（用于基本面数据）
            fs_date: 财报日期字符串（用于财报数据，如果未提供则使用date）
        
        Returns:
            包含股票数据的字典，格式为 {fundamental: {...}, fs: {...}}
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        fundamental_metrics = metrics_list.get('fundamental', [])
        fs_metrics = metrics_list.get('fs', [])
        
        # 检查至少有一个非空的指标列表
        has_fundamental = fundamental_metrics and isinstance(fundamental_metrics, list) and len(fundamental_metrics) > 0
        has_fs = fs_metrics and isinstance(fs_metrics, list) and len(fs_metrics) > 0
        
        if not has_fundamental and not has_fs:
            raise ValueError("fundamental 和 fs 至少需要提供一个非空数组")
        
        # 如果没有提供财报日期，使用基础日期
        if fs_date is None:
            fs_date = date
        
        result = {}
        
        # 并行请求基本面数据和财报数据
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {}
            
            # 提交基本面数据请求
            if has_fundamental:
                future_fundamental = executor.submit(
                    StockAPIHandler.get_stock_fundamentals,
                    stock_codes,
                    fundamental_metrics,
                    date
                )
                futures['fundamental'] = future_fundamental
            
            # 提交财报数据请求（使用财报日期）
            if has_fs:
                future_fs = executor.submit(
                    StockAPIHandler.get_stock_fs_data,
                    stock_codes,
                    fs_metrics,
                    fs_date
                )
                futures['fs'] = future_fs
            
            # 收集结果
            for key, future in futures.items():
                try:
                    result[key] = future.result()
                except Exception as e:
                    log_message(f"获取{key}数据失败: {e}")
                    # 如果异常包含理杏仁API的错误信息，保留它
                    if hasattr(e, 'api_error_message'):
                        raise
                    raise Exception(f"获取{key}数据失败: {str(e)}")
        
        return result
    
    @staticmethod
    def filter_stocks_by_metrics(metrics_filter: Dict[str, list], date: str, metrics_list: Optional[list] = None, 
                                  fs_metrics_filter: Optional[Dict[str, list]] = None, fs_date: Optional[str] = None,
                                  fs_metrics_list: Optional[list] = None) -> Dict[str, Any]:
        """
        功能：根据基本面条件和财报条件筛选股票
        
        Args:
            metrics_filter: 基本面筛选条件字典，格式为 {指标名: [min, max]}
            date: 日期字符串（用于基本面数据）
            metrics_list: 基本面指标列表（可选），如果提供则使用此列表获取数据，否则从 metrics_filter 的 keys 中提取
            fs_metrics_filter: 财报筛选条件字典，格式为 {指标名: [min, max]}
            fs_date: 财报日期字符串（用于财报数据）
            fs_metrics_list: 财报指标列表（可选），如果提供则使用此列表获取数据，否则从 fs_metrics_filter 的 keys 中提取
        
        Returns:
            包含筛选后股票数据的字典
        """
        log_message(f"接口二：筛选股票 - 基本面筛选条件={metrics_filter}, 日期={date}, 财报筛选条件={fs_metrics_filter}, 财报日期={fs_date}")
        
        # 获取所有股票代码
        stock_codes = StockAPIHandler._get_stock_codes()
        if not stock_codes:
            raise Exception("获取股票代码失败")
        
        # 获取股票代码到名称的映射
        stock_name_mapping = StockAPIHandler._get_stock_name_mapping()
        
        stocks_data = []
        
        # 处理基本面数据（如果有筛选条件或指标列表）
        has_fundamental_filter = metrics_filter and len(metrics_filter) > 0
        has_fundamental_metrics = metrics_list and isinstance(metrics_list, list) and len(metrics_list) > 0
        
        if has_fundamental_filter or has_fundamental_metrics:
            # 确定需要的指标列表（优先使用传入的 metrics_list，否则从筛选条件中提取）
            if metrics_list and isinstance(metrics_list, list) and len(metrics_list) > 0:
                required_metrics = metrics_list
                log_message(f"使用传入的基本面 metricsList: {required_metrics}")
            else:
                required_metrics = list(metrics_filter.keys())
                log_message(f"从基本面 metricsFilter 中提取指标列表: {required_metrics}")
            
            if not required_metrics:
                raise ValueError("基本面 metricsFilter 不能为空，且 metricsList 未提供")
            
            # 获取所有股票的基本面数据（优先使用缓存）
            cached_data = data_cache.get_cache(date, required_metrics, config.FUNDAMENTAL_CACHE_FILE)
            
            if cached_data:
                log_message(f"使用缓存的基本面数据进行筛选，日期: {date}, 指标: {required_metrics}")
                stocks_data = cached_data.get('data', [])
            else:
                # 批量获取基本面数据
                log_message(f"缓存未命中，批量获取基本面数据，日期: {date}, 指标: {required_metrics}")
                fundamental_data = data_fetcher.batch_fetch_data(
                    stock_codes,
                    date,
                    required_metrics,
                    config.HK_FUNDAMENTAL_URL
                )
                stocks_data = fundamental_data.get('data', [])
                
                # 如果数据量大于0才保存到缓存
                total = fundamental_data.get('total', 0)
                if total > 0:
                    data_cache.save_cache(date, fundamental_data, required_metrics, config.FUNDAMENTAL_CACHE_FILE, config.FUNDAMENTAL_CACHE_EXPIRE_DAYS)
                    log_message(f"基本面数据已获取并缓存完成，数据量: {total}")
        
        # 处理财报数据（如果有指标列表，就获取数据，即使没有筛选条件）
        fs_stocks_data = []
        has_fs_metrics = fs_metrics_list and isinstance(fs_metrics_list, list) and len(fs_metrics_list) > 0
        
        if has_fs_metrics:
            if not fs_date:
                raise ValueError("财报指标列表存在时，必须提供财报日期 fs_date")
            
            # 使用传入的 fs_metrics_list
            required_fs_metrics = fs_metrics_list
            log_message(f"使用传入的财报 metricsList: {required_fs_metrics}")
            
            # 获取所有股票的财报数据（优先使用缓存）
            cached_fs_data = data_cache.get_cache(fs_date, required_fs_metrics, config.FS_CACHE_FILE)
            
            if cached_fs_data:
                log_message(f"使用缓存的财报数据进行筛选，日期: {fs_date}, 指标: {required_fs_metrics}")
                fs_stocks_data = cached_fs_data.get('data', [])
            else:
                # 批量获取财报数据
                log_message(f"缓存未命中，批量获取财报数据，日期: {fs_date}, 指标: {required_fs_metrics}")
                fs_data = data_fetcher.batch_fetch_data(
                    stock_codes,
                    fs_date,
                    required_fs_metrics,
                    config.HK_FS_URL
                )
                fs_stocks_data = fs_data.get('data', [])
                
                # 如果数据量大于0才保存到缓存
                total = fs_data.get('total', 0)
                if total > 0:
                    data_cache.save_cache(fs_date, fs_data, required_fs_metrics, config.FS_CACHE_FILE, config.FS_CACHE_EXPIRE_DAYS)
                    log_message(f"财报数据已获取并缓存完成，数据量: {total}")
        
        # 处理财报数据的嵌套字段提取（在合并前处理）
        if fs_stocks_data and fs_metrics_list and isinstance(fs_metrics_list, list) and len(fs_metrics_list) > 0:
            # 处理每个股票的财报数据，提取嵌套字段值
            fs_stocks_data = [
                process_fs_data(stock, fs_metrics_list)
                for stock in fs_stocks_data
            ]
        
        # 合并基本面和财报数据
        if stocks_data and fs_stocks_data:
            # 按股票代码合并数据
            fs_data_map = {stock.get('stockCode'): stock for stock in fs_stocks_data}
            merged_data = []
            for stock in stocks_data:
                stock_code = stock.get('stockCode')
                if stock_code in fs_data_map:
                    # 合并财报数据到基本面数据
                    merged_stock = {**stock, **fs_data_map[stock_code]}
                    merged_data.append(merged_stock)
                else:
                    merged_data.append(stock)
            stocks_data = merged_data
        elif fs_stocks_data:
            # 如果只有财报数据
            stocks_data = fs_stocks_data
        
        if not stocks_data:
            raise ValueError("没有获取到任何股票数据")
        
        # 合并筛选条件
        combined_filter = {}
        if metrics_filter and len(metrics_filter) > 0:
            combined_filter.update(metrics_filter)
        if fs_metrics_filter and len(fs_metrics_filter) > 0:
            combined_filter.update(fs_metrics_filter)
        
        # 如果没有筛选条件，返回所有数据
        if not combined_filter:
            filtered_stocks = stocks_data
        else:
            # 根据合并后的筛选条件筛选股票
            filtered_stocks = stock_filter.filter_stocks_by_metrics(stocks_data, combined_filter)
        
        # 为每个股票添加 stockName 字段
        for stock in filtered_stocks:
            stock_code = stock.get('stockCode')
            if stock_code and stock_code in stock_name_mapping:
                stock['stockName'] = stock_name_mapping[stock_code]
            elif not stock.get('stockName'):
                stock['stockName'] = stock_code or ''
        
        log_message(f"筛选完成，原始数据量: {len(stocks_data)}, 筛选后数据量: {len(filtered_stocks)}")
        
        return {
            "total": len(filtered_stocks),
            "data": filtered_stocks
        }
    @staticmethod
    def handle_post(request_params: Dict[str, Any], request_handler: 'BaseHTTPRequestHandler') -> bool:
        """
        处理 POST 请求
        
        Args:
            request_params: 解析后的请求参数
            request_handler: HTTP 请求处理器实例
        
        Returns:
            是否成功处理请求
        """
        try:
            # 接口一：获取指定股票的分析数据
            if 'stockCodes' in request_params:
                stock_codes = request_params.get('stockCodes')
                if not stock_codes or not isinstance(stock_codes, list):
                    send_error_response(400, "stockCodes 必须是非空数组", request_handler)
                    return True
                
                metrics_list_param = request_params.get('metricsList', [])
                date = request_params.get('date', get_current_date())
                fs_date = request_params.get('fsDate')  # 财报日期（可选）
                
                # 处理metricsList格式：支持数组（向后兼容）和对象（新格式）
                metrics_list_obj = None
                if isinstance(metrics_list_param, list):
                    # 数组格式（向后兼容）：转换为对象格式
                    if not metrics_list_param:
                        send_error_response(400, "metricsList 必须是非空数组或对象", request_handler)
                        return True
                    metrics_list_obj = {
                        'fundamental': metrics_list_param,
                        'fs': []
                    }
                elif isinstance(metrics_list_param, dict):
                    # 对象格式（新格式）
                    fundamental_metrics = metrics_list_param.get('fundamental', [])
                    fs_metrics = metrics_list_param.get('fs', [])
                    
                    # 验证格式
                    if not isinstance(fundamental_metrics, list) or not isinstance(fs_metrics, list):
                        send_error_response(400, "metricsList.fundamental 和 metricsList.fs 必须是数组", request_handler)
                        return True
                    
                    # 至少需要一个非空数组
                    if (not fundamental_metrics or len(fundamental_metrics) == 0) and \
                       (not fs_metrics or len(fs_metrics) == 0):
                        send_error_response(400, "metricsList.fundamental 和 metricsList.fs 至少需要提供一个非空数组", request_handler)
                        return True
                    
                    metrics_list_obj = {
                        'fundamental': fundamental_metrics if fundamental_metrics else [],
                        'fs': fs_metrics if fs_metrics else []
                    }
                else:
                    send_error_response(400, "metricsList 必须是数组或对象", request_handler)
                    return True
                
                try:
                    result = StockAPIHandler.get_stock_data(stock_codes, metrics_list_obj, date, fs_date)
                    send_json_response(result, request_handler)
                except Exception as e:
                    # 如果异常包含理杏仁API的错误信息，直接返回给前端
                    if hasattr(e, 'api_error_message'):
                        error_msg = e.api_error_message
                        log_message(f"理杏仁API返回错误: {error_msg}")
                        send_error_response(400, error_msg, request_handler)
                    else:
                        log_message(f"获取股票数据失败: {e}")
                        send_error_response(500, f"Internal Server Error: {str(e)}", request_handler)
                return True

            # 接口二：筛选股票（stockCodes存在时忽略此接口）
            elif 'metricsFilter' in request_params:
                metrics_filter = request_params.get('metricsFilter')
                if not isinstance(metrics_filter, dict):
                    send_error_response(400, "metricsFilter 必须是对象", request_handler)
                    return True
                
                date = request_params.get('date', get_current_date())
                metrics_list = request_params.get('metricsList')  # 可选的指标列表
                
                # 财报筛选条件（可选）
                fs_metrics_filter = request_params.get('fsMetricsFilter')
                fs_date = request_params.get('fsDate')
                fs_metrics_list = request_params.get('fsMetricsList')
                
                # 验证财报筛选条件格式
                if fs_metrics_filter is not None:
                    if not isinstance(fs_metrics_filter, dict):
                        send_error_response(400, "fsMetricsFilter 必须是对象", request_handler)
                        return True
                    if fs_metrics_filter and not fs_date:
                        send_error_response(400, "财报筛选条件存在时，必须提供财报日期 fsDate", request_handler)
                        return True
                
                result = StockAPIHandler.filter_stocks_by_metrics(
                    metrics_filter, date, metrics_list,
                    fs_metrics_filter, fs_date, fs_metrics_list
                )
                send_json_response(result, request_handler)
                return True
            
            # 接口三：保存指标配置
            elif 'filterConfig' in request_params:
                filter_config_data = request_params.get('filterConfig')
                config_type = request_params.get('type', 'fundamental')  # 默认为fundamental，向后兼容
                
                if not isinstance(filter_config_data, list):
                    send_error_response(400, "filterConfig 必须是数组", request_handler)
                    return True
                
                if config_type not in ['fundamental', 'fs']:
                    send_error_response(400, "type 必须是 'fundamental' 或 'fs'", request_handler)
                    return True
                
                filter_config.FilterConfigManager.save_filter_config(filter_config_data, config_type)
                send_json_response({"success": True, "message": f"{config_type}配置已保存"}, request_handler)
                return True
            
            else:
                send_error_response(400, "缺少必要参数：需要提供 stockCodes、metricsFilter 或 filterConfig", request_handler)
                return True
        
        except ValueError as e:
            log_message(f"参数错误: {e}")
            send_error_response(400, str(e), request_handler)
            return True
        except Exception as e:
            log_message(f"处理请求失败: {e}")
            send_error_response(500, f"Internal Server Error: {str(e)}", request_handler)
            return True
    
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
        try:
            # 获取指标配置接口
            if path.startswith('/api/filter-config'):
                # 解析查询参数
                parsed_url = urlparse(path)
                query_params = parse_qs(parsed_url.query)
                config_type = query_params.get('type', [None])[0]  # 获取type参数
                
                result = filter_config.FilterConfigManager.get_filter_config(config_type)
                send_json_response(result, request_handler)
                return True
            
            return False
        except Exception as e:
            log_message(f"处理 GET 请求失败: {e}")
            send_error_response(500, f"Internal Server Error: {str(e)}", request_handler)
            return True


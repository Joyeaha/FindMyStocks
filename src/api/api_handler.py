#!/usr/bin/env python3
"""
股票业务 API 处理器
负责处理所有业务相关的 API 请求
"""

import json
import os
from typing import Dict, Any, Optional, TYPE_CHECKING

from .. import config
from . import fundamental_cache
from . import fundamental_fetcher
from . import stock_filter
from . import filter_config
from ..utils import log_message, get_current_date, send_error_response, send_json_response

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
            response_data = json.loads(fundamental_fetcher.request_api(config.HK_COMPANY_URL, payload))
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
            response_data = fundamental_fetcher.request_api(config.HK_FUNDAMENTAL_URL, payload)
            result = json.loads(response_data)
            
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
            raise
    
    @staticmethod
    def filter_stocks_by_metrics(metrics_filter: Dict[str, list], date: str, metrics_list: Optional[list] = None) -> Dict[str, Any]:
        """
        功能：根据基本面条件筛选股票
        
        Args:
            metrics_filter: 筛选条件字典，格式为 {指标名: [min, max]}
            date: 日期字符串
            metrics_list: 指标列表（可选），如果提供则使用此列表获取数据，否则从 metrics_filter 的 keys 中提取
        
        Returns:
            包含筛选后股票数据的字典
        """
        log_message(f"接口二：筛选股票 - 筛选条件={metrics_filter}, 日期={date}")
        
        # 获取所有股票代码
        stock_codes = StockAPIHandler._get_stock_codes()
        if not stock_codes:
            raise Exception("获取股票代码失败")
        
        # 获取股票代码到名称的映射
        stock_name_mapping = StockAPIHandler._get_stock_name_mapping()
        
        # 确定需要的指标列表（优先使用传入的 metrics_list，否则从筛选条件中提取）
        if metrics_list and isinstance(metrics_list, list) and len(metrics_list) > 0:
            required_metrics = metrics_list
            log_message(f"使用传入的 metricsList: {required_metrics}")
        else:
            required_metrics = list(metrics_filter.keys())
            log_message(f"从 metricsFilter 中提取指标列表: {required_metrics}")
        
        if not required_metrics:
            raise ValueError("metricsFilter 不能为空，且 metricsList 未提供")
        
        # 获取所有股票的基本面数据（优先使用缓存）
        cached_data = fundamental_cache.get_fundamental_cache(date, required_metrics)
        
        if cached_data:
            log_message(f"使用缓存的基本面数据进行筛选，日期: {date}, 指标: {required_metrics}")
            stocks_data = cached_data.get('data', [])
        else:
            # 批量获取基本面数据
            log_message(f"缓存未命中，批量获取基本面数据，日期: {date}, 指标: {required_metrics}")
            fundamental_data = fundamental_fetcher.batch_fetch_fundamental_data(
                stock_codes,
                date,
                required_metrics
            )
            stocks_data = fundamental_data.get('data', [])
            
            # 如果数据量大于0才保存到缓存
            total = fundamental_data.get('total', 0)
            if total > 0:
                fundamental_cache.save_fundamental_cache(date, fundamental_data, required_metrics)
                log_message(f"基本面数据已获取并缓存完成，数据量: {total}")
        
        # 根据 metricsFilter 筛选股票
        filtered_stocks = stock_filter.filter_stocks_by_metrics(stocks_data, metrics_filter)
        
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
                
                metrics_list = request_params.get('metricsList', [])
                if not metrics_list or not isinstance(metrics_list, list):
                    send_error_response(400, "metricsList 必须是非空数组", request_handler)
                    return True
                
                date = request_params.get('date', get_current_date())
                result = StockAPIHandler.get_stock_fundamentals(stock_codes, metrics_list, date)
                send_json_response(result, request_handler)
                return True

            # 接口二：筛选股票（stockCodes存在时忽略此接口）
            elif 'metricsFilter' in request_params:
                metrics_filter = request_params.get('metricsFilter')
                if not isinstance(metrics_filter, dict):
                    send_error_response(400, "metricsFilter 必须是对象", request_handler)
                    return True
                
                date = request_params.get('date', get_current_date())
                metrics_list = request_params.get('metricsList')  # 可选的指标列表
                result = StockAPIHandler.filter_stocks_by_metrics(metrics_filter, date, metrics_list)
                send_json_response(result, request_handler)
                return True
            
            # 接口三：保存筛选项配置
            elif 'filterConfig' in request_params:
                filter_config_data = request_params.get('filterConfig')
                if not isinstance(filter_config_data, list):
                    send_error_response(400, "filterConfig 必须是数组", request_handler)
                    return True
                
                filter_config.FilterConfigManager.save_filter_config(filter_config_data)
                send_json_response({"success": True, "message": "配置已保存"}, request_handler)
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
            # 获取筛选项配置接口
            if path == '/api/filter-config':
                result = filter_config.FilterConfigManager.get_filter_config()
                send_json_response(result, request_handler)
                return True
            
            return False
        except Exception as e:
            log_message(f"处理 GET 请求失败: {e}")
            send_error_response(500, f"Internal Server Error: {str(e)}", request_handler)
            return True


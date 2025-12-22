#!/usr/bin/env python3
"""
股票数据后端服务器
提供接口转发请求到理杏仁API
"""

import http.server
import socketserver
import json
import time
import os
import mimetypes
from typing import Dict, Any, Optional
from pathlib import Path

from . import config
from . import fundamental_cache
from . import fundamental_fetcher
from . import stock_filter
from .utils import log_message, get_current_date


class StockRequestHandler(http.server.BaseHTTPRequestHandler):
    """股票数据请求处理器"""
    
    @property
    def static_dir(self) -> Path:
        """静态文件目录"""
        return Path(config.BASE_DIR) / 'static'
    
    @property
    def html_file(self) -> Path:
        """HTML 文件路径"""
        return Path(config.BASE_DIR) / 'index.html'
    
    def send_error_response(self, code: int, message: str) -> None:
        """
        向前端返回错误响应
        
        Args:
            code: HTTP 状态码
            message: 错误消息
        """
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode('utf-8'))
    
    def send_success_response(self, data: bytes) -> None:
        """
        向前端返回成功响应
        
        Args:
            data: 响应数据（字节流）
        """
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(data)
    
    def request_api(self, url: str, payload: Dict[str, Any]) -> bytes:
        """
        向理杏仁API请求数据（使用 fundamental_fetcher 模块）
        
        Args:
            url: API 地址
            payload: 请求参数
        
        Returns:
            响应数据的字节流
        """
        return fundamental_fetcher.request_api(url, payload)

    def handle_hk_stock_codes(self) -> Optional[list]:
        """
        从缓存或请求获取所有港股股票代码
        
        Returns:
            股票代码列表，如果失败则返回 None
        """
        today = get_current_date()
        
        # 尝试从缓存读取
        if os.path.exists(config.HK_CODES_CACHE_FILE):
            try:
                with open(config.HK_CODES_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                    if cached.get('date') == today:
                        log_message("使用缓存的港股代码数据")
                        return cached.get('data')
            except (json.JSONDecodeError, IOError) as e:
                log_message(f"读取缓存失败: {e}")

        # 从 API 获取
        payload = {
            "token": config.TOKEN,
            "fsTableType": "non_financial"
        }
        log_message("处理请求: 获取港股代码")
        
        try:
            response_data = json.loads(self.request_api(config.HK_COMPANY_URL, payload))
            total = response_data.get('total', 0)
            log_message(f"请求到所有公司数据，公司数量: {total}")
            
            company_list = response_data.get('data', [])
            stock_codes = [company.get('stockCode') for company in company_list if company.get('stockCode')]

            # 保存到缓存
            try:
                data_to_cache = {
                    "date": today,
                    "data": stock_codes
                }
                with open(config.HK_CODES_CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data_to_cache, f, ensure_ascii=False, indent=2)
                log_message(f"已更新缓存文件: {config.HK_CODES_CACHE_FILE}")
            except IOError as e:
                log_message(f"写入缓存失败: {e}")
            
            return stock_codes
        except Exception as e:
            log_message(f"请求港股所有代码失败: {e}")
            return None

    def send_json_response(self, data: Dict[str, Any]) -> None:
        """
        向前端返回 JSON 响应
        
        Args:
            data: 要返回的数据字典
        """
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def get_stock_fundamentals(self, stock_codes: list, metrics_list: list, date: str) -> Dict[str, Any]:
        """
        接口一：获取指定股票的基本面数据
        
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
            response_data = self.request_api(config.HK_FUNDAMENTAL_URL, payload)
            return json.loads(response_data)
        except Exception as e:
            log_message(f"获取股票基本面数据失败: {e}")
            raise
    
    def filter_stocks_by_metrics(self, metrics_filter: Dict[str, list], date: str) -> Dict[str, Any]:
        """
        接口二：根据基本面范围筛选股票
        
        Args:
            metrics_filter: 筛选条件字典，格式为 {指标名: [min, max]}
            date: 日期字符串
        
        Returns:
            包含筛选后股票数据的字典
        """
        log_message(f"接口二：筛选股票 - 筛选条件={metrics_filter}, 日期={date}")
        
        # 获取所有股票代码
        stock_codes = self.handle_hk_stock_codes()
        if not stock_codes:
            raise Exception("获取股票代码失败")
        
        # 确定需要的指标列表（从筛选条件中提取）
        required_metrics = list(metrics_filter.keys())
        if not required_metrics:
            raise ValueError("metricsFilter 不能为空")
        
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
        
        log_message(f"筛选完成，原始数据量: {len(stocks_data)}, 筛选后数据量: {len(filtered_stocks)}")
        
        return {
            "total": len(filtered_stocks),
            "data": filtered_stocks
        }

    def do_POST(self) -> None:
        """处理 POST 请求"""
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
            self.send_error_response(400, "Invalid JSON body")
            return

        # 根据请求参数路由到不同的接口
        try:
            # 接口二：筛选股票（优先级更高，因为可能同时有 stockCodes 和 metricsFilter）
            if 'metricsFilter' in request_params:
                metrics_filter = request_params.get('metricsFilter')
                if not isinstance(metrics_filter, dict):
                    self.send_error_response(400, "metricsFilter 必须是对象")
                    return
                
                date = request_params.get('date', get_current_date())
                result = self.filter_stocks_by_metrics(metrics_filter, date)
                self.send_json_response(result)
            
            # 接口一：获取指定股票的基本面数据
            elif 'stockCodes' in request_params:
                stock_codes = request_params.get('stockCodes')
                if not stock_codes or not isinstance(stock_codes, list):
                    self.send_error_response(400, "stockCodes 必须是非空数组")
                    return
                
                metrics_list = request_params.get('metricsList', [])
                if not metrics_list or not isinstance(metrics_list, list):
                    self.send_error_response(400, "metricsList 必须是非空数组")
                    return
                
                date = request_params.get('date', get_current_date())
                result = self.get_stock_fundamentals(stock_codes, metrics_list, date)
                self.send_json_response(result)
            
            else:
                self.send_error_response(400, "缺少必要参数：需要提供 stockCodes 或 metricsFilter")
        
        except ValueError as e:
            log_message(f"参数错误: {e}")
            self.send_error_response(400, str(e))
        except Exception as e:
            log_message(f"处理请求失败: {e}")
            self.send_error_response(500, f"Internal Server Error: {str(e)}")

    def do_GET(self) -> None:
        """处理 GET 请求（静态文件和 HTML）"""
        path = self.path.split('?')[0]  # 移除查询参数
        
        # 处理根路径，返回 index.html
        if path == '/' or path == '/index.html':
            self.serve_file(self.html_file, 'text/html')
            return
        
        # 处理静态文件
        if path.startswith('/static/'):
            file_path = self.static_dir / path[8:]  # 移除 '/static/' 前缀
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
                self.serve_file(file_path, mime_type)
            else:
                self.send_error_response(404, "File not found")
            return
        
        # 其他路径返回 404
        self.send_error_response(404, "Not found")
    
    def serve_file(self, file_path: Path, content_type: str) -> None:
        """
        提供静态文件服务
        
        Args:
            file_path: 文件路径
            content_type: 内容类型
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Access-Control-Allow-Origin', '*')
            # 缓存静态资源
            if content_type.startswith('application/javascript') or content_type == 'text/css':
                self.send_header('Cache-Control', 'public, max-age=31536000')  # 1年缓存
            self.end_headers()
            self.wfile.write(content)
        except IOError as e:
            log_message(f"读取文件失败: {e}")
            self.send_error_response(500, "Internal Server Error")
    
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

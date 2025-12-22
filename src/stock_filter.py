#!/usr/bin/env python3
"""
股票筛选工具模块
提供根据基本面指标范围筛选股票的功能
"""

from typing import List, Dict, Any, Optional


def filter_stocks_by_metrics(
    stocks_data: List[Dict[str, Any]],
    metrics_filter: Dict[str, List[Optional[float]]]
) -> List[Dict[str, Any]]:
    """
    根据基本面指标范围筛选股票
    
    Args:
        stocks_data: 股票数据列表，每个元素包含股票代码和各项指标
        metrics_filter: 筛选条件字典，格式为：
            {
                "pe_ttm": [10, 20],      # pe_ttm 在 10-20 之间
                "pb": [1, 3],            # pb 在 1-3 之间
                "mc": [1000000, None]    # mc >= 1000000（max 为 None 表示无上限）
            }
    
    Returns:
        筛选后的股票列表
    """
    if not stocks_data or not metrics_filter:
        return stocks_data
    
    filtered_stocks = []
    
    for stock in stocks_data:
        # 检查该股票是否满足所有筛选条件
        matches_all = True
        
        for metric_name, value_range in metrics_filter.items():
            if not isinstance(value_range, list) or len(value_range) != 2:
                continue
            
            min_value, max_value = value_range
            
            # 获取股票数据中该指标的值
            metric_value = stock.get(metric_name)
            
            # 如果指标值为 None，认为不满足条件
            if metric_value is None:
                matches_all = False
                break
            
            # 尝试转换为浮点数
            try:
                metric_value = float(metric_value)
            except (ValueError, TypeError):
                # 如果无法转换为数字，认为不满足条件
                matches_all = False
                break
            
            # 检查是否在范围内
            if min_value is not None and metric_value < min_value:
                matches_all = False
                break
            
            if max_value is not None and metric_value > max_value:
                matches_all = False
                break
        
        # 如果所有指标都满足条件，添加到结果列表
        if matches_all:
            filtered_stocks.append(stock)
    
    return filtered_stocks


#!/usr/bin/env python3
"""
筛选项配置管理模块
负责读取和保存用户的筛选项配置
"""

import json
import os
from typing import Dict, Any, List

from .. import config
from ..utils import log_message


class FilterConfigManager:
    """筛选项配置管理器"""

    @staticmethod
    def get_filter_config() -> Dict[str, Any]:
        """
        功能：获取用户配置的筛选项

        Returns:
            包含筛选项配置的字典，格式为 {"data": [...]}
        """
        log_message("获取用户筛选项配置")

        # 如果配置文件不存在，返回空数组
        if not os.path.exists(config.FILTER_CONFIG_FILE):
            log_message("筛选项配置文件不存在，返回空配置")
            return {"data": []}

        try:
            with open(config.FILTER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                data = config_data.get('data', [])
                log_message(f"成功读取筛选项配置，共 {len(data)} 项")
                return {"data": data}
        except (json.JSONDecodeError, IOError) as e:
            log_message(f"读取筛选项配置失败: {e}")
            return {"data": []}

    @staticmethod
    def save_filter_config(filter_config: List[Dict[str, Any]]) -> None:
        """
        功能：保存用户配置的筛选项

        Args:
            filter_config: 筛选项配置列表，每个元素包含 key、label、minId、maxId 等字段

        Raises:
            ValueError: 配置格式错误
            Exception: 保存失败
        """
        log_message(f"保存用户筛选项配置，共 {len(filter_config)} 项")

        try:
            # 验证配置格式
            for field in filter_config:
                if not isinstance(field, dict):
                    raise ValueError("筛选项配置格式错误：每个项必须是对象")
                if 'key' not in field or 'label' not in field:
                    raise ValueError("筛选项配置格式错误：必须包含 key 和 label 字段")

            # 保存配置
            config_data = {
                "data": filter_config
            }

            with open(config.FILTER_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            log_message(f"筛选项配置已保存到: {config.FILTER_CONFIG_FILE}")
        except IOError as e:
            log_message(f"保存筛选项配置失败: {e}")
            raise Exception(f"保存配置失败: {e}")


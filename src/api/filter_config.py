#!/usr/bin/env python3
"""
筛选项配置管理模块
负责读取和保存用户的筛选项配置
"""

import json
import os
from typing import Dict, Any, List, Optional

from .. import config
from ..utils import log_message


class FilterConfigManager:
    """筛选项配置管理器"""

    @staticmethod
    def get_filter_config(type_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        功能：获取用户配置的筛选项

        Args:
            type_filter: 可选，过滤类型。'fundamental' 或 'fs'，如果为 None 则返回所有配置

        Returns:
            包含筛选项配置的字典，格式为 {"data": [...]} 或 {"fundamental": [...], "fs": [...]}
        """
        log_message(f"获取用户筛选项配置，类型过滤: {type_filter}")

        # 如果配置文件不存在，返回空数组
        if not os.path.exists(config.FILTER_CONFIG_FILE):
            log_message("筛选项配置文件不存在，返回空配置")
            if type_filter:
                return {type_filter: []}
            return {"fundamental": [], "fs": []}

        try:
            with open(config.FILTER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
                # 兼容旧格式：如果直接是 data 数组，则认为是基本面配置
                if 'data' in config_data and isinstance(config_data['data'], list):
                    data = config_data['data']
                    # 检查是否有 type 字段
                    has_type = any(item.get('type') for item in data if isinstance(item, dict))
                    
                    if has_type:
                        # 新格式：有 type 字段，按类型分组
                        fundamental_data = [item for item in data if item.get('type') == 'fundamental']
                        fs_data = [item for item in data if item.get('type') == 'fs']
                        
                        if type_filter == 'fundamental':
                            log_message(f"成功读取基本面筛选项配置，共 {len(fundamental_data)} 项")
                            return {"data": fundamental_data}
                        elif type_filter == 'fs':
                            log_message(f"成功读取财报筛选项配置，共 {len(fs_data)} 项")
                            return {"data": fs_data}
                        else:
                            log_message(f"成功读取筛选项配置，基本面: {len(fundamental_data)} 项，财报: {len(fs_data)} 项")
                            return {"fundamental": fundamental_data, "fs": fs_data}
                    else:
                        # 旧格式：没有 type 字段，默认为基本面配置
                        if type_filter == 'fundamental' or type_filter is None:
                            log_message(f"成功读取筛选项配置（旧格式），共 {len(data)} 项")
                            if type_filter:
                                return {"data": data}
                            return {"fundamental": data, "fs": []}
                        else:
                            return {"data": []}
                else:
                    # 新格式：直接包含 fundamental 和 fs
                    fundamental_data = config_data.get('fundamental', [])
                    fs_data = config_data.get('fs', [])
                    
                    if type_filter == 'fundamental':
                        return {"data": fundamental_data}
                    elif type_filter == 'fs':
                        return {"data": fs_data}
                    else:
                        return {"fundamental": fundamental_data, "fs": fs_data}
        except (json.JSONDecodeError, IOError) as e:
            log_message(f"读取筛选项配置失败: {e}")
            if type_filter:
                return {type_filter: []}
            return {"fundamental": [], "fs": []}

    @staticmethod
    def save_filter_config(filter_config: List[Dict[str, Any]], config_type: str) -> None:
        """
        功能：保存用户配置的筛选项

        Args:
            filter_config: 筛选项配置列表，每个元素包含 key、label、minId、maxId、type 等字段
            config_type: 配置类型，'fundamental' 或 'fs'

        Raises:
            ValueError: 配置格式错误
            Exception: 保存失败
        """
        if config_type not in ['fundamental', 'fs']:
            raise ValueError("config_type 必须是 'fundamental' 或 'fs'")
        
        log_message(f"保存用户筛选项配置，类型: {config_type}，共 {len(filter_config)} 项")

        try:
            # 验证配置格式
            for field in filter_config:
                if not isinstance(field, dict):
                    raise ValueError("筛选项配置格式错误：每个项必须是对象")
                if 'key' not in field or 'label' not in field:
                    raise ValueError("筛选项配置格式错误：必须包含 key 和 label 字段")
                # 确保每个字段都有 type
                field['type'] = config_type

            # 读取现有配置
            existing_config = FilterConfigManager.get_filter_config()
            fundamental_data = existing_config.get('fundamental', [])
            fs_data = existing_config.get('fs', [])
            
            # 更新对应类型的配置
            if config_type == 'fundamental':
                fundamental_data = filter_config
            else:
                fs_data = filter_config

            # 保存配置（统一格式：data 数组中包含 type 字段）
            all_data = fundamental_data + fs_data
            config_data = {
                "data": all_data
            }

            with open(config.FILTER_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            log_message(f"筛选项配置已保存到: {config.FILTER_CONFIG_FILE}")
        except IOError as e:
            log_message(f"保存筛选项配置失败: {e}")
            raise Exception(f"保存配置失败: {e}")


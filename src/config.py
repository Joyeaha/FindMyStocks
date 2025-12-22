#!/usr/bin/env python3
"""
项目配置模块
"""

import os

# 获取项目根目录的绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
USERDATA_DIR = os.path.join(BASE_DIR, 'userdata')

# 确保缓存目录和用户数据目录存在
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(USERDATA_DIR, exist_ok=True)

# 服务器配置
PORT = 8001

# API 配置
TOKEN = '0d9a65fe-d808-4577-95b5-2bd190fdd409'
HK_COMPANY_URL = 'https://open.lixinger.com/api/hk/company'
HK_FUNDAMENTAL_URL = 'https://open.lixinger.com/api/hk/company/fundamental/non_financial'
HK_FS_URL = 'https://open.lixinger.com/api/hk/company/fs/non_financial'

# 缓存文件路径
HK_STOCKS_CACHE_FILE = os.path.join(CACHE_DIR, 'hk_stocks_cache.json')
FUNDAMENTAL_CACHE_FILE = os.path.join(CACHE_DIR, 'fundamental_cache.json')

# 用户数据文件路径
FILTER_CONFIG_FILE = os.path.join(USERDATA_DIR, 'filter_config.json')

# 缓存配置
FUNDAMENTAL_CACHE_EXPIRE_DAYS = 3

# API 请求配置
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 10  # 秒
MAX_WORKERS = 10  # 最大并发数
BATCH_SIZE = 100  # 每批处理的股票数量


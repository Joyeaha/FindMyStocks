#!/bin/bash

# 股票筛选工具一键启动脚本

echo "=========================================="
echo "  股票筛选工具 - 启动中..."
echo "=========================================="

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请先安装 Python 3"
    exit 1
fi

# 检查必要的文件
if [ ! -f "index.html" ]; then
    echo "错误: 未找到 index.html 文件"
    exit 1
fi

if [ ! -f "static/tailwindcss.min.js" ]; then
    echo "警告: 未找到 Tailwind CSS 文件，正在下载..."
    mkdir -p static
    curl -L -o static/tailwindcss.min.js https://cdn.tailwindcss.com/3.4.1 || {
        echo "错误: 下载 Tailwind CSS 失败"
        exit 1
    }
fi

# 检查端口是否被占用
PORT=8001
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "警告: 端口 $PORT 已被占用"·
    echo "正在尝试终止占用该端口的进程..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    sleep 1
fi

# 启动服务器·       
echo ""
echo "正在启动服务器..."
echo "服务器地址: http://localhost:$PORT"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "=========================================="
echo ""

python3 run_server.py



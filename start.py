#!/usr/bin/env python3
"""
股票筛选工具一键启动脚本（Python版本）
"""

import sys
import os
import subprocess
import webbrowser
import time
from pathlib import Path

def check_python():
    """检查 Python 版本"""
    if sys.version_info < (3, 6):
        print("错误: 需要 Python 3.6 或更高版本")
        sys.exit(1)
    print(f"✓ Python 版本: {sys.version.split()[0]}")

def check_files():
    """检查必要的文件"""
    base_dir = Path(__file__).parent
    
    if not (base_dir / "index.html").exists():
        print("错误: 未找到 index.html 文件")
        sys.exit(1)
    print("✓ 找到 index.html")
    
    static_dir = base_dir / "static"
    tailwind_file = static_dir / "tailwindcss.min.js"
    
    if not tailwind_file.exists():
        print("警告: 未找到 Tailwind CSS 文件，正在下载...")
        static_dir.mkdir(exist_ok=True)
        try:
            import urllib.request
            urllib.request.urlretrieve(
                "https://cdn.tailwindcss.com/3.4.1",
                tailwind_file
            )
            print("✓ Tailwind CSS 下载完成")
        except Exception as e:
            print(f"错误: 下载 Tailwind CSS 失败: {e}")
            sys.exit(1)
    else:
        print("✓ 找到 Tailwind CSS 文件")

def check_port(port):
    """检查端口是否被占用"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0

def kill_port(port):
    """终止占用指定端口的进程"""
    try:
        if sys.platform == 'darwin':  # macOS
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    subprocess.run(['kill', '-9', pid], check=False)
                print(f"✓ 已终止占用端口 {port} 的进程")
        elif sys.platform.startswith('linux'):  # Linux
            result = subprocess.run(
                ['fuser', '-k', f'{port}/tcp'],
                capture_output=True,
                stderr=subprocess.DEVNULL
            )
            print(f"✓ 已终止占用端口 {port} 的进程")
    except Exception:
        pass

def main():
    """主函数"""
    print("=" * 50)
    print("  股票筛选工具 - 启动中...")
    print("=" * 50)
    print()
    
    # 检查环境
    check_python()
    check_files()
    
    # 检查并处理端口占用
    port = 8001
    if check_port(port):
        print(f"警告: 端口 {port} 已被占用")
        kill_port(port)
        time.sleep(1)
    
    # 启动服务器
    print()
    print("=" * 50)
    print(f"  服务器地址: http://localhost:{port}")
    print("  按 Ctrl+C 停止服务器")
    print("=" * 50)
    print()
    
    # 延迟打开浏览器
    def open_browser():
        time.sleep(1)
        webbrowser.open(f'http://localhost:{port}')
    
    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # 启动服务器
    try:
        from src.server import StockRequestHandler
        from src.config import PORT
        import socketserver
        
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), StockRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
    except Exception as e:
        print(f"\n错误: 启动服务器失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()



#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行前端服务器的入口文件
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frontend.app import frontend_app

if __name__ == '__main__':
    print("=" * 50)
    print("前端界面服务器启动中...")
    print("访问地址: http://127.0.0.1:5001")
    print("=" * 50)
    print("=" * 50)
    print("注意：请确保后端服务器(backend.py)已启动")
    print("=" * 50)

    # 前端服务器运行在5001端口
    frontend_app.run(host='0.0.0.0', port=5001, debug=True)


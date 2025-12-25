"""
前端工具函数模块
"""
import os
import requests

# 后端API地址
BACKEND_URL = "http://127.0.0.1:5000"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "host-secret")
ADMIN_HEADERS = {'X-Admin-Token': ADMIN_TOKEN}


def get_backend_data(endpoint, use_admin=False):
    """从后端获取数据"""
    try:
        headers = ADMIN_HEADERS if use_admin else None
        response = requests.get(f"{BACKEND_URL}{endpoint}", headers=headers, timeout=2)
        return response.json()
    except:
        return None


def post_backend_data(endpoint, data):
    """向后端发送POST请求"""
    try:
        response = requests.post(f"{BACKEND_URL}{endpoint}", json=data, timeout=2)
        return response.json()
    except:
        return None


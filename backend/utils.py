"""
后端工具函数模块
"""
from flask import request, jsonify
from typing import Dict, Optional
import socket
from backend.config import ADMIN_TOKEN

# 这些变量需要在运行时从app.py注入
game = None
game_lock = None
group_sockets = None
socketio = None


def init_utils(game_instance, lock, sockets_dict, socketio_instance):
    """初始化工具函数需要的全局变量"""
    global game, game_lock, group_sockets, socketio
    game = game_instance
    game_lock = lock
    group_sockets = sockets_dict
    socketio = socketio_instance


def get_local_ip():
    """获取本机局域网IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def require_admin():
    """校验主持方权限"""
    header_token = request.headers.get("X-Admin-Token", "")
    return header_token == ADMIN_TOKEN


def admin_forbidden_response():
    """返回无权限响应"""
    return make_response({}, 403, '无权限：需要主持方令牌')


def make_response(data=None, code=200, message="ok"):
    """统一响应格式"""
    payload = {
        "code": code,
        "message": message,
        "data": data or {}
    }
    return jsonify(payload), code


def get_websocket_status() -> Optional[Dict[str, bool]]:
    """
    获取各组基于WebSocket的连接状态
    如果没有WebSocket连接，则返回None，让get_online_status使用HTTP活跃时间降级方案
    """
    global game, group_sockets
    
    if game is None or group_sockets is None:
        return None
    
    # 检查是否有任何WebSocket连接
    has_any_connection = any(len(socket_ids) > 0 for socket_ids in group_sockets.values())
    
    if not has_any_connection:
        # 没有任何WebSocket连接，返回None，使用HTTP活跃时间降级
        return None
    
    # 有WebSocket连接，返回WebSocket连接状态
    websocket_status = {}
    for group_name in game.groups.keys():
        socket_ids = group_sockets.get(group_name, set())
        websocket_status[group_name] = len(socket_ids) > 0
    return websocket_status


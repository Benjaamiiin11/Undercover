"""
后端模块
"""
from .app import app, socketio, game, game_lock, group_sockets

__all__ = ['app', 'socketio', 'game', 'game_lock', 'group_sockets']


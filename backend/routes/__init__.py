"""
后端路由模块
"""
from .game import register_game_routes, init_game_routes
from .player import register_player_routes, init_player_routes
from .public import register_public_routes, init_public_routes


def register_all_routes(app):
    """注册所有路由"""
    register_game_routes(app)
    register_player_routes(app)
    register_public_routes(app)


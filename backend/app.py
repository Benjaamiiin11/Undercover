"""
后端服务器主入口
"""
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from game_logic import GameLogic
import threading
from typing import Dict

# 导入配置
from backend.config import WORD_PAIRS
from backend.utils import init_utils, get_local_ip
from backend.services import init_broadcast, init_timer
from backend.routes.game import init_game_routes
from backend.routes.player import init_player_routes
from backend.routes.public import init_public_routes
from backend.websocket.handlers import init_websocket_handlers
from backend.routes import register_all_routes
from backend.websocket import register_websocket_handlers

# Flask应用初始化
app = Flask(__name__)
CORS(app)  # 允许跨域请求
socketio = SocketIO(app, cors_allowed_origins="*")  # WebSocket支持

# 全局游戏逻辑实例
game = GameLogic()

# 线程锁，保证线程安全
game_lock = threading.Lock()

# WebSocket连接追踪：group_name -> set of session_ids
group_sockets: Dict[str, set] = {}  # 每个组对应的WebSocket连接ID集合

# 初始化所有模块
init_utils(game, game_lock, group_sockets, socketio)
init_broadcast(game, game_lock, socketio)
init_timer(game, game_lock, socketio)
init_game_routes(game, game_lock, socketio)
init_player_routes(game, game_lock, socketio)
init_public_routes(game, game_lock)
init_websocket_handlers(game, game_lock, group_sockets, socketio)

# 注册路由和WebSocket处理器
register_all_routes(app)
register_websocket_handlers(socketio)


if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"=" * 50)
    print(f"谁是卧底 - 主持方平台")
    print(f"=" * 50)
    print(f"服务器启动中...")
    print(f"本地访问: http://127.0.0.1:5000")
    print(f"局域网访问: http://{local_ip}:5000")
    print(f"WebSocket: 已启用实时推送")
    print(f"词库: {len(WORD_PAIRS)} 对词语")
    print(f"=" * 50)
    print(f"请确保游戏方能够访问上述IP地址")
    print(f"=" * 50)

    # 使用 socketio.run 替代 app.run
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)


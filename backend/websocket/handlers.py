"""
WebSocket事件处理模块
"""
from flask import request
from flask_socketio import emit
from datetime import datetime
from backend.utils import get_websocket_status
from backend.services import broadcast_status, broadcast_game_state, broadcast_groups, broadcast_scores, stop_timer_broadcast

# 这些变量需要在运行时注入
game = None
game_lock = None
group_sockets = None
socketio = None


def init_websocket_handlers(game_instance, lock, sockets_dict, socketio_instance):
    """初始化WebSocket处理器"""
    global game, game_lock, group_sockets, socketio
    game = game_instance
    game_lock = lock
    group_sockets = sockets_dict
    socketio = socketio_instance


def register_websocket_handlers(socketio_app):
    """注册WebSocket事件处理器"""
    
    @socketio_app.on('connect')
    def handle_connect():
        """客户端连接时发送当前状态"""
        with game_lock:
            websocket_status = get_websocket_status()
            status = game.get_public_status()
            # 更新在线状态（使用WebSocket连接状态）
            status['online_status'] = game.get_online_status(websocket_status)
        emit('status_update', status)

    @socketio_app.on('register_socket')
    def handle_register_socket(data):
        """客户端注册WebSocket连接（关联group_name和socket）"""
        group_name = data.get('group_name', '').strip()
        if not group_name:
            emit('error', {'message': '组名不能为空'})
            return
        
        sid = request.sid  # 获取当前连接的session ID
        
        with game_lock:
            # 将socket ID关联到组名
            if group_name not in group_sockets:
                group_sockets[group_name] = set()
            group_sockets[group_name].add(sid)
            
            # 更新活跃时间
            game.update_activity(group_name)
        
        emit('socket_registered', {'group_name': group_name, 'status': 'success'})

    @socketio_app.on('disconnect')
    def handle_disconnect():
        """客户端断开连接时自动检测并处理"""
        sid = request.sid
        
        with game_lock:
            # 找到断开连接的组
            disconnected_groups = []
            for group_name, socket_ids in list(group_sockets.items()):
                if sid in socket_ids:
                    socket_ids.remove(sid)
                    # 如果这个组没有其他连接了
                    if len(socket_ids) == 0:
                        disconnected_groups.append(group_name)
                        # 处理断开连接（视为退出游戏）
                        result = game.handle_disconnect(group_name)
                        if result:
                            # 如果有游戏结果（游戏结束），广播结果
                            if result.get('game_ended'):
                                stop_timer_broadcast()
                                socketio.emit('vote_result', result)
                                # 广播分数更新（因为游戏结束可能计算了分数）
                                socketio.start_background_task(broadcast_scores)
                            # 广播状态更新
                            socketio.start_background_task(broadcast_status)
                            socketio.start_background_task(broadcast_game_state)
                            # 广播组列表更新（因为可能有组被标记为淘汰）
                            socketio.start_background_task(broadcast_groups)
            
            # 清理空的socket集合
            for group_name in disconnected_groups:
                if group_name in group_sockets and len(group_sockets[group_name]) == 0:
                    del group_sockets[group_name]

    @socketio_app.on('request_status')
    def handle_request_status():
        """客户端请求状态更新"""
        with game_lock:
            websocket_status = get_websocket_status()
            status = game.get_public_status()
            # 更新在线状态（使用WebSocket连接状态）
            status['online_status'] = game.get_online_status(websocket_status)
        emit('status_update', status)

    @socketio_app.on('request_timer')
    def handle_request_timer():
        """客户端请求倒计时更新"""
        with game_lock:
            websocket_status = get_websocket_status()
            status = game.get_public_status()
            # 更新在线状态（使用WebSocket连接状态）
            status['online_status'] = game.get_online_status(websocket_status)
            # 添加精确的时间信息
            now = datetime.now()
            if game.phase_deadline:
                remaining = max(0, int((game.phase_deadline - now).total_seconds()))
                status['remaining_seconds'] = remaining

            if game.speaker_deadline and status.get('status') == 'describing':
                speaker_remaining = max(0, int((game.speaker_deadline - now).total_seconds()))
                status['speaker_remaining_seconds'] = speaker_remaining

        emit('timer_update', status)


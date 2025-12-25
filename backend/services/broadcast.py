"""
广播服务模块
"""
from backend.utils import get_websocket_status

# 这些变量需要在运行时注入
game = None
game_lock = None
socketio = None


def init_broadcast(game_instance, lock, socketio_instance):
    """初始化广播服务"""
    global game, game_lock, socketio
    game = game_instance
    game_lock = lock
    socketio = socketio_instance


def broadcast_status():
    """广播游戏状态变化"""
    with game_lock:
        websocket_status = get_websocket_status()
        status = game.get_public_status()
        # 更新在线状态（使用WebSocket连接状态）
        status['online_status'] = game.get_online_status(websocket_status)
    socketio.emit('status_update', status)


def broadcast_game_state():
    """广播完整游戏状态（主持方用）"""
    with game_lock:
        websocket_status = get_websocket_status()
        state = game.get_game_state()
        # 更新在线状态（使用WebSocket连接状态）
        state['online_status'] = game.get_online_status(websocket_status)
    socketio.emit('game_state_update', state)


def broadcast_descriptions():
    """广播描述列表更新"""
    with game_lock:
        round_num = game.current_round
        descriptions = game.descriptions.get(round_num, [])
        result = []
        for desc in descriptions:
            result.append({
                'group': desc['group'],
                'description': desc['description'],
                'time': desc.get('time', '')  # 包含时间字段
            })
        
        socketio.emit('descriptions_update', {
            'round': round_num,
            'descriptions': result,
            'total': len(result)
        })


def broadcast_groups():
    """广播组列表更新"""
    with game_lock:
        groups_info = []
        for name, info in game.groups.items():
            groups_info.append({
                'name': name,
                'registered_time': info['registered_time'],
                'eliminated': name in game.eliminated_groups
            })
        
        socketio.emit('groups_update', {
            'groups': groups_info,
            'total': len(groups_info)
        })


def broadcast_scores():
    """广播分数更新"""
    with game_lock:
        # 按分数排序（从高到低）
        sorted_scores = sorted(
            game.scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # 构建返回数据
        scores_list = [
            {
                'group_name': group_name,
                'total_score': score
            }
            for group_name, score in sorted_scores
        ]
        
        socketio.emit('scores_update', {
            'scores': scores_list,
            'total_groups': len(scores_list)
        })


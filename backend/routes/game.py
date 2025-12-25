"""
游戏控制路由模块（主持方专用）
"""
from flask import request
from backend.utils import require_admin, admin_forbidden_response, make_response, get_websocket_status
from backend.services import broadcast_status, broadcast_game_state, broadcast_descriptions, broadcast_groups, broadcast_scores, start_timer_broadcast, stop_timer_broadcast
from backend.config import WORD_PAIRS
import random

# 这些变量需要在运行时注入
game = None
game_lock = None
socketio = None


def init_game_routes(game_instance, lock, socketio_instance):
    """初始化游戏路由"""
    global game, game_lock, socketio
    game = game_instance
    game_lock = lock
    socketio = socketio_instance


def register_game_routes(app):
    """注册游戏控制路由"""
    
    @app.route('/api/game/start', methods=['POST'])
    def start_game():
        """开始游戏接口（主持方调用）"""
        if not require_admin():
            return admin_forbidden_response()
        data = request.json
        undercover_word = data.get('undercover_word', '').strip()
        civilian_word = data.get('civilian_word', '').strip()

        # 如果词语为空，从词库随机选择
        if (not undercover_word or not civilian_word) and WORD_PAIRS:
            civilian_word, undercover_word = random.choice(WORD_PAIRS)
            print(f"自动选词: 平民词={civilian_word}, 卧底词={undercover_word}")
        elif not undercover_word or not civilian_word:
            return make_response({}, 400, '词语不能为空，且词库未加载')

        with game_lock:
            websocket_status = get_websocket_status()
            success = game.start_game(undercover_word, civilian_word, websocket_status)
            if success:
                # 游戏开始后不启动倒计时，等待玩家准备后再开始回合
                # 广播状态变化
                socketio.start_background_task(broadcast_status)
                socketio.start_background_task(broadcast_game_state)
                # 广播组列表更新（因为可能有离线玩家被标记为淘汰）
                socketio.start_background_task(broadcast_groups)
                
                # 只返回在线玩家的角色信息
                online_status = game.get_online_status(websocket_status)
                online_groups = {name: info['role'] for name, info in game.groups.items() 
                               if online_status.get(name, False) and info.get('role') is not None}
                
                return make_response({
                    'undercover_group': game.undercover_group,
                    'groups': online_groups,
                    'civilian_word': civilian_word,
                    'undercover_word': undercover_word,
                    'excluded_groups': [name for name in game.groups.keys() 
                                      if not online_status.get(name, False)]
                }, 200, '游戏已开始，等待玩家准备（离线玩家已排除）')
            else:
                return make_response({}, 400, '无法开始游戏：游戏状态不正确或没有在线的组')

    @app.route('/api/game/round/start', methods=['POST'])
    def start_round():
        """开始新回合接口（主持方调用）"""
        if not require_admin():
            return admin_forbidden_response()
        with game_lock:
            order = game.start_round()
            if order:
                # 启动倒计时广播
                start_timer_broadcast()
                # 广播状态变化
                socketio.start_background_task(broadcast_status)
                socketio.start_background_task(broadcast_game_state)
                # 广播描述列表更新（新回合开始时描述列表被清空）
                socketio.start_background_task(broadcast_descriptions)
                return make_response({
                    'round': game.current_round,
                    'order': order
                }, 200, '回合已开始')
            else:
                return make_response({}, 400, '无法开始回合：游戏状态不正确或活跃组数不足')

    @app.route('/api/game/voting/process', methods=['POST'])
    def process_voting():
        """处理投票结果接口（主持方调用）"""
        if not require_admin():
            return admin_forbidden_response()
        with game_lock:
            # 处理投票前，先检测未提交的组并自动记录异常
            result = game.process_voting_result()
            if 'error' in result:
                return make_response(result, 400, result.get('error', '投票处理失败'))
            # 停止倒计时广播
            stop_timer_broadcast()
            # 广播状态变化
            socketio.start_background_task(broadcast_status)
            socketio.start_background_task(broadcast_game_state)
            # 广播投票结果
            socketio.emit('vote_result', result)
            # 广播分数更新（因为分数可能变化）
            socketio.start_background_task(broadcast_scores)
            
            # 如果游戏未结束且处于 ROUND_END 状态，自动开始下一回合
            if not result.get('game_ended') and game.game_status.value == 'round_end':
                order = game.start_round()
                if order:
                    # 启动倒计时广播
                    start_timer_broadcast()
                    # 广播状态变化
                    socketio.start_background_task(broadcast_status)
                    socketio.start_background_task(broadcast_game_state)
                    # 广播描述列表更新（新回合开始时描述列表被清空）
                    socketio.start_background_task(broadcast_descriptions)
            
            return make_response(result, 200, '投票结果已生成')

    @app.route('/api/game/state', methods=['GET'])
    def get_game_state():
        """获取游戏状态接口"""
        if not require_admin():
            return admin_forbidden_response()
        with game_lock:
            websocket_status = get_websocket_status()
            state = game.get_game_state()
            # 更新在线状态（使用WebSocket连接状态）
            state['online_status'] = game.get_online_status(websocket_status)
            return make_response(state)

    @app.route('/api/game/reset', methods=['POST'])
    def reset_game():
        """重置游戏接口（主持方调用）"""
        if not require_admin():
            return admin_forbidden_response()
        with game_lock:
            game.reset_game()
            # 停止倒计时广播
            stop_timer_broadcast()
            # 广播状态变化
            socketio.start_background_task(broadcast_status)
            socketio.start_background_task(broadcast_game_state)
            # 广播组列表和分数更新（重置后数据变化）
            socketio.start_background_task(broadcast_groups)
            socketio.start_background_task(broadcast_scores)
            return make_response({}, 200, '游戏已重置')

    @app.route('/api/game/clear_all', methods=['POST'])
    def clear_all():
        """完全清空所有组和缓存接口（主持方调用）"""
        if not require_admin():
            return admin_forbidden_response()
        with game_lock:
            game.clear_all()
            # 停止倒计时广播
            stop_timer_broadcast()
            # 广播状态变化
            socketio.start_background_task(broadcast_status)
            socketio.start_background_task(broadcast_game_state)
            # 广播组列表和分数更新（清空后数据变化）
            socketio.start_background_task(broadcast_groups)
            socketio.start_background_task(broadcast_scores)
            return make_response({}, 200, '已清空所有组和缓存')


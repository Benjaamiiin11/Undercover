"""
玩家相关路由模块（游戏方调用）
"""
from flask import request
from backend.utils import make_response, get_websocket_status
from backend.services import broadcast_status, broadcast_game_state, broadcast_descriptions, broadcast_groups, start_timer_broadcast, stop_timer_broadcast, broadcast_scores

# 这些变量需要在运行时注入
game = None
game_lock = None
socketio = None


def init_player_routes(game_instance, lock, socketio_instance):
    """初始化玩家路由"""
    global game, game_lock, socketio
    game = game_instance
    game_lock = lock
    socketio = socketio_instance


def register_player_routes(app):
    """注册玩家相关路由"""
    
    @app.route('/api/register', methods=['POST'])
    def register():
        """游戏方注册接口"""
        data = request.json
        group_name = data.get('group_name') or data.get('group_id', '')
        group_name = group_name.strip() if isinstance(group_name, str) else ''

        if not group_name:
            return make_response({}, 400, '组名不能为空')

        with game_lock:
            success = game.register_group(group_name)
            if success:
                # 广播状态变化
                socketio.start_background_task(broadcast_status)
                socketio.start_background_task(broadcast_game_state)
                # 广播组列表更新
                socketio.start_background_task(broadcast_groups)
                return make_response({
                    'group_name': group_name,
                    'total_groups': len(game.groups)
                }, 200, '注册成功')
            else:
                return make_response({}, 400, '注册失败：组名已存在或已达到最大组数(5组)')

    @app.route('/api/describe', methods=['POST'])
    def submit_description():
        """提交描述接口（游戏方调用）"""
        data = request.json
        group_name = data.get('group_name', '').strip()
        description = data.get('description', '').strip()

        if not group_name or not description:
            return make_response({}, 400, '组名和描述不能为空')

        with game_lock:
            success, message = game.submit_description(group_name, description)
            if success:
                # 广播状态变化
                socketio.start_background_task(broadcast_status)
                socketio.start_background_task(broadcast_game_state)
                # 广播描述列表更新
                socketio.start_background_task(broadcast_descriptions)
                # 获取当前描述列表
                current_descriptions = game.descriptions.get(game.current_round, [])
                return make_response({
                    'round': game.current_round,
                    'total_descriptions': len(current_descriptions)
                }, 200, message)
            else:
                # 返回当前状态
                websocket_status = get_websocket_status()
                status = game.get_public_status()
                # 更新在线状态（使用WebSocket连接状态）
                status['online_status'] = game.get_online_status(websocket_status)
                return make_response({
                    'current_speaker': game.get_current_speaker(),
                    'status': status.get('status'),
                    'is_eliminated': group_name in game.eliminated_groups
                }, 200, message)

    @app.route('/api/vote', methods=['POST'])
    def submit_vote():
        """提交投票接口（游戏方调用）"""
        data = request.json
        voter_group = data.get('voter_group', '').strip()
        target_group = data.get('target_group', '').strip()

        if not voter_group or not target_group:
            return make_response({}, 400, '投票者和被投票者不能为空')

        with game_lock:
            success, message, all_voted = game.submit_vote(voter_group, target_group)
            
            if success:
                # 广播状态变化
                socketio.start_background_task(broadcast_status)
                
                # 如果所有人都投票了，自动处理投票结果
                if all_voted:
                    vote_result = game.process_voting_result()
                    if 'error' not in vote_result:
                        # 停止倒计时广播
                        stop_timer_broadcast()
                        # 广播状态变化
                        socketio.start_background_task(broadcast_status)
                        socketio.start_background_task(broadcast_game_state)
                        # 广播投票结果
                        socketio.emit('vote_result', vote_result)
                        # 广播分数更新（因为分数可能变化）
                        socketio.start_background_task(broadcast_scores)
                        
                        # 如果游戏未结束且处于 ROUND_END 状态，自动开始下一回合
                        if not vote_result.get('game_ended') and game.game_status.value == 'round_end':
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
                            'auto_processed': True,
                            'vote_result': vote_result
                        }, 200, '投票提交成功，投票结果已自动处理')
                
                return make_response({}, 200, message or '投票提交成功')
            else:
                # 返回淘汰状态
                is_eliminated = voter_group in game.eliminated_groups
                return make_response({
                    'is_eliminated': is_eliminated
                }, 400, message or '投票提交失败')

    @app.route('/api/ready', methods=['POST'])
    def submit_ready():
        """提交准备就绪接口（游戏方调用）"""
        data = request.json
        group_name = data.get('group_name', '').strip()

        if not group_name:
            return make_response({}, 400, '组名不能为空')

        with game_lock:
            success, message, all_ready = game.submit_ready(group_name)
            
            if success:
                # 广播状态变化
                socketio.start_background_task(broadcast_status)
                socketio.start_background_task(broadcast_game_state)
                
                # 如果所有人都准备好了，自动开始回合
                if all_ready:
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
                            'auto_started': True,
                            'round': game.current_round,
                            'order': order
                        }, 200, '所有人已准备好，回合已自动开始')
                    else:
                        return make_response({}, 400, '所有人已准备好，但无法开始回合')
                
                return make_response({}, 200, message or '准备成功')
            else:
                return make_response({}, 400, message or '准备失败')


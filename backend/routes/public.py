"""
公开API路由模块（游戏方查询接口）
"""
from flask import request
from backend.utils import make_response, get_websocket_status

# 这些变量需要在运行时注入
game = None
game_lock = None


def init_public_routes(game_instance, lock):
    """初始化公开路由"""
    global game, game_lock
    game = game_instance
    game_lock = lock


def register_public_routes(app):
    """注册公开API路由"""
    
    @app.route('/api/status', methods=['GET'])
    def public_status():
        """游戏方公共状态接口"""
        # 可选的组名参数，用于更新活跃时间
        group_name = request.args.get('group_name', '').strip()

        with game_lock:
            # 如果提供了组名，更新活跃时间
            if group_name:
                game.update_activity(group_name)
            websocket_status = get_websocket_status()
            status = game.get_public_status()
            # 更新在线状态（使用WebSocket连接状态）
            status['online_status'] = game.get_online_status(websocket_status)
            # 添加是否为淘汰组的信息
            if group_name:
                status['is_eliminated'] = group_name in game.eliminated_groups
            return make_response(status)

    @app.route('/api/result', methods=['GET'])
    def public_result():
        """最近一次投票结果"""
        with game_lock:
            result = game.get_last_result()
            if not result:
                return make_response({}, 404, '当前暂无投票结果')
            return make_response(result)

    @app.route('/api/word', methods=['GET'])
    def get_word():
        """获取词语接口（游戏方调用，仅返回自己的词语）"""
        group_name = request.args.get('group_name', '').strip()

        if not group_name:
            return make_response({}, 400, '组名不能为空')

        with game_lock:
            # 检查是否被淘汰（淘汰组也可以看到自己的词语）
            word = game.get_group_word(group_name)
            if word:
                return make_response({'word': word})
            else:
                return make_response({}, 404, '未找到该组的词语或游戏未开始')

    @app.route('/api/descriptions', methods=['GET'])
    def get_descriptions():
        """获取当前回合的描述列表（游戏方调用）"""
        round_num = request.args.get('round', type=int)

        with game_lock:
            if round_num is None:
                round_num = game.current_round

            descriptions = game.descriptions.get(round_num, [])
            result = []
            for desc in descriptions:
                result.append({
                    'group': desc['group'],
                    'description': desc['description']
                })

            return make_response({
                'round': round_num,
                'descriptions': result,
                'total': len(result)
            })

    @app.route('/api/groups', methods=['GET'])
    def get_groups():
        """获取所有注册的组接口"""
        with game_lock:
            groups_info = []
            for name, info in game.groups.items():
                groups_info.append({
                    'name': name,
                    'registered_time': info['registered_time'],
                    'eliminated': name in game.eliminated_groups
                })
            return make_response({
                'groups': groups_info,
                'total': len(groups_info)
            })

    @app.route('/api/vote/details', methods=['GET'])
    def get_vote_details():
        """获取详细的投票信息（游戏方调用）"""
        group_name = request.args.get('group_name', '').strip()

        if not group_name:
            return make_response({}, 400, '组名不能为空')

        with game_lock:
            result = game.get_vote_details_for_group(group_name)
            return make_response(result)

    @app.route('/api/scores', methods=['GET'])
    def get_scores():
        """获取所有组的总分接口（游戏方调用）"""
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
            
            return make_response({
                'scores': scores_list,
                'total_groups': len(scores_list)
            })


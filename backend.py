"""
后端服务器模块
提供RESTful API接口，处理游戏方的请求
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from game_logic import GameLogic, GameStatus
import os
import threading
import socket
import time
from datetime import datetime
from threading import Thread

app = Flask(__name__)
CORS(app)  # 允许跨域请求
socketio = SocketIO(app, cors_allowed_origins="*")  # WebSocket支持

# 管理员令牌（主持方专用）
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "host-secret")

# 全局游戏逻辑实例
game = GameLogic()

# 线程锁，保证线程安全
game_lock = threading.Lock()

# 倒计时推送线程
timer_thread = None
timer_running = False


def timer_broadcast_loop():
    """定期广播倒计时"""
    global timer_running
    while timer_running:
        try:
            with game_lock:
                status = game.get_public_status()
                # 只有描述或投票阶段才广播倒计时
                if status.get('status') in ['describing', 'voting']:
                    # 添加精确的时间信息
                    now = datetime.now()
                    if game.phase_deadline:
                        remaining = max(0, int((game.phase_deadline - now).total_seconds()))
                        status['remaining_seconds'] = remaining

                    if game.speaker_deadline and status.get('status') == 'describing':
                        speaker_remaining = max(0, int((game.speaker_deadline - now).total_seconds()))
                        status['speaker_remaining_seconds'] = speaker_remaining

                    socketio.emit('timer_update', status)

            time.sleep(1)  # 每秒更新一次
        except Exception as e:
            print(f"定时器广播错误: {e}")
            time.sleep(1)


def start_timer_broadcast():
    """启动倒计时广播线程"""
    global timer_thread, timer_running
    if timer_thread is None or not timer_thread.is_alive():
        timer_running = True
        timer_thread = Thread(target=timer_broadcast_loop, daemon=True)
        timer_thread.start()
        print("倒计时广播线程已启动")


def stop_timer_broadcast():
    """停止倒计时广播线程"""
    global timer_running
    timer_running = False
    print("倒计时广播线程已停止")


def broadcast_status():
    """广播游戏状态变化"""
    with game_lock:
        status = game.get_public_status()
    socketio.emit('status_update', status)


def broadcast_game_state():
    """广播完整游戏状态（主持方用）"""
    with game_lock:
        state = game.get_game_state()
    socketio.emit('game_state_update', state)


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


def _require_admin():
    """校验主持方权限"""
    header_token = request.headers.get("X-Admin-Token", "")
    return header_token == ADMIN_TOKEN


def _admin_forbidden_response():
    return make_response({}, 403, '无权限：需要主持方令牌')


def make_response(data=None, code=200, message="ok"):
    payload = {
        "code": code,
        "message": message,
        "data": data or {}
    }
    return jsonify(payload), code


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
            return make_response({
                'group_name': group_name,
                'total_groups': len(game.groups)
            }, 200, '注册成功')
        else:
            return make_response({}, 400, '注册失败：组名已存在或已达到最大组数(5组)')


@app.route('/api/game/start', methods=['POST'])
def start_game():
    """开始游戏接口（主持方调用）"""
    if not _require_admin():
        return _admin_forbidden_response()
    data = request.json
    undercover_word = data.get('undercover_word', '').strip()
    civilian_word = data.get('civilian_word', '').strip()

    if not undercover_word or not civilian_word:
        return make_response({}, 400, '词语不能为空')

    with game_lock:
        success = game.start_game(undercover_word, civilian_word)
        if success:
            # 启动倒计时广播
            start_timer_broadcast()
            # 广播状态变化
            socketio.start_background_task(broadcast_status)
            socketio.start_background_task(broadcast_game_state)
            return make_response({
                'undercover_group': game.undercover_group,
                'groups': {name: info['role'] for name, info in game.groups.items()}
            }, 200, '游戏已开始')
        else:
            return make_response({}, 400, '无法开始游戏：游戏状态不正确或没有注册的组')


@app.route('/api/game/round/start', methods=['POST'])
def start_round():
    """开始新回合接口（主持方调用）"""
    if not _require_admin():
        return _admin_forbidden_response()
    with game_lock:
        order = game.start_round()
        if order:
            # 启动倒计时广播
            start_timer_broadcast()
            # 广播状态变化
            socketio.start_background_task(broadcast_status)
            socketio.start_background_task(broadcast_game_state)
            return make_response({
                'round': game.current_round,
                'order': order
            }, 200, '回合已开始')
        else:
            return make_response({}, 400, '无法开始回合：游戏状态不正确或活跃组数不足')


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
            # 获取当前描述列表
            current_descriptions = game.descriptions.get(game.current_round, [])
            return make_response({
                'round': game.current_round,
                'total_descriptions': len(current_descriptions)
            }, 200, message)
        else:
            # 返回当前状态
            status = game.get_public_status()
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
        success, message = game.submit_vote(voter_group, target_group)
        if success:
            # 广播状态变化
            socketio.start_background_task(broadcast_status)
            return make_response({}, 200, message or '投票提交成功')
        else:
            # 返回淘汰状态
            is_eliminated = voter_group in game.eliminated_groups
            return make_response({
                'is_eliminated': is_eliminated
            }, 400, message or '投票提交失败')


@app.route('/api/game/voting/process', methods=['POST'])
def process_voting():
    """处理投票结果接口（主持方调用）"""
    if not _require_admin():
        return _admin_forbidden_response()
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
        return make_response(result, 200, '投票结果已生成')


@app.route('/api/game/state', methods=['GET'])
def get_game_state():
    """获取游戏状态接口"""
    if not _require_admin():
        return _admin_forbidden_response()
    with game_lock:
        # 获取状态时自动检测未提交的组
        missing_reports = game.detect_missing_submissions()
        state = game.get_game_state()
        if missing_reports:
            # 如果有新的异常记录，广播状态更新
            socketio.start_background_task(broadcast_game_state)
        return make_response(state)


@app.route('/api/status', methods=['GET'])
def public_status():
    """游戏方公共状态接口"""
    # 可选的组名参数，用于更新活跃时间
    group_name = request.args.get('group_name', '').strip()

    with game_lock:
        # 如果提供了组名，更新活跃时间
        if group_name:
            game.update_activity(group_name)
        status = game.get_public_status()
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


@app.route('/api/game/reset', methods=['POST'])
def reset_game():
    """重置游戏接口（主持方调用）"""
    if not _require_admin():
        return _admin_forbidden_response()
    with game_lock:
        game.reset_game()
        # 停止倒计时广播
        stop_timer_broadcast()
        # 广播状态变化
        socketio.start_background_task(broadcast_status)
        socketio.start_background_task(broadcast_game_state)
        return make_response({}, 200, '游戏已重置')


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


# WebSocket事件处理
@socketio.on('connect')
def handle_connect():
    """客户端连接时发送当前状态"""
    with game_lock:
        status = game.get_public_status()
    emit('status_update', status)


@socketio.on('request_status')
def handle_request_status():
    """客户端请求状态更新"""
    with game_lock:
        status = game.get_public_status()
    emit('status_update', status)


@socketio.on('request_timer')
def handle_request_timer():
    """客户端请求倒计时更新"""
    with game_lock:
        status = game.get_public_status()
        # 添加精确的时间信息
        now = datetime.now()
        if game.phase_deadline:
            remaining = max(0, int((game.phase_deadline - now).total_seconds()))
            status['remaining_seconds'] = remaining

        if game.speaker_deadline and status.get('status') == 'describing':
            speaker_remaining = max(0, int((game.speaker_deadline - now).total_seconds()))
            status['speaker_remaining_seconds'] = speaker_remaining

    emit('timer_update', status)


if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"=" * 50)
    print(f"谁是卧底 - 主持方平台")
    print(f"=" * 50)
    print(f"服务器启动中...")
    print(f"本地访问: http://127.0.0.1:5000")
    print(f"局域网访问: http://{local_ip}:5000")
    print(f"WebSocket: 已启用实时推送")
    print(f"=" * 50)
    print(f"请确保游戏方能够访问上述IP地址")
    print(f"=" * 50)

    # 使用 socketio.run 替代 app.run
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
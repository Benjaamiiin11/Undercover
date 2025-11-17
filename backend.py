"""
后端服务器模块
提供RESTful API接口，处理游戏方的请求
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from game_logic import GameLogic, GameStatus
import threading
import socket

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局游戏逻辑实例
game = GameLogic()

# 线程锁，保证线程安全
game_lock = threading.Lock()


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


@app.route('/api/register', methods=['POST'])
def register():
    """游戏方注册接口"""
    data = request.json
    group_name = data.get('group_name', '').strip()
    
    if not group_name:
        return jsonify({'success': False, 'message': '组名不能为空'}), 400
    
    with game_lock:
        success = game.register_group(group_name)
        if success:
            return jsonify({
                'success': True,
                'message': '注册成功',
                'group_name': group_name,
                'total_groups': len(game.groups)
            })
        else:
            return jsonify({
                'success': False,
                'message': '注册失败：组名已存在或已达到最大组数(4组)'
            }), 400


@app.route('/api/game/start', methods=['POST'])
def start_game():
    """开始游戏接口（主持方调用）"""
    data = request.json
    undercover_word = data.get('undercover_word', '').strip()
    civilian_word = data.get('civilian_word', '').strip()
    
    if not undercover_word or not civilian_word:
        return jsonify({'success': False, 'message': '词语不能为空'}), 400
    
    with game_lock:
        success = game.start_game(undercover_word, civilian_word)
        if success:
            return jsonify({
                'success': True,
                'message': '游戏已开始',
                'undercover_group': game.undercover_group,
                'groups': {name: info['role'] for name, info in game.groups.items()}
            })
        else:
            return jsonify({
                'success': False,
                'message': '无法开始游戏：游戏状态不正确或没有注册的组'
            }), 400


@app.route('/api/game/round/start', methods=['POST'])
def start_round():
    """开始新回合接口（主持方调用）"""
    with game_lock:
        order = game.start_round()
        if order:
            return jsonify({
                'success': True,
                'message': '回合已开始',
                'round': game.current_round,
                'order': order
            })
        else:
            return jsonify({
                'success': False,
                'message': '无法开始回合：游戏状态不正确或活跃组数不足'
            }), 400


@app.route('/api/describe', methods=['POST'])
def submit_description():
    """提交描述接口（游戏方调用）"""
    data = request.json
    group_name = data.get('group_name', '').strip()
    description = data.get('description', '').strip()
    
    if not group_name or not description:
        return jsonify({'success': False, 'message': '组名和描述不能为空'}), 400
    
    with game_lock:
        success = game.submit_description(group_name, description)
        if success:
            # 获取当前描述列表
            current_descriptions = game.descriptions.get(game.current_round, [])
            return jsonify({
                'success': True,
                'message': '描述提交成功',
                'round': game.current_round,
                'total_descriptions': len(current_descriptions)
            })
        else:
            return jsonify({
                'success': False,
                'message': '描述提交失败：游戏状态不正确、组名无效或已提交过'
            }), 400


@app.route('/api/vote', methods=['POST'])
def submit_vote():
    """提交投票接口（游戏方调用）"""
    data = request.json
    voter_group = data.get('voter_group', '').strip()
    target_group = data.get('target_group', '').strip()
    
    if not voter_group or not target_group:
        return jsonify({'success': False, 'message': '投票者和被投票者不能为空'}), 400
    
    with game_lock:
        success = game.submit_vote(voter_group, target_group)
        if success:
            return jsonify({
                'success': True,
                'message': '投票提交成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '投票提交失败：游戏状态不正确、组名无效或不能投自己'
            }), 400


@app.route('/api/game/voting/process', methods=['POST'])
def process_voting():
    """处理投票结果接口（主持方调用）"""
    with game_lock:
        result = game.process_voting_result()
        if 'error' in result:
            return jsonify(result), 400
        return jsonify({
            'success': True,
            **result
        })


@app.route('/api/game/state', methods=['GET'])
def get_game_state():
    """获取游戏状态接口"""
    with game_lock:
        state = game.get_game_state()
        return jsonify({
            'success': True,
            **state
        })


@app.route('/api/word', methods=['GET'])
def get_word():
    """获取词语接口（游戏方调用，仅返回自己的词语）"""
    group_name = request.args.get('group_name', '').strip()
    
    if not group_name:
        return jsonify({'success': False, 'message': '组名不能为空'}), 400
    
    with game_lock:
        word = game.get_group_word(group_name)
        if word:
            return jsonify({
                'success': True,
                'word': word
            })
        else:
            return jsonify({
                'success': False,
                'message': '未找到该组的词语或游戏未开始'
            }), 404


@app.route('/api/game/reset', methods=['POST'])
def reset_game():
    """重置游戏接口（主持方调用）"""
    with game_lock:
        game.reset_game()
        return jsonify({
            'success': True,
            'message': '游戏已重置'
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
        return jsonify({
            'success': True,
            'groups': groups_info,
            'total': len(groups_info)
        })


if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"=" * 50)
    print(f"谁是卧底 - 主持方平台")
    print(f"=" * 50)
    print(f"服务器启动中...")
    print(f"本地访问: http://127.0.0.1:5000")
    print(f"局域网访问: http://{local_ip}:5000")
    print(f"=" * 50)
    print(f"请确保游戏方能够访问上述IP地址")
    print(f"=" * 50)
    
    # 运行服务器，允许局域网访问
    app.run(host='0.0.0.0', port=5000, debug=True)


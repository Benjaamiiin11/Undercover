"""
前端界面模块
提供可视化的游戏管理界面
"""
from flask import Flask, render_template_string, jsonify
import requests
import threading
import time
from datetime import datetime

# 前端服务器（用于展示界面）
frontend_app = Flask(__name__)

# 后端API地址
BACKEND_URL = "http://127.0.0.1:5000"


def get_backend_data(endpoint):
    """从后端获取数据"""
    try:
        response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=2)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def post_backend_data(endpoint, data):
    """向后端发送POST请求"""
    try:
        response = requests.post(f"{BACKEND_URL}{endpoint}", json=data, timeout=2)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


# HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>谁是卧底 - 主持方平台</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        .section h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5em;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: bold;
        }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            background: #667eea;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-right: 10px;
            margin-top: 10px;
        }
        button:hover {
            background: #5568d3;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .status {
            padding: 15px;
            background: #e3f2fd;
            border-radius: 5px;
            margin-bottom: 15px;
        }
        .status-item {
            margin: 5px 0;
            color: #333;
        }
        .groups-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .group-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            border: 2px solid #ddd;
        }
        .group-card.undercover {
            border-color: #f44336;
            background: #ffebee;
        }
        .group-card.civilian {
            border-color: #4caf50;
            background: #e8f5e9;
        }
        .group-card.eliminated {
            opacity: 0.5;
            text-decoration: line-through;
        }
        .descriptions {
            margin-top: 15px;
        }
        .description-item {
            background: white;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }
        .description-item .group-name {
            font-weight: bold;
            color: #667eea;
        }
        .description-item .time {
            color: #999;
            font-size: 0.9em;
        }
        .vote-result {
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 5px;
        }
        .vote-item {
            margin: 5px 0;
            padding: 5px;
            background: #f5f5f5;
        }
        .scores {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        .score-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border: 2px solid #667eea;
        }
        .score-value {
            font-size: 2em;
            color: #667eea;
            font-weight: bold;
        }
        .message {
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .message.success {
            background: #d4edda;
            color: #155724;
        }
        .message.error {
            background: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 谁是卧底 - 主持方平台</h1>
        
        <!-- 游戏控制区域 -->
        <div class="section">
            <h2>游戏控制</h2>
            <div class="form-group">
                <label>卧底词：</label>
                <input type="text" id="undercover-word" placeholder="输入卧底词">
            </div>
            <div class="form-group">
                <label>平民词：</label>
                <input type="text" id="civilian-word" placeholder="输入平民词">
            </div>
            <button onclick="startGame()">开始游戏</button>
            <button onclick="startRound()">开始新回合</button>
            <button onclick="processVoting()">处理投票结果</button>
            <button onclick="resetGame()">重置游戏</button>
        </div>
        
        <!-- 游戏状态 -->
        <div class="section">
            <h2>游戏状态</h2>
            <div class="status" id="game-status">
                <div class="status-item">状态：等待注册</div>
                <div class="status-item">当前回合：0</div>
                <div class="status-item">已注册组数：0</div>
            </div>
        </div>
        
        <!-- 注册的组 -->
        <div class="section">
            <h2>已注册的组</h2>
            <div class="groups-list" id="groups-list"></div>
        </div>
        
        <!-- 描述展示 -->
        <div class="section">
            <h2>当前回合描述</h2>
            <div class="descriptions" id="descriptions"></div>
        </div>
        
        <!-- 投票结果 -->
        <div class="section">
            <h2>投票结果</h2>
            <div class="vote-result" id="vote-result"></div>
        </div>
        
        <!-- 得分 -->
        <div class="section">
            <h2>得分</h2>
            <div class="scores" id="scores"></div>
        </div>
    </div>
    
    <script>
        // 自动刷新游戏状态
        setInterval(updateGameState, 2000);
        updateGameState();
        
        function updateGameState() {
            fetch('/api/game/state')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateStatus(data);
                        updateGroups(data);
                        updateDescriptions(data);
                        updateScores(data);
                    }
                })
                .catch(error => console.error('Error:', error));
        }
        
        function updateStatus(data) {
            const statusDiv = document.getElementById('game-status');
            const statusMap = {
                'waiting': '等待注册',
                'registered': '已注册',
                'word_assigned': '词语已分配',
                'describing': '描述阶段',
                'voting': '投票阶段',
                'round_end': '回合结束',
                'game_end': '游戏结束'
            };
            statusDiv.innerHTML = `
                <div class="status-item">状态：${statusMap[data.status] || data.status}</div>
                <div class="status-item">当前回合：${data.current_round || 0}</div>
                <div class="status-item">已注册组数：${Object.keys(data.groups || {}).length}</div>
                ${data.undercover_group ? `<div class="status-item">卧底组：${data.undercover_group}</div>` : ''}
            `;
        }
        
        function updateGroups(data) {
            const groupsList = document.getElementById('groups-list');
            if (!data.groups) {
                groupsList.innerHTML = '<p>暂无注册的组</p>';
                return;
            }
            
            let html = '';
            for (const [name, info] of Object.entries(data.groups)) {
                const role = info.role || 'unknown';
                const eliminated = info.eliminated || false;
                html += `
                    <div class="group-card ${role} ${eliminated ? 'eliminated' : ''}">
                        <div><strong>${name}</strong></div>
                        <div>${role === 'undercover' ? '卧底' : role === 'civilian' ? '平民' : '未知'}</div>
                        ${eliminated ? '<div style="color: red;">已淘汰</div>' : ''}
                    </div>
                `;
            }
            groupsList.innerHTML = html;
        }
        
        function updateDescriptions(data) {
            const descDiv = document.getElementById('descriptions');
            const round = data.current_round;
            if (!data.descriptions || !data.descriptions[round]) {
                descDiv.innerHTML = '<p>暂无描述</p>';
                return;
            }
            
            let html = '';
            for (const desc of data.descriptions[round]) {
                const time = new Date(desc.time).toLocaleTimeString('zh-CN');
                html += `
                    <div class="description-item">
                        <div class="group-name">${desc.group}</div>
                        <div>${desc.description}</div>
                        <div class="time">${time}</div>
                    </div>
                `;
            }
            descDiv.innerHTML = html;
        }
        
        function updateScores(data) {
            const scoresDiv = document.getElementById('scores');
            if (!data.scores || Object.keys(data.scores).length === 0) {
                scoresDiv.innerHTML = '<p>暂无得分</p>';
                return;
            }
            
            let html = '';
            for (const [group, score] of Object.entries(data.scores)) {
                html += `
                    <div class="score-card">
                        <div>${group}</div>
                        <div class="score-value">${score}</div>
                    </div>
                `;
            }
            scoresDiv.innerHTML = html;
        }
        
        function startGame() {
            const undercoverWord = document.getElementById('undercover-word').value;
            const civilianWord = document.getElementById('civilian-word').value;
            
            if (!undercoverWord || !civilianWord) {
                alert('请输入卧底词和平民词');
                return;
            }
            
            fetch('/api/game/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    undercover_word: undercoverWord,
                    civilian_word: civilianWord
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('游戏已开始！');
                    updateGameState();
                } else {
                    alert('错误：' + data.message);
                }
            })
            .catch(error => {
                alert('请求失败：' + error);
            });
        }
        
        function startRound() {
            fetch('/api/game/round/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('回合已开始！顺序：' + data.order.join(' -> '));
                    updateGameState();
                } else {
                    alert('错误：' + data.message);
                }
            })
            .catch(error => {
                alert('请求失败：' + error);
            });
        }
        
        function processVoting() {
            fetch('/api/game/voting/process', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    let message = '投票结果：\\n';
                    message += '得票统计：' + JSON.stringify(data.vote_count) + '\\n';
                    if (data.eliminated && data.eliminated.length > 0) {
                        message += '淘汰：' + data.eliminated.join(', ') + '\\n';
                    }
                    if (data.game_ended) {
                        message += '游戏结束！获胜方：' + (data.winner === 'undercover' ? '卧底' : '平民');
                    }
                    alert(message);
                    
                    // 更新投票结果显示
                    const voteDiv = document.getElementById('vote-result');
                    let html = '<div class="vote-item">得票统计：</div>';
                    for (const [group, votes] of Object.entries(data.vote_count)) {
                        html += `<div class="vote-item">${group}: ${votes}票</div>`;
                    }
                    if (data.eliminated && data.eliminated.length > 0) {
                        html += `<div class="vote-item" style="color: red;">淘汰：${data.eliminated.join(', ')}</div>`;
                    }
                    voteDiv.innerHTML = html;
                    
                    updateGameState();
                } else {
                    alert('错误：' + (data.message || data.error));
                }
            })
            .catch(error => {
                alert('请求失败：' + error);
            });
        }
        
        function resetGame() {
            if (confirm('确定要重置游戏吗？')) {
                fetch('/api/game/reset', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('游戏已重置');
                        updateGameState();
                        document.getElementById('vote-result').innerHTML = '';
                    }
                })
                .catch(error => {
                    alert('请求失败：' + error);
                });
            }
        }
    </script>
</body>
</html>
"""


@frontend_app.route('/')
def index():
    """主页面"""
    return render_template_string(HTML_TEMPLATE)


@frontend_app.route('/api/game/state')
def api_game_state():
    """代理后端API"""
    return jsonify(get_backend_data('/api/game/state'))


@frontend_app.route('/api/game/start', methods=['POST'])
def api_start_game():
    """代理后端API"""
    from flask import request
    data = request.json
    response = requests.post(f"{BACKEND_URL}/api/game/start", json=data, timeout=2)
    return jsonify(response.json())


@frontend_app.route('/api/game/round/start', methods=['POST'])
def api_start_round():
    """代理后端API"""
    response = requests.post(f"{BACKEND_URL}/api/game/round/start", timeout=2)
    return jsonify(response.json())


@frontend_app.route('/api/game/voting/process', methods=['POST'])
def api_process_voting():
    """代理后端API"""
    response = requests.post(f"{BACKEND_URL}/api/game/voting/process", timeout=2)
    return jsonify(response.json())


@frontend_app.route('/api/game/reset', methods=['POST'])
def api_reset_game():
    """代理后端API"""
    response = requests.post(f"{BACKEND_URL}/api/game/reset", timeout=2)
    return jsonify(response.json())


if __name__ == '__main__':
    print("=" * 50)
    print("前端界面服务器启动中...")
    print("访问地址: http://127.0.0.1:5001")
    print("=" * 50)
    print("注意：请确保后端服务器(backend.py)已启动")
    print("=" * 50)
    
    # 前端服务器运行在5001端口
    frontend_app.run(host='0.0.0.0', port=5001, debug=True)


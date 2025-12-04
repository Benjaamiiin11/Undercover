"""
前端界面模块 - 改进版
所有重要信息都在一个屏幕内显示，无需滚动
"""
from flask import Flask, render_template_string, jsonify
import os
import requests
import threading
import time
from datetime import datetime

# 前端服务器（用于展示界面）
frontend_app = Flask(__name__)

# 后端API地址
BACKEND_URL = "http://127.0.0.1:5000"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "host-secret")
ADMIN_HEADERS = {'X-Admin-Token': ADMIN_TOKEN}


def get_backend_data(endpoint, use_admin=False):
    """从后端获取数据"""
    try:
        headers = ADMIN_HEADERS if use_admin else None
        response = requests.get(f"{BACKEND_URL}{endpoint}", headers=headers, timeout=2)
        return response.json()
    except:
        return None


def post_backend_data(endpoint, data):
    """向后端发送POST请求"""
    try:
        response = requests.post(f"{BACKEND_URL}{endpoint}", json=data, timeout=2)
        return response.json()
    except:
        return None


# HTML模板 - 改进版：三个标签页同时显示
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>谁是卧底 - 主持控制台</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary-color: #3498db;
            --secondary-color: #2ecc71;
            --danger-color: #e74c3c;
            --warning-color: #f39c12;
            --dark-color: #2c3e50;
            --light-color: #f5f7fa;
            --bg-color: #f0f2f5;
            --card-bg: #ffffff;
            --border-color: #e1e5e9;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-color);
            color: var(--dark-color);
            min-height: 100vh;
            padding: 0;
            overflow: hidden;
            font-size: 14px;
        }

        /* 主容器 - 使用固定高度，确保不滚动 */
        .main-container {
            height: 100vh;
            display: flex;
            flex-direction: column;
            padding: 10px;
            gap: 10px;
        }

        /* 顶部控制栏 */
        .top-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            flex-shrink: 0;
            color: white;
        }

        .game-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.4em;
            font-weight: bold;
        }

        .game-controls {
            display: flex;
            gap: 8px;
        }

        .control-btn {
            padding: 8px 15px;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }

        .btn-start { background: #27ae60; color: white; }
        .btn-round { background: #3498db; color: white; }
        .btn-vote { background: #f39c12; color: white; }
        .btn-reset { background: #e74c3c; color: white; }

        .control-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 3px 5px rgba(0,0,0,0.2);
        }

        .control-btn:disabled {
            background: #bdc3c7;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        /* 游戏状态指示器 */
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .status-badge {
            padding: 6px 12px;
            border-radius: 15px;
            font-weight: bold;
            font-size: 0.9em;
            background: rgba(255,255,255,0.2);
        }

        .timer-display {
            font-size: 1.2em;
            font-weight: bold;
            background: rgba(0,0,0,0.3);
            padding: 6px 12px;
            border-radius: 5px;
            min-width: 80px;
            text-align: center;
        }

        /* 主要内容区域 - 使用flex确保不超出屏幕 */
        .content-area {
            flex: 1;
            display: flex;
            gap: 10px;
            overflow: hidden;
            min-height: 0;
        }

        /* 左侧玩家区域 */
        .players-section {
            flex: 1;
            background: var(--card-bg);
            border-radius: 8px;
            padding: 15px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid var(--border-color);
        }

        .players-section h3 {
            margin-bottom: 10px;
            color: var(--primary-color);
            display: flex;
            align-items: center;
            gap: 8px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--border-color);
        }

        /* 玩家网格 */
        .players-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            overflow-y: auto;
            padding-right: 5px;
            flex: 1;
        }

        /* 隐藏滚动条但保留功能 */
        .players-grid::-webkit-scrollbar {
            width: 5px;
        }

        .players-grid::-webkit-scrollbar-track {
            background: var(--border-color);
            border-radius: 5px;
        }

        .players-grid::-webkit-scrollbar-thumb {
            background: var(--primary-color);
            border-radius: 5px;
        }

        /* 玩家卡片 */
        .player-card {
            background: var(--light-color);
            border-radius: 8px;
            padding: 12px;
            transition: all 0.3s ease;
            border: 2px solid transparent;
            position: relative;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .player-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .player-card.current-turn {
            border-color: var(--primary-color);
            animation: pulse-border 1.5s infinite;
            background: rgba(52, 152, 219, 0.1);
        }

        .player-card.undercover {
            border-color: var(--danger-color);
            background: rgba(231, 76, 60, 0.08);
        }

        .player-card.eliminated {
            opacity: 0.7;
            border-color: #95a5a6;
            background: rgba(149, 165, 166, 0.1);
        }

        .player-card.eliminated::before {
            content: "❌";
            position: absolute;
            top: 5px;
            right: 5px;
            font-size: 1.2em;
        }

        @keyframes pulse-border {
            0% { box-shadow: 0 0 0 0 rgba(52, 152, 219, 0.7); }
            70% { box-shadow: 0 0 0 6px rgba(52, 152, 219, 0); }
            100% { box-shadow: 0 0 0 0 rgba(52, 152, 219, 0); }
        }

        .player-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .player-name {
            font-weight: bold;
            font-size: 1.1em;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .player-role {
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 0.8em;
            font-weight: bold;
        }

        .role-undercover {
            background: var(--danger-color);
            color: white;
        }

        .role-civilian {
            background: var(--secondary-color);
            color: white;
        }

        .player-status {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 8px;
            font-size: 0.85em;
        }

        .status-badge {
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.8em;
            color: white;
        }

        .status-speaking { background: var(--primary-color); }
        .status-described { background: #9b59b6; }
        .status-voted { background: var(--warning-color); }
        .status-online { background: var(--secondary-color); }
        .status-offline { background: #95a5a6; }

        .player-content {
            background: rgba(0,0,0,0.05);
            padding: 8px;
            border-radius: 5px;
            margin-top: 8px;
            font-size: 0.9em;
        }

        .player-description {
            color: #2c3e50;
            font-style: italic;
        }

        .player-vote {
            color: var(--warning-color);
            font-weight: bold;
        }

        .player-footer {
            display: flex;
            justify-content: space-between;
            margin-top: 8px;
            font-size: 0.85em;
            color: #7f8c8d;
        }

        /* 右侧信息区域 - 三栏同时显示 */
        .info-section {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 10px;
            min-height: 0;
        }

        .info-tabs-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }

        .info-tabs {
            display: flex;
            gap: 10px;
            height: 100%;
            min-height: 0;
        }

        .tab-pane {
            flex: 1;
            background: var(--card-bg);
            border-radius: 8px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid var(--border-color);
        }

        .tab-header {
            background: var(--primary-color);
            color: white;
            padding: 10px 15px;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-shrink: 0;
        }

        .tab-content {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
            padding-right: 5px;
        }

        .tab-content::-webkit-scrollbar {
            width: 5px;
        }

        .tab-content::-webkit-scrollbar-track {
            background: var(--border-color);
            border-radius: 5px;
        }

        .tab-content::-webkit-scrollbar-thumb {
            background: var(--primary-color);
            border-radius: 5px;
        }

        /* 描述项 */
        .description-item {
            background: var(--light-color);
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 8px;
            border-left: 3px solid var(--primary-color);
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        .description-item.undercover {
            border-left-color: var(--danger-color);
            background: rgba(231, 76, 60, 0.08);
        }

        .desc-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-weight: bold;
            color: var(--dark-color);
        }

        .desc-text {
            color: var(--dark-color);
            font-size: 0.95em;
        }

        /* 投票记录 */
        .round-vote-section {
            margin-bottom: 15px;
            padding: 10px;
            background: var(--light-color);
            border-radius: 6px;
            border: 1px solid var(--border-color);
        }

        .round-title {
            font-weight: bold;
            color: var(--primary-color);
            margin-bottom: 8px;
            padding-bottom: 5px;
            border-bottom: 1px solid var(--border-color);
        }

        .vote-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 5px 0;
            border-bottom: 1px dashed var(--border-color);
        }

        .vote-item:last-child {
            border-bottom: none;
        }

        .vote-from {
            color: var(--primary-color);
            font-weight: bold;
            min-width: 80px;
        }

        .vote-to {
            color: var(--warning-color);
            font-weight: bold;
        }

        .vote-count-item {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px dashed var(--border-color);
        }

        .vote-count-item:last-child {
            border-bottom: none;
        }

        /* 游戏结果 */
        .result-item {
            background: var(--light-color);
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 10px;
            border-left: 3px solid var(--warning-color);
        }

        .result-item.eliminated {
            border-left-color: var(--danger-color);
            background: rgba(231, 76, 60, 0.08);
        }

        .result-item.victory {
            border-left-color: var(--secondary-color);
            background: rgba(46, 204, 113, 0.08);
        }

        .result-header {
            font-weight: bold;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            color: var(--dark-color);
        }

        .result-details {
            font-size: 0.9em;
            color: var(--dark-color);
        }

        /* 词语设置区域 */
        .words-section {
            flex-shrink: 0;
            background: var(--card-bg);
            border-radius: 8px;
            padding: 15px;
            display: flex;
            gap: 15px;
            align-items: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid var(--border-color);
        }

        .word-input {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .word-input label {
            color: var(--dark-color);
            font-size: 0.9em;
            font-weight: 600;
        }

        .word-input input {
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            background: white;
            font-size: 1em;
            transition: border-color 0.3s ease;
        }

        .word-input input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
        }

        /* 底部信息栏 */
        .bottom-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            padding: 8px 15px;
            border-radius: 5px;
            font-size: 0.9em;
            flex-shrink: 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid var(--border-color);
        }

        /* 统计卡片 */
        .stats-cards {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            flex-shrink: 0;
        }

        .stat-card {
            flex: 1;
            background: var(--card-bg);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            transition: all 0.3s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid var(--border-color);
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .stat-card h4 {
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
        }

        .stat-value {
            font-size: 1.6em;
            font-weight: bold;
            color: var(--dark-color);
        }

        /* 响应式调整 */
        @media (max-width: 1200px) {
            .players-grid {
                grid-template-columns: 1fr;
            }

            .info-tabs {
                flex-direction: column;
            }
        }

        @media (max-width: 768px) {
            .content-area {
                flex-direction: column;
            }

            .players-section, .info-section {
                max-height: 50vh;
            }

            .words-section {
                flex-direction: column;
            }

            .game-controls {
                flex-wrap: wrap;
                justify-content: center;
            }
        }

        /* 警报消息 */
        .alert {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            z-index: 1000;
            animation: slide-in 0.3s ease, fade-out 0.3s ease 2.7s forwards;
            max-width: 300px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .alert-success { background: #27ae60; }
        .alert-danger { background: #e74c3c; }
        .alert-warning { background: #f39c12; }
        .alert-info { background: #3498db; }

        @keyframes slide-in {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        @keyframes fade-out {
            from { opacity: 1; }
            to { opacity: 0; }
        }

        /* 发光效果 */
        .glow {
            color: var(--primary-color);
            font-weight: bold;
        }

        /* 倒计时警告 */
        .timer-warning {
            color: var(--danger-color);
            animation: blink 1s infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <!-- 顶部控制栏 -->
        <div class="top-bar">
            <div class="game-title">
                <i class="fas fa-user-secret"></i>
                <span>谁是卧底 - 主持控制台</span>
                <div class="status-indicator">
                    <div id="game-status" class="status-badge">等待注册</div>
                    <div class="timer-display" id="main-timer">--:--</div>
                </div>
            </div>

            <div class="game-controls">
                <button class="control-btn btn-start" onclick="startGame()">
                    <i class="fas fa-play"></i> 开始游戏
                </button>
                <button class="control-btn btn-round" onclick="startRound()">
                    <i class="fas fa-forward"></i> 开始回合
                </button>
                <button class="control-btn btn-vote" onclick="processVoting()">
                    <i class="fas fa-vote-yea"></i> 处理投票
                </button>
                <button class="control-btn btn-reset" onclick="resetGame()">
                    <i class="fas fa-redo"></i> 重置游戏
                </button>
            </div>
        </div>

        <!-- 统计卡片 -->
        <div class="stats-cards">
            <div class="stat-card">
                <h4><i class="fas fa-users"></i> 注册组数</h4>
                <div class="stat-value" id="stat-groups">0</div>
            </div>
            <div class="stat-card">
                <h4><i class="fas fa-gamepad"></i> 游戏次数</h4>
                <div class="stat-value" id="stat-games">0</div>
            </div>
            <div class="stat-card">
                <h4><i class="fas fa-microphone"></i> 当前回合</h4>
                <div class="stat-value" id="stat-round">0</div>
            </div>
            <div class="stat-card">
                <h4><i class="fas fa-trophy"></i> 最高分</h4>
                <div class="stat-value" id="stat-highscore">0</div>
            </div>
        </div>

        <!-- 主要内容区域 -->
        <div class="content-area">
            <!-- 左侧玩家区域 -->
            <div class="players-section">
                <h3><i class="fas fa-users"></i> 玩家状态 (<span id="player-count">0</span>)</h3>
                <div class="players-grid" id="players-grid">
                    <div class="player-card">
                        <div class="player-header">
                            <div class="player-name">等待玩家注册...</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 右侧信息区域 - 三栏同时显示 -->
            <div class="info-section">
                <div class="info-tabs-container">
                    <div class="info-tabs">
                        <!-- 描述记录 -->
                        <div class="tab-pane">
                            <div class="tab-header">
                                <i class="fas fa-comments"></i> 描述记录
                            </div>
                            <div class="tab-content" id="descriptions-content">
                                <div class="description-item">
                                    <div class="desc-header">暂无描述</div>
                                </div>
                            </div>
                        </div>

                        <!-- 投票记录 -->
                        <div class="tab-pane">
                            <div class="tab-header">
                                <i class="fas fa-vote-yea"></i> 投票记录
                            </div>
                            <div class="tab-content" id="votes-content">
                                <div class="round-vote-section">
                                    <div class="round-title">暂无投票记录</div>
                                </div>
                            </div>
                        </div>

                        <!-- 游戏结果 -->
                        <div class="tab-pane">
                            <div class="tab-header">
                                <i class="fas fa-poll"></i> 游戏结果
                            </div>
                            <div class="tab-content" id="results-content">
                                <div class="result-item">
                                    <div class="result-header">暂无游戏结果</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 词语设置区域 -->
        <div class="words-section">
            <div class="word-input">
                <label for="undercover-word"><i class="fas fa-user-secret"></i> 卧底词</label>
                <input type="text" id="undercover-word" placeholder="输入卧底词">
            </div>
            <div class="word-input">
                <label for="civilian-word"><i class="fas fa-users"></i> 平民词</label>
                <input type="text" id="civilian-word" placeholder="输入平民词">
            </div>
            <button class="control-btn btn-start" onclick="startGame()" style="height: fit-content;">
                <i class="fas fa-play"></i> 开始游戏
            </button>
        </div>

        <!-- 底部信息栏 -->
        <div class="bottom-bar">
            <div>服务器: <span id="server-status" class="glow">已连接</span></div>
            <div>当前发言者: <span id="current-speaker-name" class="glow">--</span></div>
            <div>描述倒计时: <span id="desc-timer">--:--</span> | 投票倒计时: <span id="vote-timer">--:--</span></div>
            <div>描述: <span id="desc-count">0/0</span> | 投票: <span id="vote-count">0/0</span></div>
        </div>
    </div>

    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <script>
        // WebSocket 连接
        const socket = io('http://127.0.0.1:5000');
        let gameData = {};
        let allVoteResults = {}; // 存储所有回合的投票结果

        // 连接成功
        socket.on('connect', function() {
            console.log('WebSocket 已连接');
            showAlert('success', '已连接到服务器');
            updateServerStatus(true);
        });

        // 接收状态更新推送
        socket.on('status_update', function(data) {
            updateRealTimeInfo(data);
            updateTimers(data);
        });

        // 接收完整游戏状态推送
        socket.on('game_state_update', function(data) {
            console.log('收到游戏状态推送:', data);
            gameData = data;
            updateAllDisplay();
        });

        // 接收投票结果推送
        socket.on('vote_result', function(data) {
            console.log('收到投票结果推送:', data);
            showAlert('warning', '投票结果已生成');

            // 存储投票结果
            if (data.round) {
                allVoteResults[data.round] = data;
            }

            updateVoteRecords();
            updateGameResults();
        });

        // 断开连接时的处理
        socket.on('disconnect', function() {
            console.log('WebSocket 已断开');
            showAlert('danger', '与服务器断开连接');
            updateServerStatus(false);
        });

        // 连接错误
        socket.on('connect_error', function(error) {
            console.log('连接错误:', error);
            updateServerStatus(false);
        });

        // 定时获取游戏状态
        setInterval(fetchGameState, 3000);

        // 初始加载
        fetchGameState();

        function fetchGameState() {
            fetch('/api/game/state')
                .then(response => response.json())
                .then(resp => {
                    if (resp && resp.code === 200) {
                        gameData = resp.data || {};
                        updateAllDisplay();
                    } else {
                        console.error('状态刷新失败：', resp ? resp.message : '未知错误');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    updateServerStatus(false);
                });
        }

        function updateAllDisplay() {
            updateGameStatus();
            updatePlayers();
            updateDescriptions();
            updateVoteRecords();
            updateGameResults();
            updateGameStats();
        }

        function updateGameStatus() {
            const status = gameData.status || 'waiting';
            const statusMap = {
                'waiting': '等待注册',
                'registered': '已注册',
                'word_assigned': '词语已分配',
                'describing': '描述阶段',
                'voting': '投票阶段',
                'round_end': '回合结束',
                'game_end': '游戏结束'
            };

            document.getElementById('game-status').textContent = statusMap[status] || status;
            document.getElementById('stat-round').textContent = gameData.current_round || 0;
        }

        function updatePlayers() {
            const playersGrid = document.getElementById('players-grid');
            const groups = gameData.groups || {};

            document.getElementById('player-count').textContent = Object.keys(groups).length;

            if (Object.keys(groups).length === 0) {
                playersGrid.innerHTML = `
                    <div class="player-card">
                        <div class="player-header">
                            <div class="player-name">等待玩家注册...</div>
                        </div>
                    </div>
                `;
                return;
            }

            let html = '';
            const currentSpeaker = gameData.current_speaker || '';
            const eliminatedGroups = gameData.eliminated_groups || [];
            const describedGroups = gameData.described_groups || [];
            const votedGroups = gameData.voted_groups || [];
            const onlineStatus = gameData.online_status || {};
            const round = gameData.current_round;

            // 按得分排序
            const sortedGroups = Object.entries(groups).sort((a, b) => {
                const scoreA = gameData.scores?.[a[0]] || 0;
                const scoreB = gameData.scores?.[b[0]] || 0;
                return scoreB - scoreA;
            });

            sortedGroups.forEach(([name, info]) => {
                const isEliminated = eliminatedGroups.includes(name) || info.eliminated;
                const isUndercover = info.role === 'undercover';
                const isCurrentSpeaker = currentSpeaker === name;
                const hasDescribed = describedGroups.includes(name);
                const hasVoted = votedGroups.includes(name);
                const isOnline = onlineStatus[name] !== false;
                const score = gameData.scores?.[name] || 0;

                // 获取当前回合的描述
                let currentDescription = '';
                let currentVote = '';

                if (gameData.descriptions && gameData.descriptions[round]) {
                    const desc = gameData.descriptions[round].find(d => d.group === name);
                    if (desc) {
                        currentDescription = desc.description;
                    }
                }

                if (gameData.votes && gameData.votes[round]) {
                    currentVote = gameData.votes[round][name] || '';
                }

                // 玩家卡片
                html += `
                    <div class="player-card ${isUndercover ? 'undercover' : ''} ${isEliminated ? 'eliminated' : ''} ${isCurrentSpeaker ? 'current-turn' : ''}">
                        <div class="player-header">
                            <div class="player-name">
                                ${name} ${isUndercover ? '<i class="fas fa-user-secret"></i>' : ''}
                            </div>
                            <div class="player-role ${isUndercover ? 'role-undercover' : 'role-civilian'}">
                                ${isUndercover ? '卧底' : '平民'}
                            </div>
                        </div>

                        <div class="player-status">
                            ${isCurrentSpeaker ? '<span class="status-badge status-speaking">发言中</span>' : ''}
                            ${hasDescribed ? '<span class="status-badge status-described">已描述</span>' : ''}
                            ${hasVoted ? '<span class="status-badge status-voted">已投票</span>' : ''}
                            <span class="status-badge ${isOnline ? 'status-online' : 'status-offline'}">
                                ${isOnline ? '在线' : '离线'}
                            </span>
                        </div>

                        ${currentDescription ? `
                            <div class="player-content">
                                <div class="player-description">
                                    <strong>描述:</strong> ${currentDescription}
                                </div>
                            </div>
                        ` : ''}

                        ${currentVote ? `
                            <div class="player-content">
                                <div class="player-vote">
                                    <strong>投票给:</strong> ${currentVote}
                                </div>
                            </div>
                        ` : ''}

                        <div class="player-footer">
                            <span>得分: ${score}</span>
                            <span>卧底: ${info.undercover_count || 0}次</span>
                        </div>
                    </div>
                `;
            });

            playersGrid.innerHTML = html;
        }

        function updateDescriptions() {
            const container = document.getElementById('descriptions-content');
            const descriptions = gameData.descriptions || {};

            if (Object.keys(descriptions).length === 0) {
                container.innerHTML = `
                    <div class="description-item">
                        <div class="desc-header">暂无描述记录</div>
                    </div>
                `;
                return;
            }

            let html = '';
            const undercoverGroup = gameData.undercover_group;

            // 按回合顺序排列（最新的在前）
            const rounds = Object.keys(descriptions).sort((a, b) => b - a);

            rounds.forEach(round => {
                const roundDescriptions = descriptions[round];
                if (roundDescriptions.length === 0) return;

                html += `
                    <div class="round-vote-section">
                        <div class="round-title">第 ${round} 回合 - ${roundDescriptions.length} 个描述</div>
                `;

                roundDescriptions.forEach(desc => {
                    const isUndercover = desc.group === undercoverGroup;
                    const time = new Date(desc.time).toLocaleTimeString('zh-CN', { 
                        hour: '2-digit', 
                        minute: '2-digit',
                        second: '2-digit'
                    });

                    html += `
                        <div class="description-item ${isUndercover ? 'undercover' : ''}">
                            <div class="desc-header">
                                <span>${desc.group} ${isUndercover ? '<i class="fas fa-user-secret"></i>' : ''}</span>
                                <span style="color: #7f8c8d; font-size: 0.9em;">${time}</span>
                            </div>
                            <div class="desc-text">${desc.description}</div>
                        </div>
                    `;
                });

                html += `</div>`;
            });

            container.innerHTML = html || '<div class="description-item"><div class="desc-header">暂无描述记录</div></div>';
        }

        function updateVoteRecords() {
            const container = document.getElementById('votes-content');

            // 合并投票结果和当前投票数据
            const allVotes = { ...allVoteResults };

            // 添加当前回合的投票记录（如果还没处理）
            const currentRound = gameData.current_round;
            if (gameData.votes && gameData.votes[currentRound] && !allVotes[currentRound]) {
                const currentVotes = gameData.votes[currentRound];
                if (Object.keys(currentVotes).length > 0) {
                    allVotes[currentRound] = {
                        round: currentRound,
                        vote_details: currentVotes,
                        vote_count: {}
                    };

                    // 计算当前回合的票数
                    const voteCount = {};
                    Object.values(currentVotes).forEach(target => {
                        voteCount[target] = (voteCount[target] || 0) + 1;
                    });
                    allVotes[currentRound].vote_count = voteCount;
                }
            }

            if (Object.keys(allVotes).length === 0) {
                container.innerHTML = `
                    <div class="round-vote-section">
                        <div class="round-title">暂无投票记录</div>
                    </div>
                `;
                return;
            }

            let html = '';

            // 按回合顺序排列（最新的在前）
            const rounds = Object.keys(allVotes).sort((a, b) => b - a);

            rounds.forEach(round => {
                const voteData = allVotes[round];

                html += `
                    <div class="round-vote-section">
                        <div class="round-title">第 ${round} 回合投票记录</div>
                `;

                // 显示每个人的投票
                if (voteData.vote_details) {
                    html += `<div style="margin-bottom: 10px;"><strong>投票详情:</strong></div>`;
                    Object.entries(voteData.vote_details).forEach(([voter, target]) => {
                        html += `
                            <div class="vote-item">
                                <div class="vote-from">${voter}</div>
                                <i class="fas fa-arrow-right" style="color: #7f8c8d;"></i>
                                <div class="vote-to">${target}</div>
                            </div>
                        `;
                    });
                }

                // 显示得票统计
                if (voteData.vote_count && Object.keys(voteData.vote_count).length > 0) {
                    html += `<div style="margin-top: 10px;"><strong>得票统计:</strong></div>`;
                    Object.entries(voteData.vote_count).forEach(([group, count]) => {
                        html += `
                            <div class="vote-count-item">
                                <div>${group}</div>
                                <div style="color: var(--warning-color); font-weight: bold;">${count} 票</div>
                            </div>
                        `;
                    });
                }

                html += `</div>`;
            });

            container.innerHTML = html;
        }

        function updateGameResults() {
            const container = document.getElementById('results-content');

            if (Object.keys(allVoteResults).length === 0) {
                container.innerHTML = `
                    <div class="result-item">
                        <div class="result-header">暂无游戏结果</div>
                    </div>
                `;
                return;
            }

            let html = '';

            // 按回合顺序排列（最新的在前）
            const rounds = Object.keys(allVoteResults).sort((a, b) => b - a);

            rounds.forEach(round => {
                const result = allVoteResults[round];

                html += `
                    <div class="result-item ${result.game_ended ? 'victory' : ''}">
                        <div class="result-header">
                            <span>第 ${round} 回合结果</span>
                            <span style="color: ${result.game_ended ? (result.winner === 'undercover' ? 'var(--danger-color)' : 'var(--secondary-color)') : 'var(--warning-color)'}">
                                ${result.game_ended ? (result.winner === 'undercover' ? '🎭 卧底胜利' : '👥 平民胜利') : '游戏继续'}
                            </span>
                        </div>
                        <div class="result-details">
                `;

                // 显示淘汰信息
                if (result.eliminated && result.eliminated.length > 0) {
                    html += `
                        <div style="margin-bottom: 5px;">
                            <i class="fas fa-skull-crossbones" style="color: var(--danger-color);"></i>
                            <strong>被淘汰:</strong> ${result.eliminated.join(', ')}
                        </div>
                    `;
                }

                // 显示最高票数
                if (result.max_voted_groups && result.max_voted_groups.length > 0) {
                    html += `
                        <div style="margin-bottom: 5px;">
                            <i class="fas fa-chart-bar" style="color: var(--warning-color);"></i>
                            <strong>最高票:</strong> ${result.max_voted_groups.join(', ')} (${result.max_votes || 0}票)
                        </div>
                    `;
                }

                // 显示游戏结束信息
                if (result.game_ended) {
                    html += `
                        <div style="margin-bottom: 5px;">
                            <i class="fas fa-flag" style="color: var(--secondary-color);"></i>
                            <strong>游戏结束:</strong> ${result.message || ''}
                        </div>
                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border-color);">
                            <div><strong>卧底词:</strong> ${result.undercover_word || '未知'}</div>
                            <div><strong>平民词:</strong> ${result.civilian_word || '未知'}</div>
                            <div><strong>卧底:</strong> ${result.undercover_group || '未知'}</div>
                        </div>
                    `;
                }

                html += `</div></div>`;
            });

            container.innerHTML = html;
        }

        function updateGameStats() {
            const groups = gameData.groups || {};
            const scores = gameData.scores || {};

            // 注册组数
            document.getElementById('stat-groups').textContent = Object.keys(groups).length;

            // 游戏次数
            document.getElementById('stat-games').textContent = gameData.game_counter || 0;

            // 最高分
            const scoresArray = Object.values(scores);
            const maxScore = scoresArray.length > 0 ? Math.max(...scoresArray) : 0;
            document.getElementById('stat-highscore').textContent = maxScore;
        }

        function updateRealTimeInfo(data) {
            // 更新当前发言者
            const currentSpeaker = data.current_speaker || '--';
            document.getElementById('current-speaker-name').textContent = currentSpeaker;

            // 更新计数
            const describedCount = data.described_groups?.length || 0;
            const orderCount = data.describe_order?.length || 0;
            const votedCount = data.voted_groups?.length || 0;
            const activeCount = data.active_groups?.length || orderCount;

            document.getElementById('desc-count').textContent = `${describedCount}/${orderCount}`;
            document.getElementById('vote-count').textContent = `${votedCount}/${activeCount}`;
        }

        function updateTimers(data) {
            const mainTimer = document.getElementById('main-timer');
            const descTimer = document.getElementById('desc-timer');
            const voteTimer = document.getElementById('vote-timer');

            // 主计时器显示最重要的倒计时
            if (data.status === 'describing') {
                if (data.speaker_remaining_seconds !== undefined && data.speaker_remaining_seconds > 0) {
                    mainTimer.textContent = `发言:${data.speaker_remaining_seconds}s`;
                    descTimer.textContent = `阶段:${formatTime(data.remaining_seconds)}`;
                    voteTimer.textContent = '--:--';

                    // 最后10秒红色闪烁
                    if (data.speaker_remaining_seconds <= 10) {
                        mainTimer.classList.add('timer-warning');
                    } else {
                        mainTimer.classList.remove('timer-warning');
                    }
                } else if (data.remaining_seconds !== undefined && data.remaining_seconds > 0) {
                    mainTimer.textContent = `阶段:${formatTime(data.remaining_seconds)}`;
                    descTimer.textContent = formatTime(data.remaining_seconds);
                    voteTimer.textContent = '--:--';

                    if (data.remaining_seconds <= 10) {
                        mainTimer.classList.add('timer-warning');
                    } else {
                        mainTimer.classList.remove('timer-warning');
                    }
                }
            } else if (data.status === 'voting') {
                if (data.remaining_seconds !== undefined && data.remaining_seconds > 0) {
                    mainTimer.textContent = `投票:${formatTime(data.remaining_seconds)}`;
                    descTimer.textContent = '--:--';
                    voteTimer.textContent = formatTime(data.remaining_seconds);

                    if (data.remaining_seconds <= 10) {
                        mainTimer.classList.add('timer-warning');
                    } else {
                        mainTimer.classList.remove('timer-warning');
                    }
                }
            } else {
                mainTimer.textContent = '--:--';
                descTimer.textContent = '--:--';
                voteTimer.textContent = '--:--';
                mainTimer.classList.remove('timer-warning');
            }

            function formatTime(seconds) {
                if (seconds === undefined) return '--:--';
                const minutes = Math.floor(seconds / 60);
                const secs = seconds % 60;
                return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            }
        }

        function updateServerStatus(isConnected) {
            const statusElement = document.getElementById('server-status');
            if (isConnected) {
                statusElement.textContent = '已连接';
                statusElement.style.color = 'var(--secondary-color)';
            } else {
                statusElement.textContent = '已断开';
                statusElement.style.color = 'var(--danger-color)';
            }
        }

        function showAlert(type, message) {
            // 移除现有的提示
            const existingAlert = document.querySelector('.alert');
            if (existingAlert) {
                existingAlert.remove();
            }

            // 创建新的提示
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.innerHTML = `
                <i class="fas fa-${type === 'success' ? 'check-circle' : 
                                   type === 'danger' ? 'exclamation-triangle' : 
                                   type === 'warning' ? 'exclamation-circle' : 'info-circle'}"></i>
                ${message}
            `;

            document.body.appendChild(alert);

            // 3秒后自动移除
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 3000);
        }

        // 游戏控制函数
        function startGame() {
            const undercoverWord = document.getElementById('undercover-word').value;
            const civilianWord = document.getElementById('civilian-word').value;

            if (!undercoverWord || !civilianWord) {
                showAlert('danger', '请输入卧底词和平民词');
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
            .then(resp => {
                if (resp && resp.code === 200) {
                    showAlert('success', resp.message || '游戏已开始！');
                    // 清空历史投票结果（新游戏开始）
                    allVoteResults = {};
                    fetchGameState();
                } else {
                    showAlert('danger', '错误：' + (resp ? resp.message : '后端无响应'));
                }
            })
            .catch(error => {
                showAlert('danger', '请求失败：' + error);
            });
        }

        function startRound() {
            fetch('/api/game/round/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(response => response.json())
            .then(resp => {
                if (resp && resp.code === 200) {
                    showAlert('success', resp.message || '回合已开始！');
                    fetchGameState();
                } else {
                    showAlert('danger', '错误：' + (resp ? resp.message : '后端无响应'));
                }
            })
            .catch(error => {
                showAlert('danger', '请求失败：' + error);
            });
        }

        function processVoting() {
            fetch('/api/game/voting/process', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(response => response.json())
            .then(resp => {
                if (resp && resp.code === 200) {
                    showAlert('success', '投票结果已处理');
                    fetchGameState();
                } else {
                    showAlert('danger', '错误：' + (resp ? resp.message : '后端无响应'));
                }
            })
            .catch(error => {
                showAlert('danger', '请求失败：' + error);
            });
        }

        function resetGame() {
            if (confirm('确定要重置游戏吗？重置后游戏状态将清除，历史记录也会被清空。')) {
                fetch('/api/game/reset', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                })
                .then(response => response.json())
                .then(resp => {
                    if (resp && resp.code === 200) {
                        showAlert('success', resp.message || '游戏已重置');
                        // 清空所有历史数据
                        allVoteResults = {};
                        fetchGameState();
                        // 清除输入框
                        document.getElementById('undercover-word').value = '';
                        document.getElementById('civilian-word').value = '';
                    } else {
                        showAlert('danger', '错误：' + (resp ? resp.message : '后端无响应'));
                    }
                })
                .catch(error => {
                    showAlert('danger', '请求失败：' + error);
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
    data = get_backend_data('/api/game/state', use_admin=True)
    if data is None:
        return jsonify({"code": 500, "message": "后端状态接口无响应", "data": {}}), 500
    return jsonify(data)


@frontend_app.route('/api/public/status')
def api_public_status():
    """代理后端公开状态API"""
    data = get_backend_data('/api/status', use_admin=False)
    if data is None:
        return jsonify({"code": 500, "message": "后端状态接口无响应", "data": {}}), 500
    return jsonify(data)


@frontend_app.route('/api/game/start', methods=['POST'])
def api_start_game():
    """代理后端API"""
    from flask import request
    data = request.json
    response = requests.post(
        f"{BACKEND_URL}/api/game/start",
        json=data,
        headers=ADMIN_HEADERS,
        timeout=2
    )
    return jsonify(response.json()), response.status_code


@frontend_app.route('/api/game/round/start', methods=['POST'])
def api_start_round():
    """代理后端API"""
    response = requests.post(
        f"{BACKEND_URL}/api/game/round/start",
        headers=ADMIN_HEADERS,
        timeout=2
    )
    return jsonify(response.json()), response.status_code


@frontend_app.route('/api/game/voting/process', methods=['POST'])
def api_process_voting():
    """代理后端API"""
    response = requests.post(
        f"{BACKEND_URL}/api/game/voting/process",
        headers=ADMIN_HEADERS,
        timeout=2
    )
    return jsonify(response.json()), response.status_code


@frontend_app.route('/api/game/reset', methods=['POST'])
def api_reset_game():
    """代理后端API"""
    response = requests.post(
        f"{BACKEND_URL}/api/game/reset",
        headers=ADMIN_HEADERS,
        timeout=2
    )
    return jsonify(response.json()), response.status_code


if __name__ == '__main__':
    print("=" * 50)
    print("前端界面服务器启动中...")
    print("访问地址: http://127.0.0.1:5001")
    print("=" * 50)
    print("=" * 50)
    print("注意：请确保后端服务器(backend.py)已启动")
    print("=" * 50)

    # 前端服务器运行在5001端口
    frontend_app.run(host='0.0.0.0', port=5001, debug=True)
"""
前端界面模块
"""
from flask import Flask, render_template_string, jsonify
import os
import requests
import threading
import time
from datetime import datetime

# 前端服务器
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

# HTML模板
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
            font-size: 16px;
        }

        /* 主容器 */
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

        .game-state-display {
            font-size: 2em;
            font-weight: bold;
            margin: 5px 0;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 3px 5px rgba(0,0,0,0.15);
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
            min-height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .game-state-display.state-preparing {
            color: var(--primary-color);
            border-color: var(--primary-color);
        }

        .game-state-display.state-describing {
            color: var(--primary-color);
            border-color: var(--primary-color);
            animation: pulse-glow 2s infinite;
        }

        .game-state-display.state-voting {
            color: var(--warning-color);
            border-color: var(--warning-color);
        }

        .game-state-display.state-round-end {
            color: #9b59b6;
            border-color: #9b59b6;
        }

        .game-state-display.state-game-end {
            color: var(--secondary-color);
            border-color: var(--secondary-color);
            animation: celebration 1s ease-in-out 3;
        }

        @keyframes pulse-glow {
            0% { box-shadow: 0 0 5px rgba(52, 152, 219, 0.5); }
            50% { box-shadow: 0 0 15px rgba(52, 152, 219, 0.8); }
            100% { box-shadow: 0 0 5px rgba(52, 152, 219, 0.5); }
        }

        @keyframes celebration {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        /* 主要内容区域 */
        .content-area {
            flex: 1;
            display: grid;
            grid-template-columns: 280px 1fr 350px;
            gap: 10px;
            overflow: hidden;
            min-height: 0;
        }

        /* 左侧控制栏 */
        .left-sidebar {
            display: flex;
            flex-direction: column;
            gap: 10px;
            overflow-y: auto;
        }

        .left-sidebar::-webkit-scrollbar {
            width: 5px;
        }

        .left-sidebar::-webkit-scrollbar-thumb {
            background: var(--primary-color);
            border-radius: 5px;
        }

        /* 玩家区域 */
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

        .players-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            overflow-y: auto;
            padding-right: 5px;
            flex: 1;
        }

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
            overflow-y: auto;
            max-height: 300px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        /* 玩家卡片滚动条样式 */
        .player-card::-webkit-scrollbar {
            width: 4px;
        }

        .player-card::-webkit-scrollbar-track {
            background: rgba(0,0,0,0.05);
            border-radius: 4px;
        }

        .player-card::-webkit-scrollbar-thumb {
            background: rgba(52, 152, 219, 0.5);
            border-radius: 4px;
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
            border-color: var(--border-color);
            background: rgba(231, 76, 60, 0.08);
        }

        .player-card.undercover .player-name {
            color: var(--danger-color);
        }

        .player-card.undercover.current-turn {
            border-color: var(--danger-color);
            animation: pulse-danger 1.5s infinite;
            background: rgba(231, 76, 60, 0.12);
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
            font-size: 1.6em;
        }

        @keyframes pulse-border {
            0% { box-shadow: 0 0 0 0 rgba(52, 152, 219, 0.7); }
            70% { box-shadow: 0 0 0 6px rgba(52, 152, 219, 0); }
            100% { box-shadow: 0 0 0 0 rgba(52, 152, 219, 0); }
        }

        @keyframes pulse-danger {
            0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7); }
            70% { box-shadow: 0 0 0 6px rgba(231, 76, 60, 0); }
            100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
        }

        .player-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .player-name {
            font-weight: bold;
            font-size: 1.2em;
            display: flex;
            align-items: center;
            gap: 5px;
            color: var(--dark-color);
        }

        .player-role {
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 0.9em;
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
            font-size: 1em;
        }

        .status-badge {
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
            color: white;
        }

        .status-speaking { background: var(--primary-color); }
        .status-described { background: #9b59b6; }
        .status-voted { background: var(--warning-color); }
        .status-ready { background: #16a085; }
        .status-online { background: var(--secondary-color); }
        .status-offline { background: #95a5a6; }

        /* 玩家信息栏 */
        .player-info {
            display: flex;
            justify-content: space-between;
            padding: 6px 8px;
            background: rgba(0,0,0,0.03);
            border-radius: 4px;
            margin-bottom: 8px;
            font-size: 1em;
            font-weight: bold;
            color: #7f8c8d;
        }

        .player-content {
            background: rgba(0,0,0,0.05);
            padding: 8px;
            border-radius: 5px;
            margin-top: 8px;
            font-size: 1em;
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
            display: none; 
        }

        /* 信息区域 */
        .info-section {
            display: flex;
            flex-direction: column;
            gap: 10px;
            min-height: 0;
            width: 100%;
        }

        .info-tabs-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }

        /* 标签页导航按钮 */
        .tab-nav {
            display: flex;
            gap: 5px;
            margin-bottom: 10px;
            flex-shrink: 0;
        }

        .tab-nav-btn {
            flex: 1;
            padding: 10px 15px;
            border: none;
            background: var(--light-color);
            color: var(--dark-color);
            cursor: pointer;
            border-radius: 6px 6px 0 0;
            font-weight: bold;
            transition: all 0.2s;
            border: 1px solid var(--border-color);
            border-bottom: none;
        }

        .tab-nav-btn:hover {
            background: #e0e5ea;
        }

        .tab-nav-btn.active {
            background: var(--primary-color);
            color: white;
        }

        .info-tabs {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
            background: var(--card-bg);
            border-radius: 0 0 8px 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid var(--border-color);
        }

        .tab-pane {
            flex: 1;
            display: none;
            flex-direction: column;
            overflow: hidden;
        }

        .tab-pane.active {
            display: flex;
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
            flex-direction: column;
            gap: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid var(--border-color);
        }

        .words-section h4 {
            margin: 0;
            color: var(--primary-color);
            font-size: 1em;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* 控制按钮容器 */
        .control-buttons-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        /* 倒计时显示区域 */
        .timer-display {
            background: var(--card-bg);
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid var(--border-color);
        }

        .timer-display h4 {
            margin: 0 0 10px 0;
            color: var(--primary-color);
            font-size: 1em;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .timer-item {
            background: var(--light-color);
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 8px;
            text-align: center;
        }

        .timer-item:last-child {
            margin-bottom: 0;
        }

        .timer-label {
            font-size: 0.85em;
            color: #666;
            margin-bottom: 5px;
        }

        .timer-value {
            font-size: 1.3em;
            font-weight: bold;
            color: var(--primary-color);
        }

        .timer-item.voting .timer-value {
            color: var(--warning-color);
        }

        .word-input {
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
            margin-bottom: 5px;
            flex-shrink: 0;
        }

        .stat-card {
            flex: 1;
            background: var(--card-bg);
            border-radius: 8px;
            padding: 10px;
            text-align: center;
            transition: all 0.3s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px; 
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .stat-card h4 {
            color: #7f8c8d;
            font-size: 1.2em;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
        }

        .stat-value {
            font-size: 1.6em;
            font-weight: bold;
            color: var(--dark-color);
            line-height: 1; 
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

            .player-card {
                max-height: 250px;
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

        /* 模态框样式 */
        .modal {
            display: none;
            position: fixed;
            z-index: 2000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            animation: fadeIn 0.3s;
        }

        .modal.show {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .modal-content {
            background-color: var(--card-bg);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
            max-width: 700px;
            width: 90%;
            max-height: 85vh;
            overflow-y: auto;
            animation: slideDown 0.3s;
            position: relative;
        }

        @keyframes slideDown {
            from {
                transform: translateY(-50px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid var(--border-color);
        }

        .modal-header h2 {
            color: var(--dark-color);
            font-size: 1.5em;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .close-btn {
            background: none;
            border: none;
            font-size: 28px;
            color: var(--dark-color);
            cursor: pointer;
            padding: 0;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: all 0.3s ease;
        }

        .close-btn:hover {
            background-color: var(--light-color);
            color: var(--danger-color);
        }

        .modal-body {
            margin-bottom: 20px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: var(--dark-color);
            font-weight: 600;
            font-size: 1em;
        }

        .form-group input[type="number"] {
            width: 100%;
            padding: 10px 12px;
            border: 2px solid var(--border-color);
            border-radius: 6px;
            font-size: 1em;
            transition: border-color 0.3s ease;
        }

        .form-group input[type="number"]:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2);
        }

        .rounds-container {
            margin-top: 20px;
            max-height: 400px;
            overflow-y: auto;
            padding-right: 5px;
        }

        .rounds-container::-webkit-scrollbar {
            width: 6px;
        }

        .rounds-container::-webkit-scrollbar-track {
            background: var(--border-color);
            border-radius: 5px;
        }

        .rounds-container::-webkit-scrollbar-thumb {
            background: var(--primary-color);
            border-radius: 5px;
        }

        .round-item {
            background: var(--light-color);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            border: 2px solid var(--border-color);
            transition: all 0.3s ease;
        }

        .round-item:hover {
            border-color: var(--primary-color);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .round-item-header {
            font-weight: bold;
            color: var(--primary-color);
            margin-bottom: 10px;
            font-size: 1.1em;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .round-item-inputs {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }

        .round-item-input {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .round-item-input label {
            font-size: 0.9em;
            color: var(--dark-color);
            font-weight: 600;
        }

        .round-item-input input {
            padding: 8px 10px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            font-size: 0.95em;
            transition: border-color 0.3s ease;
        }

        .round-item-input input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
        }

        .modal-footer {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            padding-top: 20px;
            border-top: 2px solid var(--border-color);
        }

        .modal-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .modal-btn-primary {
            background: var(--secondary-color);
            color: white;
        }

        .modal-btn-primary:hover {
            background: #229954;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        .modal-btn-secondary {
            background: var(--light-color);
            color: var(--dark-color);
        }

        .modal-btn-secondary:hover {
            background: #e1e8ed;
        }

        @media (max-width: 768px) {
            .round-item-inputs {
                grid-template-columns: 1fr;
            }

            .modal-content {
                width: 95%;
                padding: 20px;
            }
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
                </div>
            </div>

            <div class="game-controls">
                <button class="control-btn btn-reset" onclick="resetGame()">
                    <i class="fas fa-redo"></i> 重置游戏
                </button>
            </div>
        </div>

        <!-- 游戏状态显示 -->
        <div class="game-state-display" id="game-state-display">
            等待游戏开始...
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
            <!-- 左侧控制栏 -->
            <div class="left-sidebar">
                <!-- 词语设置 -->
                <div class="words-section">
                    <h4><i class="fas fa-book"></i> 词语设置</h4>
                    <div class="word-input">
                        <label for="undercover-word"><i class="fas fa-user-secret"></i> 卧底词</label>
                        <input type="text" id="undercover-word" placeholder="留空自动选择">
                    </div>
                    <div class="word-input">
                        <label for="civilian-word"><i class="fas fa-users"></i> 平民词</label>
                        <input type="text" id="civilian-word" placeholder="留空自动选择">
                    </div>
                    <div class="control-buttons-group">
                        <button class="control-btn btn-start" onclick="startSingleGame()">
                            <i class="fas fa-play"></i> 开始游戏
                        </button>
                        <button class="control-btn btn-multi" onclick="openMultiRoundModal()">
                            <i class="fas fa-layer-group"></i> 多轮游戏
                        </button>
                    </div>
                </div>

                <!-- 倒计时显示 -->
                <div class="timer-display">
                    <h4><i class="fas fa-clock"></i> 倒计时</h4>
                    <div class="timer-item">
                        <div class="timer-label">描述阶段</div>
                        <div class="timer-value" id="desc-timer-display">--:--</div>
                    </div>
                    <div class="timer-item voting">
                        <div class="timer-label">投票阶段</div>
                        <div class="timer-value" id="vote-timer-display">--:--</div>
                    </div>
                </div>
            </div>

            <!-- 中间玩家区域 -->
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

            <!-- 右侧信息区域 -->
            <div class="info-section">
                <div class="info-tabs-container">
                    <!-- 标签页导航按钮 -->
                    <div class="tab-nav">
                        <button class="tab-nav-btn active" onclick="switchTab('descriptions')"><i class="fas fa-comments"></i> 描述</button>
                        <button class="tab-nav-btn" onclick="switchTab('votes')"><i class="fas fa-vote-yea"></i> 投票</button>
                        <button class="tab-nav-btn" onclick="switchTab('results')"><i class="fas fa-poll"></i> 结果</button>
                    </div>
                    <div class="info-tabs">
                        <!-- 描述记录 -->
                        <div class="tab-pane active" id="tab-descriptions">
                            <div class="tab-content" id="descriptions-content">
                                <div class="description-item">
                                    <div class="desc-header">暂无描述</div>
                                </div>
                            </div>
                        </div>

                        <!-- 投票记录 -->
                        <div class="tab-pane" id="tab-votes">
                            <div class="tab-content" id="votes-content">
                                <div class="round-vote-section">
                                    <div class="round-title">暂无投票记录</div>
                                </div>
                            </div>
                        </div>

                        <!-- 游戏结果 -->
                        <div class="tab-pane" id="tab-results">
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

        <!-- 底部信息栏 -->
        <div class="bottom-bar">
            <div>服务器: <span id="server-status" class="glow">已连接</span></div>
            <div>当前发言者: <span id="current-speaker-name" class="glow">--</span></div>
            <div>描述: <span id="desc-count">0/0</span> | 投票: <span id="vote-count">0/0</span></div>
        </div>
    </div>

    <!-- 多轮游戏配置模态框 -->
    <div id="multiRoundModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>
                    <i class="fas fa-layer-group"></i>
                    开始多轮游戏
                </h2>
                <button class="close-btn" onclick="closeMultiRoundModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label for="round-count">
                        <i class="fas fa-hashtag"></i>
                        游戏轮数
                    </label>
                    <input type="number" id="round-count" min="1" max="10" value="1" 
                           onchange="generateRoundInputs()" placeholder="请输入轮数（1-10）">
                </div>
                <div class="rounds-container" id="rounds-container">
                    <!-- 动态生成的轮数输入框将显示在这里 -->
                </div>
            </div>
            <div class="modal-footer">
                <button class="modal-btn modal-btn-secondary" onclick="closeMultiRoundModal()">
                    <i class="fas fa-times"></i>
                    取消
                </button>
                <button class="modal-btn modal-btn-primary" onclick="submitMultiRoundGame()">
                    <i class="fas fa-check"></i>
                    开始游戏
                </button>
            </div>
        </div>
    </div>

    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <script>
        // WebSocket 连接
        const socket = io('http://127.0.0.1:5000');
        let gameData = {};
        let allVoteResults = {}; // 存储所有回合的投票结果，键为 "gameNumber_round" 或 "round"
        let gameRoundMapping = {}; // 映射：round -> gameNumber（用于单轮游戏或兼容性）
        let descriptionRoundMapping = {}; // 映射：round -> gameNumber（用于描述记录）
        let voteRoundMapping = {}; // 映射：round -> gameNumber（用于投票记录）

        // localStorage 键名
        const STORAGE_KEYS = {
            VOTE_RESULTS: 'undercover_vote_results',
            ROUND_MAPPINGS: 'undercover_round_mappings',
            MULTI_ROUND_CONFIG: 'undercover_multi_round_config',
            CURRENT_ROUND_INDEX: 'undercover_current_round_index'
        };

        // 保存数据到 localStorage
        function saveToLocalStorage() {
            try {
                localStorage.setItem(STORAGE_KEYS.VOTE_RESULTS, JSON.stringify(allVoteResults));
                localStorage.setItem(STORAGE_KEYS.ROUND_MAPPINGS, JSON.stringify({
                    gameRoundMapping: gameRoundMapping,
                    descriptionRoundMapping: descriptionRoundMapping,
                    voteRoundMapping: voteRoundMapping
                }));
                if (multiRoundConfig) {
                    localStorage.setItem(STORAGE_KEYS.MULTI_ROUND_CONFIG, JSON.stringify(multiRoundConfig));
                    localStorage.setItem(STORAGE_KEYS.CURRENT_ROUND_INDEX, currentRoundIndex.toString());
                }
            } catch (e) {
                console.error('保存到 localStorage 失败:', e);
            }
        }

        // 从 localStorage 恢复数据
        function loadFromLocalStorage() {
            try {
                // 恢复投票结果
                const savedVoteResults = localStorage.getItem(STORAGE_KEYS.VOTE_RESULTS);
                if (savedVoteResults) {
                    allVoteResults = JSON.parse(savedVoteResults);
                }

                // 恢复轮次映射
                const savedMappings = localStorage.getItem(STORAGE_KEYS.ROUND_MAPPINGS);
                if (savedMappings) {
                    const mappings = JSON.parse(savedMappings);
                    gameRoundMapping = mappings.gameRoundMapping || {};
                    descriptionRoundMapping = mappings.descriptionRoundMapping || {};
                    voteRoundMapping = mappings.voteRoundMapping || {};
                }

                // 恢复多轮配置
                const savedConfig = localStorage.getItem(STORAGE_KEYS.MULTI_ROUND_CONFIG);
                if (savedConfig) {
                    multiRoundConfig = JSON.parse(savedConfig);
                    const savedIndex = localStorage.getItem(STORAGE_KEYS.CURRENT_ROUND_INDEX);
                    if (savedIndex !== null) {
                        currentRoundIndex = parseInt(savedIndex) || 0;
                    }
                }
            } catch (e) {
                console.error('从 localStorage 恢复数据失败:', e);
            }
        }

        // 清除 localStorage 数据
        function clearLocalStorage() {
            try {
                localStorage.removeItem(STORAGE_KEYS.VOTE_RESULTS);
                localStorage.removeItem(STORAGE_KEYS.ROUND_MAPPINGS);
                localStorage.removeItem(STORAGE_KEYS.MULTI_ROUND_CONFIG);
                localStorage.removeItem(STORAGE_KEYS.CURRENT_ROUND_INDEX);
            } catch (e) {
                console.error('清除 localStorage 失败:', e);
            }
        }

        // 页面加载时恢复数据
        loadFromLocalStorage();

        // 连接成功
        socket.on('connect', function() {
            console.log('WebSocket 已连接');
            showAlert('success', '已连接到服务器');
            updateServerStatus(true);
            // 请求初始状态
            socket.emit('request_status');
            socket.emit('request_timer');
        });

        // 接收状态更新推送
        socket.on('status_update', function(data) {
            updateRealTimeInfo(data);
            updateTimers(data);
        });

        // 接收倒计时更新推送
        socket.on('timer_update', function(data) {
            updateTimers(data);
            updateGameStateDisplay(data);
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

            // 存储投票结果，添加轮次信息
            if (data.round) {
                // 确定当前是第几轮游戏
                const gameNumber = multiRoundConfig ? (currentRoundIndex + 1) : null;
                
                // 添加轮次信息到结果数据
                data.game_number = gameNumber;
                
                // 使用组合键存储（如果有轮次信息），否则使用回合号
                const resultKey = gameNumber ? `${gameNumber}_${data.round}` : data.round.toString();
                allVoteResults[resultKey] = data;
                
                // 也保存一个回合号到轮次的映射（用于兼容性）
                if (gameNumber) {
                    gameRoundMapping[data.round] = gameNumber;
                    voteRoundMapping[data.round] = gameNumber;
                }
                
                // 保存到 localStorage
                saveToLocalStorage();
            }

            updateVoteRecords();
            updateGameResults();
            
            // 如果游戏结束且有多轮配置，检查是否需要开始下一轮
            if (data.game_ended && multiRoundConfig) {
                checkAndStartNextRound();
            }
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

        // 跟踪上一次的游戏状态，用于检测新游戏开始
        let lastGameStatus = '';
        let lastCurrentRound = 0;
        let lastGameNumber = null;
        
        function updateAllDisplay() {
            // 记录当前轮次对应的回合号（用于描述和投票记录）
            const currentRound = gameData.current_round || 0;
            const gameNumber = multiRoundConfig ? (currentRoundIndex + 1) : null;
            const currentStatus = gameData.status || '';
            
            // 检测新游戏开始：轮次变化（gameNumber变化）或状态从 game_end 变为 word_assigned
            const isNewGame = (multiRoundConfig && lastGameNumber !== null && lastGameNumber !== gameNumber) ||
                              (lastGameStatus === 'game_end' && (currentStatus === 'word_assigned' || currentStatus === 'registered'));
            
            if (currentRound > 0 && gameNumber) {
                // 如果是新游戏开始，或者映射不存在，或者映射的值不对，强制更新
                const existingGameNumber = descriptionRoundMapping[currentRound];
                // 如果轮次变化了，或者映射不存在，或者映射的值不对，则更新
                if (isNewGame || !existingGameNumber || (existingGameNumber !== gameNumber && multiRoundConfig)) {
                    descriptionRoundMapping[currentRound] = gameNumber;
                }
                
                const existingVoteGameNumber = voteRoundMapping[currentRound];
                if (isNewGame || !existingVoteGameNumber || (existingVoteGameNumber !== gameNumber && multiRoundConfig)) {
                    voteRoundMapping[currentRound] = gameNumber;
                }
                
                // 保存到 localStorage
                saveToLocalStorage();
            }
            
            // 更新跟踪变量
            lastGameStatus = currentStatus;
            lastCurrentRound = currentRound;
            lastGameNumber = gameNumber;
            
            updateGameStatus();
            updatePlayers();
            updateDescriptions();
            updateVoteRecords();
            updateGameResults();
            updateGameStats();
            updateGameStateDisplay(gameData); 
            updateRealTimeInfo(gameData);
            updateBottomCounters(); 
        }

        function updateBottomCounters() {
            // 从当前的 gameData 中获取数据
            const describedCount = gameData.described_groups?.length || 0;
            const orderCount = gameData.describe_order?.length || 0;
            const votedCount = gameData.voted_groups?.length || 0;
            const activeCount = gameData.active_groups?.length || orderCount;

            document.getElementById('desc-count').textContent = `${describedCount}/${orderCount}`;
            document.getElementById('vote-count').textContent = `${votedCount}/${activeCount}`;
        }

        function updateGameStatus() {
            const status = gameData.status || 'waiting';
            const statusMap = {
                'waiting': '准备中',
                'registered': '准备中',
                'word_assigned': '准备中',
                'describing': '描述中',
                'voting': '投票中',
                'round_end': '回合结束',
                'game_end': '游戏结束'
            };

            document.getElementById('game-status').textContent = statusMap[status] || status;
            document.getElementById('stat-round').textContent = gameData.current_round || 0;
        }

        function updatePlayers() {
            const playersGrid = document.getElementById('players-grid');
            const groups = gameData.groups || {};
            const gameStatus = gameData.status || 'waiting';

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

                const isUndercover = (gameStatus === 'word_assigned' || 
                                     gameStatus === 'describing' || 
                                     gameStatus === 'voting' || 
                                     gameStatus === 'round_end' || 
                                     gameStatus === 'game_end') 
                                     ? (info.role === 'undercover') 
                                     : false;

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

                // 构建角色显示逻辑
                let roleDisplay = '';
                let roleBadge = '';

                if (gameStatus === 'word_assigned' || 
                    gameStatus === 'describing' || 
                    gameStatus === 'voting' || 
                    gameStatus === 'round_end' || 
                    gameStatus === 'game_end') {
                    
                    if (info.role) {
                        const isUndercoverRole = info.role === 'undercover';
                        roleDisplay = isUndercoverRole ? '<i class="fas fa-user-secret"></i>' : '';
                        roleBadge = `
                            <div class="player-role ${isUndercoverRole ? 'role-undercover' : 'role-civilian'}">
                                ${isUndercoverRole ? '卧底' : '平民'}
                            </div>
                        `;
                    }
                } else {
                    roleBadge = `
                        <div class="player-role" style="background: #95a5a6; color: white;">
                            未开始
                        </div>
                    `;
                }

                // 玩家卡片
                html += `
                    <div class="player-card ${isUndercover ? 'undercover' : ''} ${isEliminated ? 'eliminated' : ''} ${isCurrentSpeaker ? 'current-turn' : ''}">
                        <div class="player-header">
                            <div class="player-name">
                                ${name} ${roleDisplay}
                            </div>
                            ${roleBadge}
                        </div>

                        <div class="player-status">
                            ${isCurrentSpeaker ? '<span class="status-badge status-speaking">发言中</span>' : ''}
                            ${hasDescribed && !isCurrentSpeaker ? '<span class="status-badge status-described">已描述</span>' : ''}
                            ${hasVoted ? '<span class="status-badge status-voted">已投票</span>' : ''}
                            ${(gameStatus === 'word_assigned' || gameStatus === 'round_end') && (gameData.ready_groups || []).includes(name) ? '<span class="status-badge status-ready">已准备</span>' : ''}
                            <span class="status-badge ${isOnline ? 'status-online' : 'status-offline'}">
                                ${isOnline ? '在线' : '离线'}
                            </span>
                        </div>

                        <!-- 玩家信息栏 -->
                        <div class="player-info">
                            <span>总分: ${score}</span>
                            <span>卧底: ${info.undercover_count || 0}次</span>
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

            // 按顺序排列（最新的在前）
            // 首先按轮次排序，然后按回合排序
            const descriptionEntries = Object.entries(descriptions).map(([round, roundDescriptions]) => {
                const roundNum = parseInt(round);
                const gameNumber = descriptionRoundMapping[roundNum] || null;
                return {
                    round: roundNum,
                    gameNumber: gameNumber || 999, // 单轮游戏放到最后
                    roundDescriptions: roundDescriptions
                };
            });
            
            // 排序：先按轮次降序，再按回合降序
            descriptionEntries.sort((a, b) => {
                if (a.gameNumber !== b.gameNumber) {
                    return b.gameNumber - a.gameNumber;
                }
                return b.round - a.round;
            });

            descriptionEntries.forEach(({round, gameNumber, roundDescriptions}) => {
                if (roundDescriptions.length === 0) return;

                // 确定这个回合属于第几轮
                const displayGameNumber = gameNumber !== 999 ? gameNumber : null;
                let titleText = '';
                // 判断是否显示轮次：如果有轮次信息且不是默认值，就显示
                if (displayGameNumber !== null) {
                    titleText = `第 ${displayGameNumber} 轮第 ${round} 回合 - ${roundDescriptions.length} 个描述`;
                } else {
                    titleText = `第 ${round} 回合 - ${roundDescriptions.length} 个描述`;
                }

                html += `
                    <div class="round-vote-section">
                        <div class="round-title">${titleText}</div>
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

            // 添加当前回合的投票记录
            const currentRound = gameData.current_round;
            if (gameData.votes && gameData.votes[currentRound]) {
                const currentVotes = gameData.votes[currentRound];
                if (Object.keys(currentVotes).length > 0) {
                    // 确定当前是第几轮游戏
                    const gameNumber = multiRoundConfig ? (currentRoundIndex + 1) : null;
                    
                    // 记录轮次映射
                    if (gameNumber && !voteRoundMapping[currentRound]) {
                        voteRoundMapping[currentRound] = gameNumber;
                        // 保存到 localStorage
                        saveToLocalStorage();
                    }
                    
                    // 使用组合键存储（如果有轮次信息），避免覆盖已有的投票结果
                    const voteKey = gameNumber ? `${gameNumber}_${currentRound}` : currentRound.toString();
                    if (!allVotes[voteKey]) {
                        allVotes[voteKey] = {
                            round: currentRound,
                            vote_details: currentVotes,
                            vote_count: {}
                        };

                        // 计算当前回合的票数
                        const voteCount = {};
                        Object.values(currentVotes).forEach(target => {
                            voteCount[target] = (voteCount[target] || 0) + 1;
                        });
                        allVotes[voteKey].vote_count = voteCount;
                    }
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

            // 按顺序排列（最新的在前）
            // 首先按轮次排序，然后按回合排序
            const voteEntries = Object.entries(allVotes).map(([key, voteData]) => {
                // 解析键：如果是 "gameNumber_round" 格式，提取轮次和回合
                const parts = key.toString().split('_');
                let gameNumber = null;
                let round = null;
                
                if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
                    gameNumber = parseInt(parts[0]);
                    round = parseInt(parts[1]);
                } else {
                    round = parseInt(key);
                    gameNumber = voteRoundMapping[round] || (voteData.game_number || null);
                }
                
                return {
                    key: key,
                    gameNumber: gameNumber || 999, // 单轮游戏放到最后
                    round: round,
                    voteData: voteData
                };
            });
            
            // 排序：先按轮次降序，再按回合降序
            voteEntries.sort((a, b) => {
                if (a.gameNumber !== b.gameNumber) {
                    return b.gameNumber - a.gameNumber;
                }
                return b.round - a.round;
            });

            voteEntries.forEach(({key, gameNumber, round, voteData}) => {
                // 确定这个回合属于第几轮
                const displayGameNumber = gameNumber !== 999 ? gameNumber : null;
                
                let titleText = '';
                // 判断是否显示轮次：如果有轮次信息且不是默认值，就显示
                if (displayGameNumber !== null) {
                    titleText = `第 ${displayGameNumber} 轮第 ${round} 回合投票记录`;
                } else {
                    titleText = `第 ${round} 回合投票记录`;
                }

                html += `
                    <div class="round-vote-section">
                        <div class="round-title">${titleText}</div>
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

            // 按顺序排列结果（最新的在前）
            // 首先按轮次排序，然后按回合排序
            const results = Object.entries(allVoteResults).map(([key, result]) => {
                // 解析键：如果是 "gameNumber_round" 格式，提取轮次和回合
                const parts = key.split('_');
                let gameNumber = null;
                let round = null;
                
                if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
                    gameNumber = parseInt(parts[0]);
                    round = parseInt(parts[1]);
                } else {
                    round = parseInt(key);
                    // 使用与投票记录相同的逻辑：优先从 voteRoundMapping 获取
                    gameNumber = voteRoundMapping[round] || (result.game_number || null);
                }
                
                return {
                    key: key,
                    gameNumber: gameNumber || 999, // 单轮游戏放到最后
                    round: round,
                    result: result
                };
            });
            
            // 排序：先按轮次降序，再按回合降序
            results.sort((a, b) => {
                if (a.gameNumber !== b.gameNumber) {
                    return b.gameNumber - a.gameNumber;
                }
                return b.round - a.round;
            });
            
            // 检查最新的游戏结果，看是否需要开始下一轮
            let latestResultChecked = false;

            results.forEach(({key, gameNumber, round, result}) => {
                const roundScores = result.round_scores || {};
                const totalScores = result.total_scores || {};
                
                // 构建标题：使用与投票记录和描述记录相同的逻辑
                const displayGameNumber = gameNumber !== 999 ? gameNumber : null;
                let titleText = '';
                // 判断是否显示轮次：如果有轮次信息且不是默认值，就显示（不管multiRoundConfig是否存在）
                if (displayGameNumber !== null && displayGameNumber !== 999) {
                    titleText = `第 ${displayGameNumber} 轮第 ${round} 回合结果`;
                } else {
                    titleText = `第 ${round} 回合结果`;
                }

                html += `
                    <div class="result-item ${result.game_ended ? 'victory' : ''}">
                        <div class="result-header">
                            <span>${titleText}</span>
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

                // 显示本轮各组成绩
                if (result.round_scores && Object.keys(result.round_scores).length > 0) {
                    html += `
                        <div style="margin: 10px 0; padding: 10px; background: rgba(0,0,0,0.05); border-radius: 5px;">
                            <strong><i class="fas fa-star"></i> 本轮得分:</strong>
                    `;

                    Object.entries(result.round_scores).forEach(([group, score]) => {
                        // 区分得分类型
                        let scoreType = '生存分';
                        if (result.game_ended && result.winner === 'undercover' && group === result.undercover_group) {
                            if (score >= 4) {  // 1生存分 + 3胜利分
                                scoreType = '生存分+胜利分';
                            }
                        }

                        html += `
                            <div style="display: flex; justify-content: space-between; padding: 2px 0;">
                                <span>${group} <small style="color: #7f8c8d">(${scoreType})</small></span>
                                <span style="font-weight: bold; color: ${score > 0 ? 'var(--secondary-color)' : '#7f8c8d'}">
                                    ${score > 0 ? '+' : ''}${score}分
                                </span>
                            </div>
                        `;
                    });

                    html += `</div>`;
                }

                // 显示累计得分
                if (Object.keys(totalScores).length > 0) {
                    html += `
                        <div style="margin: 10px 0; padding: 10px; background: rgba(243, 156, 18, 0.1); border-radius: 5px;">
                            <strong><i class="fas fa-trophy"></i> 累计得分:</strong>
                    `;

                    // 按分数排序
                    const sortedScores = Object.entries(totalScores).sort((a, b) => b[1] - a[1]);

                    sortedScores.forEach(([group, score], index) => {
                        const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '';
                        html += `
                            <div style="display: flex; justify-content: space-between; padding: 3px 0; ${index === 0 ? 'font-weight: bold;' : ''}">
                                <span>${medal} ${group}</span>
                                <span style="color: var(--warning-color)">${score}分</span>
                            </div>
                        `;
                    });

                    html += `</div>`;
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
                    
                    // 如果这是最新的结果且游戏结束，检查是否需要开始下一轮
                    if (!latestResultChecked && results[0] && results[0].key === key && multiRoundConfig) {
                        latestResultChecked = true;
                        checkAndStartNextRound();
                    }
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
            const describedGroups = data.described_groups || [];
            const describeOrder = data.describe_order || [];
            const votedGroups = data.voted_groups || [];
            const activeGroups = data.active_groups || [];

            // 描述完成人数
            const describedCount = describedGroups.length;
            const orderCount = describeOrder.length;

            // 投票完成人数
            const votedCount = votedGroups.length;
            const activeCount = activeGroups.length || orderCount;

            document.getElementById('desc-count').textContent = `${describedCount}/${orderCount}`;
            document.getElementById('vote-count').textContent = `${votedCount}/${activeCount}`;

            // 更新游戏状态显示
            updateGameStateDisplay(data);
        }

        function updateGameStateDisplay(data) {
            const displayElement = document.getElementById('game-state-display');
            const status = data.status || 'waiting';
            const currentSpeaker = data.current_speaker || '';
            const describedGroups = data.described_groups || [];
            const votedGroups = data.voted_groups || [];
            const describeOrder = data.describe_order || [];
            const activeGroups = data.active_groups || [];
            const currentRound = data.current_round || 1;
            const eliminatedGroups = data.eliminated_groups || [];
            const currentSpeakerIndex = data.current_speaker_index || 0;

            let displayText = '';
            let displayClass = '';
            let bgColor = '';

            const latestRound = Math.max(...Object.keys(allVoteResults).map(Number).filter(n => !isNaN(n)), 0);
            const latestResult = latestRound > 0 ? allVoteResults[latestRound] : null;

            switch(status) {
                case 'waiting':
                case 'registered':
                case 'word_assigned':
                    const readyGroups = data.ready_groups || [];
                    const activeGroups = data.active_groups || [];
                    if (readyGroups.length > 0 && activeGroups.length > 0) {
                        displayText = `🎮 等待准备 (${readyGroups.length}/${activeGroups.length})`;
                    } else {
                        displayText = '🎮 准备中...';
                    }
                    displayClass = 'state-preparing';
                    bgColor = 'rgba(52, 152, 219, 0.1)';
                    break;

                case 'describing':
                    if (describeOrder.length > 0) {
                        let html = '<div style="display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 8px; margin-left: 20px;">';

                        describeOrder.forEach((group, index) => {
                            const isCurrent = group === currentSpeaker;
                            const isEliminated = eliminatedGroups.includes(group);
                            const hasDescribed = describedGroups.includes(group);
                            const isBeforeCurrent = index < currentSpeakerIndex;

                            let text = group;
                            let style = '';

                            if (isEliminated) {
                                style = `
                                    padding: 3px 8px;
                                    border-radius: 4px;
                                    font-size: 0.9em;
                                    background: #95a5a6;
                                    color: white;
                                    font-weight: normal;
                                    border: 1px solid var(--border-color);
                                    opacity: 0.7;
                                `;
                                text = '💀 ' + text;
                            } else if (isCurrent) {
                                style = `
                                    padding: 5px 10px;
                                    border-radius: 6px;
                                    font-size: 1.1em;
                                    background: var(--primary-color);
                                    color: white;
                                    font-weight: bold;
                                    border: 2px solid var(--primary-color);
                                    animation: pulse-border 1.5s infinite;
                                    box-shadow: 0 0 10px rgba(52, 152, 219, 0.5);
                                `;
                                text = '🎤 ' + text;
                            } else if (isBeforeCurrent || hasDescribed) {
                                style = `
                                    padding: 3px 8px;
                                    border-radius: 4px;
                                    font-size: 0.9em;
                                    background: #2ecc71;
                                    color: white;
                                    font-weight: normal;
                                    border: 1px solid var(--border-color);
                                `;
                                text = '✅ ' + text;
                            } else {
                                style = `
                                    padding: 3px 8px;
                                    border-radius: 4px;
                                    font-size: 0.9em;
                                    background: var(--light-color);
                                    color: var(--dark-color);
                                    font-weight: normal;
                                    border: 1px solid var(--border-color);
                                `;
                                text = '⬜ ' + text;
                            }

                            html += `<span style="${style}">${text}</span>`;

                            if (index < describeOrder.length - 1) {
                                html += `<span style="color: #7f8c8d; font-size: 1.2em; margin: 0 4px;">→</span>`;
                            }
                        });

                        html += '</div>';
                        displayText = `🗣️ 描述中：${html}`;
                        displayClass = 'state-describing';
                        bgColor = 'rgba(52, 152, 219, 0.15)';
                    } else {
                        displayText = `🗣️ 描述阶段...`;
                        displayClass = 'state-describing';
                        bgColor = 'rgba(52, 152, 219, 0.15)';
                    }
                    break;

                case 'voting':
                    // 投票阶段：显示投票进度
                    const votedCount = votedGroups.length;
                    const totalCount = activeGroups.length || describeOrder.length;

                    displayText = `🗳️ 投票中 (${votedCount}/${totalCount})`;
                    displayClass = 'state-voting';

                    if (votedCount >= totalCount && totalCount > 0) {
                        bgColor = 'rgba(46, 204, 113, 0.2)';
                    } else if (votedCount >= Math.ceil(totalCount / 2)) {
                        bgColor = 'rgba(243, 156, 18, 0.2)';
                    } else {
                        bgColor = 'rgba(243, 156, 18, 0.15)';
                    }
                    break;

                case 'round_end':
                    const readyGroupsRound = data.ready_groups || [];
                    const activeGroupsRound = data.active_groups || [];
                    if (readyGroupsRound.length > 0 && activeGroupsRound.length > 0) {
                        displayText = `🏁 回合结束，等待准备 (${readyGroupsRound.length}/${activeGroupsRound.length})`;
                    } else {
                        if (latestResult) {
                            if (latestResult.eliminated && latestResult.eliminated.length > 0) {
                                displayText = `🏁 ${latestResult.eliminated.join(', ')} 被淘汰，游戏继续`;
                            } else {
                                displayText = '🏁 无人淘汰，游戏继续';
                            }
                        } else {
                            displayText = `🏁 第${currentRound}回合结束`;
                        }
                    }
                    displayClass = 'state-round-end';
                    bgColor = 'rgba(155, 89, 182, 0.1)';
                    break;

                case 'game_end':
                    let winnerText = '';
                    let winner = '';

                    if (latestResult) {
                        winner = latestResult.winner || '';
                    }

                    if (winner === 'undercover' || winner === '卧底') {
                        winnerText = '🎭 卧底胜利';
                        bgColor = 'rgba(231, 76, 60, 0.1)';
                        displayClass = 'state-game-end undercover-victory';
                    } else {
                        winnerText = '👥 平民胜利';
                        bgColor = 'rgba(46, 204, 113, 0.1)';
                        displayClass = 'state-game-end civilian-victory';
                    }
                    displayText = `🎊 游戏结束 - ${winnerText}`;
                    break;

                default:
                    displayText = `🔄 ${status}`;
                    displayClass = 'state-other';
                    bgColor = 'rgba(149, 165, 166, 0.1)';
            }

            // 更新显示内容
            displayElement.innerHTML = displayText;
            displayElement.className = 'game-state-display ' + displayClass;
            displayElement.style.background = bgColor;

            // 只在描述阶段更新当前发言者，其他阶段清除
            if (status === 'describing' && currentSpeaker) {
                document.getElementById('current-speaker-name').textContent = currentSpeaker;
                document.getElementById('current-speaker-name').style.color = 'var(--primary-color)';
            } else if (status !== 'describing') {
                // 非描述阶段，清除当前发言者显示（避免残留）
                document.getElementById('current-speaker-name').textContent = '--';
                document.getElementById('current-speaker-name').style.color = '';
            }
        }

        function updateTimers(data) {
            const mainTimer = document.getElementById('main-timer');
            const descTimer = document.getElementById('desc-timer-display');
            const voteTimer = document.getElementById('vote-timer-display');

            // 检查元素是否存在
            if (!descTimer || !voteTimer) {
                console.warn('倒计时元素未找到:', {descTimer, voteTimer});
                return;
            }

            // 清除所有警告样式
            if (mainTimer) {
                mainTimer.classList.remove('timer-warning');
                mainTimer.style.color = '';
            }

            // 主计时器
            if (data.status === 'describing') {
                if (data.speaker_remaining_seconds !== undefined && data.speaker_remaining_seconds >= 0) {
                    if (mainTimer) mainTimer.textContent = `${data.speaker_remaining_seconds}s`;

                    // 左侧倒计时显示
                    descTimer.textContent = `${data.speaker_remaining_seconds}s`;
                    voteTimer.textContent = '--:--';

                    // 最后10秒红色闪烁
                    if (data.speaker_remaining_seconds <= 10) {
                        if (mainTimer) {
                            mainTimer.classList.add('timer-warning');
                            mainTimer.style.color = 'var(--danger-color)';
                        }
                        descTimer.style.color = 'var(--danger-color)';
                    } else {
                        descTimer.style.color = '';
                    }
                } else if (data.remaining_seconds !== undefined && data.remaining_seconds >= 0) {
                    const timeStr = formatTime(data.remaining_seconds);

                    if (mainTimer) mainTimer.textContent = timeStr;
                    descTimer.textContent = timeStr;
                    voteTimer.textContent = '--:--';

                    if (data.remaining_seconds <= 10) {
                        if (mainTimer) {
                            mainTimer.classList.add('timer-warning');
                            mainTimer.style.color = 'var(--danger-color)';
                        }
                        descTimer.style.color = 'var(--danger-color)';
                    } else {
                        descTimer.style.color = '';
                    }
                } else {
                    // 没有倒计时数据时
                    if (mainTimer) mainTimer.textContent = '--:--';
                    descTimer.textContent = '--:--';
                    voteTimer.textContent = '--:--';
                    descTimer.style.color = '';
                    voteTimer.style.color = '';
                }
            } else if (data.status === 'voting') {
                if (data.remaining_seconds !== undefined && data.remaining_seconds >= 0) {
                    const timeStr = formatTime(data.remaining_seconds);

                    if (mainTimer) mainTimer.textContent = timeStr;
                    descTimer.textContent = '--:--';
                    voteTimer.textContent = timeStr;

                    if (data.remaining_seconds <= 10) {
                        if (mainTimer) {
                            mainTimer.classList.add('timer-warning');
                            mainTimer.style.color = 'var(--danger-color)';
                        }
                        voteTimer.style.color = 'var(--danger-color)';
                    } else {
                        voteTimer.style.color = '';
                    }
                } else {
                    if (mainTimer) mainTimer.textContent = '--:--';
                    descTimer.textContent = '--:--';
                    voteTimer.textContent = '--:--';
                    descTimer.style.color = '';
                    voteTimer.style.color = '';
                }
            } else {
                if (mainTimer) mainTimer.textContent = '--:--';
                descTimer.textContent = '--:--';
                voteTimer.textContent = '--:--';
                descTimer.style.color = '';
                voteTimer.style.color = '';
            }
        }

        function formatTime(seconds) {
            if (seconds === undefined || seconds < 0) return '--:--';
            const minutes = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
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

        // 标签页切换函数
        function switchTab(tabName) {
            // 切换导航按钮状态
            document.querySelectorAll('.tab-nav-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            // 切换内容面板
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
            document.getElementById('tab-' + tabName).classList.add('active');
        }

        function showAlert(type, message) {
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

        // 多轮游戏配置
        function openMultiRoundModal() {
            const modal = document.getElementById('multiRoundModal');
            modal.classList.add('show');
            // 初始化默认值
            document.getElementById('round-count').value = '1';
            generateRoundInputs();
        }

        function closeMultiRoundModal() {
            const modal = document.getElementById('multiRoundModal');
            modal.classList.remove('show');
        }

        // 点击模态框外部关闭
        window.onclick = function(event) {
            const modal = document.getElementById('multiRoundModal');
            if (event.target === modal) {
                closeMultiRoundModal();
            }
        }

        function generateRoundInputs() {
            const roundCount = parseInt(document.getElementById('round-count').value) || 1;
            const container = document.getElementById('rounds-container');
            
            // 限制轮数范围
            if (roundCount < 1) {
                document.getElementById('round-count').value = '1';
                return;
            }
            if (roundCount > 10) {
                document.getElementById('round-count').value = '10';
                return;
            }

            let html = '';
            for (let i = 1; i <= roundCount; i++) {
                html += `
                    <div class="round-item">
                        <div class="round-item-header">
                            <i class="fas fa-circle"></i>
                            第 ${i} 轮
                        </div>
                        <div class="round-item-inputs">
                            <div class="round-item-input">
                                <label for="undercover-word-round-${i}">
                                    <i class="fas fa-user-secret"></i> 卧底词
                                </label>
                                <input type="text" id="undercover-word-round-${i}" 
                                       placeholder="输入第${i}轮的卧底词" required>
                            </div>
                            <div class="round-item-input">
                                <label for="civilian-word-round-${i}">
                                    <i class="fas fa-users"></i> 平民词
                                </label>
                                <input type="text" id="civilian-word-round-${i}" 
                                       placeholder="输入第${i}轮的平民词" required>
                            </div>
                        </div>
                    </div>
                `;
            }
            container.innerHTML = html;
        }

        function submitMultiRoundGame() {
            const roundCount = parseInt(document.getElementById('round-count').value) || 1;
            
            // 收集所有轮次的词语（允许为空，后端会自动选词）
            const rounds = [];
            
            for (let i = 1; i <= roundCount; i++) {
                const undercoverWord = document.getElementById(`undercover-word-round-${i}`).value.trim();
                const civilianWord = document.getElementById(`civilian-word-round-${i}`).value.trim();
                
                rounds.push({
                    round: i,
                    undercover_word: undercoverWord,
                    civilian_word: civilianWord
                });
            }
            
            // 关闭模态框
            closeMultiRoundModal();
            
            // 显示提示
            showAlert('info', `已配置 ${roundCount} 轮游戏，准备开始第一轮...`);
            
            // 开始第一轮游戏
            const firstRound = rounds[0];
            startGameWithWords(firstRound.undercover_word, firstRound.civilian_word, rounds, true);
        }

        // 存储多轮配置
        let multiRoundConfig = null;
        let currentRoundIndex = 0; // 当前进行到第几轮（从0开始）
        let nextRoundCheckDone = false; // 防止重复触发下一轮检查

        function startGameWithWords(undercoverWord, civilianWord, roundsConfig = null, isFirstRound = false) {
            if (roundsConfig) {
                multiRoundConfig = roundsConfig;
                if (isFirstRound) {
                    currentRoundIndex = 0; // 只有第一轮才重置索引
                    // 只有第一轮才清空历史投票结果
                    allVoteResults = {};
                    gameRoundMapping = {};
                    descriptionRoundMapping = {};
                    voteRoundMapping = {};
                    nextRoundCheckDone = false; // 重置下一轮检查标志
                }
                // 保存多轮配置到 localStorage
                saveToLocalStorage();
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
                    nextRoundCheckDone = false; // 新游戏开始，重置检查标志
                    // 显示自动选择的词语
                    if (resp.data && resp.data.civilian_word && resp.data.undercover_word) {
                        document.getElementById('civilian-word').value = resp.data.civilian_word;
                        document.getElementById('undercover-word').value = resp.data.undercover_word;
                    }
                    fetchGameState();
                } else {
                    showAlert('danger', '错误：' + (resp ? resp.message : '后端无响应'));
                }
            })
            .catch(error => {
                showAlert('danger', '请求失败：' + error);
            });
        }

        // 检查并开始下一轮游戏
        function checkAndStartNextRound() {
            // 防止重复触发
            if (nextRoundCheckDone) {
                return;
            }
            
            if (!multiRoundConfig || multiRoundConfig.length === 0) {
                return; // 没有多轮配置
            }

            // 标记为已检查，防止重复
            nextRoundCheckDone = true;

            // 检查是否还有下一轮
            const nextRoundIndex = currentRoundIndex + 1;
            if (nextRoundIndex >= multiRoundConfig.length) {
                // 所有轮次都已完成
                showAlert('info', `所有 ${multiRoundConfig.length} 轮游戏已完成！`);
                multiRoundConfig = null; // 清空配置
                currentRoundIndex = 0;
                return;
            }

            // 延迟3秒后自动开始下一轮，给用户时间查看结果
            setTimeout(() => {
                const nextRound = multiRoundConfig[nextRoundIndex];
                currentRoundIndex = nextRoundIndex;
                
                // 保存到 localStorage
                saveToLocalStorage();
                
                showAlert('info', `准备开始第 ${nextRoundIndex + 1} 轮游戏...`);
                
                // 开始下一轮游戏（允许自动选词，不清空历史数据）
                startGameWithWords(
                    nextRound.undercover_word, 
                    nextRound.civilian_word,
                    multiRoundConfig, // 保持多轮配置
                    false // 不是第一轮
                );
            }, 3000);
        }

        // 开始单轮游戏（从输入框获取词语）
        function startSingleGame() {
            const undercoverWord = document.getElementById('undercover-word').value.trim();
            const civilianWord = document.getElementById('civilian-word').value.trim();
            
            // 允许词语为空，后端会自动从词库选择
            // if (!undercoverWord || !civilianWord) {
            //     showAlert('danger', '请输入卧底词和平民词');
            //     return;
            // }
            
            // 清空多轮配置（单轮游戏不需要多轮配置）
            multiRoundConfig = null;
            currentRoundIndex = 0;
            nextRoundCheckDone = false;
            
            // 开始单轮游戏，不传多轮配置
            startGameWithWords(undercoverWord, civilianWord, null, false);
        }

        // 游戏控制函数（保持向后兼容，但不再使用）
        function startGame() {
            // 这个方法保留用于向后兼容，但实际应该使用 openMultiRoundModal()
            openMultiRoundModal();
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

        function resetGame() {
            if (confirm('确定要重置游戏吗？')) {
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
                        gameRoundMapping = {};
                        descriptionRoundMapping = {};
                        voteRoundMapping = {};
                        // 清空多轮配置
                        multiRoundConfig = null;
                        currentRoundIndex = 0;
                        nextRoundCheckDone = false;
                        // 清除 localStorage
                        clearLocalStorage();
                        // 立即更新投票记录和游戏结果的显示
                        updateVoteRecords();
                        updateGameResults();
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
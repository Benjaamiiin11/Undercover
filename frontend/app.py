"""
前端界面模块 - Flask应用主文件
"""
from flask import Flask, render_template, jsonify, request
from .utils import BACKEND_URL, ADMIN_HEADERS
import requests

# 前端服务器
frontend_app = Flask(__name__, 
                     template_folder='templates',
                     static_folder='static')


@frontend_app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@frontend_app.route('/api/game/state')
def api_game_state():
    """代理后端API"""
    from .utils import get_backend_data
    data = get_backend_data('/api/game/state', use_admin=True)
    if data is None:
        return jsonify({"code": 500, "message": "后端状态接口无响应", "data": {}}), 500
    return jsonify(data)


@frontend_app.route('/api/public/status')
def api_public_status():
    """代理后端公开状态API"""
    from .utils import get_backend_data
    data = get_backend_data('/api/status', use_admin=False)
    if data is None:
        return jsonify({"code": 500, "message": "后端状态接口无响应", "data": {}}), 500
    return jsonify(data)


@frontend_app.route('/api/game/start', methods=['POST'])
def api_start_game():
    """代理后端API"""
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


@frontend_app.route('/api/game/clear_all', methods=['POST'])
def api_clear_all():
    """代理后端API"""
    response = requests.post(
        f"{BACKEND_URL}/api/game/clear_all",
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


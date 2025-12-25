# 后端模块说明

后端代码已重构为模块化结构，便于维护和协作开发。

## 目录结构

```
backend/
├── __init__.py          # 模块初始化，导出主要对象
├── app.py               # Flask应用主入口
├── config.py            # 配置（词库、令牌等）
├── utils.py             # 工具函数（认证、响应格式化、IP获取等）
├── routes/
│   ├── __init__.py      # 路由注册
│   ├── game.py          # 游戏控制路由（主持方专用）
│   ├── player.py        # 玩家相关路由（注册、描述、投票等）
│   └── public.py        # 公开API路由（状态查询、结果等）
├── websocket/
│   ├── __init__.py      # WebSocket模块初始化
│   └── handlers.py      # WebSocket事件处理
└── services/
    ├── __init__.py      # 服务模块初始化
    ├── broadcast.py     # 广播服务（状态、游戏状态、描述等）
    └── timer.py         # 倒计时服务
```

## 运行方式

### 方式1：使用新的入口文件（推荐）

```bash
python run_backend.py
```

### 方式2：直接运行app.py

```bash
cd backend
python app.py
```

### 方式3：作为模块导入

```python
from backend.app import app, socketio
socketio.run(app, host='0.0.0.0', port=5000, debug=True)
```

## 模块说明

### config.py
- 管理员令牌配置
- 词库加载函数

### utils.py
- `get_local_ip()`: 获取本机IP地址
- `require_admin()`: 校验主持方权限
- `make_response()`: 统一响应格式
- `get_websocket_status()`: 获取WebSocket连接状态

### routes/
- **game.py**: 游戏控制路由（start, reset, clear_all, round/start, voting/process, state）
- **player.py**: 玩家操作路由（register, describe, vote, ready）
- **public.py**: 公开查询路由（status, result, word, descriptions, groups, scores）

### websocket/
- **handlers.py**: 所有WebSocket事件处理（connect, disconnect, register_socket, request_status, request_timer）

### services/
- **broadcast.py**: 广播服务（status, game_state, descriptions, groups, scores）
- **timer.py**: 倒计时广播线程管理

## 优势

1. **职责清晰**: 路由、WebSocket、服务分离，便于维护
2. **易于协作**: 多人可同时修改不同模块，减少冲突
3. **易于测试**: 各模块可独立测试
4. **可扩展**: 新增功能时结构清晰，易于扩展

## 注意事项

- 旧的 `backend.py` 文件已保留，但建议使用新的模块化结构
- 确保所有模块在 `app.py` 中正确初始化
- 访问地址：http://127.0.0.1:5000


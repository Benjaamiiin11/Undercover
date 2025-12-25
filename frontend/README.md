# 前端模块说明

前端代码已重构为模块化结构，便于维护和协作开发。

## 目录结构

```
frontend/
├── __init__.py          # 模块初始化文件
├── app.py               # Flask应用主文件（路由和API代理）
├── utils.py             # 工具函数（后端API调用）
├── templates/
│   └── index.html       # HTML模板
└── static/
    ├── css/
    │   └── style.css    # 所有CSS样式
    └── js/
        └── main.js      # JavaScript代码（包含所有功能）
```

## 运行方式

### 方式1：使用新的入口文件（推荐）

```bash
python run_frontend.py
```

### 方式2：直接运行app.py

```bash
cd frontend
python app.py
```

### 方式3：作为模块导入

```python
from frontend.app import frontend_app
frontend_app.run(host='0.0.0.0', port=5001, debug=True)
```

## 文件说明

- **app.py**: Flask应用，包含所有路由和API代理
- **utils.py**: 工具函数，用于与后端API通信
- **templates/index.html**: HTML模板，使用Jinja2模板引擎
- **static/css/style.css**: 所有CSS样式代码
- **static/js/main.js**: 所有JavaScript代码（WebSocket、UI更新、游戏控制等）

## 优势

1. **职责清晰**: HTML、CSS、JS分离，便于维护
2. **易于协作**: 多人可同时修改不同文件，减少冲突
3. **可复用**: CSS和JS可被其他页面复用
4. **性能更好**: 浏览器可缓存静态资源

## 注意事项

- 旧的 `frontend.py` 文件已保留，但建议使用新的模块化结构
- 确保后端服务器（backend.py）已启动
- 访问地址：http://127.0.0.1:5001


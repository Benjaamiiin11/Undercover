"""
倒计时服务模块
"""
import time
from datetime import datetime
from threading import Thread
from backend.utils import get_websocket_status

# 这些变量需要在运行时注入
game = None
game_lock = None
socketio = None

# 倒计时推送线程
timer_thread = None
timer_running = False


def init_timer(game_instance, lock, socketio_instance):
    """初始化倒计时服务"""
    global game, game_lock, socketio
    game = game_instance
    game_lock = lock
    socketio = socketio_instance


def timer_broadcast_loop():
    """定期广播倒计时"""
    global timer_running
    while timer_running:
        try:
            with game_lock:
                websocket_status = get_websocket_status()
                status = game.get_public_status()
                # 更新在线状态（使用WebSocket连接状态）
                status['online_status'] = game.get_online_status(websocket_status)
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


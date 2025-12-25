"""
倒计时服务模块
"""
import time
from datetime import datetime
from threading import Thread
from backend.utils import get_websocket_status
from backend.services import broadcast_status, broadcast_game_state, broadcast_descriptions, broadcast_groups, broadcast_scores

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
    """定期广播倒计时并检查超时"""
    global timer_running
    while timer_running:
        try:
            with game_lock:
                websocket_status = get_websocket_status()
                status = game.get_public_status()
                # 更新在线状态（使用WebSocket连接状态）
                status['online_status'] = game.get_online_status(websocket_status)
                
                now = datetime.now()
                need_broadcast = False
                
                # 描述阶段：检查发言者是否超时
                if status.get('status') == 'describing':
                    if game.speaker_deadline and now > game.speaker_deadline:
                        # 当前发言者超时，自动跳过
                        if game.skip_current_speaker():
                            print(f"发言者超时，已自动跳过")
                            need_broadcast = True
                            # 广播状态和描述列表更新
                            socketio.start_background_task(broadcast_status)
                            socketio.start_background_task(broadcast_game_state)
                            socketio.start_background_task(broadcast_descriptions)
                    
                    # 添加精确的时间信息
                    if game.phase_deadline:
                        remaining = max(0, int((game.phase_deadline - now).total_seconds()))
                        status['remaining_seconds'] = remaining

                    if game.speaker_deadline:
                        speaker_remaining = max(0, int((game.speaker_deadline - now).total_seconds()))
                        status['speaker_remaining_seconds'] = speaker_remaining
                    
                    if not need_broadcast:
                        socketio.emit('timer_update', status)
                
                # 投票阶段：检查是否有未投票的组超时
                elif status.get('status') == 'voting':
                    if game.phase_deadline:
                        remaining = max(0, int((game.phase_deadline - now).total_seconds()))
                        status['remaining_seconds'] = remaining
                        
                        # 检查每个未投票的组是否超过60秒
                        active_groups = [g for g in game.describe_order if g not in game.eliminated_groups]
                        round_votes = game.votes.get(game.current_round, {})
                        for group_name in active_groups:
                            if group_name not in round_votes and group_name in game.vote_start_times:
                                # 该组还未投票，检查是否超过60秒
                                vote_start_time = game.vote_start_times[group_name]
                                elapsed = (now - vote_start_time).total_seconds()
                                if elapsed >= 60:  # 超过60秒未投票，自动跳过
                                    if game.skip_vote_for_group(group_name):
                                        print(f"组 {group_name} 投票超时（{int(elapsed)}秒），已自动跳过")
                                        need_broadcast = True
                        
                        # 重新获取投票数据（因为可能已经跳过了一些投票）
                        round_votes = game.votes.get(game.current_round, {})
                        
                        # 检查是否所有人都投票了（包括超时跳过的）
                        # 同时检查游戏状态是否还是 VOTING（避免重复处理）
                        if len(round_votes) >= len(active_groups) and game.game_status.value == 'voting':
                            # 所有人已投票，自动处理投票结果
                            vote_result = game.process_voting_result()
                            if 'error' not in vote_result:
                                print("所有人已投票，自动处理投票结果")
                                need_broadcast = True
                                # 停止倒计时广播
                                stop_timer_broadcast()
                                # 广播状态变化
                                socketio.start_background_task(broadcast_status)
                                socketio.start_background_task(broadcast_game_state)
                                # 广播投票结果
                                socketio.emit('vote_result', vote_result)
                                # 广播分数更新
                                socketio.start_background_task(broadcast_scores)
                                
                                # 如果游戏未结束且处于 ROUND_END 状态，自动开始下一回合
                                if not vote_result.get('game_ended') and game.game_status.value == 'round_end':
                                    order = game.start_round()
                                    if order:
                                        # 启动倒计时广播
                                        start_timer_broadcast()
                                        # 广播状态变化
                                        socketio.start_background_task(broadcast_status)
                                        socketio.start_background_task(broadcast_game_state)
                                        # 广播描述列表更新
                                        socketio.start_background_task(broadcast_descriptions)
                        
                        elif remaining <= 0:
                            # 投票阶段总时间到了，自动跳过所有未投票的组
                            for group_name in active_groups:
                                if group_name not in round_votes:
                                    if game.skip_vote_for_group(group_name):
                                        print(f"投票阶段时间到，组 {group_name} 已自动跳过")
                                        need_broadcast = True
                            
                            # 跳过所有未投票的组后，再次检查是否所有人都投票了
                            round_votes = game.votes.get(game.current_round, {})
                            # 同时检查游戏状态是否还是 VOTING（避免重复处理）
                            if len(round_votes) >= len(active_groups) and game.game_status.value == 'voting':
                                vote_result = game.process_voting_result()
                                if 'error' not in vote_result:
                                    print("投票阶段时间到，所有人已投票，自动处理投票结果")
                                    need_broadcast = True
                                    # 停止倒计时广播
                                    stop_timer_broadcast()
                                    # 广播状态变化
                                    socketio.start_background_task(broadcast_status)
                                    socketio.start_background_task(broadcast_game_state)
                                    # 广播投票结果
                                    socketio.emit('vote_result', vote_result)
                                    # 广播分数更新
                                    socketio.start_background_task(broadcast_scores)
                                    
                                    # 如果游戏未结束且处于 ROUND_END 状态，自动开始下一回合
                                    if not vote_result.get('game_ended') and game.game_status.value == 'round_end':
                                        order = game.start_round()
                                        if order:
                                            # 启动倒计时广播
                                            start_timer_broadcast()
                                            # 广播状态变化
                                            socketio.start_background_task(broadcast_status)
                                            socketio.start_background_task(broadcast_game_state)
                                            # 广播描述列表更新
                                            socketio.start_background_task(broadcast_descriptions)
                        
                        if need_broadcast and not (len(round_votes) >= len(active_groups)):
                            # 广播状态更新（但不要重复广播，如果已经处理了投票结果）
                            socketio.start_background_task(broadcast_status)
                            socketio.start_background_task(broadcast_game_state)
                    
                    if not need_broadcast:
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


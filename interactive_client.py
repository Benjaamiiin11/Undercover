"""
交互式游戏方客户端
可以看到其他人的描述、倒计时，手动输入描述和投票
"""
import requests
import time
import os
import sys
import socketio
import threading
from urllib.parse import urlparse

# 配置服务器地址
BASE_URL = "http://192.168.241.90:5000"


class InteractiveClient:
    def __init__(self, group_name: str):
        self.group_name = group_name
        self.word = None
        self.last_descriptions = []
        self.is_registered = False
        self.last_word = None
        self.is_eliminated = False  # 记录是否被淘汰
        self.total_score = 0  # 记录总得分
        self.reconnect_count = 0
        self.max_reconnect = 100  # 增大重连次数
        
        # WebSocket 相关
        self.sio = None
        self.socket_thread = None
        self.websocket_connected = False
        self.websocket_registered = False
        self._setup_websocket()

    def _setup_websocket(self):
        """设置 WebSocket 连接"""
        # 解析 BASE_URL 获取 WebSocket 地址
        parsed = urlparse(BASE_URL)
        ws_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # 创建 SocketIO 客户端
        self.sio = socketio.Client()
        
        # 注册事件处理器
        @self.sio.on('connect')
        def on_connect():
            """连接成功时注册 socket"""
            print(f"✓ WebSocket 已连接")
            self.websocket_connected = True
            # 发送注册事件
            try:
                self.sio.emit('register_socket', {'group_name': self.group_name})
                self.websocket_registered = True
                print(f"✓ WebSocket 已注册: {self.group_name}")
            except Exception as e:
                print(f"✗ WebSocket 注册失败: {e}")
                self.websocket_registered = False
        
        @self.sio.on('disconnect')
        def on_disconnect():
            """断开连接时的处理"""
            print(f"✗ WebSocket 已断开")
            self.websocket_connected = False
            self.websocket_registered = False
        
        @self.sio.on('socket_registered')
        def on_socket_registered(data):
            """收到注册成功确认"""
            if data.get('status') == 'success':
                self.websocket_registered = True
                print(f"✓ WebSocket 注册确认: {data.get('group_name')}")
        
        @self.sio.on('status_update')
        def on_status_update(data):
            """接收状态更新推送（可选，当前仍主要使用 HTTP 轮询）"""
            pass
        
        @self.sio.on('game_state_update')
        def on_game_state_update(data):
            """接收游戏状态更新推送（可选）"""
            pass
        
        @self.sio.on('vote_result')
        def on_vote_result(data):
            """接收投票结果推送"""
            pass
        
        @self.sio.on('connect_error')
        def on_connect_error(data):
            """连接错误"""
            print(f"✗ WebSocket 连接错误: {data}")
            self.websocket_connected = False
            self.websocket_registered = False
    
    def connect_websocket(self):
        """连接到 WebSocket 服务器"""
        if self.websocket_connected:
            return True
        
        try:
            parsed = urlparse(BASE_URL)
            ws_url = f"{parsed.scheme}://{parsed.netloc}"
            self.sio.connect(ws_url, wait_timeout=5)
            # 等待连接建立
            time.sleep(0.5)
            return self.websocket_connected
        except Exception as e:
            print(f"✗ WebSocket 连接失败: {e}")
            return False
    
    def disconnect_websocket(self):
        """断开 WebSocket 连接"""
        if self.sio and self.websocket_connected:
            try:
                self.sio.disconnect()
            except:
                pass
            self.websocket_connected = False
            self.websocket_registered = False
    
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self, title: str):
        """打印标题"""
        print("\n" + "=" * 50)
        print(f"  {title}")
        print("=" * 50)

    def get_status(self, retry=3):
        """获取游戏状态，增加重试机制"""
        for attempt in range(retry):
            try:
                r = requests.get(f"{BASE_URL}/api/status",
                                 params={"group_name": self.group_name},
                                 timeout=5)
                if r.status_code == 200:
                    data = r.json().get('data', {})
                    # 更新淘汰状态
                    if 'is_eliminated' in data:
                        self.is_eliminated = data['is_eliminated']
                    return data
            except:
                if attempt < retry - 1:
                    print(f"连接失败，第{attempt + 1}次重试...")
                    time.sleep(1)
        return {}

    def get_vote_details(self):
        """获取详细的投票信息"""
        try:
            r = requests.get(f"{BASE_URL}/api/vote/details",
                             params={"group_name": self.group_name},
                             timeout=5)
            if r.status_code == 200:
                return r.json().get('data', {})
        except:
            pass
        return {}

    def get_descriptions(self):
        """获取当前回合的描述"""
        try:
            r = requests.get(f"{BASE_URL}/api/descriptions", timeout=3)
            if r.status_code == 200:
                return r.json().get('data', {})
        except:
            pass
        return {}

    def register(self) -> bool:
        """注册，如果已经注册则跳过"""
        try:
            # 先检查是否已经注册
            if self.is_registered:
                print(f"✓ 组 {self.group_name} 已注册，跳过注册")
                return True

            # 从服务器获取已注册的组列表
            r = requests.get(f"{BASE_URL}/api/groups", timeout=5)
            if r.status_code == 200:
                result = r.json()
                if result.get('code') == 200:
                    groups = result.get('data', {}).get('groups', [])
                    for group in groups:
                        if group.get('name') == self.group_name:
                            print(f"✓ 组 {self.group_name} 已经在服务器注册")
                            self.is_registered = True
                            return True

            # 未注册则进行注册
            print(f"正在注册组: {self.group_name}...")
            r = requests.post(f"{BASE_URL}/api/register",
                              json={"group_name": self.group_name}, timeout=5)
            result = r.json()
            if result.get('code') == 200:
                print(f"✓ 注册成功！")
                self.is_registered = True
                return True
            else:
                print(f"✗ 注册失败: {result.get('message')}")
                return False
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            return False

    def get_word(self):
        """获取词语"""
        try:
            r = requests.get(f"{BASE_URL}/api/word",
                             params={"group_name": self.group_name}, timeout=5)
            result = r.json()
            if result.get('code') == 200:
                self.word = result['data'].get('word')
                if self.word and self.word != self.last_word:
                    print(f"🎯 获取到词语: 【{self.word}】")
                    self.last_word = self.word
                return self.word
        except:
            pass
        return None

    def submit_description(self, desc: str) -> tuple:
        """提交描述"""
        # 检查是否被淘汰
        if self.is_eliminated:
            return False, "你已被淘汰，不能发言"

        try:
            r = requests.post(f"{BASE_URL}/api/describe",
                              json={"group_name": self.group_name, "description": desc}, timeout=5)
            result = r.json()
            return result.get('code') == 200 and '成功' in result.get('message', ''), result.get('message', '')
        except Exception as e:
            return False, str(e)

    def submit_vote(self, target: str) -> tuple:
        """提交投票"""
        # 检查是否被淘汰
        if self.is_eliminated:
            return False, "你已被淘汰，不能投票"

        try:
            r = requests.post(f"{BASE_URL}/api/vote",
                              json={"voter_group": self.group_name, "target_group": target}, timeout=5)
            result = r.json()
            return result.get('code') == 200, result.get('message', '')
        except Exception as e:
            return False, str(e)

    def submit_ready(self) -> tuple:
        """提交准备就绪"""
        # 检查是否被淘汰
        if self.is_eliminated:
            return False, False, "你已被淘汰，不能准备"

        try:
            r = requests.post(f"{BASE_URL}/api/ready",
                              json={"group_name": self.group_name}, timeout=5)
            result = r.json()
            success = result.get('code') == 200
            auto_started = result.get('data', {}).get('auto_started', False) if success else False
            return success, auto_started, result.get('message', '')
        except Exception as e:
            return False, False, str(e)

    def display_status(self, status: dict):
        """显示当前状态"""
        self.clear_screen()

        print(f"╔{'═' * 48}╗")
        print(f"║  🎮 谁是卧底 - 游戏方终端  [{self.group_name}]".ljust(49) + "║")
        if self.is_registered:
            print(f"║  ✅ 已注册".ljust(49) + "║")
        if self.is_eliminated:
            print(f"║  💀 已淘汰（可观看游戏）".ljust(49) + "║")
        print(f"╠{'═' * 48}╣")

        # 我的词语（如果未被淘汰且有词语）
        if self.word and not self.is_eliminated:
            print(f"║  📝 我的词语: {self.word}".ljust(49) + "║")

        # 显示得分
        scores = status.get('scores', {})
        if self.group_name in scores:
            self.total_score = scores[self.group_name]
            print(f"║  🏆 累计得分: {self.total_score}".ljust(49) + "║")

        # 游戏状态
        status_map = {
            'waiting': '⏳ 等待注册',
            'registered': '✅ 已注册，等待开始',
            'word_assigned': '📋 词语已分配，等待开始回合',
            'describing': '🎤 描述阶段',
            'voting': '🗳️ 投票阶段',
            'round_end': '🔄 回合结束',
            'game_end': '🏁 游戏结束'
        }
        game_status = status.get('status', 'waiting')
        phase_info = status.get('phase_info', '')

        # 添加状态指示
        if game_status == 'describing':
            print(f"║  状态: 🎤 描述中".ljust(49) + "║")
        elif game_status == 'voting':
            print(f"║  状态: 🗳️ 投票中".ljust(49) + "║")
        else:
            print(f"║  状态: {status_map.get(game_status, game_status)}".ljust(49) + "║")

        # 检查是否有新游戏开始
        if status.get('new_game_started'):
            print(f"║  🆕 新游戏已开始，等待发言顺序".ljust(49) + "║")
            # 重置淘汰状态（新游戏开始）
            if self.is_eliminated:
                self.is_eliminated = False
                print(f"║  🔄 淘汰状态已重置".ljust(49) + "║")

        # 倒计时（只对未淘汰的组显示）
        if not self.is_eliminated:
            if game_status == 'describing':
                speaker_time = status.get('speaker_remaining_seconds')
                if speaker_time is not None:
                    print(f"║  ⏱️ 当前发言者剩余: {speaker_time} 秒".ljust(49) + "║")

            remaining = status.get('remaining_seconds')
            if remaining is not None:
                print(f"║  ⏱️ 阶段剩余时间: {remaining} 秒".ljust(49) + "║")

        print(f"╠{'═' * 48}╣")

        # 发言顺序
        if game_status in ['describing', 'voting']:
            order = status.get('describe_order', [])
            current = status.get('current_speaker', '')
            current_idx = status.get('current_speaker_index', 0)

            print(f"║  📋 发言顺序:".ljust(50) + "║")
            for i, name in enumerate(order):
                if name in status.get('eliminated_groups', []):
                    marker = "❌"
                elif game_status == 'describing' and i < current_idx:
                    marker = "✅"
                elif name == current and game_status == 'describing':
                    marker = "👉"
                else:
                    marker = "⬜"

                me_marker = " (我)" if name == self.group_name else ""
                eliminated_marker = " 💀" if name in status.get('eliminated_groups', []) else ""
                print(f"║     {marker} {name}{me_marker}{eliminated_marker}".ljust(50) + "║")

        # 显示当前回合的描述
        descriptions = status.get('descriptions', [])
        if descriptions:
            print(f"╠{'═' * 48}╣")
            print(f"║  💬 本回合描述:".ljust(50) + "║")
            for desc in descriptions:
                group = desc.get('group', '???')
                text = desc.get('description', '')
                # 截断过长的描述
                if len(text) > 30:
                    text = text[:27] + "..."
                me_marker = " ←我" if group == self.group_name else ""
                eliminated_marker = " 💀" if group in status.get('eliminated_groups', []) else ""
                print(f"║    [{group}]{me_marker}{eliminated_marker}: {text}".ljust(50) + "║")

        # 淘汰的组
        eliminated = status.get('eliminated_groups', [])
        if eliminated:
            print(f"╠{'═' * 48}╣")
            print(f"║  💀 已淘汰: {', '.join(eliminated)}".ljust(49) + "║")

        # 活跃组数
        active = status.get('active_groups', [])
        if active:
            print(f"║  🟢 活跃组: {len(active)}组".ljust(49) + "║")

        # 显示投票结果
        last_result = status.get('last_vote_result', {})
        if last_result and last_result.get('message'):
            print(f"╠{'═' * 48}╣")
            print(f"║  📊 上轮投票结果:".ljust(50) + "║")
            # 只显示消息的第一行
            message_lines = last_result.get('message', '').split('\n')
            if message_lines:
                print(f"║    {message_lines[0]}".ljust(50) + "║")

        print(f"╚{'═' * 48}╝")

    def show_vote_details(self, vote_details: dict):
        """显示详细的投票信息"""
        if not vote_details:
            return

        print(f"\n{'=' * 60}")
        print("📊 详细投票信息")
        print("=" * 60)

        # 显示我投给了谁
        my_vote = vote_details.get('my_vote')
        if my_vote:
            print(f"我投给了: {my_vote}")

        # 显示谁投了我
        voted_by = vote_details.get('voted_by', [])
        if voted_by:
            print(f"投我的组: {', '.join(voted_by)} ({len(voted_by)}票)")
        else:
            print("没有组投我")

        # 显示淘汰信息
        eliminated = vote_details.get('eliminated', [])
        if eliminated:
            if self.group_name in eliminated:
                print(f"😢 我被淘汰了")
                self.is_eliminated = True
            else:
                print(f"淘汰的组: {', '.join(eliminated)}")

        # 显示游戏结果
        if vote_details.get('game_ended'):
            winner = vote_details.get('winner')
            if winner == 'undercover':
                print("🎭 卧底胜利！")
            else:
                print("👥 平民胜利！")

        # 显示消息
        message = vote_details.get('message', '')
        if message:
            print(f"\n📝 结果说明:")
            for line in message.split('\n'):
                if line:
                    print(f"  {line}")

        print("=" * 60)

    def wait_for_game_start(self):
        """等待游戏开始"""
        print(f"\n等待游戏开始...")

        while True:
            status = self.get_status()
            game_status = status.get('status')

            # 检查是否有新游戏开始
            if status.get('new_game_started'):
                print("🆕 新游戏开始！")
                # 获取词语（如果未被淘汰）
                if not self.is_eliminated:
                    self.word = self.get_word()
                return True

            if game_status in ['word_assigned', 'describing', 'voting', 'round_end']:
                print("游戏开始！")
                # 获取词语（如果未被淘汰）
                if not self.is_eliminated:
                    self.word = self.get_word()
                return True

            if game_status == 'game_end':
                print("游戏已结束，等待新游戏...")
                time.sleep(2)
                continue

            # 显示等待状态
            print(f"当前状态: {game_status}")
            time.sleep(2)

    def wait_for_my_turn(self):
        """等待轮到自己发言，同时显示状态"""
        while True:
            status = self.get_status()
            self.display_status(status)

            if status.get('status') != 'describing':
                return status.get('status')

            # 如果被淘汰，只观看不发言
            if self.is_eliminated:
                print(f"\n你已被淘汰，观看游戏中...")
                print(f"当前发言者: {status.get('current_speaker')}")
                time.sleep(2)
                continue

            if status.get('current_speaker') == self.group_name:
                return 'my_turn'

            print(f"\n等待 {status.get('current_speaker')} 发言中...")
            time.sleep(2)

    def voting_phase(self, status: dict):
        """投票阶段处理"""
        self.display_status(status)

        # 如果被淘汰，只观看不投票
        if self.is_eliminated:
            print(f"\n你已被淘汰，观看投票阶段...")
            voted_groups = status.get('voted_groups', [])
            active_groups = status.get('active_groups', [])
            print(f"已投票: {len(voted_groups)}/{len(active_groups)}组")

            # 等待投票结束
            print("等待投票结束...")
            while True:
                s = self.get_status()
                if s.get('status') != 'voting':
                    break
                time.sleep(2)
            return False

        # 获取可投票的组
        active = status.get('active_groups', [])

        # 先检查自己是否在活跃组中
        if self.group_name not in active:
            print(f"⚠️  自己不在活跃组列表中，可能被淘汰或状态错误")
            return False

        # 从活跃组中排除自己
        others = [g for g in active if g != self.group_name]

        print(f"- 可投票的组: {others}")
        print(f"- 可投票组数: {len(others)}")

        if not others:
            print("\n⚠️  没有其他组可以投票，等待中...")
            return False

        print(f"\n🗳️ 投票阶段！剩余 {status.get('remaining_seconds', 120)} 秒")
        print("可投票的组:")
        for i, g in enumerate(others, 1):
            print(f"  {i}. {g}")

        # 循环直到输入有效的投票
        while True:
            try:
                # 检查游戏状态是否改变（例如游戏被重置）
                current_status = self.get_status()
                game_status = current_status.get('status')
                if game_status not in ['voting', 'round_end', 'game_end']:
                    # 游戏状态已改变（可能是被重置）
                    print(f"\n⚠️  游戏状态已改变: {game_status}")
                    return False

                # 显示投票提示
                choice = input(f"\n请输入要投票的组名或序号 (输入 'skip' 跳过): ").strip()

                if choice.lower() == 'skip':
                    print("跳过投票")
                    return False

                # 支持输入序号
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(others):
                        choice = others[idx]
                    else:
                        print(f"序号无效，请输入 1-{len(others)} 之间的数字")
                        continue

                if choice in others:
                    success, msg = self.submit_vote(choice)
                    if success:
                        print(f"✓ {msg}: {self.group_name} → {choice}")
                        return True
                    else:
                        # 检查是否因为游戏状态改变导致投票失败
                        current_status = self.get_status()
                        game_status = current_status.get('status')
                        if game_status not in ['voting', 'round_end', 'game_end']:
                            print(f"\n⚠️  游戏状态已改变: {game_status}")
                            return False
                        print(f"✗ 投票失败: {msg}")
                        # 重新显示可投票的组
                        print("请重新选择，可投票的组:")
                        for i, g in enumerate(others, 1):
                            print(f"  {i}. {g}")
                        continue
                else:
                    print(f"✗ 组名无效: {choice}")
                    print("请从以下组中选择:")
                    for i, g in enumerate(others, 1):
                        print(f"  {i}. {g}")
                    continue

            except KeyboardInterrupt:
                print("\n\n投票被取消")
                return False
            except Exception as e:
                print(f"\n投票出错: {e}")
                return False

    def handle_game_reset(self):
        """处理游戏重置的情况"""
        print(f"\n{'=' * 60}")
        print("⚠️  游戏被重置或重新开始")
        print("=" * 60)

        # 保持注册状态，等待游戏重新开始
        print(f"保持已注册状态: {self.group_name}")
        print(f"累计得分: {self.total_score}")
        print("等待主持方重新开始游戏...")
        
        # 确保 WebSocket 连接正常
        if not self.websocket_connected:
            self.connect_websocket()

        # 重置淘汰状态（新游戏开始）
        self.is_eliminated = False

        # 等待游戏重新开始
        return self.wait_for_game_start()

    def run(self):
        """运行客户端"""
        self.print_header(f"谁是卧底 - 游戏方客户端")
        print(f"服务器: {BASE_URL}")
        print(f"组名: {self.group_name}")

        # 连接 WebSocket
        print(f"\n正在连接 WebSocket...")
        self.connect_websocket()

        # 注册
        if not self.register():
            print("注册失败，请检查服务器连接")
            return True

        # 等待游戏开始
        if not self.wait_for_game_start():
            print("等待游戏开始失败")
            return True

        # 游戏主循环
        while True:
            status = self.get_status()
            game_status = status.get('status')

            # 检查游戏是否被重置
            if game_status == 'waiting' or game_status == 'registered':
                if not self.handle_game_reset():
                    return True
                continue

            if game_status == 'game_end':
                self.display_status(status)
                print("\n🏁 游戏结束！")

                # 获取详细的投票信息
                vote_details = self.get_vote_details()
                if vote_details:
                    self.show_vote_details(vote_details)

                # 显示得分
                scores = status.get('scores', {})
                if self.group_name in scores:
                    print(f"\n🎯 你的累计得分: {scores[self.group_name]}")
                    self.total_score = scores[self.group_name]

                print("\n游戏结束，等待下一轮游戏...")
                time.sleep(3)
                # 继续等待新游戏
                self.wait_for_game_start()
                continue

            elif game_status == 'describing':
                # 等待轮到自己
                result = self.wait_for_my_turn()

                if result == 'my_turn':
                    status = self.get_status()
                    self.display_status(status)

                    speaker_time = status.get('speaker_remaining_seconds', 30)
                    print(f"\n👉 轮到你发言了！剩余 {speaker_time} 秒")
                    print(f"你的词语是: 【{self.word}】")

                    desc = input("请输入你的描述: ").strip()
                    if not desc:
                        desc = "我选择沉默"

                    success, msg = self.submit_description(desc)
                    if success:
                        print(f"✓ 描述提交成功!")
                    else:
                        print(f"✗ 提交失败: {msg}")

                    time.sleep(1)

                elif result == 'voting':
                    continue
                else:
                    time.sleep(1)

            elif game_status == 'voting':
                # 投票阶段
                self.voting_phase(status)

                # 等待投票阶段结束
                print("\n等待其他人投票...")
                while True:
                    s = self.get_status()
                    if s.get('status') != 'voting':
                        # 显示投票结果
                        if s.get('status') in ['round_end', 'game_end']:
                            vote_details = self.get_vote_details()
                            if vote_details:
                                self.show_vote_details(vote_details)
                        break
                    time.sleep(2)

            elif game_status == 'round_end':
                self.display_status(status)
                print("\n该轮游戏结束，准备开始下一轮...")
                
                # 如果未被淘汰，等待用户手动确认准备
                if not self.is_eliminated:
                    ready_groups = status.get('ready_groups', [])
                    if self.group_name not in ready_groups:
                        print(f"\n请输入 'ready' 或 'r' 表示准备就绪...")
                        
                        # 等待用户输入
                        while True:
                            try:
                                user_input = input("> ").strip().lower()
                                if user_input in ['ready', 'r', '准备']:
                                    print(f"\n正在提交准备就绪...")
                                    success, auto_started, msg = self.submit_ready()
                                    if success:
                                        if auto_started:
                                            print(f"✓ {msg}")
                                            break  # 回合已自动开始，退出等待循环
                                        else:
                                            print(f"✓ {msg}")
                                            # 显示准备状态
                                            status = self.get_status()
                                            ready_groups = status.get('ready_groups', [])
                                            active_groups = status.get('active_groups', [])
                                            print(f"已准备: {len(ready_groups)}/{len(active_groups)} 组")
                                            break  # 已准备，退出等待循环
                                    else:
                                        print(f"✗ 准备失败: {msg}")
                                        break
                                else:
                                    print("输入无效，请输入 'ready' 或 'r' 表示准备就绪")
                            except KeyboardInterrupt:
                                print("\n\n用户中断")
                                return False
                            except EOFError:
                                print("\n\n输入结束")
                                return False
                
                # 等待所有人准备好或状态改变
                while True:
                    s = self.get_status()
                    new_status = s.get('status')
                    
                    if new_status == 'describing':
                        print("\n所有人已准备好，回合开始！")
                        break
                    elif new_status in ['game_end', 'waiting', 'registered']:
                        break
                    
                    # 显示准备进度
                    ready_groups = s.get('ready_groups', [])
                    active_groups = s.get('active_groups', [])
                    if len(active_groups) > 0:
                        print(f"\r等待准备: {len(ready_groups)}/{len(active_groups)} 组已准备", end='', flush=True)
                    
                    time.sleep(2)

            elif game_status == 'word_assigned':
                self.display_status(status)
                print("\n等待所有人准备好开始新一轮游戏...")
                
                # 如果未被淘汰，等待用户手动确认准备
                if not self.is_eliminated:
                    ready_groups = status.get('ready_groups', [])
                    if self.group_name not in ready_groups:
                        print(f"\n请输入 'ready' 或 'r' 表示准备就绪...")
                        
                        # 等待用户输入
                        while True:
                            try:
                                user_input = input("> ").strip().lower()
                                if user_input in ['ready', 'r', '准备']:
                                    print(f"\n正在提交准备就绪...")
                                    success, auto_started, msg = self.submit_ready()
                                    if success:
                                        if auto_started:
                                            print(f"✓ {msg}")
                                            break  # 回合已自动开始，退出等待循环
                                        else:
                                            print(f"✓ {msg}")
                                            # 显示准备状态
                                            status = self.get_status()
                                            ready_groups = status.get('ready_groups', [])
                                            active_groups = status.get('active_groups', [])
                                            print(f"已准备: {len(ready_groups)}/{len(active_groups)} 组")
                                            break  # 已准备，退出等待循环
                                    else:
                                        print(f"✗ 准备失败: {msg}")
                                        break
                                else:
                                    print("输入无效，请输入 'ready' 或 'r' 表示准备就绪")
                            except KeyboardInterrupt:
                                print("\n\n用户中断")
                                return False
                            except EOFError:
                                print("\n\n输入结束")
                                return False
                
                # 等待所有人准备好或状态改变
                while True:
                    s = self.get_status()
                    new_status = s.get('status')
                    
                    if new_status == 'describing':
                        print("\n所有人已准备好，新一轮游戏开始！")
                        break
                    elif new_status in ['game_end', 'waiting', 'registered']:
                        break
                    
                    # 显示准备进度
                    ready_groups = s.get('ready_groups', [])
                    active_groups = s.get('active_groups', [])
                    if len(active_groups) > 0:
                        print(f"\r等待准备: {len(ready_groups)}/{len(active_groups)} 组已准备", end='', flush=True)
                    
                    time.sleep(2)

            else:
                time.sleep(2)

        return True


def test_connection():
    """测试服务器连接"""
    print("正在测试服务器连接...")
    try:
        r = requests.get(f"{BASE_URL}/api/status", timeout=5)
        if r.status_code == 200:
            print("✓ 服务器连接成功")
            return True
        else:
            print(f"✗ 服务器返回错误: {r.status_code}")
            return False
    except Exception as e:
        print(f"✗ 无法连接服务器 {BASE_URL}: {e}")
        return False


def main():
    print("=" * 50)
    print("  谁是卧底 - 交互式游戏方客户端")
    print("=" * 50)

    # 测试连接
    if not test_connection():
        print("\n请确保 backend.py 已启动")
        retry = input("是否重试连接？(y/n): ").lower()
        if retry == 'y':
            if not test_connection():
                return
        else:
            return

    # 输入组名
    while True:
        group_name = input("\n请输入你的组名: ").strip()
        if group_name:
            break
        print("组名不能为空，请重新输入")

    client = InteractiveClient(group_name)

    # 持续运行客户端
    reconnect_count = 0
    max_reconnect = 100

    while reconnect_count < max_reconnect:
        try:
            print(f"\n{'=' * 60}")
            print(f"第 {reconnect_count + 1} 次连接")
            print("=" * 60)
            
            # 每次重连前重新连接 WebSocket
            if reconnect_count > 0:
                print("重新连接 WebSocket...")
                client.connect_websocket()

            should_reconnect = client.run()

            if not should_reconnect:
                print("\n客户端正常退出")
                break

            reconnect_count += 1
            if reconnect_count >= max_reconnect:
                print(f"\n已达到最大重连次数 ({max_reconnect})")
                break

            # 断开 WebSocket 连接（如果已连接）
            if client.sio and client.websocket_connected:
                client.disconnect_websocket()
            
            print(f"\n3秒后重新连接... (按Ctrl+C退出)")
            for i in range(3, 0, -1):
                print(f"{i}...", end=' ', flush=True)
                time.sleep(1)
            print("重新连接！")

        except KeyboardInterrupt:
            print("\n\n已退出")
            break
        except Exception as e:
            print(f"\n客户端异常: {e}")
            reconnect_count += 1
            if reconnect_count >= max_reconnect:
                print(f"已达到最大重连次数 ({max_reconnect})")
                break

            print("5秒后重新连接...")
            time.sleep(5)

    print("\n游戏结束，感谢参与！")
    
    # 断开 WebSocket 连接
    if client.sio and client.websocket_connected:
        client.disconnect_websocket()
        print("✓ WebSocket 连接已关闭")
    
    input("按Enter退出...")


if __name__ == '__main__':
    client_instance = None
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已退出")
        # 注意：client_instance 在这里可能未定义，因为它在 main() 内部创建
        # 如果需要，可以在 main() 中处理退出逻辑
    except Exception as e:
        print(f"\n程序异常退出: {e}")
        input("按Enter退出...")
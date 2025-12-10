"""
游戏逻辑模块
负责游戏状态管理、投票判定、得分计算等核心逻辑
"""
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

# 配置常量
MAX_GROUPS = 5  # 最大组数
DESCRIBE_TIMEOUT = 180  # 描述阶段总超时时间（秒）
VOTE_TIMEOUT = 120  # 投票阶段超时时间（秒）
SPEAKER_TIMEOUT = 30  # 每个人发言超时时间（秒）


class GameStatus(Enum):
    """游戏状态枚举"""
    WAITING = "waiting"  # 等待注册
    REGISTERED = "registered"  # 已注册，等待开始
    WORD_ASSIGNED = "word_assigned"  # 词语已分配
    DESCRIBING = "describing"  # 描述阶段
    VOTING = "voting"  # 投票阶段
    ROUND_END = "round_end"  # 回合结束
    GAME_END = "game_end"  # 游戏结束


class GameLogic:
    """游戏逻辑核心类"""

    def __init__(self):
        self.groups: Dict[str, Dict] = {}  # 组名 -> 组信息
        self.game_status = GameStatus.WAITING
        self.undercover_group: Optional[str] = None  # 卧底组名
        self.undercover_word: str = ""  # 卧底词
        self.civilian_word: str = ""  # 平民词
        self.current_round = 0  # 当前回合数
        self.describe_order: List[str] = []  # 描述顺序
        self.current_speaker_index: int = 0  # 当前发言者索引
        self.descriptions: Dict[int, List[Dict]] = {}  # 每回合的描述 {round: [{group, desc, time}]}
        self.votes: Dict[int, Dict[str, str]] = {}  # 每回合的投票 {round: {voter: target}}
        self.eliminated_groups: List[str] = []  # 已淘汰的组
        self.scores: Dict[str, int] = {}  # 得分 {group: score}
        self.reports: List[Dict] = []  # 异常上报记录（由主持端自动检测生成）
        self.last_vote_result: Optional[Dict] = None  # 最近一次投票结果
        self.phase_deadline: Optional[datetime] = None  # 当前阶段截止时间
        self.speaker_deadline: Optional[datetime] = None  # 当前发言者截止时间
        # 游戏统计
        self.game_counter = 0  # 游戏计数
        self.undercover_history: Dict[str, int] = {}  # 每个组当卧底的次数
        self.total_games_played = 0  # 总游戏次数
        self.last_activity: Dict[str, datetime] = {}  # 组名 -> 最后活跃时间（用于检测在线状态）
        self.ready_groups: List[str] = []  # 已准备好开始回合的组（每回合开始前清空）

    def register_group(self, group_name: str) -> bool:
        """
        注册游戏组
        :param group_name: 组名
        :return: 是否注册成功
        """
        if group_name in self.groups:
            return False
        if len(self.groups) >= MAX_GROUPS:
            return False

        self.groups[group_name] = {
            "name": group_name,
            "role": None,  # "undercover" 或 "civilian"
            "word": "",
            "registered_time": datetime.now().isoformat(),
            "eliminated": False
        }

        # 初始化统计和分数
        if group_name not in self.undercover_history:
            self.undercover_history[group_name] = 0

        # 初始化得分
        if group_name not in self.scores:
            self.scores[group_name] = 0

        if len(self.groups) > 0:
            self.game_status = GameStatus.REGISTERED
        # 更新活跃时间
        self.update_activity(group_name)

        return True

    def start_game(self, undercover_word: str, civilian_word: str, websocket_status: Optional[Dict[str, bool]] = None) -> bool:
        """
        开始游戏，分配身份和词语（只给在线玩家分配）
        :param undercover_word: 卧底词
        :param civilian_word: 平民词
        :param websocket_status: WebSocket连接状态字典，用于判断哪些玩家在线
        :return: 是否成功开始
        """
        # 获取在线状态
        online_status = self.get_online_status(websocket_status)
        
        # 获取在线玩家列表
        online_groups = [name for name in self.groups.keys() if online_status.get(name, False)]
        
        # 允许至少1个在线玩家开始
        if len(online_groups) < 1:
            return False
        # 允许在 REGISTERED 或 GAME_END 状态下开始新游戏（用于多轮游戏）
        if self.game_status not in [GameStatus.REGISTERED, GameStatus.GAME_END]:
            return False

        # 清空淘汰组和重置所有组的淘汰状态（用于多轮游戏）
        self.eliminated_groups = []
        
        # 更新所有组的淘汰状态
        for group_name in self.groups:
            self.groups[group_name]["eliminated"] = False
        
        # 离线玩家标记为淘汰（不参与游戏）
        for group_name in self.groups:
            if group_name not in online_groups:
                self.eliminated_groups.append(group_name)
                self.groups[group_name]["eliminated"] = True
                # 清空离线玩家的角色和词语
                self.groups[group_name]["role"] = None
                self.groups[group_name]["word"] = ""

        self.undercover_word = undercover_word
        self.civilian_word = civilian_word

        # 只给在线玩家分配角色
        group_names = online_groups

        # 选择卧底时考虑历史次数，尽量平衡（只从在线玩家中选择）
        if group_names:
            # 确保所有组都有统计记录
            for name in group_names:
                if name not in self.undercover_history:
                    self.undercover_history[name] = 0

            # 找出当卧底次数最少的组
            min_count = min(self.undercover_history[name] for name in group_names)
            eligible_groups = [name for name in group_names
                               if self.undercover_history[name] == min_count]

            # 从符合条件的组中随机选择
            self.undercover_group = random.choice(eligible_groups)

            # 增加计数
            self.undercover_history[self.undercover_group] += 1
            self.game_counter += 1
            self.total_games_played += 1

        # 分配身份和词语（只给在线玩家）
        for group_name in group_names:
            if group_name == self.undercover_group:
                self.groups[group_name]["role"] = "undercover"
                self.groups[group_name]["word"] = undercover_word
            else:
                self.groups[group_name]["role"] = "civilian"
                self.groups[group_name]["word"] = civilian_word

        self.current_round = 1

        # 确保所有组都有分数记录
        for group_name in self.groups:
            if group_name not in self.scores:
                self.scores[group_name] = 0

        # 清空准备状态
        self.ready_groups = []

        self.game_status = GameStatus.WORD_ASSIGNED
        return True

    def start_round(self) -> List[str]:
        """
        开始新回合，随机排序（只包括未淘汰的组）
        """
        if self.game_status not in [GameStatus.WORD_ASSIGNED, GameStatus.ROUND_END]:
            return []

        # 如果当前状态是ROUND_END，增加回合数
        if self.game_status == GameStatus.ROUND_END:
            self.current_round += 1

        # 获取未淘汰的组
        active_groups = [g for g in self.groups.keys() if g not in self.eliminated_groups]
        # 即使只有1组也可以开始回合
        if len(active_groups) < 1:
            return []

        # 清空准备状态（新回合开始）
        self.ready_groups = []

        # 随机排序（只包括活跃组）
        self.describe_order = active_groups.copy()
        random.shuffle(self.describe_order)

        # 初始化本回合的描述和投票
        self.descriptions[self.current_round] = []
        self.votes[self.current_round] = {}

        # 重置发言者索引
        self.current_speaker_index = 0

        # 设置描述阶段截止时间
        self.phase_deadline = datetime.now() + timedelta(seconds=DESCRIBE_TIMEOUT)

        # 设置第一个发言者的截止时间
        if len(self.describe_order) > 0:
            self.speaker_deadline = datetime.now() + timedelta(seconds=SPEAKER_TIMEOUT)

        self.game_status = GameStatus.DESCRIBING
        return self.describe_order

    def submit_description(self, group_name: str, description: str) -> Tuple[bool, str]:
        """
        提交描述
        """
        # 检查是否被淘汰
        if group_name in self.eliminated_groups:
            return False, "该组已被淘汰，不能发言"

        if self.game_status != GameStatus.DESCRIBING:
            return False, "当前不是描述阶段"

        if group_name not in self.describe_order:
            return False, "该组不在发言列表中"

        # 检查是否已经提交过
        for desc in self.descriptions.get(self.current_round, []):
            if desc["group"] == group_name:
                return False, "该组已提交过描述"

        # 检查是否轮到该组发言
        current_speaker = self.get_current_speaker()
        if current_speaker != group_name:
            return False, f"请等待，当前应由 {current_speaker} 发言"

        # 检查是否超时
        is_timeout = False
        if self.speaker_deadline and datetime.now() > self.speaker_deadline:
            is_timeout = True

        self.descriptions[self.current_round].append({
            "group": group_name,
            "description": description,
            "time": datetime.now().isoformat(),
            "timeout": is_timeout  # 标记是否超时提交
        })

        # 更新活跃时间
        self.update_activity(group_name)
        # 移动到下一个发言者
        self.current_speaker_index += 1

        # 设置下一个发言者的截止时间
        if self.current_speaker_index < len(self.describe_order):
            self.speaker_deadline = datetime.now() + timedelta(seconds=SPEAKER_TIMEOUT)
        else:
            self.speaker_deadline = None

        # 检查是否所有人都提交了
        active_groups = [g for g in self.describe_order if g not in self.eliminated_groups]
        if len(self.descriptions[self.current_round]) >= len(active_groups):
            # 设置投票阶段截止时间
            self.phase_deadline = datetime.now() + timedelta(seconds=VOTE_TIMEOUT)
            self.speaker_deadline = None
            self.game_status = GameStatus.VOTING

        msg = "描述提交成功"
        if is_timeout:
            msg += "（超时提交）"
        return True, msg

    def submit_vote(self, voter_group: str, target_group: str) -> Tuple[bool, str, bool]:
        """
        提交投票
        返回: (成功与否, 消息, 是否所有人已投票)
        """
        # 检查是否被淘汰
        if voter_group in self.eliminated_groups:
            return False, "该组已被淘汰，不能投票", False

        if self.game_status != GameStatus.VOTING:
            return False, "当前不是投票阶段", False

        if target_group in self.eliminated_groups:
            return False, "被投票的组已被淘汰", False

        if voter_group not in self.groups:
            return False, "投票组不存在", False

        if target_group not in self.groups:
            return False, "被投票的组不存在", False

        if voter_group == target_group:  # 不能投自己
            return False, "不能投票给自己", False

        # 检查是否已经投过票
        if voter_group in self.votes[self.current_round]:
            return False, "已经投过票了", False

        # 检查被投票的是否是活跃组
        active_groups = [g for g in self.describe_order if g not in self.eliminated_groups]
        if target_group not in active_groups:
            return False, "被投票的组不是活跃组", False

        self.votes[self.current_round][voter_group] = target_group

        # 更新活跃时间
        self.update_activity(voter_group)

        # 检查是否所有人投票完成
        round_votes = self.votes[self.current_round]
        active_groups = [g for g in self.describe_order if g not in self.eliminated_groups]
        all_voted = len(round_votes) >= len(active_groups)

        return True, "投票成功", all_voted

    def submit_ready(self, group_name: str) -> Tuple[bool, str, bool]:
        """
        提交准备就绪状态
        返回: (成功与否, 消息, 是否所有人已准备好且自动开始回合)
        """
        # 检查组是否存在
        if group_name not in self.groups:
            return False, "组不存在", False

        # 检查是否被淘汰
        if group_name in self.eliminated_groups:
            return False, "该组已被淘汰，不能准备", False

        # 只有在词语已分配或回合结束状态时才能准备
        if self.game_status not in [GameStatus.WORD_ASSIGNED, GameStatus.ROUND_END]:
            return False, "当前状态不能准备", False

        # 检查是否已经准备过
        if group_name in self.ready_groups:
            return True, "已经准备过了", False

        # 添加到准备列表
        self.ready_groups.append(group_name)
        
        # 更新活跃时间
        self.update_activity(group_name)

        # 获取活跃组列表（未淘汰的）
        active_groups = [g for g in self.groups.keys() if g not in self.eliminated_groups]
        
        # 检查是否所有人都准备好了
        all_ready = len(self.ready_groups) >= len(active_groups)

        return True, "准备成功", all_ready

    def process_voting_result(self) -> Dict:
        """处理投票结果，判定淘汰和游戏状态"""
        if self.game_status != GameStatus.VOTING:
            return {"error": "当前不在投票阶段"}

        round_votes = self.votes[self.current_round]
        active_groups = [g for g in self.describe_order if g not in self.eliminated_groups]

        # 检查是否所有活跃组都投票了
        if len(round_votes) < len(active_groups):
            return {"error": "还有组未投票"}

        # 统计票数
        vote_count: Dict[str, int] = {}
        for target in round_votes.values():
            vote_count[target] = vote_count.get(target, 0) + 1

        # 找出得票最多的组
        max_votes = max(vote_count.values()) if vote_count else 0
        max_voted_groups = [g for g, v in vote_count.items() if v == max_votes]

        # 构建详细的投票信息
        vote_details = {}
        for voter, target in round_votes.items():
            vote_details[voter] = target

        result = {
            "round": self.current_round,
            "vote_count": vote_count,
            "vote_details": vote_details,
            "max_voted_groups": max_voted_groups,
            "max_votes": max_votes,
            "eliminated": [],
            "game_ended": False,
            "winner": None,
            "message": "",
            "undercover_group": self.undercover_group if self.game_status != GameStatus.WAITING else None,
            "undercover_word": "",
            "civilian_word": "",
            "round_scores": {},
            "total_scores": self.scores.copy(),
            "active_groups": active_groups,
            "voted_groups": list(round_votes.keys())
        }

        # 判定结果
        if len(max_voted_groups) == 1:
            # 情况a：票数最多的有1组，该组被淘汰
            eliminated = max_voted_groups[0]
            self.eliminated_groups.append(eliminated)
            # 更新组的淘汰状态
            if eliminated in self.groups:
                self.groups[eliminated]["eliminated"] = True
            result["eliminated"] = [eliminated]

            # 计算本轮得分
            self._calculate_round_scores(result)

            if eliminated == self.undercover_group:
                # 卧底被淘汰，游戏结束，平民胜利
                result["game_ended"] = True
                result["winner"] = "civilian"
                result["message"] = f"🎉 投票结果：{eliminated} 被投出，TA是卧底！\n"
                result["message"] += f"得票情况：{eliminated} 获得 {max_votes} 票\n"
                result["message"] += "🎊 平民胜利！"
                result["undercover_word"] = self.undercover_word
                result["civilian_word"] = self.civilian_word
                self.game_status = GameStatus.GAME_END
            else:
                # 平民被淘汰，检查剩余人数
                remaining_groups = [g for g in self.groups.keys() if g not in self.eliminated_groups]
                remaining_civilians = [g for g in remaining_groups if g != self.undercover_group]

                if len(remaining_civilians) <= 1:
                    # 平民只剩1组或0组，卧底胜利
                    result["game_ended"] = True
                    result["winner"] = "undercover"
                    result["message"] = f"😈 投票结果：{eliminated} 是平民，被投出后平民只剩{len(remaining_civilians)}组\n"
                    result["message"] += f"🎭 卧底 {self.undercover_group} 胜利！"
                    result["undercover_word"] = self.undercover_word
                    result["civilian_word"] = self.civilian_word
                    self.game_status = GameStatus.GAME_END
                else:
                    # 继续下一轮
                    result["message"] = f"👋 投票结果：{eliminated} 被投出，TA是平民。\n"
                    result["message"] += f"得票情况：{eliminated} 获得 {max_votes} 票\n"
                    result["message"] += "游戏继续。"
                    # 不立即增加回合数，等待玩家准备下一轮
                    self.game_status = GameStatus.ROUND_END  # 保持当前回合状态
                    # 清空准备状态，等待玩家准备下一轮
                    self.ready_groups = []

        elif len(max_voted_groups) == 2:
            # 情况c：票数最多的组有2组，进入下一轮
            groups_str = ' 和 '.join(max_voted_groups)
            result["message"] = f"⚖️ 投票结果：{groups_str} 票数相同（各{max_votes}票），无人淘汰。\n"
            result["message"] += "进入下一轮。"

            # 计算本轮得分（平局情况）
            self._calculate_round_scores(result)

            self.game_status = GameStatus.ROUND_END
            # 清空准备状态，等待玩家准备下一轮
            self.ready_groups = []

        elif len(max_voted_groups) >= 3:
            # 情况b：得票最多有3组或更多
            all_civilians = all(g != self.undercover_group for g in max_voted_groups)
            if all_civilians:
                # 都是平民，全部淘汰，游戏结束，卧底胜利
                self.eliminated_groups.extend(max_voted_groups)
                # 更新组的淘汰状态
                for g in max_voted_groups:
                    if g in self.groups:
                        self.groups[g]["eliminated"] = True
                result["eliminated"] = max_voted_groups

                # 计算本轮得分
                self._calculate_round_scores(result)

                result["game_ended"] = True
                result["winner"] = "undercover"
                result["message"] = f"😈 投票结果：{', '.join(max_voted_groups)} 票数相同且都是平民，全部淘汰！\n"
                result["message"] += f"🎭 卧底 {self.undercover_group} 胜利！"
                result["undercover_word"] = self.undercover_word
                result["civilian_word"] = self.civilian_word
                self.game_status = GameStatus.GAME_END
            else:
                # 包含卧底，进入下一轮
                result["message"] = f"投票结果：{', '.join(max_voted_groups)} 票数相同，包含卧底，进入下一轮。"

                # 计算本轮得分（平局情况）
                self._calculate_round_scores(result)

                self.game_status = GameStatus.ROUND_END
                # 清空准备状态，等待玩家准备下一轮
                self.ready_groups = []

        # 清除倒计时
        self.phase_deadline = None
        self.speaker_deadline = None

        self.last_vote_result = result
        return result

    def _calculate_round_scores(self, result: Dict):
        """
        得分规则：
        1. 卧底得分 = 胜利分（如果平民只剩1组，得3分） + 生存分（每生存一轮得1分）
        2. 平民得分 = 生存分（每生存一轮得1分）
        """
        round_scores = {}  # 初始化每轮得分字典

        # 本轮被淘汰的组
        eliminated_this_round = result.get('eliminated', [])
        # 游戏是否结束
        game_ended = result.get('game_ended', False)
        winner = result.get('winner')

        # 计算本轮结束后存活的平民组数量
        remaining_civilians = 0
        for group_name in self.groups.keys():
            if (group_name != self.undercover_group and
                    group_name not in self.eliminated_groups and
                    group_name not in eliminated_this_round):
                remaining_civilians += 1

        # 遍历所有组计算本轮得分
        for group_name in self.groups.keys():
            round_score = 0

            # 规则1：生存分 - 所有存活到本轮结束的组获得1分
            if group_name not in eliminated_this_round and group_name not in self.eliminated_groups:
                round_score += 1

            # 规则2：胜利分 - 卧底胜利时（平民剩余≤1组）加3分
            if group_name == self.undercover_group and remaining_civilians <= 1:
                round_score += 3

            round_scores[group_name] = round_score

        # 更新总得分（累加本轮得分）
        for group_name, score in round_scores.items():
            self.scores[group_name] = self.scores.get(group_name, 0) + score

        result["round_scores"] = round_scores
        result["total_scores"] = self.scores.copy()

    def add_report(self, group_name: str, report_type: str, detail: str) -> Dict:

        """记录异常报告"""
        ticket = f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.reports) + 1:03d}"

        entry = {
            "ticket": ticket,
            "group": group_name or "unknown",
            "type": report_type,
            "detail": detail,
            "time": datetime.now().isoformat()
        }
        self.reports.append(entry)
        return entry

    def get_vote_details_for_group(self, group_name: str) -> Dict:
        """获取指定组的投票详情"""
        if not self.last_vote_result:
            return {}

        result = {
            'my_vote': None,
            'voted_by': [],
            'eliminated': self.last_vote_result.get('eliminated', []),
            'winner': self.last_vote_result.get('winner'),
            'game_ended': self.last_vote_result.get('game_ended', False),
            'message': self.last_vote_result.get('message', ''),
            'round': self.last_vote_result.get('round'),
            'vote_details': self.last_vote_result.get('vote_details', {})
        }

        # 获取我投给了谁
        if group_name in self.last_vote_result.get('vote_details', {}):
            result['my_vote'] = self.last_vote_result['vote_details'][group_name]

        # 获取谁投了我
        vote_details = self.last_vote_result.get('vote_details', {})
        for voter, target in vote_details.items():
            if target == group_name:
                result['voted_by'].append(voter)

        return result

    def update_activity(self, group_name: str):
        """更新组的最后活跃时间"""
        if group_name in self.groups:
            self.last_activity[group_name] = datetime.now()

    def get_online_status(self, websocket_status: Optional[Dict[str, bool]] = None) -> Dict[str, bool]:
        """检测各组是否在线（优先使用WebSocket连接状态，降级使用活跃时间）"""
        online_status = {}
        threshold = timedelta(seconds=60)  # 60秒未活跃视为离线

        for group_name in self.groups.keys():
            # 优先使用WebSocket连接状态
            if websocket_status is not None and group_name in websocket_status:
                online_status[group_name] = websocket_status[group_name]
            else:
                # 降级：使用HTTP活跃时间
                last_active = self.last_activity.get(group_name)
                if last_active:
                    online_status[group_name] = (datetime.now() - last_active) < threshold
                else:
                    online_status[group_name] = False

        return online_status

    def _has_existing_report(self, group_name: str, report_type: str, round_num: int) -> bool:
        """检查是否已经为指定组在当前轮次记录过相同类型的异常"""
        for report in self.reports:
            if report.get('group') == group_name and report.get('type') == report_type:
                # 对于断开连接类型，检查是否在最近一段时间内已经记录过（避免重复记录）
                if report_type == 'disconnect':
                    try:
                        report_time = datetime.fromisoformat(report.get('time', ''))
                        # 5分钟内不重复记录断开连接
                        if (datetime.now() - report_time).total_seconds() < 300:
                            return True
                    except:
                        pass
                # 对于其他类型，检查轮次
                elif f'第{round_num}轮' in report.get('detail', ''):
                    return True
        return False

    def handle_disconnect(self, group_name: str) -> Optional[Dict]:
        """
        处理断开连接（视为退出游戏）
        如果断开的是卧底，则平民胜利
        如果断开的是平民，则根据游戏规则判定游戏是否继续
        返回游戏结果（如果有）或None
        """
        # 只在游戏进行中时处理断开连接
        if self.game_status in [GameStatus.WAITING, GameStatus.REGISTERED]:
            return None
        
        # 如果已经淘汰了，不需要处理
        if group_name in self.eliminated_groups:
            return None
        
        # 标记为淘汰（退出游戏）
        self.eliminated_groups.append(group_name)
        if group_name in self.groups:
            self.groups[group_name]["eliminated"] = True
        
        # 记录异常
        if not self._has_existing_report(group_name, 'disconnect', self.current_round):
            self.add_report(
                group_name,
                'disconnect',
                f'检测到断开连接，视为退出游戏（第{self.current_round}轮）'
            )
        
        # 如果断开的是卧底，平民胜利，游戏结束
        if group_name == self.undercover_group:
            # 计算得分
            self._calculate_scores()
            
            result = {
                "round": self.current_round,
                "vote_count": {},
                "vote_details": {},
                "max_voted_groups": [],
                "max_votes": 0,
                "eliminated": [group_name],
                "game_ended": True,
                "winner": "civilian",
                "message": f"📡 {group_name}（卧底）断开连接，视为退出游戏。\n🎊 平民胜利！",
                "undercover_group": self.undercover_group,
                "undercover_word": self.undercover_word,
                "civilian_word": self.civilian_word,
                "round_scores": {},
                "total_scores": self.scores.copy(),
                "active_groups": [g for g in self.groups.keys() if g not in self.eliminated_groups],
                "voted_groups": []
            }
            
            # 计算本轮得分
            self._calculate_round_scores(result)
            
            self.game_status = GameStatus.GAME_END
            self.last_vote_result = result
            
            return result
        
        # 如果断开的是平民，检查是否满足游戏结束条件
        remaining_groups = [g for g in self.groups.keys() if g not in self.eliminated_groups]
        remaining_civilians = [g for g in remaining_groups if g != self.undercover_group]
        
        if len(remaining_civilians) <= 1:
            # 平民只剩1组或0组，卧底胜利，游戏结束
            self._calculate_scores()
            
            result = {
                "round": self.current_round,
                "vote_count": {},
                "vote_details": {},
                "max_voted_groups": [],
                "max_votes": 0,
                "eliminated": [group_name],
                "game_ended": True,
                "winner": "undercover",
                "message": f"📡 {group_name}（平民）断开连接，视为退出游戏。\n"
                          f"平民只剩{len(remaining_civilians)}组\n"
                          f"🎭 卧底 {self.undercover_group} 胜利！",
                "undercover_group": self.undercover_group,
                "undercover_word": self.undercover_word,
                "civilian_word": self.civilian_word,
                "round_scores": {},
                "total_scores": self.scores.copy(),
                "active_groups": remaining_groups,
                "voted_groups": []
            }
            
            # 计算本轮得分
            self._calculate_round_scores(result)
            
            self.game_status = GameStatus.GAME_END
            self.last_vote_result = result
            
            return result
        
        # 平民断开连接，但游戏继续
        # 不生成投票结果，只是更新状态
        # 如果正在描述或投票阶段，需要从发言顺序中移除
        if self.game_status == GameStatus.DESCRIBING:
            if group_name in self.describe_order:
                self.describe_order.remove(group_name)
                # 如果断开的组是当前发言者，需要调整
                if self.get_current_speaker() == group_name:
                    # 会自动跳过，因为已从顺序中移除
                    pass
        elif self.game_status == GameStatus.VOTING:
            # 从投票中移除（如果已投票）
            if self.current_round in self.votes and group_name in self.votes[self.current_round]:
                del self.votes[self.current_round][group_name]
        
        return None

    def detect_missing_submissions(self, websocket_status: Optional[Dict[str, bool]] = None) -> List[Dict]:
        """
        检测未提交的组（已移除超时异常上报功能）
        保留方法以保持API兼容性，但不再自动上报异常
        """
        # 不再自动上报超时异常，只返回空列表
        return []

    def _calculate_scores(self):
        """
        计算得分
        规则：
        - 卧底胜利条件：平民只剩1组
        - 胜利分：卧底胜利时得3分
        - 生存分：每生存一轮得1分
        - 卧底得分 = 胜利分 + 生存分
        - 平民得分 = 生存分（生存的轮数）
        """
        if not self.undercover_group:
            return

        undercover_eliminated = self.undercover_group in self.eliminated_groups

        # 计算每个组的生存轮数
        # 生存轮数 = 被淘汰时的回合数，如果未被淘汰则为当前回合数
        survival_rounds: Dict[str, int] = {}

        for group_name in self.groups.keys():
            if group_name in self.eliminated_groups:
                # 找到该组被淘汰的回合
                eliminated_round = self._get_eliminated_round(group_name)
                survival_rounds[group_name] = eliminated_round - 1  # 被淘汰前的轮数
            else:
                # 存活到最后
                survival_rounds[group_name] = self.current_round

        if undercover_eliminated:
            # 卧底被淘汰，平民胜利
            # 卧底：只有生存分（被淘汰前的轮数）
            self.scores[self.undercover_group] = max(0, survival_rounds[self.undercover_group])

            # 平民：生存分
            for group_name in self.groups.keys():
                if group_name != self.undercover_group:
                    self.scores[group_name] = survival_rounds[group_name]
        else:
            # 卧底存活到最后，卧底胜利
            # 卧底得分 = 胜利分(3) + 生存分
            victory_bonus = 3
            self.scores[self.undercover_group] = victory_bonus + survival_rounds[self.undercover_group]

            # 平民：生存分
            for group_name in self.groups.keys():
                if group_name != self.undercover_group:
                    self.scores[group_name] = survival_rounds[group_name]

    def _get_eliminated_round(self, group_name: str) -> int:
        """获取某组被淘汰的回合数"""
        # 遍历投票结果找到该组被淘汰的回合
        if self.last_vote_result and group_name in self.last_vote_result.get("eliminated", []):
            return self.last_vote_result.get("round", self.current_round)
        # 默认返回当前回合
        return self.current_round

    def get_game_state(self) -> Dict:
        """获取当前游戏状态"""
        # 获取当前回合已发言的组
        described_groups = []
        if self.current_round in self.descriptions:
            described_groups = [d["group"] for d in self.descriptions[self.current_round]]

        # 获取当前回合已投票的组
        voted_groups = []
        if self.current_round in self.votes:
            voted_groups = list(self.votes[self.current_round].keys())

        return {
            "status": self.game_status.value,
            "groups": {name: {
                "name": info["name"],
                "role": info["role"],
                "eliminated": info.get("eliminated", False) or name in self.eliminated_groups,
                "undercover_count": self.undercover_history.get(name, 0)
            } for name, info in self.groups.items()},
            "undercover_group": self.undercover_group if self.game_status != GameStatus.WAITING else None,
            "current_round": self.current_round,
            "describe_order": self.describe_order,
            "current_speaker": self.get_current_speaker(),
            "current_speaker_index": self.current_speaker_index,
            "described_groups": described_groups,  # 已发言的组
            "voted_groups": voted_groups,  # 已投票的组
            "eliminated_groups": self.eliminated_groups,
            "scores": self.scores,  # 返回累计得分
            "descriptions": self.descriptions,
            "votes": self.votes,
            "reports": self.reports,
            "game_counter": self.game_counter,  # 游戏计数
            "undercover_history": self.undercover_history,  # 卧底历史
            "total_games_played": self.total_games_played,  # 总游戏次数
            "undercover_word": self.undercover_word if self.game_status == GameStatus.GAME_END else "",
            "civilian_word": self.civilian_word if self.game_status == GameStatus.GAME_END else "",
            "online_status": self.get_online_status(),  # 各组在线状态
            "ready_groups": self.ready_groups  # 已准备好的组
        }

    def get_public_status(self) -> Dict:
        """面向游戏方的公开状态"""
        active_groups = [g for g in self.groups.keys() if g not in self.eliminated_groups]

        # 计算阶段剩余时间
        remaining_seconds = None
        if self.phase_deadline:
            delta = self.phase_deadline - datetime.now()
            remaining_seconds = max(0, int(delta.total_seconds()))

        # 计算当前发言者剩余时间
        speaker_remaining = None
        if self.speaker_deadline and self.game_status == GameStatus.DESCRIBING:
            delta = self.speaker_deadline - datetime.now()
            speaker_remaining = max(0, int(delta.total_seconds()))

        # 获取当前发言人（只对活跃组）
        current_speaker = self.get_current_speaker() if self.game_status == GameStatus.DESCRIBING else None

        # 获取当前回合已提交的描述（供游戏方查看）
        current_descriptions = []
        if self.current_round in self.descriptions:
            for desc in self.descriptions[self.current_round]:
                current_descriptions.append({
                    "group": desc["group"],
                    "description": desc["description"]
                })

        # 获取当前回合已投票的组
        voted_groups = []
        if self.current_round in self.votes:
            voted_groups = list(self.votes[self.current_round].keys())

        # 构建阶段信息
        phase_info = ""
        if self.game_status == GameStatus.DESCRIBING:
            phase_info = "🎤 描述阶段"
        elif self.game_status == GameStatus.VOTING:
            phase_info = "🗳️ 投票阶段"
        elif self.game_status == GameStatus.ROUND_END:
            phase_info = "🔄 回合结束"
        elif self.game_status == GameStatus.GAME_END:
            phase_info = "🏁 游戏结束"
        elif self.game_status == GameStatus.WORD_ASSIGNED:
            phase_info = "📋 词语已分配"
        elif self.game_status == GameStatus.REGISTERED:
            phase_info = "✅ 已注册"
        elif self.game_status == GameStatus.WAITING:
            phase_info = "⏳ 等待注册"

        # 获取上次投票结果（如果有）
        last_vote_info = {}
        if self.last_vote_result:
            last_vote_info = {
                'round': self.last_vote_result.get('round'),
                'eliminated': self.last_vote_result.get('eliminated', []),
                'winner': self.last_vote_result.get('winner'),
                'game_ended': self.last_vote_result.get('game_ended', False),
                'message': self.last_vote_result.get('message', '')
            }

        # 检查是否有新游戏开始（当前回合为1且没有描述记录）
        new_game_started = False
        if (self.game_status == GameStatus.WORD_ASSIGNED and
                self.current_round == 1 and
                len(self.descriptions) == 0):
            new_game_started = True

        return {
            "status": self.game_status.value,
            "phase_info": phase_info,
            "round": self.current_round,
            "active_groups": active_groups,
            "describe_order": self.describe_order if self.game_status in [GameStatus.DESCRIBING,
                                                                          GameStatus.VOTING] else [],
            "current_speaker": current_speaker,
            "current_speaker_index": self.current_speaker_index if self.game_status == GameStatus.DESCRIBING else None,
            "eliminated_groups": self.eliminated_groups,
            "remaining_seconds": remaining_seconds,
            "speaker_remaining_seconds": speaker_remaining,
            "descriptions": current_descriptions,
            "voted_groups": voted_groups,
            "last_vote_result": last_vote_info,
            "scores": self.scores,  # 返回得分信息
            "new_game_started": new_game_started,
            "game_ended": self.game_status == GameStatus.GAME_END,
            "ready_groups": self.ready_groups  # 已准备好的组
        }

    def get_current_speaker(self) -> Optional[str]:
        """获取当前应该发言的组"""
        if self.game_status != GameStatus.DESCRIBING:
            return None
        if self.current_speaker_index >= len(self.describe_order):
            return None
        return self.describe_order[self.current_speaker_index]

    def get_last_result(self) -> Optional[Dict]:
        """最近一轮的公开投票结果"""
        return self.last_vote_result

    def get_group_word(self, group_name: str) -> Optional[str]:
        """获取指定组的词语（仅在该组查询时返回）"""
        if group_name not in self.groups:
            return None
        # 更新活跃时间
        self.update_activity(group_name)
        return self.groups[group_name].get("word")

    def reset_game(self):
        """
        重置游戏
        """
        groups_backup = self.groups.copy()
        scores_backup = self.scores.copy()
        undercover_history_backup = self.undercover_history.copy()
        reports_backup = self.reports.copy()
        total_games_backup = self.total_games_played

        # 清除游戏状态相关字段
        self.game_status = GameStatus.WAITING
        self.undercover_group = None
        self.undercover_word = ""
        self.civilian_word = ""
        self.current_round = 0
        self.describe_order = []
        self.current_speaker_index = 0
        self.descriptions.clear()
        self.votes.clear()
        self.eliminated_groups = []  # 清空淘汰组
        self.last_vote_result = None
        self.phase_deadline = None
        self.speaker_deadline = None
        self.last_activity.clear()

        # 恢复保留的数据
        self.groups = groups_backup
        self.scores = scores_backup  # 保留得分
        self.undercover_history = undercover_history_backup
        self.reports = reports_backup
        self.total_games_played = total_games_backup

        # 重置组的游戏相关状态（但保留注册信息）
        for group_name in self.groups:
            self.groups[group_name]["role"] = None
            self.groups[group_name]["word"] = ""
            self.groups[group_name]["eliminated"] = False  # 重置淘汰状态

        # 如果有注册的组，恢复状态为已注册
        if len(self.groups) > 0:
            self.game_status = GameStatus.REGISTERED
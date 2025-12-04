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
            "eliminated": False  # 新增：淘汰状态
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

    def start_game(self, undercover_word: str, civilian_word: str) -> bool:
        """
        开始游戏，分配身份和词语
        :param undercover_word: 卧底词
        :param civilian_word: 平民词
        :return: 是否成功开始
        """
        # 允许至少1组开始
        if len(self.groups) < 1:
            return False
        if self.game_status != GameStatus.REGISTERED:
            return False

        # 清空淘汰组（新游戏开始，重置所有淘汰状态）
        self.eliminated_groups = []

        # 更新所有组的淘汰状态
        for group_name in self.groups:
            self.groups[group_name]["eliminated"] = False

        self.undercover_word = undercover_word
        self.civilian_word = civilian_word

        group_names = list(self.groups.keys())

        # 选择卧底时考虑历史次数，尽量平衡
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

        # 分配身份和词语
        for group_name in group_names:
            if group_name == self.undercover_group:
                self.groups[group_name]["role"] = "undercover"
                self.groups[group_name]["word"] = undercover_word
            else:
                self.groups[group_name]["role"] = "civilian"
                self.groups[group_name]["word"] = civilian_word

        self.current_round = 1

        # 确保所有组都有分数记录
        for group_name in group_names:
            if group_name not in self.scores:
                self.scores[group_name] = 0

        self.game_status = GameStatus.WORD_ASSIGNED
        return True

    def start_round(self) -> List[str]:
        """
        开始新回合，随机排序（只包括未淘汰的组）
        :return: 描述顺序列表
        """
        if self.game_status not in [GameStatus.WORD_ASSIGNED, GameStatus.ROUND_END]:
            return []

        # 获取未淘汰的组
        active_groups = [g for g in self.groups.keys() if g not in self.eliminated_groups]
        # 即使只有1组也可以开始回合
        if len(active_groups) < 1:
            return []

        # 随机排序（只包括活跃组）
        self.describe_order = active_groups.copy()
        random.shuffle(self.describe_order)

        # 初始化本回合的描述和投票
        self.descriptions[self.current_round] = []
        self.votes[self.current_round] = {}

        # 重置发言者索引
        self.current_speaker_index = 0

        # 设置描述阶段截止时间（现在实时计算）
        self.phase_deadline = datetime.now() + timedelta(seconds=DESCRIBE_TIMEOUT)

        # 设置第一个发言者的截止时间
        if len(self.describe_order) > 0:
            self.speaker_deadline = datetime.now() + timedelta(seconds=SPEAKER_TIMEOUT)

        self.game_status = GameStatus.DESCRIBING
        return self.describe_order

    def submit_description(self, group_name: str, description: str) -> Tuple[bool, str]:
        """
        提交描述
        修改：被淘汰的组不能发言
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

        # 设置下一个发言者的截止时间（实时更新）
        if self.current_speaker_index < len(self.describe_order):
            self.speaker_deadline = datetime.now() + timedelta(seconds=SPEAKER_TIMEOUT)
        else:
            self.speaker_deadline = None

        # 检查是否所有人都提交了
        active_groups = [g for g in self.describe_order if g not in self.eliminated_groups]
        if len(self.descriptions[self.current_round]) >= len(active_groups):
            # 进入投票阶段前，检测是否有组未提交（可能因为网络问题）
            self.detect_missing_submissions()
            # 设置投票阶段截止时间（实时更新）
            self.phase_deadline = datetime.now() + timedelta(seconds=VOTE_TIMEOUT)
            self.speaker_deadline = None
            self.game_status = GameStatus.VOTING

        msg = "描述提交成功"
        if is_timeout:
            msg += "（超时提交）"
        return True, msg

    def submit_vote(self, voter_group: str, target_group: str) -> Tuple[bool, str]:
        """
        提交投票
        修改：被淘汰的组不能投票
        """
        # 检查是否被淘汰
        if voter_group in self.eliminated_groups:
            return False, "该组已被淘汰，不能投票"

        if self.game_status != GameStatus.VOTING:
            return False, "当前不是投票阶段"

        if target_group in self.eliminated_groups:
            return False, "被投票的组已被淘汰"

        if voter_group not in self.groups:
            return False, "投票组不存在"

        if target_group not in self.groups:
            return False, "被投票的组不存在"

        if voter_group == target_group:  # 不能投自己
            return False, "不能投票给自己"

        # 检查是否已经投过票
        if voter_group in self.votes[self.current_round]:
            return False, "已经投过票了"

        # 检查被投票的是否是活跃组
        active_groups = [g for g in self.describe_order if g not in self.eliminated_groups]
        if target_group not in active_groups:
            return False, "被投票的组不是活跃组"

        self.votes[self.current_round][voter_group] = target_group

        # 更新活跃时间
        self.update_activity(voter_group)

        return True, "投票成功"

    def process_voting_result(self) -> Dict:
        """
        处理投票结果，判定淘汰和游戏状态
        修改：增加详细投票信息
        """
        if self.game_status != GameStatus.VOTING:
            return {"error": "当前不在投票阶段"}

        # 检测未提交的组并自动记录异常
        missing_reports = self.detect_missing_submissions()

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
            "vote_details": vote_details,  # 新增：每个人的投票详情
            "max_voted_groups": max_voted_groups,
            "max_votes": max_votes,
            "eliminated": [],
            "game_ended": False,
            "winner": None,
            "message": "",  # 提示信息
            "undercover_group": None,  # 游戏结束时揭示卧底
            "undercover_word": "",  # 卧底词
            "civilian_word": "",  # 平民词
            "round_scores": {},  # 本轮得分
            "total_scores": self.scores.copy(),  # 总得分
            "active_groups": active_groups,  # 投票时的活跃组
            "voted_groups": list(round_votes.keys())  # 已投票的组
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
                result["undercover_group"] = self.undercover_group
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
                    result["undercover_group"] = self.undercover_group
                    result["undercover_word"] = self.undercover_word
                    result["civilian_word"] = self.civilian_word
                    self.game_status = GameStatus.GAME_END
                else:
                    # 继续下一轮（返回第3步）
                    result["message"] = f"👋 投票结果：{eliminated} 被投出，TA是平民。\n"
                    result["message"] += f"得票情况：{eliminated} 获得 {max_votes} 票\n"
                    result["message"] += f"游戏继续，进入第 {self.current_round + 1} 轮。"
                    self.current_round += 1
                    self.game_status = GameStatus.ROUND_END

        elif len(max_voted_groups) == 2:
            # 情况c：票数最多的组有2组，进入下一轮
            groups_str = ' 和 '.join(max_voted_groups)
            result["message"] = f"⚖️ 投票结果：{groups_str} 票数相同（各{max_votes}票），无人淘汰。\n"
            result["message"] += f"进入第 {self.current_round + 1} 轮。"

            # 计算本轮得分（平局情况）
            self._calculate_round_scores(result)

            self.current_round += 1
            self.game_status = GameStatus.ROUND_END

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
                result["undercover_group"] = self.undercover_group
                result["undercover_word"] = self.undercover_word
                result["civilian_word"] = self.civilian_word
                self.game_status = GameStatus.GAME_END
            else:
                # 包含卧底，进入下一轮
                result["message"] = f"投票结果：{', '.join(max_voted_groups)} 票数相同，包含卧底，进入下一轮。"

                # 计算本轮得分（平局情况）
                self._calculate_round_scores(result)

                self.current_round += 1
                self.game_status = GameStatus.ROUND_END

        # 清除倒计时
        self.phase_deadline = None
        self.speaker_deadline = None

        self.last_vote_result = result
        return result

    def _calculate_round_scores(self, result: Dict):
        """
        计算本轮得分并更新总得分
        """
        round_scores = {}

        # 得分规则：
        # 1. 存活到本轮结束：+1分
        # 2. 投出卧底（如果是平民）：+2分
        # 3. 卧底存活到最后：+3分
        # 4. 平民存活到最后：+1分

        active_groups = [g for g in self.groups.keys() if g not in self.eliminated_groups]
        eliminated_this_round = result.get('eliminated', [])

        for group_name in self.groups.keys():
            round_score = 0

            # 1. 存活到本轮结束：+1分
            if group_name not in eliminated_this_round:
                round_score += 1

            # 2. 如果本轮投出了卧底，给投票给卧底的平民加分
            if (result.get('winner') == 'civilian' and
                    group_name != self.undercover_group and
                    group_name in self.votes.get(self.current_round, {})):

                vote_target = self.votes[self.current_round][group_name]
                if vote_target == self.undercover_group:
                    round_score += 2  # 投出卧底奖励

            # 3. 卧底存活到最后奖励
            if (result.get('game_ended') and
                    result.get('winner') == 'undercover' and
                    group_name == self.undercover_group):
                round_score += 3

            # 4. 平民存活到最后奖励
            if (result.get('game_ended') and
                    result.get('winner') == 'civilian' and
                    group_name != self.undercover_group and
                    group_name not in self.eliminated_groups):
                round_score += 1

            round_scores[group_name] = round_score

            # 更新总得分
            if group_name in self.scores:
                self.scores[group_name] += round_score
            else:
                self.scores[group_name] = round_score

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

    def get_online_status(self) -> Dict[str, bool]:
        """检测各组是否在线（基于最后活跃时间）"""
        online_status = {}
        threshold = timedelta(seconds=60)  # 60秒未活跃视为离线

        for group_name in self.groups.keys():
            last_active = self.last_activity.get(group_name)
            if last_active:
                online_status[group_name] = (datetime.now() - last_active) < threshold
            else:
                online_status[group_name] = False

        return online_status

    def _has_existing_report(self, group_name: str, report_type: str, round_num: int) -> bool:
        """检查是否已经为指定组在当前轮次记录过相同类型的异常"""
        for report in self.reports:
            if (report.get('group') == group_name and
                    report.get('type') == report_type and
                    f'第{round_num}轮' in report.get('detail', '')):
                return True
        return False

    def detect_missing_submissions(self) -> List[Dict]:
        """检测未提交的组，自动记录异常（避免重复记录）"""
        missing_reports = []

        if self.game_status == GameStatus.DESCRIBING:
            # 只检查当前应该发言的组，而不是所有未提交的组
            current_speaker = self.get_current_speaker()
            if current_speaker:
                # 检查当前发言者是否已提交
                submitted_groups = [d["group"] for d in self.descriptions.get(self.current_round, [])]
                if current_speaker not in submitted_groups:
                    # 检查是否超时
                    if self.speaker_deadline and datetime.now() > self.speaker_deadline:
                        # 检查是否已经记录过这个异常，避免重复记录
                        if not self._has_existing_report(current_speaker, 'timeout', self.current_round):
                            # 自动记录异常
                            report = self.add_report(
                                current_speaker,
                                'timeout',
                                f'描述阶段超时未提交（第{self.current_round}轮，当前发言者：{current_speaker}）'
                            )
                            missing_reports.append(report)

        elif self.game_status == GameStatus.VOTING:
            # 检查是否有组未投票
            active_groups = [g for g in self.describe_order if g not in self.eliminated_groups]
            voted_groups = list(self.votes.get(self.current_round, {}).keys())

            for group in active_groups:
                if group not in voted_groups:
                    # 检查是否超时
                    if self.phase_deadline and datetime.now() > self.phase_deadline:
                        # 检查是否已经记录过这个异常，避免重复记录
                        if not self._has_existing_report(group, 'timeout', self.current_round):
                            report = self.add_report(
                                group,
                                'timeout',
                                f'投票阶段超时未提交（第{self.current_round}轮）'
                            )
                            missing_reports.append(report)

        return missing_reports

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
            "online_status": self.get_online_status()  # 各组在线状态
        }

    def get_public_status(self) -> Dict:
        """面向游戏方的公开状态"""
        active_groups = [g for g in self.groups.keys() if g not in self.eliminated_groups]

        # 计算阶段剩余时间（实时计算）
        remaining_seconds = None
        if self.phase_deadline:
            delta = self.phase_deadline - datetime.now()
            remaining_seconds = max(0, int(delta.total_seconds()))

        # 计算当前发言者剩余时间（实时计算）
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
            "game_ended": self.game_status == GameStatus.GAME_END
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
"""
游戏逻辑模块
负责游戏状态管理、投票判定、得分计算等核心逻辑
"""
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum


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
        self.descriptions: Dict[str, List[Dict]] = {}  # 每回合的描述 {round: [{group, desc, time}]}
        self.votes: Dict[int, Dict[str, str]] = {}  # 每回合的投票 {round: {voter: target}}
        self.eliminated_groups: List[str] = []  # 已淘汰的组
        self.scores: Dict[str, int] = {}  # 得分 {group: score}
        
    def register_group(self, group_name: str) -> bool:
        """
        注册游戏组
        :param group_name: 组名
        :return: 是否注册成功
        """
        if group_name in self.groups:
            return False
        if len(self.groups) >= 4:
            return False
        
        self.groups[group_name] = {
            "name": group_name,
            "role": None,  # "undercover" 或 "civilian"
            "word": "",
            "registered_time": datetime.now().isoformat()
        }
        
        if len(self.groups) > 0:
            self.game_status = GameStatus.REGISTERED
        
        return True
    
    def start_game(self, undercover_word: str, civilian_word: str) -> bool:
        """
        开始游戏，分配身份和词语
        :param undercover_word: 卧底词
        :param civilian_word: 平民词
        :return: 是否成功开始
        """
        if len(self.groups) < 1:
            return False
        if self.game_status != GameStatus.REGISTERED:
            return False
        
        self.undercover_word = undercover_word
        self.civilian_word = civilian_word
        
        # 随机选择卧底
        group_names = list(self.groups.keys())
        self.undercover_group = random.choice(group_names)
        
        # 分配身份和词语
        for group_name in group_names:
            if group_name == self.undercover_group:
                self.groups[group_name]["role"] = "undercover"
                self.groups[group_name]["word"] = undercover_word
            else:
                self.groups[group_name]["role"] = "civilian"
                self.groups[group_name]["word"] = civilian_word
        
        self.current_round = 1
        self.game_status = GameStatus.WORD_ASSIGNED
        return True
    
    def start_round(self) -> List[str]:
        """
        开始新回合，随机排序
        :return: 描述顺序列表
        """
        if self.game_status not in [GameStatus.WORD_ASSIGNED, GameStatus.ROUND_END]:
            return []
        
        # 获取未淘汰的组
        active_groups = [g for g in self.groups.keys() if g not in self.eliminated_groups]
        if len(active_groups) < 2:
            return []
        
        # 随机排序
        self.describe_order = active_groups.copy()
        random.shuffle(self.describe_order)
        
        # 初始化本回合的描述和投票
        self.descriptions[self.current_round] = []
        self.votes[self.current_round] = {}
        
        self.game_status = GameStatus.DESCRIBING
        return self.describe_order
    
    def submit_description(self, group_name: str, description: str) -> bool:
        """
        提交描述
        :param group_name: 组名
        :param description: 描述内容
        :return: 是否成功
        """
        if self.game_status != GameStatus.DESCRIBING:
            return False
        if group_name not in self.describe_order:
            return False
        if group_name in self.eliminated_groups:
            return False
        
        # 检查是否已经提交过
        for desc in self.descriptions[self.current_round]:
            if desc["group"] == group_name:
                return False
        
        self.descriptions[self.current_round].append({
            "group": group_name,
            "description": description,
            "time": datetime.now().isoformat()
        })
        
        # 检查是否所有人都提交了
        active_groups = [g for g in self.describe_order if g not in self.eliminated_groups]
        if len(self.descriptions[self.current_round]) >= len(active_groups):
            self.game_status = GameStatus.VOTING
        
        return True
    
    def submit_vote(self, voter_group: str, target_group: str) -> bool:
        """
        提交投票
        :param voter_group: 投票者组名
        :param target_group: 被投票者组名
        :return: 是否成功
        """
        if self.game_status != GameStatus.VOTING:
            return False
        if voter_group in self.eliminated_groups:
            return False
        if target_group in self.eliminated_groups:
            return False
        if voter_group not in self.groups:
            return False
        if target_group not in self.groups:
            return False
        if voter_group == target_group:  # 不能投自己
            return False
        
        self.votes[self.current_round][voter_group] = target_group
        return True
    
    def process_voting_result(self) -> Dict:
        """
        处理投票结果，判定淘汰和游戏状态
        :return: 投票结果信息
        """
        if self.game_status != GameStatus.VOTING:
            return {"error": "当前不在投票阶段"}
        
        round_votes = self.votes[self.current_round]
        active_groups = [g for g in self.describe_order if g not in self.eliminated_groups]
        
        # 检查是否所有人都投票了
        if len(round_votes) < len(active_groups):
            return {"error": "还有组未投票"}
        
        # 统计票数
        vote_count: Dict[str, int] = {}
        for target in round_votes.values():
            vote_count[target] = vote_count.get(target, 0) + 1
        
        # 找出得票最多的组
        max_votes = max(vote_count.values()) if vote_count else 0
        max_voted_groups = [g for g, v in vote_count.items() if v == max_votes]
        
        result = {
            "round": self.current_round,
            "vote_count": vote_count,
            "max_voted_groups": max_voted_groups,
            "max_votes": max_votes,
            "eliminated": [],
            "game_ended": False,
            "winner": None
        }
        
        # 判定结果
        if len(max_voted_groups) == 1:
            # 情况a：票数最多的有1组
            eliminated = max_voted_groups[0]
            self.eliminated_groups.append(eliminated)
            result["eliminated"] = [eliminated]
            
            if eliminated == self.undercover_group:
                # 卧底被淘汰，游戏结束
                result["game_ended"] = True
                result["winner"] = "civilian"
                self.game_status = GameStatus.GAME_END
                self._calculate_scores()
            else:
                # 平民被淘汰，继续游戏
                remaining_civilians = [g for g in self.groups.keys() 
                                     if g not in self.eliminated_groups and g != self.undercover_group]
                if len(remaining_civilians) == 0:
                    # 平民全部淘汰，游戏结束
                    result["game_ended"] = True
                    result["winner"] = "undercover"
                    self.game_status = GameStatus.GAME_END
                    self._calculate_scores()
                else:
                    # 继续下一轮
                    self.current_round += 1
                    self.game_status = GameStatus.ROUND_END
                    
        elif len(max_voted_groups) == 2:
            # 情况b：得票最多有2组
            both_civilians = all(g != self.undercover_group for g in max_voted_groups)
            if both_civilians:
                # 都是平民，都淘汰，游戏结束
                self.eliminated_groups.extend(max_voted_groups)
                result["eliminated"] = max_voted_groups
                result["game_ended"] = True
                result["winner"] = "undercover"
                self.game_status = GameStatus.GAME_END
                self._calculate_scores()
            else:
                # 包含卧底，进入下一轮
                self.current_round += 1
                self.game_status = GameStatus.ROUND_END
        else:
            # 情况c：票数最多的组超过2组，进入下一轮
            self.current_round += 1
            self.game_status = GameStatus.ROUND_END
        
        return result
    
    def _calculate_scores(self):
        """计算得分"""
        if not self.undercover_group:
            return
        
        # 计算生存分（每生存一轮得1分）
        survival_score = self.current_round
        
        # 计算胜利分
        remaining_civilians = [g for g in self.groups.keys() 
                             if g not in self.eliminated_groups and g != self.undercover_group]
        victory_score = 3 if len(remaining_civilians) == 1 else 0
        
        # 得分为胜利分与生存分的大者
        self.scores[self.undercover_group] = max(survival_score, victory_score)
        
        # 平民组得分为0（根据题目描述）
        for group_name in self.groups.keys():
            if group_name != self.undercover_group:
                self.scores[group_name] = 0
    
    def get_game_state(self) -> Dict:
        """获取当前游戏状态"""
        return {
            "status": self.game_status.value,
            "groups": {name: {
                "name": info["name"],
                "role": info["role"],
                "eliminated": name in self.eliminated_groups
            } for name, info in self.groups.items()},
            "undercover_group": self.undercover_group if self.game_status != GameStatus.WAITING else None,
            "current_round": self.current_round,
            "describe_order": self.describe_order,
            "eliminated_groups": self.eliminated_groups,
            "scores": self.scores,
            "descriptions": self.descriptions,
            "votes": self.votes
        }
    
    def get_group_word(self, group_name: str) -> Optional[str]:
        """获取指定组的词语（仅在该组查询时返回）"""
        if group_name not in self.groups:
            return None
        return self.groups[group_name].get("word")
    
    def reset_game(self):
        """重置游戏"""
        self.groups.clear()
        self.game_status = GameStatus.WAITING
        self.undercover_group = None
        self.undercover_word = ""
        self.civilian_word = ""
        self.current_round = 0
        self.describe_order = []
        self.descriptions.clear()
        self.votes.clear()
        self.eliminated_groups = []
        self.scores.clear()


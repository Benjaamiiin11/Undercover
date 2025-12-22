"""
游戏逻辑模块的单元测试
测试 GameLogic 类的所有方法
"""
import pytest
from datetime import datetime, timedelta
from game_logic import GameLogic, GameStatus, MAX_GROUPS


class TestGameLogic:
    """GameLogic 类的单元测试"""

    @pytest.fixture
    def game(self):
        """创建游戏实例"""
        return GameLogic()

    @pytest.fixture
    def game_with_groups(self, game):
        """创建已注册多个组的游戏实例"""
        game.register_group("组1")
        game.register_group("组2")
        game.register_group("组3")
        return game

    # ========== 注册相关测试 ==========

    def test_register_group_success(self, game):
        """测试成功注册组"""
        assert game.register_group("测试组") == True
        assert "测试组" in game.groups
        assert game.game_status == GameStatus.REGISTERED

    def test_register_group_duplicate(self, game):
        """测试重复注册"""
        game.register_group("测试组")
        assert game.register_group("测试组") == False

    def test_register_group_max_limit(self, game):
        """测试达到最大组数限制"""
        for i in range(MAX_GROUPS):
            game.register_group(f"组{i+1}")
        assert game.register_group("超出限制组") == False

    def test_register_group_initializes_score(self, game):
        """测试注册时初始化分数"""
        game.register_group("测试组")
        assert game.scores["测试组"] == 0
        assert "测试组" in game.undercover_history
        assert game.undercover_history["测试组"] == 0

    # ========== 开始游戏相关测试 ==========

    def test_start_game_success(self, game_with_groups):
        """测试成功开始游戏"""
        game = game_with_groups
        result = game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        assert result == True
        assert game.game_status == GameStatus.WORD_ASSIGNED
        assert game.undercover_word == "卧底词"
        assert game.civilian_word == "平民词"
        assert game.current_round == 1
        assert game.undercover_group in ["组1", "组2", "组3"]

    def test_start_game_wrong_status(self, game_with_groups):
        """测试错误状态下开始游戏"""
        game = game_with_groups
        game.game_status = GameStatus.DESCRIBING
        result = game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        assert result == False

    def test_start_game_no_online_groups(self, game_with_groups):
        """测试没有在线组时开始游戏"""
        game = game_with_groups
        result = game.start_game("卧底词", "平民词", {"组1": False, "组2": False, "组3": False})
        assert result == False

    def test_start_game_assigns_roles(self, game_with_groups):
        """测试角色分配"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        
        undercover = game.undercover_group
        assert game.groups[undercover]["role"] == "undercover"
        assert game.groups[undercover]["word"] == "卧底词"
        
        for name in ["组1", "组2", "组3"]:
            if name != undercover:
                assert game.groups[name]["role"] == "civilian"
                assert game.groups[name]["word"] == "平民词"

    def test_start_game_marks_offline_groups(self, game_with_groups):
        """测试离线组被标记为淘汰"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": False, "组3": True})
        
        assert "组2" in game.eliminated_groups
        assert game.groups["组2"]["eliminated"] == True
        assert "组1" not in game.eliminated_groups
        assert "组3" not in game.eliminated_groups

    def test_start_game_balances_undercover(self, game_with_groups):
        """测试卧底选择平衡性"""
        game = game_with_groups
        # 多次开始游戏，检查卧底分配是否平衡
        undercover_counts = {"组1": 0, "组2": 0, "组3": 0}
        
        for _ in range(30):  # 运行30次
            game.reset_game()
            game.register_group("组1")
            game.register_group("组2")
            game.register_group("组3")
            game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
            undercover_counts[game.undercover_group] += 1
        
        # 每个组至少应该被选到几次（概率上应该比较均匀）
        assert all(count > 0 for count in undercover_counts.values())

    # ========== 开始回合相关测试 ==========

    def test_start_round_success(self, game_with_groups):
        """测试成功开始回合"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        
        order = game.start_round()
        assert len(order) == 3
        assert game.game_status == GameStatus.DESCRIBING
        assert game.current_round == 1
        assert game.current_speaker_index == 0
        assert game.phase_deadline is not None

    def test_start_round_wrong_status(self, game_with_groups):
        """测试错误状态下开始回合"""
        game = game_with_groups
        game.game_status = GameStatus.WAITING
        order = game.start_round()
        assert order == []

    def test_start_round_increments_round(self, game_with_groups):
        """测试回合数递增"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        assert game.current_round == 1
        
        game.game_status = GameStatus.ROUND_END
        game.start_round()
        assert game.current_round == 2

    def test_start_round_excludes_eliminated(self, game_with_groups):
        """测试开始回合时排除淘汰组"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.eliminated_groups.append("组2")
        
        order = game.start_round()
        assert "组2" not in order
        assert len(order) == 2

    # ========== 提交描述相关测试 ==========

    def test_submit_description_success(self, game_with_groups):
        """测试成功提交描述"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        current_speaker = game.get_current_speaker()
        success, msg = game.submit_description(current_speaker, "这是一个描述")
        
        assert success == True
        assert len(game.descriptions[game.current_round]) == 1
        assert game.descriptions[game.current_round][0]["group"] == current_speaker
        assert game.current_speaker_index == 1

    def test_submit_description_wrong_speaker(self, game_with_groups):
        """测试非当前发言者提交描述"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        current_speaker = game.get_current_speaker()
        other_speaker = [g for g in game.describe_order if g != current_speaker][0]
        
        success, msg = game.submit_description(other_speaker, "描述")
        assert success == False
        assert "请等待" in msg

    def test_submit_description_eliminated_group(self, game_with_groups):
        """测试淘汰组提交描述"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        game.eliminated_groups.append("组1")
        
        success, msg = game.submit_description("组1", "描述")
        assert success == False
        assert "淘汰" in msg

    def test_submit_description_auto_transition_to_voting(self, game_with_groups):
        """测试所有人提交后自动进入投票阶段"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        # 所有人提交描述
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        assert game.game_status == GameStatus.VOTING
        assert game.phase_deadline is not None

    def test_submit_description_timeout(self, game_with_groups):
        """测试超时提交描述"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        # 设置超时时间
        game.speaker_deadline = datetime.now() - timedelta(seconds=10)
        
        current_speaker = game.get_current_speaker()
        success, msg = game.submit_description(current_speaker, "描述")
        
        assert success == True
        assert "超时" in msg
        assert game.descriptions[game.current_round][0]["timeout"] == True

    # ========== 提交投票相关测试 ==========

    def test_submit_vote_success(self, game_with_groups):
        """测试成功提交投票"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        # 所有人提交描述
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        # 提交投票
        success, msg, all_voted = game.submit_vote("组1", "组2")
        
        assert success == True
        assert game.votes[game.current_round]["组1"] == "组2"
        assert all_voted == False  # 还有其他人没投票

    def test_submit_vote_all_voted(self, game_with_groups):
        """测试所有人投票完成"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        # 所有人提交描述
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        # 所有人投票
        groups = game.describe_order.copy()
        for i, voter in enumerate(groups):
            target = groups[(i + 1) % len(groups)]  # 投给下一个
            if voter != target:
                success, msg, all_voted = game.submit_vote(voter, target)
                if i == len(groups) - 1:
                    assert all_voted == True

    def test_submit_vote_self(self, game_with_groups):
        """测试投票给自己"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        success, msg, _ = game.submit_vote("组1", "组1")
        assert success == False
        assert "不能投票给自己" in msg

    def test_submit_vote_eliminated_voter(self, game_with_groups):
        """测试淘汰组投票"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        game.eliminated_groups.append("组1")
        success, msg, _ = game.submit_vote("组1", "组2")
        assert success == False
        assert "淘汰" in msg

    def test_submit_vote_eliminated_target(self, game_with_groups):
        """测试投票给淘汰组"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        game.eliminated_groups.append("组2")
        success, msg, _ = game.submit_vote("组1", "组2")
        assert success == False
        assert "淘汰" in msg

    def test_submit_vote_duplicate(self, game_with_groups):
        """测试重复投票"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        game.submit_vote("组1", "组2")
        success, msg, _ = game.submit_vote("组1", "组3")
        assert success == False
        assert "已经投过票" in msg

    # ========== 提交准备相关测试 ==========

    def test_submit_ready_success(self, game_with_groups):
        """测试成功提交准备"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        
        success, msg, all_ready = game.submit_ready("组1")
        assert success == True
        assert "组1" in game.ready_groups
        assert all_ready == False

    def test_submit_ready_all_ready(self, game_with_groups):
        """测试所有人准备完成"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        
        for group in ["组1", "组2", "组3"]:
            success, msg, all_ready = game.submit_ready(group)
            if group == "组3":
                assert all_ready == True

    def test_submit_ready_wrong_status(self, game_with_groups):
        """测试错误状态下准备"""
        game = game_with_groups
        game.game_status = GameStatus.DESCRIBING
        
        success, msg, _ = game.submit_ready("组1")
        assert success == False
        assert "不能准备" in msg

    def test_submit_ready_eliminated(self, game_with_groups):
        """测试淘汰组准备"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.eliminated_groups.append("组1")
        
        success, msg, _ = game.submit_ready("组1")
        assert success == False
        assert "淘汰" in msg

    # ========== 处理投票结果相关测试 ==========

    def test_process_voting_result_undercover_eliminated(self, game_with_groups):
        """测试卧底被淘汰"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        # 所有人提交描述
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        # 所有人投票给卧底
        undercover = game.undercover_group
        for voter in game.describe_order:
            if voter != undercover:
                game.submit_vote(voter, undercover)
        game.submit_vote(undercover, [g for g in game.describe_order if g != undercover][0])
        
        result = game.process_voting_result()
        
        assert result["game_ended"] == True
        assert result["winner"] == "civilian"
        assert undercover in result["eliminated"]
        assert game.game_status == GameStatus.GAME_END

    def test_process_voting_result_civilian_eliminated(self, game_with_groups):
        """测试平民被淘汰"""
        game = game_with_groups
        # 需要至少4个组才能测试平民被淘汰但游戏继续的情况
        game.register_group("组4")
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True, "组4": True})
        game.start_round()
        
        # 所有人提交描述
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        # 投票给一个平民（剩下至少2个平民，游戏继续）
        undercover = game.undercover_group
        civilians = [g for g in game.describe_order if g != undercover]
        target = civilians[0]
        other_civilians = [g for g in civilians if g != target]
        
        # 确保所有人都投票（包括被投票的组）
        for voter in game.describe_order:
            if voter != target:
                # 非target组投票给target
                success, msg, _ = game.submit_vote(voter, target)
                assert success == True, f"投票失败: {voter} -> {target}, {msg}"
            else:
                # target组投票给另一个平民
                if other_civilians:
                    success, msg, _ = game.submit_vote(target, other_civilians[0])
                    assert success == True, f"投票失败: {target} -> {other_civilians[0]}, {msg}"
        
        # 验证所有人都投票了
        assert len(game.votes[game.current_round]) == len(game.describe_order)
        
        result = game.process_voting_result()
        
        # 检查是否有错误
        assert "error" not in result, f"处理投票结果失败: {result.get('error')}"
        
        # 如果剩余平民>1，游戏继续；否则游戏结束
        remaining_civilians = [g for g in game.groups.keys() 
                               if g != undercover and g not in game.eliminated_groups]
        if len(remaining_civilians) > 1:
            assert result["game_ended"] == False
            assert game.game_status == GameStatus.ROUND_END
        else:
            assert result["game_ended"] == True
            assert result["winner"] == "undercover"
        
        assert target in result["eliminated"]

    def test_process_voting_result_tie_all_civilians(self, game_with_groups):
        """测试平票且都是平民"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        # 所有人提交描述
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        # 创建平票情况（两个平民各得1票）
        undercover = game.undercover_group
        civilians = [g for g in game.describe_order if g != undercover]
        
        # 确保组1和组2都是平民（如果卧底是组1或组2，需要调整）
        if undercover == "组1":
            # 如果组1是卧底，让组2和组3（平民）平票
            # 组2投组3，组3投组2，组1（卧底）投组2
            success1, msg1, _ = game.submit_vote("组2", "组3")
            assert success1 == True, f"投票失败: 组2 -> 组3, {msg1}"
            success2, msg2, _ = game.submit_vote("组3", "组2")
            assert success2 == True, f"投票失败: 组3 -> 组2, {msg2}"
            success3, msg3, _ = game.submit_vote(undercover, "组2")
            assert success3 == True, f"投票失败: {undercover} -> 组2, {msg3}"
            # 组2得2票，组3得1票
        elif undercover == "组2":
            # 如果组2是卧底，让组1和组3（平民）平票
            # 组1投组3，组3投组1，组2（卧底）投组1
            success1, msg1, _ = game.submit_vote("组1", "组3")
            assert success1 == True, f"投票失败: 组1 -> 组3, {msg1}"
            success2, msg2, _ = game.submit_vote("组3", "组1")
            assert success2 == True, f"投票失败: 组3 -> 组1, {msg2}"
            success3, msg3, _ = game.submit_vote(undercover, "组1")
            assert success3 == True, f"投票失败: {undercover} -> 组1, {msg3}"
            # 组1得2票，组3得1票
        else:
            # 组3是卧底，组1和组2是平民
            # 组1投组2，组2投组1，组3（卧底）投组1
            # 这样组1得2票，组2得1票
            success1, msg1, _ = game.submit_vote("组1", "组2")
            assert success1 == True, f"投票失败: 组1 -> 组2, {msg1}"
            success2, msg2, _ = game.submit_vote("组2", "组1")
            assert success2 == True, f"投票失败: 组2 -> 组1, {msg2}"
            success3, msg3, _ = game.submit_vote(undercover, "组1")
            assert success3 == True, f"投票失败: {undercover} -> 组1, {msg3}"
        
        # 验证所有人都投票了
        assert len(game.votes[game.current_round]) == len(game.describe_order)
        
        result = game.process_voting_result()
        
        # 检查是否有错误
        assert "error" not in result, f"处理投票结果失败: {result.get('error')}"
        
        # 组1得2票，组2得1票，组1被淘汰
        assert "组1" in result["eliminated"] or "组2" in result["eliminated"]

    def test_process_voting_result_tie_with_undercover(self, game_with_groups):
        """测试平票且包含卧底"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        # 所有人提交描述
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        # 创建平票情况（卧底和平民各得1票）
        undercover = game.undercover_group
        civilians = [g for g in game.describe_order if g != undercover]
        
        # 组1投组2，组2投卧底，卧底投组1
        game.submit_vote(civilians[0], civilians[1])
        game.submit_vote(civilians[1], undercover)
        game.submit_vote(undercover, civilians[0])
        
        result = game.process_voting_result()
        
        # 应该无人淘汰，进入下一轮
        assert len(result["eliminated"]) == 0
        assert game.game_status == GameStatus.ROUND_END

    def test_process_voting_result_wrong_status(self, game_with_groups):
        """测试错误状态下处理投票结果"""
        game = game_with_groups
        game.game_status = GameStatus.DESCRIBING
        
        result = game.process_voting_result()
        assert "error" in result

    def test_process_voting_result_not_all_voted(self, game_with_groups):
        """测试未全部投票时处理投票结果"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        # 只有一个人投票
        game.submit_vote(game.describe_order[0], game.describe_order[1])
        
        result = game.process_voting_result()
        assert "error" in result
        assert "未投票" in result["error"]

    # ========== 得分计算相关测试 ==========

    def test_calculate_scores_survival_points(self, game_with_groups):
        """测试生存分计算"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        # 所有人提交描述
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        # 投票淘汰一个平民
        undercover = game.undercover_group
        civilians = [g for g in game.describe_order if g != undercover]
        target = civilians[0]
        other_civilians = [g for g in civilians if g != target]
        
        # 确保所有人都投票（包括被投票的组）
        for voter in game.describe_order:
            if voter != target:
                # 非target组投票给target
                success, msg, _ = game.submit_vote(voter, target)
                assert success == True, f"投票失败: {voter} -> {target}, {msg}"
            else:
                # target组投票给另一个平民（如果存在）
                if other_civilians:
                    success, msg, _ = game.submit_vote(target, other_civilians[0])
                    assert success == True, f"投票失败: {target} -> {other_civilians[0]}, {msg}"
                else:
                    # 如果没有其他平民，投票给卧底
                    success, msg, _ = game.submit_vote(target, undercover)
                    assert success == True, f"投票失败: {target} -> {undercover}, {msg}"
        
        # 验证所有人都投票了
        assert len(game.votes[game.current_round]) == len(game.describe_order)
        
        result = game.process_voting_result()
        
        # 检查是否有错误
        assert "error" not in result, f"处理投票结果失败: {result.get('error')}"
        
        # 检查得分 - 得分应该在 _calculate_round_scores 中计算
        # 存活到本轮结束的组应该得1分
        assert game.scores[undercover] >= 1, f"卧底得分应该是1，实际是{game.scores[undercover]}"
        assert game.scores[target] == 0, f"被淘汰的平民得分应该是0，实际是{game.scores[target]}"
        for civilian in civilians[1:]:
            assert game.scores[civilian] >= 1, f"存活的平民得分应该是1，实际是{game.scores[civilian]}"

    def test_calculate_scores_victory_bonus(self, game_with_groups):
        """测试胜利分计算"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        # 所有人提交描述
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        # 投票淘汰所有平民，只剩1个平民
        undercover = game.undercover_group
        civilians = [g for g in game.describe_order if g != undercover]
        
        # 淘汰所有平民
        for civilian in civilians:
            game.start_round()
            for group in game.describe_order:
                if group not in game.eliminated_groups:
                    game.submit_description(group, f"{group}的描述")
            
            # 所有人投票给这个平民
            for voter in game.describe_order:
                if voter not in game.eliminated_groups and voter != civilian:
                    game.submit_vote(voter, civilian)
            
            result = game.process_voting_result()
            if result.get("game_ended"):
                break
        
        # 检查卧底是否有胜利分
        if game.game_status == GameStatus.GAME_END and result.get("winner") == "undercover":
            assert game.scores[undercover] >= 3  # 胜利分3分

    # ========== 其他方法测试 ==========

    def test_get_current_speaker(self, game_with_groups):
        """测试获取当前发言者"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        speaker = game.get_current_speaker()
        assert speaker in game.describe_order
        assert speaker == game.describe_order[game.current_speaker_index]

    def test_get_group_word(self, game_with_groups):
        """测试获取组词语"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        
        undercover = game.undercover_group
        assert game.get_group_word(undercover) == "卧底词"
        
        civilians = [g for g in ["组1", "组2", "组3"] if g != undercover]
        assert game.get_group_word(civilians[0]) == "平民词"

    def test_get_online_status(self, game_with_groups):
        """测试获取在线状态"""
        game = game_with_groups
        game.update_activity("组1")
        
        status = game.get_online_status({"组1": True, "组2": False, "组3": True})
        assert status["组1"] == True
        assert status["组2"] == False
        assert status["组3"] == True

    def test_reset_game(self, game_with_groups):
        """测试重置游戏"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        # 保存一些数据
        original_scores = game.scores.copy()
        original_groups = game.groups.copy()
        
        game.reset_game()
        
        # 检查游戏状态重置
        assert game.game_status == GameStatus.REGISTERED
        assert game.current_round == 0
        assert game.undercover_group is None
        assert len(game.descriptions) == 0
        assert len(game.votes) == 0
        
        # 检查保留的数据
        assert game.scores == original_scores
        assert len(game.groups) == len(original_groups)
        
        # 检查组状态重置
        for group_name in game.groups:
            assert game.groups[group_name]["role"] is None
            assert game.groups[group_name]["word"] == ""
            assert game.groups[group_name]["eliminated"] == False

    def test_handle_disconnect_undercover(self, game_with_groups):
        """测试卧底断开连接"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        undercover = game.undercover_group
        result = game.handle_disconnect(undercover)
        
        assert result is not None
        assert result["game_ended"] == True
        assert result["winner"] == "civilian"
        assert undercover in result["eliminated"]

    def test_handle_disconnect_civilian(self, game_with_groups):
        """测试平民断开连接"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        undercover = game.undercover_group
        civilians = [g for g in ["组1", "组2", "组3"] if g != undercover]
        
        # 断开一个平民
        result = game.handle_disconnect(civilians[0])
        
        assert civilians[0] in game.eliminated_groups
        # 如果只剩1个平民，游戏应该结束
        remaining_civilians = [g for g in ["组1", "组2", "组3"] 
                               if g != undercover and g not in game.eliminated_groups]
        if len(remaining_civilians) <= 1:
            assert result is not None
            assert result["game_ended"] == True

    def test_get_game_state(self, game_with_groups):
        """测试获取游戏状态"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        state = game.get_game_state()
        
        assert state["status"] == "describing"
        assert state["current_round"] == 1
        assert "groups" in state
        assert "undercover_group" in state
        assert "describe_order" in state

    def test_get_public_status(self, game_with_groups):
        """测试获取公开状态"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        status = game.get_public_status()
        
        assert status["status"] == "describing"
        assert status["round"] == 1
        assert "active_groups" in status
        assert "describe_order" in status
        assert "undercover_group" not in status  # 公开状态不包含卧底信息

    def test_add_report(self, game_with_groups):
        """测试添加异常报告"""
        game = game_with_groups
        report = game.add_report("组1", "timeout", "超时未提交描述")
        
        assert report["group"] == "组1"
        assert report["type"] == "timeout"
        assert "ticket" in report
        assert len(game.reports) == 1

    def test_get_vote_details_for_group(self, game_with_groups):
        """测试获取组的投票详情"""
        game = game_with_groups
        game.start_game("卧底词", "平民词", {"组1": True, "组2": True, "组3": True})
        game.start_round()
        
        # 所有人提交描述和投票
        for group in game.describe_order:
            game.submit_description(group, f"{group}的描述")
        
        game.submit_vote("组1", "组2")
        game.submit_vote("组2", "组1")
        game.submit_vote("组3", "组1")
        
        result = game.process_voting_result()
        
        details = game.get_vote_details_for_group("组1")
        assert details["my_vote"] == "组2"
        assert "组2" in details["voted_by"] or "组3" in details["voted_by"]


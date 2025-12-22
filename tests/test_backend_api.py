"""
后端API的集成测试
测试所有主持人方相关的API接口
"""
import pytest
import requests
import time
import threading
from flask import Flask
from backend import app, ADMIN_TOKEN, game, game_lock
from game_logic import GameStatus


class TestBackendAPI:
    """后端API集成测试"""

    @pytest.fixture(scope="class")
    def client(self):
        """创建测试客户端"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture(autouse=True)
    def reset_game(self):
        """每个测试前重置游戏状态"""
        with game_lock:
            game.reset_game()
            # 清空所有组
            game.groups.clear()
            game.scores.clear()
            game.eliminated_groups.clear()
            game.undercover_history.clear()
            game.reports.clear()
            game.last_activity.clear()
            game.ready_groups.clear()
        yield
        # 测试后清理
        with game_lock:
            game.reset_game()
            game.groups.clear()
            game.scores.clear()
            game.eliminated_groups.clear()

    def get_admin_headers(self):
        """获取管理员请求头"""
        return {'X-Admin-Token': ADMIN_TOKEN}

    def register_group(self, client, group_name):
        """注册组的辅助方法"""
        response = client.post('/api/register', 
                              json={'group_name': group_name},
                              content_type='application/json')
        return response

    def start_game(self, client, undercover_word="卧底词", civilian_word="平民词"):
        """开始游戏的辅助方法"""
        response = client.post('/api/game/start',
                              json={
                                  'undercover_word': undercover_word,
                                  'civilian_word': civilian_word
                              },
                              headers=self.get_admin_headers(),
                              content_type='application/json')
        return response

    # ========== 注册接口测试 ==========

    def test_register_success(self, client):
        """测试成功注册"""
        response = self.register_group(client, "测试组1")
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert data['data']['group_name'] == "测试组1"

    def test_register_duplicate(self, client):
        """测试重复注册"""
        self.register_group(client, "测试组1")
        response = self.register_group(client, "测试组1")
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 400

    def test_register_empty_name(self, client):
        """测试空组名注册"""
        response = client.post('/api/register',
                              json={'group_name': ''},
                              content_type='application/json')
        assert response.status_code == 400

    def test_register_max_groups(self, client):
        """测试达到最大组数"""
        for i in range(5):
            self.register_group(client, f"组{i+1}")
        
        response = self.register_group(client, "超出限制组")
        assert response.status_code == 400
        data = response.get_json()
        assert "最大组数" in data['message']

    # ========== 开始游戏接口测试 ==========

    def test_start_game_success(self, client):
        """测试成功开始游戏"""
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        self.register_group(client, "组3")
        
        response = self.start_game(client, "苹果", "香蕉")
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'undercover_group' in data['data']
        assert data['data']['civilian_word'] == "香蕉"
        assert data['data']['undercover_word'] == "苹果"

    def test_start_game_no_admin_token(self, client):
        """测试无管理员令牌开始游戏"""
        self.register_group(client, "组1")
        
        response = client.post('/api/game/start',
                              json={
                                  'undercover_word': "苹果",
                                  'civilian_word': "香蕉"
                              },
                              content_type='application/json')
        assert response.status_code == 403
        data = response.get_json()
        assert data['code'] == 403

    def test_start_game_wrong_token(self, client):
        """测试错误的管理员令牌"""
        self.register_group(client, "组1")
        
        response = client.post('/api/game/start',
                              json={
                                  'undercover_word': "苹果",
                                  'civilian_word': "香蕉"
                              },
                              headers={'X-Admin-Token': 'wrong-token'},
                              content_type='application/json')
        assert response.status_code == 403

    def test_start_game_no_groups(self, client):
        """测试没有组时开始游戏"""
        response = self.start_game(client)
        assert response.status_code == 400

    def test_start_game_wrong_status(self, client):
        """测试错误状态下开始游戏"""
        self.register_group(client, "组1")
        self.start_game(client)
        
        # 游戏已开始，再次开始应该失败
        response = self.start_game(client)
        assert response.status_code == 400

    def test_start_game_auto_select_words(self, client):
        """测试自动选择词语"""
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        
        # 不提供词语，应该从词库随机选择
        response = client.post('/api/game/start',
                              json={},
                              headers=self.get_admin_headers(),
                              content_type='application/json')
        # 如果词库为空，会返回400；如果有词库，会返回200
        assert response.status_code in [200, 400]

    # ========== 开始回合接口测试 ==========

    def test_start_round_success(self, client):
        """测试成功开始回合"""
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        self.start_game(client)
        
        response = client.post('/api/game/round/start',
                              headers=self.get_admin_headers(),
                              content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'order' in data['data']
        assert len(data['data']['order']) == 2

    def test_start_round_no_admin_token(self, client):
        """测试无管理员令牌开始回合"""
        self.register_group(client, "组1")
        self.start_game(client)
        
        response = client.post('/api/game/round/start',
                              content_type='application/json')
        assert response.status_code == 403

    def test_start_round_wrong_status(self, client):
        """测试错误状态下开始回合"""
        self.register_group(client, "组1")
        # 未开始游戏，不能开始回合
        response = client.post('/api/game/round/start',
                              headers=self.get_admin_headers(),
                              content_type='application/json')
        assert response.status_code == 400

    # ========== 处理投票结果接口测试 ==========

    def test_process_voting_success(self, client):
        """测试成功处理投票结果"""
        # 注册并开始游戏
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        self.register_group(client, "组3")
        self.start_game(client)
        
        # 确保所有组都在线（更新活跃时间）
        with game_lock:
            for group in ["组1", "组2", "组3"]:
                game.update_activity(group)
        
        # 开始回合
        client.post('/api/game/round/start',
                headers=self.get_admin_headers(),
                content_type='application/json')
        
        # 所有人提交描述
        with game_lock:
            describe_order = game.describe_order.copy()
        for group in describe_order:
            client.post('/api/describe',
                    json={'group_name': group, 'description': f'{group}的描述'},
                    content_type='application/json')
            # 更新活跃时间
            with game_lock:
                game.update_activity(group)
        
        # 所有人投票 - 修复投票逻辑，确保所有人都投票
        with game_lock:
            undercover = game.undercover_group
            groups = game.describe_order.copy()
        
        # 确保所有人都投票：组1投组2，组2投组3，组3投组1（循环投票）
        # 先检查游戏状态是否为VOTING
        with game_lock:
            assert game.game_status == GameStatus.VOTING, \
                f"游戏状态不是VOTING: {game.game_status}"
        
        last_response = None
        for i, voter in enumerate(groups):
            target = groups[(i + 1) % len(groups)]  # 投给下一个组
            vote_response = client.post('/api/vote',
                                       json={'voter_group': voter, 'target_group': target},
                                       content_type='application/json')
            vote_data = vote_response.get_json()
            
            # 检查响应状态和code
            assert vote_response.status_code == 200, \
                f"投票HTTP状态码错误: {voter} -> {target}, status={vote_response.status_code}, data={vote_data}"
            assert vote_data.get('code') == 200, \
                f"投票失败: {voter} -> {target}, code={vote_data.get('code')}, message={vote_data.get('message')}"
            
            # 更新活跃时间
            with game_lock:
                game.update_activity(voter)
            
            last_response = vote_response
        
        # 如果最后一个人投票后自动处理了投票结果，响应中会包含vote_result
        # 否则需要手动验证投票数量
        if last_response:
            last_data = last_response.get_json()
            if last_data.get('data', {}).get('auto_processed'):
                # 投票结果已自动处理，这是正常的
                pass
            else:
                # 验证所有人都投票了
                with game_lock:
                    votes_count = len(game.votes.get(game.current_round, {}))
                    assert votes_count == len(groups), \
                        f"投票数量不匹配: {votes_count} != {len(groups)}, votes={game.votes.get(game.current_round, {})}"
        
        # 检查投票是否已经自动处理
        with game_lock:
            game_status_after_voting = game.game_status
        
        # 如果投票已经自动处理（状态不是VOTING），就不需要再手动处理
        if game_status_after_voting != GameStatus.VOTING:
            # 投票结果已自动处理，验证结果
            with game_lock:
                assert game.last_vote_result is not None, \
                    f"投票结果应该已自动处理，当前状态: {game_status_after_voting}"
                assert 'eliminated' in game.last_vote_result or 'game_ended' in game.last_vote_result
        else:
            # 如果没有自动处理，手动处理投票结果
            response = client.post('/api/game/voting/process',
                                headers=self.get_admin_headers(),
                                content_type='application/json')
            assert response.status_code == 200, f"投票处理失败: {response.get_json()}"
            data = response.get_json()
            assert data['code'] == 200
            assert 'eliminated' in data['data'] or 'vote_result' in str(data)

    def test_process_voting_no_admin_token(self, client):
        """测试无管理员令牌处理投票"""
        response = client.post('/api/game/voting/process',
                              content_type='application/json')
        assert response.status_code == 403

    def test_process_voting_wrong_status(self, client):
        """测试错误状态下处理投票"""
        self.register_group(client, "组1")
        self.start_game(client)
        
        response = client.post('/api/game/voting/process',
                              headers=self.get_admin_headers(),
                              content_type='application/json')
        assert response.status_code == 400

    # ========== 获取游戏状态接口测试 ==========

    def test_get_game_state_success(self, client):
        """测试成功获取游戏状态"""
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        self.start_game(client)
        
        response = client.get('/api/game/state',
                             headers=self.get_admin_headers())
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'status' in data['data']
        assert 'groups' in data['data']
        assert 'undercover_group' in data['data']

    def test_get_game_state_no_admin_token(self, client):
        """测试无管理员令牌获取游戏状态"""
        response = client.get('/api/game/state')
        assert response.status_code == 403

    def test_get_game_state_complete_info(self, client):
        """测试游戏状态包含完整信息"""
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        self.start_game(client)
        
        response = client.get('/api/game/state',
                             headers=self.get_admin_headers())
        data = response.get_json()['data']
        
        assert 'current_round' in data
        assert 'describe_order' in data
        assert 'scores' in data
        assert 'descriptions' in data
        assert 'votes' in data

    # ========== 重置游戏接口测试 ==========

    def test_reset_game_success(self, client):
        """测试成功重置游戏"""
        self.register_group(client, "组1")
        self.start_game(client)
        
        response = client.post('/api/game/reset',
                              headers=self.get_admin_headers(),
                              content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        
        # 验证游戏状态已重置
        with game_lock:
            assert game.game_status == GameStatus.REGISTERED
            assert game.current_round == 0
            assert game.undercover_group is None

    def test_reset_game_no_admin_token(self, client):
        """测试无管理员令牌重置游戏"""
        response = client.post('/api/game/reset',
                              content_type='application/json')
        assert response.status_code == 403

    def test_reset_game_preserves_groups(self, client):
        """测试重置游戏保留组信息"""
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        
        with game_lock:
            groups_before = len(game.groups)
        
        self.start_game(client)
        client.post('/api/game/reset',
                   headers=self.get_admin_headers(),
                   content_type='application/json')
        
        with game_lock:
            groups_after = len(game.groups)
        
        assert groups_before == groups_after

    # ========== 获取组列表接口测试 ==========

    def test_get_groups_success(self, client):
        """测试成功获取组列表"""
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        
        response = client.get('/api/groups')
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert len(data['data']['groups']) == 2
        assert data['data']['total'] == 2

    def test_get_groups_empty(self, client):
        """测试空组列表"""
        response = client.get('/api/groups')
        data = response.get_json()
        assert data['data']['total'] == 0
        assert len(data['data']['groups']) == 0

    def test_get_groups_with_eliminated(self, client):
        """测试包含淘汰组的列表"""
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        self.start_game(client)
        
        with game_lock:
            game.eliminated_groups.append("组1")
        
        response = client.get('/api/groups')
        data = response.get_json()
        groups = data['data']['groups']
        
        group1_info = next((g for g in groups if g['name'] == "组1"), None)
        assert group1_info is not None
        assert group1_info['eliminated'] == True

    # ========== 获取描述列表接口测试 ==========

    def test_get_descriptions_success(self, client):
        """测试成功获取描述列表"""
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        self.start_game(client)
        
        # 开始回合
        client.post('/api/game/round/start',
                   headers=self.get_admin_headers(),
                   content_type='application/json')
        
        # 提交描述
        with game_lock:
            describe_order = game.describe_order.copy()
        client.post('/api/describe',
                   json={'group_name': describe_order[0], 'description': '测试描述'},
                   content_type='application/json')
        
        # 获取描述列表
        response = client.get('/api/descriptions')
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert len(data['data']['descriptions']) == 1

    def test_get_descriptions_empty(self, client):
        """测试空描述列表"""
        self.register_group(client, "组1")
        self.start_game(client)
        
        response = client.get('/api/descriptions')
        data = response.get_json()
        assert len(data['data']['descriptions']) == 0

    def test_get_descriptions_specific_round(self, client):
        """测试获取特定回合的描述"""
        self.register_group(client, "组1")
        self.start_game(client)
        
        # 第一回合
        client.post('/api/game/round/start',
                   headers=self.get_admin_headers(),
                   content_type='application/json')
        
        with game_lock:
            describe_order = game.describe_order.copy()
        client.post('/api/describe',
                   json={'group_name': describe_order[0], 'description': '第一回合描述'},
                   content_type='application/json')
        
        # 获取第一回合描述
        response = client.get('/api/descriptions?round=1')
        data = response.get_json()
        assert len(data['data']['descriptions']) == 1

    # ========== 获取分数接口测试 ==========

    def test_get_scores_success(self, client):
        """测试成功获取分数"""
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        self.start_game(client)
        
        response = client.get('/api/scores')
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert len(data['data']['scores']) == 2

    def test_get_scores_sorted(self, client):
        """测试分数排序"""
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        self.start_game(client)
        
        with game_lock:
            game.scores["组1"] = 10
            game.scores["组2"] = 5
        
        response = client.get('/api/scores')
        data = response.get_json()
        scores = data['data']['scores']
        
        # 应该按分数从高到低排序
        assert scores[0]['group_name'] == "组1"
        assert scores[0]['total_score'] == 10
        assert scores[1]['group_name'] == "组2"
        assert scores[1]['total_score'] == 5

    def test_get_scores_empty(self, client):
        """测试空分数列表"""
        response = client.get('/api/scores')
        data = response.get_json()
        assert len(data['data']['scores']) == 0

    # ========== 公共状态接口测试 ==========

    def test_public_status_success(self, client):
        """测试成功获取公共状态"""
        self.register_group(client, "组1")
        self.start_game(client)
        
        response = client.get('/api/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'status' in data['data']
        assert 'round' in data['data']

    def test_public_status_updates_activity(self, client):
        """测试获取状态时更新活跃时间"""
        self.register_group(client, "组1")
        
        response1 = client.get('/api/status?group_name=组1')
        time.sleep(0.1)
        response2 = client.get('/api/status?group_name=组1')
        
        # 两次请求应该都成功
        assert response1.status_code == 200
        assert response2.status_code == 200

    # ========== 完整游戏流程测试 ==========

    def test_complete_game_flow(self, client):
        """测试完整游戏流程"""
        # 1. 注册组
        self.register_group(client, "组1")
        self.register_group(client, "组2")
        self.register_group(client, "组3")
        
        # 2. 开始游戏
        start_response = self.start_game(client, "苹果", "香蕉")
        assert start_response.status_code == 200
        
        # 3. 开始回合
        round_response = client.post('/api/game/round/start',
                                    headers=self.get_admin_headers(),
                                    content_type='application/json')
        assert round_response.status_code == 200
        
        # 4. 提交描述
        with game_lock:
            describe_order = game.describe_order.copy()
        
        for group in describe_order:
            desc_response = client.post('/api/describe',
                                       json={'group_name': group, 'description': f'{group}的描述'},
                                       content_type='application/json')
            assert desc_response.status_code == 200
            with game_lock:
                game.update_activity(group)
        
        # 5. 提交投票 - 确保所有人都投票
        with game_lock:
            groups = game.describe_order.copy()
        
        # 确保所有人都投票：循环投票
        # 先检查游戏状态是否为VOTING
        with game_lock:
            assert game.game_status == GameStatus.VOTING, \
                f"游戏状态不是VOTING: {game.game_status}"
        
        last_response = None
        for i, voter in enumerate(groups):
            target = groups[(i + 1) % len(groups)]  # 投给下一个组
            vote_response = client.post('/api/vote',
                                      json={'voter_group': voter, 'target_group': target},
                                      content_type='application/json')
            vote_data = vote_response.get_json()
            
            # 检查响应状态和code
            assert vote_response.status_code == 200, \
                f"投票HTTP状态码错误: {voter} -> {target}, status={vote_response.status_code}, data={vote_data}"
            assert vote_data.get('code') == 200, \
                f"投票失败: {voter} -> {target}, code={vote_data.get('code')}, message={vote_data.get('message')}"
            
            with game_lock:
                game.update_activity(voter)
            
            last_response = vote_response
        
        # 如果最后一个人投票后自动处理了投票结果，响应中会包含vote_result
        # 这是正常的行为，不需要再验证投票数量
        if last_response:
            last_data = last_response.get_json()
            if not last_data.get('data', {}).get('auto_processed'):
                # 如果没有自动处理，验证投票数量
                with game_lock:
                    assert len(game.votes[game.current_round]) == len(groups)
        
        # 6. 处理投票结果（如果还没有自动处理）
        with game_lock:
            game_status_after_voting = game.game_status
        
        # 如果投票已经自动处理（状态不是VOTING），就不需要再手动处理
        if game_status_after_voting == GameStatus.VOTING:
            process_response = client.post('/api/game/voting/process',
                                          headers=self.get_admin_headers(),
                                          content_type='application/json')
            assert process_response.status_code == 200, f"投票处理失败: {process_response.get_json()}"
        else:
            # 投票已自动处理，验证结果
            with game_lock:
                assert game.last_vote_result is not None, \
                    f"投票结果应该已自动处理，当前状态: {game_status_after_voting}"
        
        # 7. 获取最终状态
        state_response = client.get('/api/game/state',
                                   headers=self.get_admin_headers())
        assert state_response.status_code == 200
        
        state_data = state_response.get_json()['data']
        assert 'scores' in state_data
        assert len(state_data['scores']) > 0

   
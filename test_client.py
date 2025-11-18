"""
游戏方测试客户端
用于测试API接口功能
"""
import requests
import time
import json

# 配置服务器地址（请修改为实际的主持方服务器IP）
BASE_URL = "http://192.168.81.102:5000"

def print_response(response, title=""):
    """打印响应结果"""
    print(f"\n{'='*50}")
    if title:
        print(f"{title}")
    print(f"{'='*50}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text)
    print(f"{'='*50}\n")

def test_connection():
    """测试服务器连接"""
    print("测试服务器连接...")
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        if response.status_code == 200 and response.json().get('code') == 200:
            print("✓ 服务器连接成功！")
        else:
            print("✗ 服务器返回异常响应")
            print_response(response, "连接响应")
            return False
        return True
    except requests.exceptions.ConnectionError:
        print("✗ 连接失败：无法连接到服务器")
        print(f"  请检查：")
        print(f"  1. 后端服务器是否已启动（运行 python backend.py）")
        print(f"  2. 服务器IP地址是否正确（当前: {BASE_URL}）")
        print(f"  3. 防火墙是否允许5000端口")
        return False
    except requests.exceptions.Timeout:
        print("✗ 连接超时：服务器响应时间过长")
        print(f"  请检查服务器IP地址是否正确（当前: {BASE_URL}）")
        return False
    except Exception as e:
        print(f"✗ 连接错误: {e}")
        return False

def test_register(group_name):
    """测试注册"""
    print(f"测试注册: {group_name}")
    try:
        response = requests.post(
            f"{BASE_URL}/api/register",
            json={"group_name": group_name},
            timeout=5
        )
        print_response(response, f"注册结果 - {group_name}")
        return response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        print(f"✗ 请求失败: {e}")
        return None

def test_get_state():
    """测试获取游戏状态"""
    print("获取游戏状态")
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        print_response(response, "游戏状态")
        return response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        print(f"✗ 请求失败: {e}")
        return None

def test_get_word(group_name):
    """测试获取词语"""
    print(f"获取词语: {group_name}")
    try:
        response = requests.get(
            f"{BASE_URL}/api/word",
            params={"group_name": group_name},
            timeout=5
        )
        print_response(response, f"词语 - {group_name}")
        return response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        print(f"✗ 请求失败: {e}")
        return None

def test_submit_description(group_name, description):
    """测试提交描述"""
    print(f"提交描述: {group_name} - {description}")
    try:
        response = requests.post(
            f"{BASE_URL}/api/describe",
            json={
                "group_name": group_name,
                "description": description
            },
            timeout=5
        )
        print_response(response, f"描述提交 - {group_name}")
        return response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        print(f"✗ 请求失败: {e}")
        return None

def test_submit_vote(voter_group, target_group):
    """测试提交投票"""
    print(f"提交投票: {voter_group} -> {target_group}")
    try:
        response = requests.post(
            f"{BASE_URL}/api/vote",
            json={
                "voter_group": voter_group,
                "target_group": target_group
            },
            timeout=5
        )
        print_response(response, f"投票提交 - {voter_group}")
        return response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        print(f"✗ 请求失败: {e}")
        return None

def test_get_groups():
    """测试获取所有组"""
    print("获取所有注册的组")
    try:
        response = requests.get(f"{BASE_URL}/api/groups", timeout=5)
        print_response(response, "所有组")
        return response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        print(f"✗ 请求失败: {e}")
        return None

def main():
    """主测试流程"""
    print("="*60)
    print("谁是卧底 - 游戏方测试客户端")
    print("="*60)
    print(f"服务器地址: {BASE_URL}")
    print("="*60)
    print("\n提示：请确保后端服务器已启动")
    print("提示：可以修改BASE_URL变量来连接不同的服务器")
    print("="*60)
    
    # 首先测试连接
    if not test_connection():
        print("\n无法连接到服务器，请检查上述问题后重试")
        return
    
    # 测试注册
    group_name = input("\n请输入组名进行注册（或按Enter使用默认'测试组'）: ").strip()
    if not group_name:
        group_name = "测试组"
    
    result = test_register(group_name)
    if not result or result.get('code') != 200:
        print("注册失败，退出测试")
        return
    
    # 获取所有组
    test_get_groups()
    
    # 等待游戏开始
    print("\n等待游戏开始...")
    print("（请主持方在另一个终端启动游戏）")
    input("按Enter继续...")
    
    # 获取游戏状态
    state = test_get_state()
    state_data = (state or {}).get('data') or {}
    if state_data.get('status') == 'word_assigned':
        # 获取词语
        word_result = test_get_word(group_name)
        if word_result and word_result.get('code') == 200:
            word = (word_result.get('data') or {}).get('word')
            if word:
                print(f"\n你的词语是: {word}")
    
    # 等待描述阶段
    print("\n等待描述阶段...")
    input("按Enter继续...")
    
    # 提交描述
    description = input(f"\n请输入描述（或按Enter使用默认'这是一个测试描述'）: ").strip()
    if not description:
        description = "这是一个测试描述"
    test_submit_description(group_name, description)
    
    # 等待投票阶段
    print("\n等待投票阶段...")
    input("按Enter继续...")
    
    # 获取游戏状态以查看其他组
    state = test_get_state()
    state_data = (state or {}).get('data') or {}
    groups = state_data.get('active_groups') or state_data.get('groups', {})

    other_groups = []
    if isinstance(groups, dict):
        other_groups = [
            name for name, info in groups.items()
            if name != group_name and not info.get('eliminated')
        ]
    elif isinstance(groups, list):
        other_groups = [name for name in groups if name != group_name]

    if other_groups:
        print(f"\n可投票的组: {', '.join(other_groups)}")
        target = input(f"请输入要投票的组名（或按Enter使用'{other_groups[0]}'）: ").strip()
        if not target:
            target = other_groups[0]
        test_submit_vote(group_name, target)
    else:
        print("\n没有可供投票的其他组，跳过投票步骤。")
    # 最终状态
    print("\n获取最终游戏状态...")
    test_get_state()
    
    print("\n测试完成！")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试中断")
    except Exception as e:
        print(f"\n错误: {e}")


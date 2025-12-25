"""
后端配置模块
"""
import os

# 管理员令牌（主持方专用）
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "host-secret")


def load_word_pairs():
    """从words.txt加载词语对"""
    word_pairs = []
    words_file = 'words.txt'
    
    if not os.path.exists(words_file):
        print(f"警告: 词库文件 {words_file} 不存在")
        return word_pairs
    
    try:
        with open(words_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                # 解析词语对（格式：平民词|卧底词）
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) == 2:
                        civilian_word = parts[0].strip()
                        undercover_word = parts[1].strip()
                        if civilian_word and undercover_word:
                            word_pairs.append((civilian_word, undercover_word))
        print("词库加载成功")
    except Exception as e:
        print(f"加载词库失败: {e}")
    
    return word_pairs


# 全局词库
WORD_PAIRS = load_word_pairs()


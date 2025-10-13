import os
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils import get_token_manager  # type: ignore
from API.openai_server import _is_suspect_token  # type: ignore


def test_is_suspect_token():
    sus, reason = _is_suspect_token('test')
    assert sus and '长度' in reason
    sus, reason = _is_suspect_token('your-puter-demo-xxxxxxx')
    assert sus
    sus, reason = _is_suspect_token('VLTKN_a1b2c3d4e5f6g7h8i9j0XYZ')
    assert not sus


def test_token_rotation_sequence(tmp_path, monkeypatch):
    # 使用测试模式隔离文件
    monkeypatch.setenv('TEST_MODE', '1')
    pool_file = tmp_path / 'token_pool.json'
    tm = get_token_manager()
    # 重置为独立文件
    tm.token_file = str(pool_file)
    tm.token_pool.clear()
    tm.current_token_index = 0

    tokens = [f'valid_token_{i}_12345678901234567890' for i in range(3)]
    for t in tokens:
        tm.add_token(t)
    first = tm.get_current_token()
    assert first == tokens[0]
    second = tm.switch_to_next_token()
    assert second == tokens[1]
    third = tm.switch_to_next_token()
    assert third == tokens[2]
    cycle = tm.switch_to_next_token()
    assert cycle == tokens[0]


def test_env_suspect_token_filtered(monkeypatch, tmp_path):
    monkeypatch.setenv('TEST_MODE', '1')
    monkeypatch.setenv('API_TOKEN', 'your-puter-placeholder-token')
    # 强制新实例以触发 load_from_env
    from utils.token_manager import TokenManager
    tm = TokenManager(token_file=str(tmp_path / 'tp.json'))
    # 可疑 env token 不应进入池
    assert len(tm.token_pool) == 0

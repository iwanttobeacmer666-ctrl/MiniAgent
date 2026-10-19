import pytest
from pydantic import ValidationError
from tool_registry import execute_tool
from unittest.mock import Mock
from tool_registry import TOOL_REGISTRY

def test_execute_tool_calculator() -> None:
    result=execute_tool("calculator",{"operation": "multiply", "a": 135, "b": 27})
    assert result == 3645.0

def test_execute_tool_invalid_arguments() -> None:
    with pytest.raises(ValidationError):
        execute_tool("calculator",{"operation": "multiply", "a": 135})  # Missing 'b'

def test_execute_tool_unknown_name() -> None:
    with pytest.raises(KeyError):
        execute_tool("unknown_tool",{})


def test_invalid_arguments_do_not_call_handler(monkeypatch) -> None:
    # pytest 提供 monkeypatch；测试结束后会自动恢复下面的替换。
    # Mock 是记录调用情况的假函数，不执行真正的计算器。
    fake_handler=Mock()
    # 临时替换注册表里的执行函数，保留原来的 Pydantic 参数模型。
    monkeypatch.setitem(
        TOOL_REGISTRY["calculator"],
        "function",fake_handler
    )
    # 缺少 b，应当在参数验证阶段抛出异常。
    with pytest.raises(ValidationError):
        execute_tool("calculator",{"operation": "multiply", "a": 135})  # Missing 'b'
    # 再检查假函数是否从未被调用；只检查异常无法证明这一点。
    fake_handler.assert_not_called()

import agent
from unittest.mock import Mock
from openai.types.chat import ChatCompletionMessage
import json
from openai.types.chat import ChatCompletionMessageFunctionToolCall
import pytest
from openai import APITimeoutError
from httpx2 import Request

def test_agent_direct_answer(monkeypatch) -> None:
    # 创建一个假的 chat_once 函数，返回一个预定义的回答。
    fake_chat_once = Mock(return_value=ChatCompletionMessage(
        role="assistant",
        content=" 这是离线回答 "
    ))
    # 使用 monkeypatch 替换 agent 模块中的 chat_once 函数。
    monkeypatch.setattr(agent, "chat_once", fake_chat_once)
    # 调用 agent.chat 函数，传入一个简单的消息列表。
    result=agent.run_agent("你好")
    assert result == "这是离线回答"
    fake_chat_once.assert_called_once();

def test_execute_tool_call_invalid_json() -> None:
    # 构造一个工具调用，其 arguments 是非法 JSON。
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="test-invalid-json",
        type="function",
        function={
            "name": "calculator",
            "arguments": '{"operation":',
        },
    )
    fake_response=agent.execute_tool_call(tool_call)
    fake_message=fake_response["content"]
    # 解析返回的 JSON 内容，检查是否包含错误信息。
    result=json.loads(fake_message)
    assert "error" in result
    assert fake_response["role"] == "tool"
    assert fake_response["tool_call_id"] == tool_call.id
    assert isinstance(fake_response["content"], str)

def test_agent_one_tool_call(monkeypatch) -> None:
    # 第一次模型回复：要求调用计算器，arguments 是 JSON 字符串。
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="test-calculate",
        type="function",
        function={
            "name": "calculator",
            "arguments": '{"operation": "multiply", "a": 135, "b": 27}',
        },
    )
    first_response = ChatCompletionMessage(
        role="assistant",
        content=None,
        tool_calls=[tool_call],
    )

    # 第二次模型回复：给出最终文字，不再调用工具。
    second_response = ChatCompletionMessage(
        role="assistant",
        content="计算结果是 3645",
    )

    # 两次调用依次返回两条回复；只替换模型请求，保留真实工具执行。
    fake_chat_once = Mock(side_effect=[first_response, second_response])
    monkeypatch.setattr(agent, "chat_once", fake_chat_once)

    result = agent.run_agent("请计算 135 × 27")
    assert result == "计算结果是 3645"
    assert fake_chat_once.call_count == 2

    # 最后一次请求的第一个位置参数，就是发给模型的消息历史。
    messages = fake_chat_once.call_args.args[0]
    assert len(messages) == 4
    assert messages[2] is first_response

    # 检查真实工具的结果以及它对应的调用 ID。
    tool_message = messages[-1]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == tool_call.id
    assert isinstance(tool_message["content"], str)
    assert json.loads(tool_message["content"]) == 3645

def test_agent_multiple_tool_calls(monkeypatch) -> None:
    lookup_a=ChatCompletionMessageFunctionToolCall(
        id="lookup-a",
        type="function",
        function={
            "name": "lookup_product",
            "arguments": '{"product_id": "A"}',
        },
    )
    lookup_b=ChatCompletionMessageFunctionToolCall(
        id="lookup-b",
        type="function",
        function={
            "name": "lookup_product",
            "arguments": '{"product_id": "B"}',
        },
    )
   
    multiply_a=ChatCompletionMessageFunctionToolCall(
        id="multiply_a",
        type="function",
        function={
            "name": "calculator",
            "arguments": '{"operation":"multiply","a":25,"b":12}',
        },
    )
    multiply_b=ChatCompletionMessageFunctionToolCall(
        id="multiply_b",
        type="function",
        function={
            "name": "calculator",
            "arguments": '{"operation":"multiply","a":40,"b":9}',
        },
    )
    difference=ChatCompletionMessageFunctionToolCall(
        id="difference",
        type="function",
        function={
            "name": "calculator",
            "arguments": '{"operation":"subtract","a":360,"b":300}',
        },
    )
    first_response=ChatCompletionMessage(
        role="assistant",
        content=None,
        tool_calls=[lookup_a, lookup_b],
    )
    second_response=ChatCompletionMessage(
        role="assistant",
        content=None,
        tool_calls=[multiply_a, multiply_b],
    )
    third_response=ChatCompletionMessage(
        role="assistant",
        content=None,
        tool_calls=[difference],
    )
    final_response=ChatCompletionMessage(
        role="assistant",
        content="商品 A：300 元；商品 B：360 元；商品 B 比商品 A 高 60 元。",
    )
    fake_chat_once=Mock(side_effect=[first_response, second_response, third_response, final_response])
    monkeypatch.setattr(agent, "chat_once", fake_chat_once)
    prompt = "查询商品 A 和 B 的单价及库存，计算库存总价值并比较差额。"
    result=agent.run_agent(prompt)
    messages=fake_chat_once.call_args.args[0]
    tool_messages = []

    for message in messages:
        if isinstance(message, dict) and message.get("role") == "tool":
            tool_messages.append(message)
    # 检查最终回答、模型请求次数和消息数量。
    assert result == final_response.content
    assert fake_chat_once.call_count == 4
    assert len(messages) == 10
    assert len(tool_messages) == 5

    # 每个工具结果都必须对应原来的调用 ID，顺序也应一致。
    assert tool_messages[0]["tool_call_id"] == lookup_a.id
    assert tool_messages[1]["tool_call_id"] == lookup_b.id
    assert tool_messages[2]["tool_call_id"] == multiply_a.id
    assert tool_messages[3]["tool_call_id"] == multiply_b.id
    assert tool_messages[4]["tool_call_id"] == difference.id

    # 商品结果的 content 是 JSON 字符串，解析后与预期字典比较。
    assert json.loads(tool_messages[0]["content"]) == {
        "product_id": "A",
        "unit_price": 25.0,
        "stock": 12,
    }
    assert json.loads(tool_messages[1]["content"]) == {
        "product_id": "B",
        "unit_price": 40.0,
        "stock": 9,
    }

    # 计算结果解析后是数字，检查真实工具的输出。
    assert json.loads(tool_messages[2]["content"]) == 300
    assert json.loads(tool_messages[3]["content"]) == 360
    assert json.loads(tool_messages[4]["content"]) == 60

def test_agent_max_steps(monkeypatch) -> None:
    # 模拟模型连续调用工具，超过最大步骤限制。
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="test-max-steps",
        type="function",
        function={
            "name": "calculator",
            "arguments": '{"operation": "add", "a": 1, "b": 1}',
        },
    )
    response = ChatCompletionMessage(
        role="assistant",
        content=None,
        tool_calls=[tool_call],
    )
    # 模拟模型总是返回同一个工具调用，导致无限循环。
    fake_chat_once = Mock(return_value=response)
    monkeypatch.setattr(agent, "chat_once", fake_chat_once)

    with pytest.raises(RuntimeError, match="Exceeded maximum steps"):
        agent.run_agent("计算 1 + 1", max_steps=2)
    assert fake_chat_once.call_count == 2

def test_agent_api_timeout(monkeypatch) -> None:
    request = Request("POST", "https://example.invalid/chat/completions")
    timeout_error = APITimeoutError(request=request)
    fake_chat_once = Mock(side_effect=timeout_error)
    monkeypatch.setattr(agent, "chat_once", fake_chat_once)
    with pytest.raises(APITimeoutError):
        agent.run_agent("测试 API 超时")
    assert fake_chat_once.call_count == 1

@pytest.mark.parametrize("arguments", [
    "[]",
    "null",
    "135",
    '"A"',
])
def test_execute_tool_call_non_object_arguments(monkeypatch, arguments) -> None:
    fake_execute_tool = Mock()
    monkeypatch.setattr(agent, "execute_tool", fake_execute_tool)
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="test-non-object",
        type="function",
        function={
            "name": "calculator",
            "arguments": arguments,
        },
    )
    response = agent.execute_tool_call(tool_call)
    assert response["role"] == "tool"
    assert response["tool_call_id"] == tool_call.id
    assert isinstance(response["content"], str)
    data = json.loads(response["content"])
    assert data == {
    "error": "工具参数必须是 JSON 对象，也就是字典。"
    }
    fake_execute_tool.assert_not_called()


@pytest.mark.parametrize("content", [None, "", "  \t\n"])
def test_agent_empty_response(monkeypatch, content) -> None:
    # 三种空内容都没有工具调用，不能作为最终答案。
    response = ChatCompletionMessage(
        role="assistant",
        content=content,
    )
    fake_chat_once = Mock(return_value=response)
    monkeypatch.setattr(agent, "chat_once", fake_chat_once)

    # 检查实际抛出的异常类型和错误信息。
    with pytest.raises(RuntimeError, match="no non-empty content"):
        agent.run_agent("测试模型空回复")

    # 空回复应立即报错，不继续请求模型。
    fake_chat_once.assert_called_once()


def test_execute_tool_call_overflow_returns_error() -> None:
    # 两个输入都是有限数字，但乘积会超出浮点数范围。
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="test-overflow",
        type="function",
        function={
            "name": "calculator",
            "arguments": '{"operation": "multiply", "a": 1e308, "b": 1e308}',
        },
    )

    # 应返回可回传给模型的错误消息，而不是在 JSON 序列化时崩溃。
    response = agent.execute_tool_call(tool_call)
    assert response["role"] == "tool"
    assert response["tool_call_id"] == tool_call.id
    assert isinstance(response["content"], str)
    assert json.loads(response["content"]) == {
        "error": "计算结果超出有效数值范围。"
    }

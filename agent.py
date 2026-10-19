import json
import math
from openai.types.chat import ChatCompletionMessageFunctionToolCall
from tool_registry import execute_tool
from llm_client import chat_once
from pydantic import ValidationError

def execute_tool_call(
        tool_call: ChatCompletionMessageFunctionToolCall
    )->dict:
    tool_name = tool_call.function.name
    
    try:
        tool_args = json.loads(tool_call.function.arguments)
        if not isinstance(tool_args, dict):
            result = {"error": "工具参数必须是 JSON 对象，也就是字典。"}
        else:
            # 第二步：验证参数，再执行对应工具。
            result = execute_tool(tool_name, tool_args)
    except json.JSONDecodeError as exc:
        result = {"error": str(exc)}
    except ZeroDivisionError as exc:
        result = {"error": str(exc)}
    except KeyError as exc:
        result = {"error": f"工具或商品不存在：{exc}"}
    except ValidationError as exc:
        result = {"error": str(exc)}

    # 有限的输入也可能算出无穷大；先转为错误消息，避免 JSON 序列化失败。
    if isinstance(result, float) and not math.isfinite(result):
        result = {"error": "计算结果超出有效数值范围。"}

    content = json.dumps(
        result, ensure_ascii=False,
        allow_nan=False, 
    )
    return {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": content,
    }

def run_agent(user_text: str,max_steps: int = 5) -> str:
    """最多请求模型 max_steps 次，支持每轮多个工具调用，返回最终文字。"""
    if type(max_steps) is not int or max_steps <= 0:
            raise ValueError("max_steps must be a positive integer.")
    user_text = user_text.strip()
    if user_text == "":
        raise ValueError("User text cannot be empty.")
    # messages 是整段对话的历史列表；每次请求模型都传这个列表。
    messages = [
        {"role": "system", "content": "你是一名中文助手，计算任务请使用计算器工具。"},
        {"role": "user", "content": user_text},
    ]
    for step in range(max_steps):
        # 类型注解不会自动验证参数，需要手动检查。
       
        ai_response = chat_once(messages)
        # tool_calls 可能是 None 或空列表，两者都表示没有工具调用。
        if not ai_response.tool_calls:
            if ai_response.content is None or not ai_response.content.strip():
                raise RuntimeError("AI response has no non-empty content.")
            return ai_response.content.strip()

        # 保存完整 assistant 回复，其中包含工具调用的名称、参数和 id。
        messages.append(ai_response)
        for tool_call in ai_response.tool_calls:
            if not isinstance(tool_call, ChatCompletionMessageFunctionToolCall):
                raise TypeError("tool_call must be an instance of ChatCompletionMessageFunctionToolCall.")
            if not tool_call.function.name:
                raise ValueError("tool_call must have a valid function name.")
            # step 从 0 开始；日志从第 1 轮显示，参数直接打印原始字符串。
            print(
                f"[第{step + 1}轮][调用][{tool_call.id}] "
                f"{tool_call.function.name} 参数={tool_call.function.arguments}"
            )
            tool_result = execute_tool_call(tool_call)
            # 使用同一个调用 ID 对应结果，错误消息也会显示在这里。
            print(f"[第{step + 1}轮][结果][{tool_call.id}] {tool_result['content']}")
            # tool_result 是 role=tool 的消息，通过 tool_call_id 对应原始调用。
            messages.append(tool_result)
    raise RuntimeError(f"Exceeded maximum steps ({max_steps}) without completing the task.")
       

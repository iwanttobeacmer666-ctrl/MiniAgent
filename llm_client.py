import os
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage
from tool_registry import get_tool_schemas

def chat_once(
        messages:list[dict| ChatCompletionMessage],
) -> ChatCompletionMessage:
    if not isinstance(messages, list):
        raise TypeError("messages must be a list of dict or ChatCompletionMessage instances.")
    if  len(messages) == 0:
        raise ValueError("messages list cannot be empty.")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError("DEEPSEEK_API_KEY environment variable is not set.")
    deepseek_model = os.getenv("DEEPSEEK_MODEL")
    if not deepseek_model or not deepseek_model.strip():
        raise RuntimeError("DEEPSEEK_MODEL environment variable is not set.")
    with OpenAI( 
        api_key=api_key,
        base_url="https://api.deepseek.com",
        max_retries=0,
    ) as client:
        # 在这里发送请求
        response = client.chat.completions.create(
        model=deepseek_model,
        messages=messages,
        tools=get_tool_schemas(),
        tool_choice= "auto",
        stream=False,
        extra_body={"thinking": {"type": "disabled"}},
        timeout=30.0,
        )
    if not response.choices or not response.choices[0].message :
        raise RuntimeError("Received an empty response from the model.")
    answer = response.choices[0].message
    return answer


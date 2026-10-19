# MiniAgent

MiniAgent 是一个用于学习 Agent 原理的 Python 命令行项目。用户输入自然语言任务后，模型可以选择商品查询和计算器工具；程序执行工具、回传结果，再由模型决定是否继续调用工具或给出最终回答。

项目使用 Pydantic 验证工具参数，通过 OpenAI Python SDK 调用 DeepSeek API，使用 pytest 和 Mock 做离线测试，没有引入 Agent 框架。

## 运行环境

项目使用根目录中的 `.venv` 虚拟环境。开发时已验证的版本如下，这些是环境记录，不表示只能使用这些版本。

| 组件 | 版本 |
| --- | --- |
| Python | 3.14.7 |
| openai | 3.35.1 |
| pydantic | 2.14.1 |
| pytest | 9.1.1 |

下面的命令需要在项目根目录的 Windows PowerShell 中执行，并明确指定项目解释器。换到其他电脑时，需要单独准备环境；本说明不包含安装依赖的操作。

## 配置模型并运行

真实模型调用需要两个环境变量：

| 名称 | 用途 |
| --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `DEEPSEEK_MODEL` | 账号可用且支持本项目工具调用方式的模型名称 |

程序在 `llm_client.py` 中读取它们，API 地址目前固定为 `https://api.deepseek.com`。程序没有加载 `.env` 文件的逻辑。

在同一个 PowerShell 终端中执行：

```powershell
$miniAgentKey = Read-Host '请输入 DeepSeek API Key' -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $miniAgentKey).Password
$env:DEEPSEEK_MODEL = Read-Host '请输入之前已验证可用的模型名称'

& '.\.venv\Scripts\python.exe' .\main.py
```

密钥输入不会直接显示在终端中；这些环境变量设置用于当前 PowerShell 会话及它启动的程序，关闭终端后需要重新设置。不要把真实密钥写进源码、README 或截图。

看到“请输入你的任务”后，输入任务并回车。当前命令行每次启动处理一个任务。

## 使用示例

可以输入：

```text
查询商品 A 和商品 B 的单价及库存，分别计算库存总价值，比较哪个商品更高、相差多少。商品数据必须通过查询工具获取，乘法和差值计算必须使用计算器工具，最后用中文汇总结果。
```

项目内的示例商品数据为：

| 商品 | 单价 | 库存 | 库存总价值 |
| --- | --- | --- | --- |
| A | 25 元 | 12 | 300 元 |
| B | 40 元 | 9 | 360 元 |

预期结论：商品 B 的库存总价值比商品 A 高 60 元。

运行时会打印工具调用的轮次、调用 ID、名称、参数和结果，再显示模型的最终回答。实际工具调用顺序和回答措辞由模型决定，可能与测试中的预设顺序不同。

## 项目结构

```text
MiniAgent/
├── main.py
├── llm_client.py
├── tools.py
├── tool_registry.py
├── agent.py
├── tests/
│   ├── test_tools.py
│   ├── test_tool_registry.py
│   └── test_agent.py
└── README.md
```

| 文件 | 职责 |
| --- | --- |
| `main.py` | 读取命令行输入，调用 Agent，打印最终回答 |
| `llm_client.py` | 读取模型配置，发送一次包含消息历史和工具 Schema 的模型请求，返回完整回复对象 |
| `tools.py` | 定义 Pydantic 参数模型、计算器函数和商品查询函数 |
| `tool_registry.py` | 注册工具，生成工具 Schema，验证参数并调用对应函数 |
| `agent.py` | 解析工具调用、封装工具结果、维护消息历史并控制循环 |
| `tests/test_tools.py` | 测试四则运算、除零、商品查询及商品不存在 |
| `tests/test_tool_registry.py` | 测试工具调度、参数验证、未知工具以及验证失败时不执行工具 |
| `tests/test_agent.py` | 测试消息处理、多轮工具调用、轮数限制、超时和异常参数等行为 |

## 一次任务如何执行

```text
用户输入任务
    ↓
main() 调用 run_agent()
    ↓
创建 system、user 消息，向模型提供消息历史和工具 Schema
    ↓
模型返回完整 assistant 消息
    ├── 没有工具调用：检查正文，返回有效文字
    └── 有工具调用：保存 assistant 消息，逐个处理调用
            ↓
        解析 JSON 参数，确认得到字典
            ↓
        根据工具名称查找注册项，用 Pydantic 验证参数
            ↓
        执行 Python 工具函数
            ↓
        将结果转为字符串，生成 role=tool 的消息
            ↓
        用 tool_call_id 对应原调用，将消息加入历史
            ↓
        再次请求模型，直到返回最终文字或达到轮数限制
```

模型负责提出工具调用，Python 程序负责实际执行。工具结果成为后续决策的依据，这体现了 ReAct 中的 Action、Observation 和继续决策的过程。日志记录工具动作与结果，不包含模型内部推理过程。

## 运行离线测试

离线测试使用 Mock 替代模型请求，不需要密钥，也不会发送真实模型请求。

```powershell
& '.\.venv\Scripts\python.exe' -m pytest .\tests -v
```

只运行一个测试时，可以在文件路径后用 `::` 指定函数名：

```powershell
& '.\.venv\Scripts\python.exe' -m pytest .\tests\test_agent.py::test_agent_max_steps -v
```

当前已验证结果为 **27 passed**。参数化测试的一组参数算一个用例，所以用例数量多于测试函数数量。

测试覆盖四则运算、除零、运算结果溢出、商品查询、未知工具、参数验证、非法 JSON、JSON 解析后不是字典、单次及多轮工具调用、最大轮数、超时异常传播和模型空回复。

综合 Mock 测试预设了四条模型回复：查询 A/B、计算两个总价值、计算差值、输出最终文字。真实工具参与执行；测试会检查请求次数、历史消息数量、工具调用 ID 和实际结果。它验证的是程序处理这些回复的能力，真实模型能否自主选择工具还需要联网运行确认。

## 当前限制与异常处理

- 商品查询使用内存中的 A、B 两条示例数据，没有连接外部商品系统。
- `run_agent()` 默认最多请求模型 5 次，一次回复可以包含多个工具调用；达到上限仍没有最终回答时抛出 `RuntimeError`。
- 非法 JSON、非字典参数、Pydantic 验证失败、除零、运算结果溢出、未知工具或商品不存在，会被封装成工具错误消息，交给模型继续处理。
- 模型没有工具调用且正文为空时，Agent 抛出异常，不返回空答案。
- 模型请求设置了 `timeout=30.0`，SDK 自动重试次数为 0。API 超时等请求异常向外抛出，当前命令行没有统一错误提示，会显示异常信息。
- 每次运行创建新的消息历史，没有跨任务记忆。计算器使用普通浮点数，当前用于教学示例。

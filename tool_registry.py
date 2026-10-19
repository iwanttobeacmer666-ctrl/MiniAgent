from tools import calculator, CalculatorInput, LookupProductInput,lookup_product
TOOL_REGISTRY = {
    "calculator": {
        "function": calculator,
        "input_model": CalculatorInput,
        "description": "支持四则运算，适合准确计算",
    },
    # 补充 lookup_product
    "lookup_product": {
        "function": lookup_product,
        "input_model": LookupProductInput,
        "description": "根据商品编号查询单价和库存",
    },
}
def execute_tool(tool_name: str, arguments: dict) -> float | dict:
    if not isinstance(arguments, dict):
        raise TypeError("arguments 必须是字典")

    if tool_name not in TOOL_REGISTRY:
        raise KeyError(f"未知工具：{tool_name}")
    tool = TOOL_REGISTRY[tool_name]
    InputModel = tool["input_model"]
    handler = tool["function"]
    args=InputModel.model_validate(arguments)
    result = handler(**args.model_dump())
    return result
def get_tool_schemas()->list[dict]:
    schema=[]
    for tool_name,tool_info in TOOL_REGISTRY.items():
        InputModel=tool_info["input_model"]
        tool_schema={
            "name":tool_name,
            "description":tool_info["description"],
            "parameters":InputModel.model_json_schema()
        }
        schema.append({
            "type": "function",
            "function": tool_schema,
        })   
    return schema
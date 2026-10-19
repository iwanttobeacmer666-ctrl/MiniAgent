from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

# 参数模型：创建实例时由 Pydantic 验证输入，不负责执行计算。
class CalculatorInput(BaseModel):
    # model_config 是模型的统一配置；ConfigDict 用来声明配置项。
    model_config = ConfigDict(
    strict=True,  # 数值字段拒绝数字字符串和布尔值，仍接受整数和浮点数。
    extra="forbid",  # 拒绝 operation、a、b 之外的字段。
    allow_inf_nan=False,  # 拒绝无穷大和 NaN 等非有限数值。
    )
    # Literal 限定可选值；Field 的 ... 表示必填，description 提供字段说明。
    operation: Literal["add", "subtract", "multiply", "divide"] = Field(..., description="The operation to perform: add, subtract, multiply, divide.")
    # 没有默认值的字段也是必填；description 本身不增加数值约束。
    a: float = Field( description="The first number.")
    b: float = Field( description="The second number.")

class LookupProductInput(BaseModel):
    model_config=ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,  # 字符串字段自动去除首尾空白。  
        str_to_upper=True,  # 字符串字段自动转换为大写。
    )
    product_id : str=Field(..., description="The product ID to look up.",min_length=1)  # 最小长度为 1，确保非空。
# 运算函数：参数验证需由调用方先执行，例如 CalculatorInput.model_validate(data)。
def calculator(operation:str,a:float,b:float)->float:
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        return a / b
    else:
        raise ValueError("Invalid operation. Supported operations are: add, subtract, multiply, divide.")
PRODUCTS = {
        "A":{"product_id": "A","unit_price": 25.0,"stock": 12,},
        "B":{"product_id": "B","unit_price": 40.0,"stock": 9,},
}
def lookup_product(product_id: str) -> dict:
    
    product_id=product_id.strip().upper();
    if(product_id ==""):
        raise ValueError("Product ID cannot be empty.")
    product = PRODUCTS.get(product_id);
    if product is None:
        raise KeyError(f"Product with ID '{product_id}' not found.")
    return product.copy()
from tools import calculator
import pytest
from tools import lookup_product

@pytest.mark.parametrize(
    "operation, a, b, expected",
    [
        ("add", 2.0, 3.0, 5.0),
        ("subtract", 9.0, 4.0, 5.0),
        ("multiply", 135.0, 27.0, 3645.0),
        ("divide", 10.0, 4.0, 2.5),
    ],
)
def test_calculator_operations(operation, a, b, expected) -> None:
    result = calculator(operation=operation, a=a, b=b)
    assert result == expected

def test_calculator_divide_by_zero() -> None:
    with pytest.raises(ZeroDivisionError):
        calculator(operation="divide", a=2.0, b=0.0)

@pytest.mark.parametrize(
    "product_id, expected",
    [
        ("A",{"product_id": "A", "unit_price": 25.0, "stock": 12}),
        ("B",{"product_id": "B", "unit_price": 40.0, "stock": 9}),
        (" a ",{"product_id": "A", "unit_price": 25.0, "stock": 12}),
    ],
)
def test_lookup_product(product_id, expected) -> None:
    result = lookup_product(product_id=product_id)
    assert result == expected
def test_lookup_product_not_found() -> None:
    with pytest.raises(KeyError):
        lookup_product(product_id="C")
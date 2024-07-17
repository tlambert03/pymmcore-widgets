from pydantic import BaseModel


class X(BaseModel):
    z: list[int]


class Y(BaseModel):
    x: X


class Z(BaseModel):
    y: Y


z = Z.model_validate({"y": {"x": {"z": [1, 2, 3]}}})

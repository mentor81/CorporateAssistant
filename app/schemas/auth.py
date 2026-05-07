from pydantic import BaseModel
from typing import List


class UserCreate(BaseModel):
    username: str
    password: str
    scopes: List[str]


class UserLogin(BaseModel):
    username: str
    password: str

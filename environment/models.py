from pydantic import BaseModel
from typing import List

class Item(BaseModel):
    color: str
    position: int

class State(BaseModel):
    items: List[Item]
    score: int
    done: bool
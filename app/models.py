from pydantic import BaseModel
from typing import Optional

class QueueItem(BaseModel):
    filename: str
    position: Optional[int] = None

class MoveQueueItem(BaseModel):
    old_index: int
    new_index: int

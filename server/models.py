import time
import uuid

from pydantic import BaseModel, Field
from pydantic.types import UUID4


class Snippet(BaseModel):
    content: str
    name: str = ""
    description: str = ""
    prompt: str = ""
    highlighting_language: str = ""
    id: UUID4 = Field(default_factory=uuid.uuid4)
    creation_time: int = Field(default_factory=lambda: int(time.time()))

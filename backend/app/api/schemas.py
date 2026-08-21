from typing import Literal

from pydantic import BaseModel, Field


class PatchBody(BaseModel):
    fields: dict[str, str] = Field(default_factory=dict)


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class ChatBody(BaseModel):
    message: str
    document_id: str | None = None
    history: list[ChatTurn] = Field(default_factory=list)


class EmailBody(BaseModel):
    document_id: str
    to: str

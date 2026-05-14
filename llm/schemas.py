from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ParsedActionType(str, Enum):
    LOOK = "look"
    GO = "go"
    TAKE = "take"
    USE = "use"
    ATTACK = "attack"
    TALK = "talk"
    INVENTORY = "inventory"
    HELP = "help"
    QUIT = "quit"


class ParsedPlayerAction(BaseModel):
    action: ParsedActionType
    direction: str | None = None
    target: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class NarrationResponse(BaseModel):
    text: str

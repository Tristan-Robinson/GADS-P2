from __future__ import annotations

from game.actions import ActionResult
from game.models import GameState
from llm.client import OllamaClient
from llm.prompts import build_narrator_messages, narrator_schema
from llm.schemas import NarrationResponse

import config


class Narrator:
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    def narrate(self, result: ActionResult, state: GameState) -> str:
        mode = result.narration_mode or "outcome"
        temperature = config.NARRATOR_TEMPERATURE
        if mode in ("interact", "ask"):
            temperature = min(1.0, config.NARRATOR_TEMPERATURE + 0.3)
        try:
            response = self.client.chat_structured(
                build_narrator_messages(result.to_payload(), state.context_slice()),
                temperature=temperature,
                schema=narrator_schema(),
                model_cls=NarrationResponse,
            )
            return response.text.strip()
        except Exception:
            return result.message

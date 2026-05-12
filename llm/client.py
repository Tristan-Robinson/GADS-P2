from __future__ import annotations

from typing import Any

import ollama
from pydantic import ValidationError

import config
from llm.prompts import build_parser_messages, build_parser_retry_message, parser_schema


class OllamaUnavailableError(RuntimeError):
    pass


class OllamaClient:
    def __init__(
        self,
        *,
        host: str = config.OLLAMA_HOST,
        model: str = config.OLLAMA_MODEL,
    ) -> None:
        self.host = host
        self.model = model
        self._client = ollama.Client(host=host)

    def verify(self) -> None:
        try:
            models = self._client.list().get("models", [])
        except Exception as exc:
            raise OllamaUnavailableError(
                f"Could not reach Ollama at {self.host}. "
                "Start Ollama and pull a model before playing."
            ) from exc

        available = {
            entry.get("model", "").split(":")[0]
            for entry in models
            if entry.get("model")
        }
        requested = self.model.split(":")[0]
        if requested not in available:
            raise OllamaUnavailableError(
                f"Model '{self.model}' is not available. "
                f"Run: ollama pull {self.model}"
            )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        schema: dict[str, Any] | None = None,
    ) -> str:
        options: dict[str, Any] = {"temperature": temperature}
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "options": options,
        }
        if schema is not None:
            kwargs["format"] = schema

        response = self._client.chat(**kwargs)
        content = response.get("message", {}).get("content", "")
        if not content:
            raise RuntimeError("Ollama returned an empty response.")
        return content

    def chat_structured(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        schema: dict[str, Any],
        model_cls: type,
    ) -> Any:
        content = self.chat(messages, temperature=temperature, schema=schema)
        try:
            return model_cls.model_validate_json(content)
        except ValidationError as exc:
            raise RuntimeError("Ollama returned invalid structured output.") from exc

    def parse_with_retry(self, user_input: str, context: dict[str, Any], model_cls: type) -> Any:
        messages = build_parser_messages(user_input, context)
        try:
            return self.chat_structured(
                messages,
                temperature=config.PARSER_TEMPERATURE,
                schema=parser_schema(),
                model_cls=model_cls,
            )
        except RuntimeError:
            messages.append(build_parser_retry_message(user_input))
            return self.chat_structured(
                messages,
                temperature=config.PARSER_TEMPERATURE,
                schema=parser_schema(),
                model_cls=model_cls,
            )

from __future__ import annotations

import subprocess
import sys
import time
from typing import Any, Protocol

import ollama
from pydantic import ValidationError

import config
from llm.prompts import build_parser_messages, build_parser_retry_message, parser_schema


class OllamaUnavailableError(RuntimeError):
    pass


class _ConsoleLike(Protocol):
    def print(self, *args: Any, **kwargs: Any) -> None: ...


def _base_model_name(model: str) -> str:
    return model.split(":")[0]


def _parse_models_list(payload: dict[str, Any]) -> set[str]:
    return {
        _base_model_name(entry.get("model", ""))
        for entry in payload.get("models", [])
        if entry.get("model")
    }


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

    def _available_models(self) -> set[str]:
        return _parse_models_list(self._client.list())

    def is_reachable(self) -> bool:
        try:
            self._client.list()
            return True
        except Exception:
            return False

    def ensure_service_running(self, console: _ConsoleLike | None = None) -> None:
        if self.is_reachable():
            return

        if console is not None:
            console.print("[yellow]Ollama is not running. Starting it now...[/yellow]")

        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        except FileNotFoundError as exc:
            raise OllamaUnavailableError(
                "Ollama is not installed or not on your PATH. "
                "Install it from https://ollama.com then launch the game again."
            ) from exc
        except Exception as exc:
            raise OllamaUnavailableError(
                f"Could not start Ollama at {self.host}. "
                "Open the Ollama app manually, then try again."
            ) from exc

        deadline = time.monotonic() + config.OLLAMA_STARTUP_TIMEOUT_SEC
        while time.monotonic() < deadline:
            if self.is_reachable():
                if console is not None:
                    console.print("[green]Ollama is ready.[/green]")
                return
            time.sleep(0.5)

        raise OllamaUnavailableError(
            f"Ollama did not respond at {self.host} within "
            f"{config.OLLAMA_STARTUP_TIMEOUT_SEC} seconds. "
            "Open the Ollama app from https://ollama.com and try again."
        )

    def ensure_model(self, console: _ConsoleLike | None = None) -> None:
        if not config.AUTO_PULL_ON_STARTUP:
            self._require_model_present()
            return

        requested = _base_model_name(self.model)
        if requested in self._available_models():
            return

        if console is not None:
            console.print(
                f"[yellow]Downloading model '{self.model}' (first run only; "
                "this may take several minutes)...[/yellow]"
            )

        try:
            for chunk in self._client.pull(self.model, stream=True):
                status = chunk.get("status", "")
                total = chunk.get("total") or 0
                completed = chunk.get("completed") or 0
                if console is not None and total:
                    pct = (completed / total) * 100
                    console.print(
                        f"  {status} — {pct:.1f}%",
                        end="\r",
                    )
                elif console is not None and status:
                    console.print(f"  {status}")
        except Exception as exc:
            raise OllamaUnavailableError(
                f"Failed to download model '{self.model}'. "
                "Check your internet connection and disk space, then try again."
            ) from exc

        if console is not None:
            console.print()

        if requested not in self._available_models():
            raise OllamaUnavailableError(
                f"Model '{self.model}' is still not available after download. "
                f"Try running: ollama pull {self.model}"
            )

        if console is not None:
            console.print(f"[green]Model '{self.model}' is ready.[/green]")

    def _require_model_present(self) -> None:
        requested = _base_model_name(self.model)
        if requested not in self._available_models():
            raise OllamaUnavailableError(
                f"Model '{self.model}' is not available. "
                f"Run: ollama pull {self.model}"
            )

    def ensure_ready(self, console: _ConsoleLike | None = None) -> None:
        if console is not None:
            console.print("[cyan]Checking Ollama...[/cyan]")
        self.ensure_service_running(console)
        self.ensure_model(console)
        self._require_model_present()
        if console is not None:
            console.print("[green]Ready. Opening Cryptoriale...[/green]")

    def verify(self) -> None:
        self.ensure_ready()

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

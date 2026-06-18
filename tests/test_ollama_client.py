from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from llm.client import OllamaClient, OllamaUnavailableError


def _client_with_mock(mock_client: MagicMock) -> OllamaClient:
    with patch("llm.client.ollama.Client", return_value=mock_client):
        return OllamaClient()


def test_ensure_model_skips_pull_when_present() -> None:
    mock = MagicMock()
    mock.list.return_value = {"models": [{"model": "llama3:latest"}]}
    client = _client_with_mock(mock)

    client.ensure_model()

    mock.pull.assert_not_called()


def test_ensure_model_pulls_when_missing() -> None:
    mock = MagicMock()
    mock.list.side_effect = [
        {"models": []},
        {"models": [{"model": "llama3:latest"}]},
    ]
    mock.pull.return_value = iter([{"status": "success"}])
    client = _client_with_mock(mock)

    client.ensure_model()

    mock.pull.assert_called_once_with("llama3", stream=True)


def test_ensure_service_running_starts_ollama_when_unreachable() -> None:
    mock = MagicMock()
    mock.list.side_effect = [Exception("down"), {"models": []}]
    client = _client_with_mock(mock)

    with patch("llm.client.subprocess.Popen") as popen, patch("llm.client.time.sleep"):
        popen.return_value = MagicMock()
        client.ensure_service_running()

    popen.assert_called_once()


def test_ensure_service_running_raises_when_ollama_not_installed() -> None:
    mock = MagicMock()
    mock.list.side_effect = Exception("down")
    client = _client_with_mock(mock)

    with patch("llm.client.subprocess.Popen", side_effect=FileNotFoundError()):
        with pytest.raises(OllamaUnavailableError, match="not installed"):
            client.ensure_service_running()


def test_ensure_service_running_times_out() -> None:
    mock = MagicMock()
    mock.list.side_effect = Exception("down")
    client = _client_with_mock(mock)

    with patch("llm.client.subprocess.Popen", return_value=MagicMock()), patch(
        "llm.client.time.monotonic", side_effect=[0.0, 100.0]
    ), patch("llm.client.time.sleep"):
        with pytest.raises(OllamaUnavailableError, match="did not respond"):
            client.ensure_service_running()


def test_ensure_ready_with_model_present() -> None:
    mock = MagicMock()
    mock.list.return_value = {"models": [{"model": "llama3:latest"}]}
    client = _client_with_mock(mock)

    client.ensure_ready()

    mock.pull.assert_not_called()

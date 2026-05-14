"""Entry point for Cryptoriale.

Verifies the local Ollama install and then hands control to the Pygame
front-end in :mod:`gui.app`.
"""

from __future__ import annotations

import sys

from rich.console import Console

from gui import app as gui_app
from llm.client import OllamaClient, OllamaUnavailableError
from llm.narrator import Narrator
from llm.parser import IntentParser


console = Console()


def main() -> int:
    try:
        client = OllamaClient()
        client.verify()
    except OllamaUnavailableError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    parser = IntentParser(client)
    narrator = Narrator(client)

    gui_app.run(parser, narrator)
    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from game import engine
from game.actions import ActionType
from game.models import GameOutcome, GameState
from game.world import build_initial_state
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

    while True:
        state = build_initial_state()
        if not run_game(state, parser, narrator):
            break
        if not ask_restart():
            break

    console.print("Farewell, adventurer.")
    return 0


def run_game(state: GameState, parser: IntentParser, narrator: Narrator) -> bool:
    console.print(
        Panel.fit(
            "[bold]Dungeon Adventure[/bold]\n"
            "A hybrid text dungeon powered by local Ollama narration.",
            border_style="cyan",
        )
    )
    console.print(engine.HELP_TEXT)

    opening = engine.apply_action(state, engine.parse_fallback("look") or _look_action())
    console.print(narrator.narrate(opening, state))

    while not state.game_over:
        render_status(state)
        user_input = console.input("[bold green]> [/bold green]").strip()
        action = parser.parse(user_input, state)
        if action.action == ActionType.QUIT:
            console.print("You leave the dungeon.")
            return True

        result = engine.apply_action(state, action)
        console.print(narrator.narrate(result, state))

    if state.outcome == GameOutcome.VICTORY:
        console.print("[bold cyan]Victory![/bold cyan]")
    elif state.outcome == GameOutcome.DEFEAT:
        console.print("[bold red]Defeat.[/bold red]")

    return True


def render_status(state: GameState) -> None:
    room = state.current_room()
    table = Table.grid(padding=(0, 2))
    table.add_row("Room", room.name)
    table.add_row("HP", f"{state.player.hp}/{state.player.max_hp}")
    table.add_row("Inventory", state.inventory_summary())
    console.print(Panel(table, title="Status", border_style="blue"))


def ask_restart() -> bool:
    answer = console.input("Play again? [y/n]: ").strip().lower()
    return answer in {"y", "yes"}


def _look_action():
    from game.actions import PlayerAction

    return PlayerAction(action=ActionType.LOOK)


if __name__ == "__main__":
    sys.exit(main())

"""Pygame window and scene orchestrator.

The :class:`App` owns the display, the clock, and a single background
:class:`LLMWorker` that runs the parser + engine + narrator off the UI
thread so the window stays responsive while Ollama is thinking.
"""

from __future__ import annotations

import queue
import random
import threading
import traceback
from dataclasses import dataclass
from typing import Optional

import pygame

from game import engine, nlp
from game.actions import ActionResult, ActionType, PlayerAction
from game.models import GameState
from gui.clipboard import init_clipboard
from llm.narrator import Narrator
from llm.parser import IntentParser

init_clipboard()


WINDOW_TITLE = "Cryptoriale"
FRAME_RATE = 60


def _display_flags(display_mode: str) -> int:
    if display_mode == "fullscreen":
        return pygame.FULLSCREEN
    if display_mode == "borderless":
        return pygame.NOFRAME
    return 0


def _should_break_chain(
    action: Optional[PlayerAction], result: Optional[ActionResult]
) -> bool:
    if action is not None and action.action == ActionType.QUIT:
        return True
    if result is None:
        return False
    if result.battle_pending:
        return True
    if result.descend:
        return True
    if result.open_quest_offer_ui or result.open_merchant_ui:
        return True
    if result.game_over:
        return True
    return False


def _clarify_if_chained_failure(
    index: int, segment: str, result: ActionResult
) -> tuple[ActionResult, bool]:
    if index == 0 or result.success:
        return result, False
    if result.narration_mode in ("clarify", "reject", "ask", "interact"):
        return result, False
    result.narration_mode = "clarify"
    result.player_intent = segment
    return result, True


@dataclass
class TurnResult:
    user_input: str
    action: Optional[PlayerAction]
    result: Optional[ActionResult]
    narration: str
    error: Optional[str] = None
    battle_pending: bool = False


class LLMWorker:
    """Runs parse / engine / narrate steps on a single background thread."""

    def __init__(self, parser: IntentParser, narrator: Narrator) -> None:
        self.parser = parser
        self.narrator = narrator
        self._jobs: "queue.Queue[tuple[GameState, str]]" = queue.Queue()
        self._results: "queue.Queue[TurnResult]" = queue.Queue()
        self._busy = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    @property
    def busy(self) -> bool:
        return self._busy.is_set()

    @property
    def pending_count(self) -> int:
        return self._jobs.qsize() + self._results.qsize()

    def submit_turn(self, state: GameState, user_input: str) -> bool:
        self._jobs.put((state, user_input))
        self._busy.set()
        return True

    def poll(self) -> Optional[TurnResult]:
        try:
            result = self._results.get_nowait()
        except queue.Empty:
            return None
        if self._jobs.empty() and self._results.empty():
            self._busy.clear()
        return result

    def _run_segment(self, state: GameState, segment: str) -> TurnResult:
        action = self.parser.parse(segment, state)
        result = engine.apply_action(state, action)
        if result is not None and result.battle_pending:
            narration = ""
        elif result is not None and (
            result.open_quest_offer_ui or result.open_merchant_ui
        ):
            narration = (result.message or "").strip()
        else:
            narration = self.narrator.narrate(result, state)
        return TurnResult(
            user_input=segment,
            action=action,
            result=result,
            narration=narration,
            battle_pending=bool(result.battle_pending) if result else False,
        )

    def _process_job(self, state: GameState, user_input: str) -> None:
        segments = nlp.split_player_commands(user_input)
        for index, segment in enumerate(segments):
            try:
                turn = self._run_segment(state, segment)
                if turn.result is not None:
                    turn.result, upgraded = _clarify_if_chained_failure(
                        index, segment, turn.result
                    )
                    if upgraded:
                        turn.narration = self.narrator.narrate(turn.result, state)
                self._results.put(turn)
                if _should_break_chain(turn.action, turn.result):
                    break
            except Exception as exc:  # pragma: no cover - safety net
                self._results.put(
                    TurnResult(
                        user_input=segment,
                        action=None,
                        result=None,
                        narration="",
                        error=f"{exc}\n{traceback.format_exc()}",
                        battle_pending=False,
                    )
                )
                break

    def _loop(self) -> None:
        while True:
            state, user_input = self._jobs.get()
            self._busy.set()
            try:
                self._process_job(state, user_input)
            except Exception as exc:  # pragma: no cover - safety net
                self._results.put(
                    TurnResult(
                        user_input=user_input,
                        action=None,
                        result=None,
                        narration="",
                        error=f"{exc}\n{traceback.format_exc()}",
                        battle_pending=False,
                    )
                )
            finally:
                if self._jobs.empty() and self._results.empty():
                    self._busy.clear()


class App:
    def __init__(self, parser: IntentParser, narrator: Narrator) -> None:
        from gui import settings as gui_settings

        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.settings = gui_settings.load_settings()
        self._size: tuple[int, int] = gui_settings.current_resolution(self.settings)
        self._display_mode: str = str(self.settings.get("display_mode", "windowed"))
        if self._display_mode not in gui_settings.DISPLAY_MODES:
            self._display_mode = "windowed"
        flags = _display_flags(self._display_mode)
        self.screen = pygame.display.set_mode(self._size, flags)
        self.clock = pygame.time.Clock()
        self.worker = LLMWorker(parser, narrator)
        self.rng = random.Random()
        self.running = True
        self._scene = None
        from gui.scenes import TitleScene

        self._scene = TitleScene(self)

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    @property
    def fullscreen(self) -> bool:
        return self._display_mode == "fullscreen"

    @property
    def display_mode(self) -> str:
        return self._display_mode

    def set_scene(self, scene) -> None:
        self._scene = scene

    def quit(self) -> None:
        self.running = False

    def apply_resolution(
        self,
        width: int,
        height: int,
        *,
        display_mode: str | None = None,
        fullscreen: bool | None = None,
    ) -> None:
        """Persist and switch to a new window size or display mode. Rebuilds the current scene
        because every scene reads its rects from ``app.size`` in ``__init__``."""

        from gui import settings as gui_settings
        from gui.scenes import TitleScene

        self._size = (int(width), int(height))
        if display_mode is not None:
            if display_mode in gui_settings.DISPLAY_MODES:
                self._display_mode = display_mode
        elif fullscreen is not None:
            self._display_mode = "fullscreen" if fullscreen else "windowed"
        self.settings["resolution"] = [self._size[0], self._size[1]]
        self.settings["display_mode"] = self._display_mode
        self.settings["fullscreen"] = self._display_mode == "fullscreen"
        gui_settings.save_settings(self.settings)

        flags = _display_flags(self._display_mode)
        self.screen = pygame.display.set_mode(self._size, flags)
        self._scene = TitleScene(self)

    def run(self) -> None:
        try:
            while self.running:
                dt = self.clock.tick(FRAME_RATE) / 1000.0
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        break
                    self._scene.handle_event(event)
                if not self.running:
                    break
                self._scene.update(dt)
                self._scene.draw(self.screen)
                pygame.display.flip()
        finally:
            pygame.quit()


def run(parser: IntentParser, narrator: Narrator) -> None:
    App(parser, narrator).run()

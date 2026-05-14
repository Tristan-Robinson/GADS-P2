"""Title, gameplay, and game-over scenes."""

from __future__ import annotations

import math
from typing import Optional

import pygame

from game import npc_engine
from game.actions import ActionResult, ActionType
from game.battle import (
    BattleChoice,
    BattleRoundOutcome,
    apply_enemy_turn,
    apply_player_turn,
    clear_pending_battle,
)
from game.levels import LevelTheme, next_level, theme_by_name
from game.models import GameOutcome, GameState
from game.world import build_initial_state
from gui.app import TurnResult
from gui.background import ThemeBackground
from gui.highlight import Span, highlight
from gui.inventory_overlay import InventoryOverlay
from gui.npc_overlays import MerchantOverlay, QuestOfferOverlay
from gui.pause_menu import PauseOverlay
from gui.widgets import (
    BattlePanel,
    Button,
    InputBox,
    LABEL_BRIGHT,
    LABEL_DIM,
    NarrationPanel,
    STATUS_BAR_HEIGHT,
    StatusBar,
)


def _make_fonts() -> dict[str, pygame.font.Font]:
    title = pygame.font.SysFont("georgia", 30, bold=True)
    big = pygame.font.SysFont("georgia", 54, bold=True)
    heading = pygame.font.SysFont("georgia", 19, bold=True)
    body = pygame.font.SysFont("georgia", 21)
    label = pygame.font.SysFont("verdana", 14)
    value = pygame.font.SysFont("verdana", 17)
    prompt = pygame.font.SysFont("consolas", 24, bold=True)
    button = pygame.font.SysFont("georgia", 22, bold=True)
    return {
        "title": title,
        "big": big,
        "heading": heading,
        "body": body,
        "label": label,
        "value": value,
        "prompt": prompt,
        "button": button,
    }


def _make_inventory_fonts() -> dict[str, pygame.font.Font]:
    """Larger fonts used only by the inventory overlay for readability."""

    heading = pygame.font.SysFont("georgia", 24, bold=True)
    body = pygame.font.SysFont("georgia", 25)
    label = pygame.font.SysFont("verdana", 17)
    caption = pygame.font.SysFont("verdana", 15)
    button = pygame.font.SysFont("georgia", 24, bold=True)
    return {
        "heading": heading,
        "body": body,
        "label": label,
        "caption": caption,
        "button": button,
    }


class TitleScene:
    def __init__(self, app) -> None:
        self.app = app
        self.fonts = _make_fonts()
        self.background = ThemeBackground(theme_by_name("Dungeon"), app.size, seed=1)
        cx = app.size[0] // 2
        cy = app.size[1] // 2
        self.descend_button = Button(
            pygame.Rect(cx - 130, cy + 60, 260, 56),
            "Descend",
            self.fonts["button"],
            on_click=self._start_game,
        )
        self.descend_button.set_border((220, 200, 140))
        self.settings_button = Button(
            pygame.Rect(cx - 130, cy + 130, 260, 48),
            "Settings",
            self.fonts["button"],
            on_click=self._open_settings,
        )
        self.settings_button.set_border((180, 170, 200))
        self.quit_button = Button(
            pygame.Rect(cx - 130, cy + 190, 260, 48),
            "Quit",
            self.fonts["button"],
            on_click=self.app.quit,
        )
        self.quit_button.set_border((200, 140, 140))
        self.subtitle_pulse = 0.0

    def _start_game(self) -> None:
        self.app.set_scene(GameScene(self.app))

    def _open_settings(self) -> None:
        self.app.set_scene(SettingsScene(self.app))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._start_game()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.quit()
            return
        self.descend_button.handle_event(event)
        self.settings_button.handle_event(event)
        self.quit_button.handle_event(event)

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.subtitle_pulse += dt

    def draw(self, surface: pygame.Surface) -> None:
        self.background.draw(surface)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 110))
        surface.blit(overlay, (0, 0))

        title = self.fonts["big"].render("Cryptoriale", True, (245, 230, 195))
        surface.blit(
            title,
            (surface.get_width() // 2 - title.get_width() // 2, surface.get_height() // 3 - 30),
        )

        sub = self.fonts["body"].render(
            "Endless descent narrated by a local model.",
            True,
            (210, 200, 180),
        )
        surface.blit(
            sub,
            (
                surface.get_width() // 2 - sub.get_width() // 2,
                surface.get_height() // 3 + 36,
            ),
        )

        pulse = 0.5 + 0.5 * math.sin(self.subtitle_pulse * 2.0)
        hint_color = (
            int(180 + pulse * 60),
            int(170 + pulse * 50),
            int(140 + pulse * 60),
        )
        hint = self.fonts["label"].render(
            "Press Enter to descend. Esc quits from this screen.",
            True,
            hint_color,
        )
        surface.blit(
            hint,
            (
                surface.get_width() // 2 - hint.get_width() // 2,
                surface.get_height() // 2 + 260,
            ),
        )

        self.descend_button.draw(surface)
        self.settings_button.draw(surface)
        self.quit_button.draw(surface)


class GameScene:
    def __init__(self, app) -> None:
        self.app = app
        self.fonts = _make_fonts()
        self.state: GameState = build_initial_state()
        self.state.auto_equip_gear = bool(self.app.settings.get("auto_equip_gear", True))
        self.theme: LevelTheme = theme_by_name(self.state.theme_name)
        self.background = ThemeBackground(self.theme, app.size)

        w, h = app.size
        margin = 20
        status_h = STATUS_BAR_HEIGHT
        input_h = 64
        main_w = max(280, w - margin * 2)

        self.status_bar = StatusBar(
            pygame.Rect(margin, margin, w - margin * 2, status_h),
            self.fonts["title"],
            self.fonts["label"],
            self.fonts["value"],
        )

        narration_top = margin + status_h + 16
        top_bar_y = narration_top
        bar_btn_w, bar_btn_h = 100, 32
        bar_gap = 8
        bar_total = bar_btn_w * 2 + bar_gap
        bar_left = w // 2 - bar_total // 2
        narration_top += bar_btn_h + 10
        narration_bottom = h - margin - input_h - 16
        self.narration = NarrationPanel(
            pygame.Rect(
                margin,
                narration_top,
                main_w,
                narration_bottom - narration_top,
            ),
            self.fonts["body"],
            self.fonts["heading"],
        )

        self.pause_button = Button(
            pygame.Rect(bar_left, top_bar_y, bar_btn_w, bar_btn_h),
            "Pause",
            self.fonts["button"],
            on_click=self._open_pause_menu,
        )
        self.pack_button = Button(
            pygame.Rect(bar_left + bar_btn_w + bar_gap, top_bar_y, bar_btn_w, bar_btn_h),
            "Pack",
            self.fonts["button"],
            on_click=self._open_inventory_overlay,
        )

        self.input_box = InputBox(
            pygame.Rect(margin, h - margin - input_h, main_w, input_h),
            self.fonts["body"],
            self.fonts["prompt"],
        )

        battle_margin = 16
        self.battle_panel = BattlePanel(
            pygame.Rect(
                battle_margin,
                battle_margin,
                w - battle_margin * 2,
                h - battle_margin * 2,
            ),
            self.fonts["heading"],
            self.fonts["body"],
            self.fonts["button"],
            self.theme.palette[2],
            self._on_battle_choice,
        )

        self._battle_active = False

        self._inventory_open = False
        self.inventory_overlay = InventoryOverlay(
            _make_inventory_fonts(),
            self.theme.palette[2],
            on_close=self._close_inventory,
        )

        self._pause_open = False
        self.pause_overlay = PauseOverlay(self.fonts)

        self._quest_offer_open = False
        self._merchant_open = False
        self._quest_overlay = QuestOfferOverlay(
            self.fonts,
            on_accept=npc_engine.accept_quest,
            on_decline=npc_engine.decline_quest,
            on_close=self._close_quest_offer_ui,
        )
        self._merchant_overlay = MerchantOverlay(
            self.fonts,
            on_buy=npc_engine.merchant_buy,
            on_sell=npc_engine.merchant_sell,
            on_close=self._close_merchant_ui,
        )

        self._apply_theme(self.theme)

        self.flash_timer = 0.0
        self.flash_duration = 1.4
        self.flash_active = False
        self.flash_message = ""

        self._submit_initial_look()

    def _submit_initial_look(self) -> None:
        self.app.worker.submit_turn(self.state, "look")

    def _apply_theme(self, theme: LevelTheme) -> None:
        accent = theme.palette[2]
        self.status_bar.set_border(accent)
        self.narration.set_border(accent)
        self.input_box.set_border(accent)
        self.battle_panel.set_button_borders(accent)
        self.inventory_overlay.accent = accent
        self.pause_overlay.set_accent(accent)
        self.pause_button.set_border(accent)
        self.pack_button.set_border(accent)

    def _open_pause_menu(self) -> None:
        self._inventory_open = False
        self._pause_open = True
        self.pause_overlay.open()

    def _open_inventory_overlay(self) -> None:
        if self._battle_active:
            return
        self._inventory_open = True

    def _close_inventory(self) -> None:
        self._inventory_open = False

    def _close_quest_offer_ui(self) -> None:
        self._quest_offer_open = False
        self.state.draft_quest_offer = None

    def _close_merchant_ui(self) -> None:
        self._merchant_open = False
        self._merchant_overlay.reset_selection()

    def _append_npc_message(self, result: ActionResult, *, heading: str = "NPC") -> None:
        msg = (result.message or "").strip()
        if not msg:
            return
        color = LABEL_BRIGHT if result.success else (255, 120, 120)
        self.narration.append([Span(msg, color)], heading=heading, accent=self.theme.palette[2])
        self.narration.scroll_to_bottom()

    def _quit_to_title(self) -> None:
        if self._battle_active:
            clear_pending_battle(self.state)
            self._battle_active = False
        self._inventory_open = False
        self._pause_open = False
        self._quest_offer_open = False
        self._merchant_open = False
        self.app.set_scene(TitleScene(self.app))

    def _append_engine_message(self, result: ActionResult) -> None:
        msg = (result.message or "").strip()
        if not msg:
            return
        color = LABEL_BRIGHT if result.success else (255, 120, 120)
        self.narration.append(
            [Span(msg, color)],
            heading="BACKPACK",
            accent=self.theme.palette[2],
        )
        self.narration.scroll_to_bottom()

    def handle_event(self, event: pygame.event.Event) -> None:
        screen_rect = pygame.Rect(0, 0, *self.app.size)

        if self._pause_open:
            self.pause_overlay.handle_event(event, screen_rect)
            choice = self.pause_overlay.take_choice()
            if choice == "resume":
                self._pause_open = False
            elif choice == "quit_menu":
                self._quit_to_title()
            elif choice == "quit_desktop":
                self.app.quit()
            return

        if self._quest_offer_open:
            r = self._quest_overlay.handle_event(event, self.state, screen_rect)
            if r is not None:
                self._append_npc_message(r, heading="QUEST")
            self._quest_offer_open = bool(self.state.draft_quest_offer)
            return

        if self._merchant_open:
            r = self._merchant_overlay.handle_event(event, self.state, screen_rect)
            if r is not None:
                self._append_npc_message(r, heading="MERCHANT")
            return

        if self.pause_button.handle_event(event):
            self._open_pause_menu()
            return
        if not self._battle_active and self.pack_button.handle_event(event):
            return

        if self._inventory_open:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._inventory_open = False
                return
            inv_result = self.inventory_overlay.handle_event(
                event,
                self.state,
                screen_rect,
                busy=self.app.worker.busy,
            )
            if inv_result is not None:
                msg = (inv_result.message or "").strip()
                if msg:
                    self.inventory_overlay.notify(msg, error=not inv_result.success)
                else:
                    self.inventory_overlay.notify(
                        "Nothing changed." if inv_result.success else "That cannot be done.",
                        error=not inv_result.success,
                    )
                self._append_engine_message(inv_result)
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._open_pause_menu()
            return
        if self._battle_active:
            self.battle_panel.handle_event(event, self.state)
            return
        self.narration.handle_event(event)
        submitted = self.input_box.handle_event(event)
        if submitted:
            if not self.app.worker.submit_turn(self.state, submitted):
                return

    def update(self, dt: float) -> None:
        self.background.update(dt)
        self.input_box.update(dt)
        self.input_box.set_enabled(
            not self.app.worker.busy
            and not self._battle_active
            and not self._inventory_open
            and not self._pause_open
            and not self._quest_offer_open
            and not self._merchant_open
        )

        turn = self.app.worker.poll()
        if turn is not None:
            self._handle_turn(turn)

        if self.flash_active:
            self.flash_timer += dt
            if self.flash_timer >= self.flash_duration:
                self.flash_active = False
                self.flash_timer = 0.0

    def _handle_turn(self, turn: TurnResult) -> None:
        if turn.error:
            self.narration.append(
                [Span(f"Engine error: {turn.error}", (255, 120, 120))],
                heading="ERROR",
                accent=self.theme.palette[2],
            )
            return

        action = turn.action
        result = turn.result

        if action is not None and action.action == ActionType.QUIT:
            self.app.set_scene(TitleScene(self.app))
            return

        if result is not None and result.battle_pending:
            prelude = (result.message or "Combat begins.").strip()
            self.narration.append(
                [Span(prelude, LABEL_BRIGHT)],
                heading="FIGHT",
                accent=self.theme.palette[2],
            )
            self.narration.scroll_to_bottom()
            self._battle_active = True
            self.battle_panel.clear_log()
            return

        if (
            result is not None
            and result.success
            and result.action == ActionType.INVENTORY
        ):
            self._inventory_open = True

        if result is not None and result.open_quest_offer_ui:
            self._quest_offer_open = True
        if result is not None and result.open_merchant_ui:
            self._merchant_open = True
            self._merchant_overlay.reset_selection()

        narration_text = turn.narration.strip() or (result.message if result else "")
        if not narration_text:
            narration_text = "..."
        spans = highlight(narration_text, self.state)
        heading = self._heading_for(turn)
        self.narration.append(spans, heading=heading, accent=self.theme.palette[2])
        self.narration.scroll_to_bottom()

        if result is not None and result.descend:
            self._descend()
            return

        if self.state.game_over and self.state.outcome == GameOutcome.DEFEAT:
            self.app.set_scene(GameOverScene(self.app, self.state))

    def _on_battle_choice(self, choice: BattleChoice, spell_id: str | None = None) -> None:
        eid = self.state.pending_battle_enemy_id
        if not eid or not self._battle_active:
            return
        p = apply_player_turn(self.state, eid, choice, spell_id=spell_id)
        narr_lines: list[str] = []
        for line in p.log_lines:
            self.battle_panel.push_log(line)
            narr_lines.append(line)
        outcome = p
        if p.await_enemy_strike and not p.battle_ended:
            self.battle_panel.push_log("— Enemy turn —")
            narr_lines.append("— Enemy turn —")
            e = apply_enemy_turn(self.state, eid)
            for line in e.log_lines:
                self.battle_panel.push_log(line)
                narr_lines.append(line)
            outcome = BattleRoundOutcome(
                log_lines=narr_lines,
                battle_ended=e.battle_ended,
                victory=p.victory or e.victory,
                surrendered=p.surrendered,
                player_defeated=e.player_defeated,
                loot_dropped=list(p.loot_dropped),
            )

        self.narration.append(
            [Span(line, LABEL_DIM) for line in narr_lines],
            heading="BATTLE",
            accent=self.theme.palette[2],
        )
        self.narration.scroll_to_bottom()

        if outcome.player_defeated and self.state.game_over:
            self._battle_active = False
            self.battle_panel.clear_log()
            self.app.set_scene(GameOverScene(self.app, self.state))
            return

        if outcome.battle_ended:
            self._battle_active = False
            self.battle_panel.clear_log()
            if outcome.victory:
                summary = "You stand victorious over the foe."
                if outcome.loot_dropped:
                    npc_engine.drop_loot_to_room(self.state, outcome.loot_dropped)
                    loot_names = ", ".join(x.name for x in outcome.loot_dropped)
                    self.narration.append(
                        [Span(f"Loot scattered here: {loot_names}.", LABEL_DIM)],
                        heading="LOOT",
                        accent=self.theme.palette[2],
                    )
                npc_engine.mark_quest_slay_ready(self.state, eid)
            elif outcome.surrendered:
                summary = "You withdraw—you can explore while the enemy hangs back."
            else:
                summary = "The fight ends."
            self.narration.append(
                [Span(summary, LABEL_BRIGHT)],
                heading="RESULT",
                accent=self.theme.palette[2],
            )
            self.narration.scroll_to_bottom()

    def _descend(self) -> None:
        self._inventory_open = False
        self._pause_open = False
        self._quest_offer_open = False
        self._merchant_open = False
        self.state.draft_quest_offer = None
        new_theme = next_level(self.state, self.app.rng)
        self.theme = new_theme
        self.background = ThemeBackground(new_theme, self.app.size)
        self._apply_theme(new_theme)
        self.flash_active = True
        self.flash_timer = 0.0
        self.flash_message = f"Depth {self.state.level_depth}: {new_theme.name}"
        descent_spans = [
            Span(
                f"You descend into the {new_theme.name}. "
                f"Depth {self.state.level_depth}.",
                (255, 255, 255),
            )
        ]
        self.narration.append(
            descent_spans,
            heading="DESCENT",
            accent=new_theme.palette[2],
        )
        self.app.worker.submit_turn(self.state, "look")

    def _heading_for(self, turn: TurnResult) -> str:
        if turn.action is None:
            return "..."
        verb = turn.action.action.value.upper()
        cleaned = turn.user_input.strip()
        if cleaned and cleaned.lower() != verb.lower():
            return f"{verb} - {cleaned}"
        return verb

    def draw(self, surface: pygame.Surface) -> None:
        self.background.draw(surface)

        self.status_bar.draw(surface, self.state, thinking=self.app.worker.busy)
        self.narration.draw(surface)
        self.input_box.draw(surface, thinking=self.app.worker.busy)
        if self._battle_active:
            self.battle_panel.draw(surface, self.state)
        if not self._pause_open:
            self.pause_button.draw(surface)
            if not self._battle_active:
                self.pack_button.draw(surface)

        if self._inventory_open:
            self.inventory_overlay.draw(surface, self.state, busy=self.app.worker.busy)

        if self._quest_offer_open:
            self._quest_overlay.draw(surface, self.state)
        if self._merchant_open:
            self._merchant_overlay.draw(surface, self.state)

        if self._pause_open:
            self.pause_overlay.draw(surface, surface.get_rect())

        if self.flash_active:
            progress = self.flash_timer / self.flash_duration
            alpha = max(0, int(220 * (1 - progress)))
            flash = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            flash.fill((*self.theme.palette[2], alpha // 3))
            surface.blit(flash, (0, 0))
            banner_alpha = max(0, int(255 * (1 - progress * 0.8)))
            banner = self.fonts["big"].render(self.flash_message, True, (255, 250, 240))
            banner.set_alpha(banner_alpha)
            surface.blit(
                banner,
                (
                    surface.get_width() // 2 - banner.get_width() // 2,
                    surface.get_height() // 2 - banner.get_height() // 2,
                ),
            )


class GameOverScene:
    def __init__(self, app, state: GameState) -> None:
        self.app = app
        self.state = state
        self.fonts = _make_fonts()
        self.background = ThemeBackground(
            theme_by_name(state.theme_name), app.size, seed=7
        )
        cx = app.size[0] // 2
        cy = app.size[1] // 2
        self.restart_button = Button(
            pygame.Rect(cx - 280, cy + 80, 260, 56),
            "Descend Again",
            self.fonts["button"],
            on_click=self._restart,
        )
        self.quit_button = Button(
            pygame.Rect(cx + 20, cy + 80, 260, 56),
            "Quit",
            self.fonts["button"],
            on_click=self.app.quit,
        )
        accent = theme_by_name(state.theme_name).palette[2]
        self.restart_button.set_border(accent)
        self.quit_button.set_border(accent)

    def _restart(self) -> None:
        self.app.set_scene(GameScene(self.app))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._restart()
            return
        self.restart_button.handle_event(event)
        self.quit_button.handle_event(event)

    def update(self, dt: float) -> None:
        self.background.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.background.draw(surface)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        title = self.fonts["big"].render("You have fallen", True, (240, 110, 110))
        surface.blit(
            title,
            (
                surface.get_width() // 2 - title.get_width() // 2,
                surface.get_height() // 3,
            ),
        )

        depth_msg = (
            f"You reached depth {self.state.level_depth} - {self.state.theme_name}."
        )
        depth_surface = self.fonts["body"].render(depth_msg, True, LABEL_BRIGHT)
        surface.blit(
            depth_surface,
            (
                surface.get_width() // 2 - depth_surface.get_width() // 2,
                surface.get_height() // 3 + 80,
            ),
        )

        self.restart_button.draw(surface)
        self.quit_button.draw(surface)


class SettingsScene:
    def __init__(self, app) -> None:
        from gui import settings as gui_settings

        self.app = app
        self._gui_settings = gui_settings
        self.fonts = _make_fonts()
        self.background = ThemeBackground(
            theme_by_name("Dungeon"), app.size, seed=3
        )
        self.resolutions = list(gui_settings.RESOLUTIONS)

        cx = app.size[0] // 2
        top = max(120, min(160, app.size[1] // 5))
        self.title_y = top - 56

        button_w = 208
        button_h = 40
        gap = 10
        col_gap = 14
        pair_w = 2 * button_w + col_gap
        left_x = cx - pair_w // 2

        self.res_buttons: list[tuple[Button, tuple[int, int]]] = []
        for i, (w, h) in enumerate(self.resolutions):
            col = i % 2
            row = i // 2
            rect = pygame.Rect(
                left_x + col * (button_w + col_gap),
                top + row * (button_h + gap),
                button_w,
                button_h,
            )
            button = Button(
                rect,
                f"{w} x {h}",
                self.fonts["button"],
                on_click=lambda w=w, h=h: self._select_resolution(w, h),
            )
            self.res_buttons.append((button, (w, h)))

        rows = (len(self.resolutions) + 1) // 2
        toggle_y = top + rows * (button_h + gap) + 14
        mode_w = 132
        mode_gap = 10
        mode_row_w = 3 * mode_w + 2 * mode_gap
        mode_left = cx - mode_row_w // 2
        self.mode_buttons: list[tuple[Button, str]] = []
        for mi, (label, mode_id) in enumerate(
            (("Windowed", "windowed"), ("Borderless", "borderless"), ("Fullscreen", "fullscreen"))
        ):
            rect = pygame.Rect(
                mode_left + mi * (mode_w + mode_gap),
                toggle_y,
                mode_w,
                button_h,
            )
            self.mode_buttons.append(
                (
                    Button(
                        rect,
                        label,
                        self.fonts["button"],
                        on_click=lambda m=mode_id: self._set_display_mode(m),
                    ),
                    mode_id,
                )
            )
        auto_y = toggle_y + button_h + gap
        self.auto_equip_button = Button(
            pygame.Rect(cx - button_w // 2, auto_y, button_w, button_h),
            self._auto_equip_label(),
            self.fonts["button"],
            on_click=self._toggle_auto_equip,
        )
        back_y = auto_y + button_h + 18
        self.back_button = Button(
            pygame.Rect(cx - button_w // 2, back_y, button_w, button_h),
            "Back",
            self.fonts["button"],
            on_click=self._back,
        )

        self._refresh_borders()

    def _auto_equip_label(self) -> str:
        on = bool(self.app.settings.get("auto_equip_gear", True))
        return f"Auto-equip gear: {'on' if on else 'off'}"

    def _refresh_borders(self) -> None:
        active = (220, 200, 140)
        dim = (160, 150, 180)
        current = tuple(self.app.size)
        for button, size in self.res_buttons:
            button.set_border(active if tuple(size) == current else dim)
        cur_mode = self.app.display_mode
        for button, mode_id in self.mode_buttons:
            button.set_border(active if mode_id == cur_mode else dim)
        ae = bool(self.app.settings.get("auto_equip_gear", True))
        self.auto_equip_button.set_border(active if ae else dim)
        self.back_button.set_border((200, 190, 220))

    def _select_resolution(self, width: int, height: int) -> None:
        if tuple(self.app.size) == (width, height):
            return
        self.app.apply_resolution(width, height, display_mode=self.app.display_mode)

    def _set_display_mode(self, mode: str) -> None:
        if self.app.display_mode == mode:
            return
        self.app.apply_resolution(
            self.app.size[0], self.app.size[1], display_mode=mode
        )
        self._refresh_borders()

    def _toggle_auto_equip(self) -> None:
        cur = bool(self.app.settings.get("auto_equip_gear", True))
        self.app.settings["auto_equip_gear"] = not cur
        self._gui_settings.save_settings(self.app.settings)
        self.auto_equip_button.label = self._auto_equip_label()
        self._refresh_borders()

    def _back(self) -> None:
        self.app.set_scene(TitleScene(self.app))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._back()
            return
        for button, _ in self.res_buttons:
            button.handle_event(event)
        for button, _ in self.mode_buttons:
            button.handle_event(event)
        self.auto_equip_button.handle_event(event)
        self.back_button.handle_event(event)

    def update(self, dt: float) -> None:
        self.background.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.background.draw(surface)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        title = self.fonts["big"].render("Settings", True, (245, 230, 195))
        surface.blit(
            title,
            (
                surface.get_width() // 2 - title.get_width() // 2,
                self.title_y,
            ),
        )

        hint = self.fonts["label"].render(
            "Resolution; display: windowed, borderless (no frame), or fullscreen. Auto-equip. Esc: back.",
            True,
            LABEL_DIM,
        )
        surface.blit(
            hint,
            (
                surface.get_width() // 2 - hint.get_width() // 2,
                self.title_y + 70,
            ),
        )

        for button, _ in self.res_buttons:
            button.draw(surface)
        for button, _ in self.mode_buttons:
            button.draw(surface)
        self.auto_equip_button.label = self._auto_equip_label()
        self.auto_equip_button.draw(surface)
        self.back_button.draw(surface)

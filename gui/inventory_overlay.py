"""Inventory and equipment overlay (open from the inventory command)."""

from __future__ import annotations

import time
from collections.abc import Callable

import pygame

from game import engine
from game.actions import ActionResult, ActionType, PlayerAction
from game.models import GameState, Item, ItemKind
from gui.highlight import Color
from gui.widgets import LABEL_BRIGHT, LABEL_DIM, Button, draw_panel, fit_text

ROW_H = 68
ROW_GAP = 8
ROW_STRIDE = ROW_H + ROW_GAP
ROW_PAD_Y = 8
NAME_SUMMARY_GAP = 6

_TAB_DEFS: tuple[tuple[str, str], ...] = (
    ("all", "All"),
    ("gear", "Gear"),
    ("use", "Use"),
    ("other", "Other"),
    ("info", "Info"),
)

_GEAR_KINDS = frozenset(
    {ItemKind.WEAPON, ItemKind.ARMOR, ItemKind.RING, ItemKind.AMULET}
)
_USE_KINDS = frozenset({ItemKind.POTION, ItemKind.BUFF, ItemKind.SPELL})


def _row_rect(list_rect: pygame.Rect, index: int) -> pygame.Rect:
    return pygame.Rect(
        list_rect.left,
        list_rect.top + index * ROW_STRIDE,
        list_rect.width,
        ROW_H,
    )


def _row_index_from_click(list_rect: pygame.Rect, click_y: int) -> int | None:
    local_y = click_y - list_rect.top
    if local_y < 0:
        return None
    row = local_y // ROW_STRIDE
    if local_y % ROW_STRIDE >= ROW_H:
        return None
    return row


def _sorted_inventory(state: GameState) -> list[Item]:
    return sorted(state.player.inventory, key=lambda i: (i.name.lower(), i.id))


def _filtered_inventory(state: GameState, category: str) -> list[Item]:
    all_items = _sorted_inventory(state)
    if category == "all":
        return all_items
    if category == "gear":
        return [i for i in all_items if i.kind in _GEAR_KINDS]
    if category == "use":
        return [i for i in all_items if i.kind in _USE_KINDS]
    if category == "other":
        return [i for i in all_items if i.kind not in _GEAR_KINDS and i.kind not in _USE_KINDS]
    if category == "info":
        return []
    return all_items


def _equipped_display_name(state: GameState, item_id: str | None) -> str:
    if not item_id:
        return "—"
    for it in state.player.inventory:
        if it.id == item_id:
            return it.name
    return "—"


def _kind_label(kind: ItemKind) -> str:
    if kind == ItemKind.POTION:
        return "POT"
    if kind == ItemKind.BUFF:
        return "BUF"
    if kind == ItemKind.KEY:
        return "KEY"
    if kind == ItemKind.SPELL:
        return "SPL"
    return kind.value[:4].upper()


def _kind_title(kind: ItemKind) -> str:
    return kind.value.replace("_", " ").title()


def _wrap_lines(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.strip().split("\n"):
        words = paragraph.split()
        if not words:
            continue
        cur = words[0]
        for w in words[1:]:
            cand = f"{cur} {w}"
            if font.size(cand)[0] <= max_width:
                cur = cand
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def _item_one_line_summary(item: Item) -> str:
    k = item.kind
    if k == ItemKind.WEAPON and item.weapon_damage:
        return f"+{item.weapon_damage} damage when equipped"
    if k == ItemKind.ARMOR:
        parts: list[str] = []
        if item.defense_bonus:
            parts.append(f"+{item.defense_bonus} mitigation")
        if item.armor_bonus:
            parts.append(f"+{item.armor_bonus} armor")
        return ", ".join(parts) if parts else "Armor"
    if k in (ItemKind.RING, ItemKind.AMULET):
        bits: list[str] = []
        if item.strength_bonus:
            bits.append(f"+{item.strength_bonus} STR")
        if item.agility_bonus:
            bits.append(f"+{item.agility_bonus} AGI")
        if item.armor_bonus:
            bits.append(f"+{item.armor_bonus} ARM")
        return " · ".join(bits) if bits else "Jewelry"
    if k == ItemKind.POTION and item.consumable and item.heal_amount:
        return f"Heals up to {item.heal_amount} HP"
    if k == ItemKind.BUFF and item.consumable:
        bits = []
        if item.max_hp_bonus:
            bits.append(f"+{item.max_hp_bonus} max HP")
        if item.strength_bonus:
            bits.append(f"+{item.strength_bonus} STR")
        if item.agility_bonus:
            bits.append(f"+{item.agility_bonus} AGI")
        if item.armor_bonus:
            bits.append(f"+{item.armor_bonus} ARM")
        return "Buff: " + ", ".join(bits) if bits else "Permanent stat buff"
    if k == ItemKind.KEY:
        return "Unlocks matching doors"
    if k == ItemKind.SPELL and item.spell_grant_id:
        return f"Teaches spell ({item.spell_grant_id})"
    from game.economy import sell_value

    price = sell_value(item)
    if price > 0:
        return f"Sell value ~{price} gold"
    return (item.description or "")[:72] + ("…" if len(item.description or "") > 72 else "")


def _item_effect_lines(item: Item) -> list[str]:
    out: list[str] = []
    k = item.kind

    if k == ItemKind.WEAPON and item.weapon_damage:
        out.append(f"Damage when equipped: +{item.weapon_damage}")
    if k == ItemKind.ARMOR:
        if item.defense_bonus:
            out.append(f"Extra mitigation from this armor: +{item.defense_bonus}")
        if item.armor_bonus:
            out.append(f"Armor rating from gear: +{item.armor_bonus}")
    if k in (ItemKind.RING, ItemKind.AMULET):
        if item.strength_bonus:
            out.append(f"Strength while worn: +{item.strength_bonus}")
        if item.agility_bonus:
            out.append(f"Agility while worn: +{item.agility_bonus}")
        if item.armor_bonus:
            out.append(f"Armor while worn: +{item.armor_bonus}")

    if k == ItemKind.POTION and item.consumable and item.heal_amount:
        out.append(f"Heals up to {item.heal_amount} HP when drunk.")

    if k == ItemKind.BUFF and item.consumable:
        bits: list[str] = []
        if item.max_hp_bonus:
            bits.append(f"+{item.max_hp_bonus} max HP")
        if item.strength_bonus:
            bits.append(f"+{item.strength_bonus} strength")
        if item.agility_bonus:
            bits.append(f"+{item.agility_bonus} agility")
        if item.armor_bonus:
            bits.append(f"+{item.armor_bonus} armor")
        if bits:
            out.append("When drunk, permanently gains: " + ", ".join(bits) + ".")
        else:
            out.append("Buff vial: drink for permanent stat bonuses.")

    if k == ItemKind.KEY:
        out.append("Unlocks matching locked exits when used in the right room.")

    if k == ItemKind.SPELL and item.spell_grant_id:
        out.append("Read to learn the inscribed spell for combat.")

    if k in (ItemKind.WEAPON, ItemKind.ARMOR, ItemKind.RING, ItemKind.AMULET):
        out.append("Use / Equip toggles wearing this piece.")
    elif k == ItemKind.SPELL:
        out.append("Use from the pack to learn the spell.")
    elif item.usable and k not in (ItemKind.KEY, ItemKind.POTION, ItemKind.BUFF):
        out.append("May be usable in specific situations.")

    if not item.usable:
        out.append("Cannot be used from the pack.")

    return out if out else ["No combat bonuses on this item."]


class InventoryOverlay:
    def __init__(
        self,
        fonts: dict[str, pygame.font.Font],
        accent: Color,
        *,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        self.fonts = fonts
        self.accent = accent
        self._on_close = on_close
        self._scroll = 0
        self._info_scroll = 0
        self._sel = 0
        self._category_tab = "all"
        self._selected_item_id: str | None = None
        self._panel_rect = pygame.Rect(0, 0, 0, 0)
        self._list_rect = pygame.Rect(0, 0, 0, 0)
        self._max_rows = 1
        self._use_rect = pygame.Rect(0, 0, 0, 0)
        self._notif_rect = pygame.Rect(0, 0, 0, 0)
        self._tab_rects: list[tuple[pygame.Rect, str, str]] = []
        self._unequip_boxes: list[tuple[pygame.Rect, str]] = []
        self._notify_text: str = ""
        self._notify_error: bool = False
        self._notify_until: float = 0.0
        self._close_btn = Button(
            pygame.Rect(0, 0, 1, 1),
            "Close inventory",
            fonts["button"],
            on_click=self._invoke_close,
        )

    def _invoke_close(self) -> None:
        if self._on_close is not None:
            self._on_close()

    def notify(self, message: str, *, error: bool = False) -> None:
        text = (message or "").strip()
        if len(text) > 420:
            text = text[:417] + "..."
        self._notify_text = text
        self._notify_error = error
        self._notify_until = time.monotonic() + 6.0

    def _layout(self, screen: pygame.Rect) -> None:
        pad = 22
        self._panel_rect = pygame.Rect(pad, pad, screen.width - 2 * pad, screen.height - 2 * pad)
        inner = 16
        x0 = self._panel_rect.left + inner
        total_w = self._panel_rect.width - 2 * inner
        split = int(total_w * 0.34)
        left_w = split - 10
        right_x = x0 + split + 10
        right_w = total_w - split - 10

        y = self._panel_rect.top + inner
        title_block_h = self.fonts["heading"].get_height() + 8 + self.fonts["label"].get_height() + 8
        tab_y = y + title_block_h
        tab_h = 32
        n_tabs = len(_TAB_DEFS)
        tab_gap = 6
        tab_w = max(52, (left_w - (n_tabs - 1) * tab_gap) // n_tabs)
        self._tab_rects = []
        tx = x0
        for key, label in _TAB_DEFS:
            self._tab_rects.append((pygame.Rect(tx, tab_y, tab_w, tab_h), key, label))
            tx += tab_w + tab_gap
        list_top = tab_y + tab_h + 10

        footer_h = 52
        notif_h = 42
        list_bottom = self._panel_rect.bottom - inner - footer_h - notif_h - 10
        self._list_rect = pygame.Rect(x0, list_top, left_w, max(ROW_H, list_bottom - list_top))
        self._max_rows = max(1, self._list_rect.height // ROW_STRIDE)

        self._notif_rect = pygame.Rect(x0, list_bottom + 4, left_w, notif_h)

        footer_y = self._panel_rect.bottom - inner - 44
        self._use_rect = pygame.Rect(x0, footer_y, 168, 40)
        self._close_btn.rect = pygame.Rect(self._use_rect.right + 12, footer_y, 188, 40)

        self._loadout_right = (right_x, right_w, list_top)

    def _item_for_info(self, state: GameState) -> Item | None:
        if self._selected_item_id:
            for it in state.player.inventory:
                if it.id == self._selected_item_id:
                    return it
        return None

    def _sync_selection(self, state: GameState, filtered: list[Item]) -> None:
        if not filtered:
            self._sel = 0
            return
        if self._selected_item_id:
            for i, it in enumerate(filtered):
                if it.id == self._selected_item_id:
                    self._sel = i
                    return
        self._sel = max(0, min(self._sel, len(filtered) - 1))
        self._selected_item_id = filtered[self._sel].id

    def handle_event(
        self,
        event: pygame.event.Event,
        state: GameState,
        screen_rect: pygame.Rect,
        *,
        busy: bool,
    ) -> ActionResult | None:
        self._layout(screen_rect)
        self._close_btn.set_border(self.accent)
        if self._close_btn.handle_event(event):
            return None
        if busy:
            return None

        if self._category_tab == "info":
            filtered: list[Item] = []
        else:
            filtered = _filtered_inventory(state, self._category_tab)
            self._sync_selection(state, filtered)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, key, _label in self._tab_rects:
                if rect.collidepoint(event.pos):
                    if key != self._category_tab:
                        self._info_scroll = 0
                        self._scroll = 0
                    self._category_tab = key
                    if key != "info":
                        nf = _filtered_inventory(state, key)
                        self._sync_selection(state, nf)
                    return None

        if event.type == pygame.MOUSEWHEEL:
            if self._list_rect.collidepoint(pygame.mouse.get_pos()):
                if self._category_tab != "info":
                    n = len(filtered)
                    max_scroll = max(0, n - self._max_rows)
                    self._scroll = max(0, min(max_scroll, self._scroll - event.y))
                else:
                    it = self._item_for_info(state)
                    items_all = _sorted_inventory(state)
                    max_scroll = max(
                        0,
                        self._info_scroll_max(state, items_all, it) - self._list_rect.height,
                    )
                    self._info_scroll = max(0, min(max_scroll, self._info_scroll - event.y * 28))
                return None

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        if self._use_rect.collidepoint(event.pos):
            if self._category_tab == "info" or not filtered:
                return None
            self._sync_selection(state, filtered)
            target = filtered[self._sel].name
            return engine.apply_action(state, PlayerAction(action=ActionType.USE, target=target))

        for rect, slot in self._unequip_boxes:
            if rect.collidepoint(event.pos):
                return engine.unequip_slot(state, slot)

        if self._category_tab != "info" and self._list_rect.collidepoint(event.pos):
            row = _row_index_from_click(self._list_rect, event.pos[1])
            if row is None:
                return None
            idx = self._scroll + row
            if 0 <= idx < len(filtered):
                if self._sel != idx:
                    self._info_scroll = 0
                self._sel = idx
                self._selected_item_id = filtered[idx].id
            return None

        return None

    def _info_content_lines(
        self, state: GameState, items_all: list[Item], selected: Item | None
    ) -> list[tuple[str, bool]]:
        """(text, is_heading) for the info tab."""

        if selected is None:
            return [
                ("No item selected.", False),
                ("Pick All, Gear, Use, or Other and click a row, then open Info.", False),
            ]
        it = selected
        lines: list[tuple[str, bool]] = []
        lines.append((it.name, True))
        lines.append((f"Type: {_kind_title(it.kind)}", False))
        lines.append(("", False))
        desc = (it.description or "No written description.").strip()
        for ln in _wrap_lines(self.fonts["body"], desc, max(60, self._list_rect.width - 8)):
            lines.append((ln, False))
        lines.append(("", False))
        lines.append(("Effects & use", True))
        for el in _item_effect_lines(it):
            for ln in _wrap_lines(self.fonts["label"], el, max(60, self._list_rect.width - 8)):
                lines.append((ln, False))
        return lines

    def _info_scroll_max(
        self, state: GameState, items_all: list[Item], selected: Item | None
    ) -> int:
        info_lines = self._info_content_lines(state, items_all, selected)
        iy = 0
        mw = max(40, self._list_rect.width - 12)
        for text, is_head in info_lines:
            font = self.fonts["heading"] if is_head else self.fonts["body"]
            if not text.strip() and not is_head:
                iy += 6
                continue
            for _ln in _wrap_lines(font, text, mw):
                iy += font.get_height() + 2
            if is_head:
                iy += 4
        return iy

    def draw(self, surface: pygame.Surface, state: GameState, *, busy: bool) -> None:
        screen = surface.get_rect()
        veil = pygame.Surface(screen.size, pygame.SRCALPHA)
        veil.fill((0, 0, 0, 130))
        surface.blit(veil, (0, 0))

        self._layout(screen)
        draw_panel(surface, self._panel_rect, border_color=self.accent)

        x0 = self._panel_rect.left + 16
        y = self._panel_rect.top + 16

        title = self.fonts["heading"].render("Inventory & gear", True, LABEL_BRIGHT)
        surface.blit(title, (x0, y))
        hint_y = y + self.fonts["heading"].get_height() + 6
        hint = self.fonts["label"].render(
            "Tabs sort your pack. Subtext under each row summarizes stats. Esc or Close hides this.",
            True,
            LABEL_DIM,
        )
        surface.blit(hint, (x0, hint_y))

        for rect, key, label in self._tab_rects:
            active = key == self._category_tab
            fill = (28, 40, 52, 230) if active else (18, 18, 24, 200)
            draw_panel(surface, rect, border_color=self.accent, fill=fill)
            col = LABEL_BRIGHT if active else LABEL_DIM
            sf = fit_text(self.fonts["label"], label, rect.width - 8)
            lab = self.fonts["label"].render(sf, True, col)
            surface.blit(lab, (rect.centerx - lab.get_width() // 2, rect.centery - lab.get_height() // 2))

        items_all = _sorted_inventory(state)
        filtered = _filtered_inventory(state, self._category_tab)
        if self._category_tab != "info":
            self._sync_selection(state, filtered)
            max_scroll = max(0, len(filtered) - self._max_rows)
            self._scroll = max(0, min(max_scroll, self._scroll))
        else:
            filtered = []

        cap_font = self.fonts.get("caption") or self.fonts["label"]

        if self._category_tab != "info":
            for i in range(self._max_rows):
                idx = self._scroll + i
                if idx >= len(filtered):
                    break
                item = filtered[idx]
                row_rect = _row_rect(self._list_rect, i)
                if idx == self._sel:
                    sel_surf = pygame.Surface(row_rect.size, pygame.SRCALPHA)
                    sel_surf.fill((*self.accent[:3], 35))
                    surface.blit(sel_surf, row_rect.topleft)
                    pygame.draw.rect(surface, self.accent, row_rect, 1, border_radius=6)

                tag = self.fonts["label"].render(_kind_label(item.kind), True, LABEL_DIM)
                surface.blit(tag, (row_rect.left + 6, row_rect.top + ROW_PAD_Y))
                name_x = row_rect.left + 50
                name_w = row_rect.width - 54
                name_line = fit_text(self.fonts["body"], item.name, name_w)
                name_sf = self.fonts["body"].render(name_line, True, LABEL_BRIGHT)
                surface.blit(name_sf, (name_x, row_rect.top + ROW_PAD_Y))
                sub = _item_one_line_summary(item)
                sub_fit = fit_text(cap_font, sub, name_w)
                sub_sf = cap_font.render(sub_fit, True, LABEL_DIM)
                surface.blit(
                    sub_sf,
                    (name_x, row_rect.top + ROW_PAD_Y + name_sf.get_height() + NAME_SUMMARY_GAP),
                )
        else:
            clip = surface.get_clip()
            surface.set_clip(self._list_rect)
            selected = self._item_for_info(state)
            info_lines = self._info_content_lines(state, items_all, selected)
            iy = self._list_rect.top - self._info_scroll
            ix = self._list_rect.left + 4
            mw = max(40, self._list_rect.width - 12)
            for text, is_head in info_lines:
                if iy > self._list_rect.bottom:
                    break
                font = self.fonts["heading"] if is_head else self.fonts["body"]
                color = self.accent if is_head else LABEL_DIM
                if not text.strip() and not is_head:
                    iy += 6
                    continue
                for ln in _wrap_lines(font, text, mw):
                    if iy > self._list_rect.bottom:
                        break
                    sf = font.render(ln, True, color)
                    bottom = iy + sf.get_height()
                    if bottom >= self._list_rect.top:
                        surface.blit(sf, (ix, iy))
                    iy += sf.get_height() + 2
                if is_head:
                    iy += 4
            surface.set_clip(clip)
            max_scroll = max(
                0,
                self._info_scroll_max(state, items_all, selected) - self._list_rect.height,
            )
            self._info_scroll = min(self._info_scroll, max_scroll)

        right_x, right_w, load_y = self._loadout_right
        atk = state.effective_attack()
        arm = state.effective_armor()
        agi = state.effective_agility()
        stats_line = self.fonts["heading"].render(f"ATK {atk}   DEF {arm}   AGI {agi}", True, self.accent)
        surface.blit(stats_line, (right_x, load_y - 6))

        p = state.player
        lines: list[tuple[str, str | None, str]] = [
            ("Weapon", p.equipped_weapon_id, "weapon"),
            ("Armor", p.equipped_armor_id, "armor"),
            ("Ring 1", p.equipped_ring1_id, "ring1"),
            ("Ring 2", p.equipped_ring2_id, "ring2"),
            ("Amulet", p.equipped_amulet_id, "amulet"),
        ]
        btn_w = 72
        btn_h = 24
        ry = load_y + stats_line.get_height() + 8
        self._unequip_boxes.clear()
        for slot_title, eq_id, slot_key in lines:
            name = _equipped_display_name(state, eq_id)
            label = f"{slot_title}: "
            lab_sf = self.fonts["body"].render(label, True, LABEL_DIM)
            surface.blit(lab_sf, (right_x, ry))
            name_fit = fit_text(self.fonts["body"], name, right_w - 84)
            name_sf = self.fonts["body"].render(name_fit, True, LABEL_BRIGHT)
            surface.blit(name_sf, (right_x + lab_sf.get_width(), ry))
            bx = right_x + right_w - btn_w
            urect = pygame.Rect(bx, ry + 2, btn_w, btn_h)
            self._unequip_boxes.append((urect, slot_key))
            fill = (22, 22, 28, 160 if busy else 210)
            draw_panel(surface, urect, border_color=self.accent, fill=fill)
            rm = self.fonts["label"].render("Remove", True, LABEL_DIM if busy else LABEL_BRIGHT)
            surface.blit(rm, (urect.centerx - rm.get_width() // 2, urect.centery - rm.get_height() // 2))
            ry += 34

        now = time.monotonic()
        if self._notify_text and now < self._notify_until:
            bg = (60, 22, 22, 210) if self._notify_error else (22, 42, 38, 210)
            draw_panel(surface, self._notif_rect, border_color=(255, 120, 120) if self._notify_error else self.accent, fill=bg)
            msg_fit = fit_text(self.fonts["body"], self._notify_text, self._notif_rect.width - 12)
            msg_sf = self.fonts["body"].render(msg_fit, True, LABEL_BRIGHT)
            surface.blit(
                msg_sf,
                (
                    self._notif_rect.left + 6,
                    self._notif_rect.centery - msg_sf.get_height() // 2,
                ),
            )
        elif self._notify_text and now >= self._notify_until:
            self._notify_text = ""

        can_use = bool(filtered) if self._category_tab != "info" else False
        use_fill = (22, 22, 28, 120 if busy or not can_use else 210)
        draw_panel(surface, self._use_rect, border_color=self.accent, fill=use_fill)
        if self._category_tab == "info":
            ul = "Use Info tab to read"
        elif not filtered:
            ul = "Empty tab"
        else:
            ul = "Use / Equip"
        use_sf = self.fonts["button"].render(ul, True, LABEL_DIM if busy or not can_use else LABEL_BRIGHT)
        surface.blit(
            use_sf,
            (
                self._use_rect.centerx - use_sf.get_width() // 2,
                self._use_rect.centery - use_sf.get_height() // 2,
            ),
        )
        self._close_btn.set_border(self.accent)
        self._close_btn.draw(surface)

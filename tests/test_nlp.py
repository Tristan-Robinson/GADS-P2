from __future__ import annotations

from game import nlp


def test_split_semicolon() -> None:
    assert nlp.split_player_commands("go north; take torch") == [
        "go north",
        "take torch",
    ]


def test_split_then() -> None:
    assert nlp.split_player_commands("go north then take torch") == [
        "go north",
        "take torch",
    ]


def test_split_and_then() -> None:
    assert nlp.split_player_commands("go north and then look") == [
        "go north",
        "look",
    ]


def test_split_newline() -> None:
    assert nlp.split_player_commands("go north\ntake torch") == [
        "go north",
        "take torch",
    ]


def test_combine_line_not_split() -> None:
    assert nlp.split_player_commands("combine ichor and vial") == [
        "combine ichor and vial",
    ]


def test_split_empty_and_whitespace() -> None:
    assert nlp.split_player_commands("") == []
    assert nlp.split_player_commands("   ") == []
    assert nlp.split_player_commands(";\n") == []


def test_single_command_unchanged() -> None:
    assert nlp.split_player_commands("look") == ["look"]

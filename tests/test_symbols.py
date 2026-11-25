# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for symbols deprecated in place with `DeprecatedSymbol`.

A symbol entry goes in the same table as alias entries. The symbol isn't moving,
so its entry has a `value` instead of a target. It can also have a `replacement`,
which is only used in messages.

Like the other static tests, these never import `frequenz-core`.
"""

import contextlib
import logging
from collections.abc import Iterator
from typing import Any

import griffe
import pytest
from griffe import Attribute, DocstringSectionAdmonition, Module, Parser

from griffe_frequenz_core.deprecations import DeprecationsExtension

_LOGGER = "griffe_frequenz_core.deprecations"
_GENERIC = "Deprecated. It will be removed in a future release."
_RUNTIME_ONLY = (
    "there is no notice written for the documentation, so the runtime warning "
    "is shown instead"
)


@contextlib.contextmanager
def visit(
    entries: str, *, before: str = "", **options: Any
) -> Iterator[tuple[Module, list[str]]]:
    """Visit a module with a table of deprecated symbols, and render it.

    Args:
        entries: The entries of the table, as written in the call.
        before: The code before the table, like the declarations for type
            checkers.
        **options: The extension's options.

    Yields:
        The module, and the warnings the extension logged. The list is filled
            when the module is rendered, before this yields.
    """
    code = (
        "from frequenz.core.warnings import (\n"
        "    DeprecatedAlias, DeprecatedSymbol, deprecated_symbols\n"
        ")\n"
        f"{before}"
        f"__getattr__ = deprecated_symbols(__name__, {entries})\n"
    )
    logger = logging.getLogger(_LOGGER)
    logged: list[str] = []

    class Handler(logging.Handler):
        """A handler that keeps the warnings."""

        def emit(self, record: logging.LogRecord) -> None:
            """Keep a warning.

            Args:
                record: The log record.
            """
            if record.levelno == logging.WARNING:
                logged.append(record.getMessage())

    handler = Handler()
    logger.addHandler(handler)
    try:
        with griffe.temporary_visited_module(
            code,
            docstring_parser=Parser.google,
            extensions=griffe.load_extensions(
                DeprecationsExtension(checked_packages=("module",), **options)
            ),
        ) as module:
            if module.docstring is not None:
                _ = module.docstring.parsed
            for member in module.members.values():
                if not isinstance(member, griffe.Alias) and member.docstring:
                    _ = member.docstring.parsed
            yield module, logged
    finally:
        logger.removeHandler(handler)


def only(logged: list[str]) -> str:
    """Return the only warning logged.

    Args:
        logged: The warnings the extension logged.

    Returns:
        The warning.
    """
    assert len(logged) == 1, logged
    return logged[0]


def symbol(module: Module, name: str = "OLD") -> Attribute:
    """Return one attribute of a visited module.

    Args:
        module: The visited module.
        name: The name of the attribute.

    Returns:
        The attribute.
    """
    member = module[name]
    assert isinstance(member, Attribute)
    return member


def test_a_symbol_with_a_replacement_gets_the_default_message() -> None:
    """Ensure `since` and `replacement` make a complete notice, with a link."""
    with visit(
        "DeprecatedSymbol('OLD', value=1, replacement='pkg.new.NEW', since='v1.5.0')"
    ) as (module, logged):
        member = symbol(module)
        assert "deprecated" in member.labels
        assert member.deprecated == (
            "Deprecated since v1.5.0. Use [`pkg.new.NEW`][] instead."
        )
        assert member.docstring is not None
        [section] = member.docstring.parsed
        assert isinstance(section, DocstringSectionAdmonition)
        assert section.title == "Deprecated"
        assert section.value.contents == member.deprecated
        assert not logged


def test_a_replacement_in_the_same_module_shows_only_its_name() -> None:
    """Ensure the link is short if the replacement is next to the symbol."""
    with visit(
        "DeprecatedSymbol('OLD', value=1, replacement='module.NEW', since='v1')"
    ) as (module, logged):
        assert symbol(module).deprecated == (
            "Deprecated since v1. Use [`NEW`][module.NEW] instead."
        )
        assert not logged


def test_a_replacement_without_a_module_is_linked_as_written() -> None:
    """Ensure a built-in replacement, like `int`, is linked by its name."""
    with visit("DeprecatedSymbol('OLD', value=1, replacement='int', since='v1')") as (
        module,
        logged,
    ):
        assert (
            symbol(module).deprecated == "Deprecated since v1. Use [`int`][] instead."
        )
        assert not logged


def test_the_message_does_not_change_a_generated_notice() -> None:
    """Ensure `message` is only the runtime warning if there is a replacement."""
    with visit(
        "DeprecatedSymbol('OLD', value=1, replacement='pkg.NEW', since='v1', "
        "message='{old} is going away. Use {new} instead.')"
    ) as (module, logged):
        assert symbol(module).deprecated == (
            "Deprecated since v1. Use [`pkg.NEW`][] instead."
        )
        assert not logged


def test_the_default_message_option_is_used() -> None:
    """Ensure symbols use the same notice template as aliases."""
    with visit(
        "DeprecatedSymbol('OLD', value=1, replacement='pkg.NEW', since='v1')",
        default_message="{old} is replaced by {new} ({new_link}) since {since}.",
    ) as (module, _):
        assert symbol(module).deprecated == (
            "module.OLD is replaced by pkg.NEW ([`pkg.NEW`][]) since v1."
        )


def test_a_missing_since_is_warned_about() -> None:
    """Ensure a notice without a version says what to use, and logs a warning."""
    with visit("DeprecatedSymbol('OLD', value=1, replacement='pkg.NEW')") as (
        module,
        logged,
    ):
        assert symbol(module).deprecated == "Deprecated. Use [`pkg.NEW`][] instead."
        warning = only(logged)
        assert warning == (
            "module.OLD: the notice can't say since which version it is "
            "deprecated, because `since` isn't given. Pass `since` or write a "
            "`Deprecated:` section in the docstring to fix this."
        )


def test_a_symbol_without_a_replacement_shows_its_runtime_warning() -> None:
    """Ensure the message is shown, after the version, if nothing else can help.

    The message is a template. `{old}` is replaced like at runtime.
    """
    with visit(
        "DeprecatedSymbol('OLD', value=1, since='v1.6.0', "
        "message='{old} is deprecated. Define your own instead.')"
    ) as (module, logged):
        assert symbol(module).deprecated == (
            "Deprecated since v1.6.0. module.OLD is deprecated. Define your own "
            "instead."
        )
        warning = only(logged)
        assert warning.startswith(f"module.OLD: {_RUNTIME_ONLY}. Write a ")


def test_a_runtime_warning_without_since_is_shown_as_written() -> None:
    """Ensure nothing is added before the message if the version isn't known."""
    with visit("DeprecatedSymbol('OLD', value=1, message='{old} is gone.')") as (
        module,
        logged,
    ):
        assert symbol(module).deprecated == "module.OLD is gone."
        assert len(logged) == 1


def test_a_handwritten_notice_replaces_the_runtime_warning() -> None:
    """Ensure a hand-written notice is used, moved to the top, with no warning."""
    declaration = (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    OLD = 1\n"
        '    """An old thing.\n\n'
        "    Deprecated:\n"
        "        Deprecated since v1.6.0. Define your own instead.\n"
        '    """\n'
    )
    with visit(
        "DeprecatedSymbol('OLD', value=1, since='v1.6.0', message='{old} is gone.')",
        before=declaration,
    ) as (module, logged):
        member = symbol(module)
        assert "deprecated" in member.labels
        assert member.docstring is not None
        first = member.docstring.parsed[0]
        assert isinstance(first, DocstringSectionAdmonition)
        assert "Define your own instead." in first.value.contents
        assert len(member.docstring.parsed) == 2
        assert not logged


@pytest.mark.parametrize(
    ("arguments", "notice", "warned"),
    [
        (
            "since='v1'",
            "Deprecated since v1.",
            "the notice can't say what to use instead, because `replacement` "
            "isn't given",
        ),
        (
            "",
            _GENERIC,
            "the notice can't say since which version it is deprecated, because "
            "`since` isn't given, nor what to use instead, because `replacement` "
            "isn't given",
        ),
        (
            "since='v1', message=MESSAGE",
            "Deprecated since v1.",
            "because `replacement` isn't given and `message` can't be read",
        ),
        (
            "since='v1', replacement=NEW",
            "Deprecated since v1.",
            "what to use instead, because `replacement` can't be read",
        ),
        (
            "since=SINCE, replacement='pkg.NEW'",
            "Deprecated. Use [`pkg.NEW`][] instead.",
            "since which version it is deprecated, because `since` can't be read",
        ),
        (
            "since='v1', replacement=NEW, message='{old} is gone. Use {new}.'",
            "Deprecated since v1.",
            "what to use instead, because `replacement` can't be read",
        ),
        (
            "since='v1', message='{old} is gone. Use {new}.'",
            "Deprecated since v1.",
            "because `replacement` isn't given",
        ),
        (
            "since='v1', message='  '",
            "Deprecated since v1.",
            "because `replacement` isn't given",
        ),
    ],
    ids=[
        "only-since",
        "nothing",
        "unreadable-message",
        "unreadable-replacement",
        "unreadable-since",
        "message-needs-unreadable-replacement",
        "message-needs-missing-replacement",
        "blank-message",
    ],
)
def test_a_notice_short_of_the_guide_is_warned_about(
    arguments: str, notice: str, warned: str
) -> None:
    """Ensure a symbol's notice says what the extension knows, and warns about the rest.

    All of them ask for a hand-written notice, because a symbol doesn't always
    have a replacement to pass.
    """
    with visit(f"DeprecatedSymbol('OLD', value=1, {arguments})") as (module, logged):
        assert symbol(module).deprecated == notice
        warning = only(logged)
        assert warned in warning
        assert "`Deprecated:` section in the docstring to fix this." in warning


def test_an_unreadable_replacement_falls_back_to_the_message() -> None:
    """Ensure a message that doesn't need the replacement is shown instead."""
    with visit(
        "DeprecatedSymbol('OLD', value=1, replacement=NEW, "
        "message='{old} is gone. Ask us.')"
    ) as (module, logged):
        assert symbol(module).deprecated == "module.OLD is gone. Ask us."
        warning = only(logged)
        assert _RUNTIME_ONLY in warning


def test_the_value_of_a_private_attribute_is_shown() -> None:
    """Ensure the docs show the value itself, not the private name that holds it."""
    before = (
        "from typing import TYPE_CHECKING, Final\n"
        "_OLD: Final = 30.0\n"
        "if TYPE_CHECKING:\n"
        "    OLD: Final = _OLD\n"
        '    """How long to wait, in seconds."""\n'
    )
    with visit(
        "DeprecatedSymbol('OLD', value=_OLD, replacement='pkg.NEW', since='v1')",
        before=before,
    ) as (module, logged):
        assert str(symbol(module).value) == "30.0"
        assert not logged


@pytest.mark.parametrize(
    ("value", "shown"),
    [
        ("TypeVar('OLD')", "TypeVar('OLD')"),
        ("None", "None"),
        ("PUBLIC", "PUBLIC"),
        ("_imported", "_imported"),
        ("other._OLD", "other._OLD"),
    ],
)
def test_other_values_are_shown_as_written_in_the_entry(value: str, shown: str) -> None:
    """Ensure only a private attribute of the same module is followed."""
    before = "from elsewhere import _imported, other\nPUBLIC = 2\n"
    with visit(
        f"DeprecatedSymbol('OLD', value={value}, replacement='pkg.NEW', since='v1')",
        before=before,
    ) as (module, logged):
        assert str(symbol(module).value) == shown
        assert not logged


def test_the_declared_value_is_kept_without_show_target() -> None:
    """Ensure `show_target: false` leaves the declaration for type checkers alone."""
    before = "_OLD = 30.0\nOLD = _OLD\n"
    with visit(
        "DeprecatedSymbol('OLD', value=_OLD, replacement='pkg.NEW', since='v1')",
        before=before,
        show_target=False,
    ) as (module, _):
        assert str(symbol(module).value) == "_OLD"


def test_a_symbol_hidden_from_type_checkers_is_created() -> None:
    """Ensure an entry without a declaration is still documented, with its value."""
    with visit(
        "DeprecatedSymbol('OLD', value=30.0, replacement='pkg.NEW', since='v1')"
    ) as (module, logged):
        member = symbol(module)
        assert "deprecated" in member.labels
        assert str(member.value) == "30.0"
        assert not logged


def test_aliases_and_symbols_can_share_a_table() -> None:
    """Ensure every entry of a mixed table is documented in its own way."""
    with visit(
        "DeprecatedAlias('Moved', new_module='pkg.new', since='v1'), "
        "DeprecatedSymbol('OLD', value=1, replacement='pkg.NEW', since='v2'), "
        "DeprecatedAlias('Renamed', new_name='Other', since='v3')"
    ) as (module, logged):
        assert symbol(module, "Moved").deprecated == (
            "Deprecated since v1. Use [`pkg.new.Moved`][] instead."
        )
        assert symbol(module, "Moved").value == griffe.ExprName("pkg.new.Moved")
        assert symbol(module).deprecated == (
            "Deprecated since v2. Use [`pkg.NEW`][] instead."
        )
        assert str(symbol(module).value) == "1"
        assert symbol(module, "Renamed").deprecated == (
            "Deprecated since v3. Use [`Other`][module.Other] instead."
        )
        assert not logged


@pytest.mark.parametrize(
    ("entry", "warned"),
    [
        ("DeprecatedSymbol('OLD')", "needs a positional name and `value`"),
        ("DeprecatedSymbol('OLD', replacement='pkg.NEW')", "needs a positional name"),
        ("DeprecatedSymbol('OLD', 1)", "needs a positional name and `value`"),
        ("DeprecatedSymbol(name='OLD', value=1)", "needs a positional name"),
        ("DeprecatedSymbol('OLD', value=1, until='v2')", "needs a positional name"),
        ("DeprecatedSymbol('OLD', value=1, value=2)", "needs a positional name"),
        (
            "DeprecatedSymbol('OLD', value=1, new_module='pkg.new')",
            "needs a positional name",
        ),
        (
            "DeprecatedSymbol(NAME, value=1)",
            "the name of the symbol entry `DeprecatedSymbol(NAME, value=1)` isn't "
            "a string literal, so it's skipped",
        ),
        (
            "DeprecatedSymbol(*ARGS, value=1)",
            "the arguments of the symbol entry `DeprecatedSymbol(*ARGS, value=1)` "
            "are unpacked, so it's skipped",
        ),
        (
            "DeprecatedSymbol(**KWARGS)",
            "the arguments of the symbol entry `DeprecatedSymbol(**KWARGS)` are "
            "unpacked, so it's skipped",
        ),
    ],
)
def test_an_unreadable_symbol_entry_is_skipped_loudly(entry: str, warned: str) -> None:
    """Ensure a symbol that can't be marked logs a warning.

    The warning waits for the module's docstring, because the entry has no
    object.
    """
    with visit(entry) as (module, logged):
        assert "OLD" not in module.members
        warning = only(logged)
        assert warning.startswith("module: ")
        assert warned in warning


def test_unpacked_keywords_leave_only_the_name() -> None:
    """Ensure a symbol is still marked if only its name can be read.

    Anything could be in the `**kwargs`, so the declared value is kept and the
    notice is generic. Both are warned about.
    """
    with visit(
        "DeprecatedSymbol('OLD', **KWARGS)", before='OLD = _OLD\n"""An old thing."""\n'
    ) as (module, logged):
        member = symbol(module)
        assert "deprecated" in member.labels
        assert member.deprecated == _GENERIC
        assert str(member.value) == "_OLD"
        assert len(logged) == 2
        assert any(
            "the value of the symbol can't be read, so it's shown as written" in warning
            for warning in logged
        )
        assert any("`replacement` can't be read" in warning for warning in logged)


def test_the_symbol_classes_are_an_option() -> None:
    """Ensure the option replaces the default, like the other path options."""
    before = "from mypkg.compat import Gone\n"
    with visit(
        "Gone('Mine', value=1, replacement='pkg.NEW', since='v1'), "
        "DeprecatedSymbol('Core', value=1, replacement='pkg.NEW', since='v1')",
        before=before,
        symbol_classes=["mypkg.compat.Gone"],
    ) as (module, logged):
        assert "deprecated" in symbol(module, "Mine").labels
        assert "Core" not in module.members
        warning = only(logged)
        assert "isn't a call to a known alias or symbol class" in warning

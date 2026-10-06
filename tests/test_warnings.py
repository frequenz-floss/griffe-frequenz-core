# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the warnings the deprecations extension logs.

The extension logs a warning when it can't document a deprecation the way the
deprecations guide asks for. For example, when it can't read an argument, or
when the code only has a runtime warning. This makes strict `mkdocs` builds
fail. The extension logs the reason at debug level.
"""

import logging
from typing import Any

import griffe
import pytest
from griffe import Parser

from griffe_frequenz_core.deprecations import DeprecationsExtension

_LOGGER = "griffe_frequenz_core.deprecations"


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Return the warnings the extension logged.

    Args:
        caplog: The captured log records.

    Returns:
        The message of every warning logged by the extension.
    """
    return [
        record.message
        for record in caplog.records
        if record.name == _LOGGER and record.levelno == logging.WARNING
    ]


@pytest.mark.parametrize(
    ("code", "warned"),
    [
        (
            "from frequenz.core.enum import Enum, deprecated_member\n"
            "class Status(Enum):\n"
            "    A = deprecated_member(7, _MESSAGE)\n",
            "A: the deprecation message isn't a string literal",
        ),
        (
            "from frequenz.core.enum import Enum, deprecated_member\n"
            "class Status(Enum):\n"
            "    A = deprecated_member(7, 'mod.Status.A is deprecated.')\n",
            "A: there is no notice written for the documentation, so the runtime "
            "warning is shown instead",
        ),
        (
            "from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases\n"
            "__getattr__ = deprecated_aliases(\n"
            "    __name__, DeprecatedAlias('A', new_module='pkg.new', since=SINCE)\n"
            ")\n",
            "A: the notice can't say since which version it is deprecated",
        ),
        (
            "from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases\n"
            "__getattr__ = deprecated_aliases(\n"
            "    __name__, DeprecatedAlias('A', new_module='pkg.new', message='Gone')\n"
            ")\n",
            "A: the notice can't say since which version it is deprecated",
        ),
    ],
    ids=["enum-unreadable", "enum-runtime-only", "alias-unreadable", "alias-message"],
)
def test_a_notice_short_of_the_guide_is_warned_about(
    caplog: pytest.LogCaptureFixture, code: str, warned: str
) -> None:
    """Ensure a notice missing information the guide asks for logs a warning."""
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code, extensions=griffe.load_extensions(DeprecationsExtension())
        ),
    ):
        pass
    [warning] = _warnings(caplog)
    assert warned in warning
    assert warning.endswith(
        ". Write a `Deprecated:` section in the docstring to fix this."
    )


@pytest.mark.parametrize("message", ["_MESSAGE", "'mod.Status.A is deprecated.'"])
def test_a_handwritten_notice_silences_the_generated_one(
    caplog: pytest.LogCaptureFixture, message: str
) -> None:
    """Ensure no warning is logged if the notice was written by hand."""
    code = (
        "from frequenz.core.enum import Enum, deprecated_member\n"
        "class Status(Enum):\n"
        f"    A = deprecated_member(7, {message})\n"
        '    """A status.\n\n    Deprecated:\n        Use B instead.\n    """\n'
    )
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code,
            docstring_parser=Parser.google,
            extensions=griffe.load_extensions(DeprecationsExtension()),
        ),
    ):
        pass
    assert not _warnings(caplog)


def test_a_message_from_another_extension_silences_the_generic_one(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure no warning is logged if another extension already found the message."""

    class Earlier(griffe.Extension):
        """An extension that runs first and finds a message."""

        def on_attribute_instance(
            self, *, attr: griffe.Attribute, **kwargs: Any
        ) -> None:
            """Give every attribute a message.

            Args:
                attr: The attribute just created.
                **kwargs: Other arguments passed by Griffe, not used.
            """
            attr.deprecated = "Use B."

    code = (
        "from frequenz.core.enum import Enum, deprecated_member\n"
        "class Status(Enum):\n"
        "    A = deprecated_member(7, _MESSAGE)\n"
    )
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code, extensions=griffe.load_extensions(Earlier(), DeprecationsExtension())
        ),
    ):
        pass
    assert not _warnings(caplog)


@pytest.mark.parametrize(
    ("arguments", "warned"),
    [
        ("__name__, *ENTRIES", "are unpacked, so they aren't marked"),
        ("__name__, ENTRY", "isn't a call to a known alias class"),
        (
            "__name__, DeprecatedAlias(NAME, new_module='pkg.new', since='v1')",
            "isn't a string literal, so it's skipped",
        ),
        (
            "__name__, DeprecatedAlias(*ARGS, since='v1')",
            "are unpacked, so it's skipped",
        ),
        (
            "__name__, DeprecatedAlias('A', since='v1')",
            "needs a positional name",
        ),
        (
            "__name__, DeprecatedAlias('A', new_module=TARGET, since='v1')",
            "the target of the alias can't be read",
        ),
        ("__name__, DeprecatedAlias('A', new_module='pkg.new', since='v1')", None),
    ],
)
def test_an_alias_that_cannot_be_fully_documented_is_warned_about(
    caplog: pytest.LogCaptureFixture, arguments: str, warned: str | None
) -> None:
    """Ensure a warning is logged if an alias isn't documented or has no target.

    An entry whose arguments don't match the ones of `DeprecatedAlias` also logs
    a warning, because it isn't documented as deprecated either. An entry that
    can be fully read doesn't log anything. If the target can't be read, the
    notice doesn't have a target either, which logs a separate warning.
    """
    code = (
        "from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases\n"
        f"__getattr__ = deprecated_aliases({arguments})\n"
    )
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code, extensions=griffe.load_extensions(DeprecationsExtension())
        ),
    ):
        pass
    logged = _warnings(caplog)
    if warned is None:
        assert not logged
    else:
        assert any(warned in message for message in logged)
        assert len(logged) == (2 if "TARGET" in arguments else 1)


@pytest.mark.parametrize(
    ("wrapper", "warned"),
    [
        ("deprecated_member(*ARGS)", "its value is shown as the whole call"),
        ("deprecated_member(1)", "don't match `deprecated_member(value, message)`"),
        ("deprecated_member(1, 'Gone')", None),
    ],
)
def test_an_enum_member_that_cannot_be_fully_documented_is_warned_about(
    caplog: pytest.LogCaptureFixture, wrapper: str, warned: str | None
) -> None:
    """Ensure a warning is logged if an enum member's value or deprecation can't be shown.

    Because of the hand-written notice, there is no warning about the generic
    message, only the one about the member itself.
    """
    code = (
        "from frequenz.core.enum import Enum, deprecated_member\n"
        "class Status(Enum):\n"
        f"    A = {wrapper}\n"
        '    """A status.\n\n    Deprecated:\n        Use B instead.\n    """\n'
    )
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code,
            docstring_parser=Parser.google,
            extensions=griffe.load_extensions(DeprecationsExtension()),
        ),
    ):
        pass
    logged = _warnings(caplog)
    if warned is None:
        assert not logged
    else:
        assert len(logged) == 1
        assert warned in logged[0]

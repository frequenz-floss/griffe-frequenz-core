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


def _render(obj: griffe.Object) -> None:
    """Parse the docstrings of an object and its members, as rendering does.

    The extension adds notices and warns about missing information during
    parsing, just before mkdocstrings renders the docstring.

    Args:
        obj: The object to render.
    """
    if obj.docstring is not None:
        _ = obj.docstring.parsed
    for member in obj.members.values():
        if not isinstance(member, griffe.Alias):
            _render(member)


_DOCSTRING_FIX = ". Write a `Deprecated:` section in the docstring to fix this."
_SINCE_FIX = (
    ". Pass `since` or write a `Deprecated:` section in the docstring to fix this."
)


@pytest.mark.parametrize(
    ("code", "warned", "fix"),
    [
        (
            "from frequenz.core.enum import Enum, deprecated_member\n"
            "class Status(Enum):\n"
            "    A = deprecated_member(7, _MESSAGE)\n",
            "A: the deprecation message isn't a string literal",
            _DOCSTRING_FIX,
        ),
        (
            "from frequenz.core.enum import Enum, deprecated_member\n"
            "class Status(Enum):\n"
            "    A = deprecated_member(7, 'mod.Status.A is deprecated.')\n",
            "A: there is no notice written for the documentation, so the runtime "
            "warning is shown instead",
            _DOCSTRING_FIX,
        ),
        (
            "from frequenz.core.enum import Enum, deprecated_member\n"
            "class Status(Enum):\n"
            "    B = 7\n"
            "    A = deprecated_member(7, new_name='B')\n",
            "A: the notice can't say since which version it is deprecated, because "
            "`since` isn't given",
            _SINCE_FIX,
        ),
        (
            "from frequenz.core.enum import Enum, deprecated_member\n"
            "class Status(Enum):\n"
            "    B = 7\n"
            "    A = deprecated_member(7, new_name='B', since=SINCE)\n",
            "A: the notice can't say since which version it is deprecated, because "
            "`since` isn't a string literal",
            _DOCSTRING_FIX,
        ),
        (
            "from frequenz.core.enum import Enum, deprecated_member\n"
            "class Status(Enum):\n"
            "    A = deprecated_member(7, new_name=NEW, since='v1')\n",
            "A: the notice can't say what to use instead",
            _DOCSTRING_FIX,
        ),
        (
            "from frequenz.core.enum import Enum, deprecated_member\n"
            "class Status(Enum):\n"
            "    A = deprecated_member(7, new_name=NEW)\n",
            "A: the notice can't say since which version it is deprecated, because "
            "`since` isn't given, nor what to use instead",
            _DOCSTRING_FIX,
        ),
        (
            "from frequenz.core.enum import Enum, deprecated_member\n"
            "class Status(Enum):\n"
            "    A = deprecated_member(7, 'mod.Status.A is deprecated.', since='v1')\n",
            "A: there is no notice written for the documentation, so the runtime "
            "warning is shown instead",
            _DOCSTRING_FIX,
        ),
        (
            "from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases\n"
            "__getattr__ = deprecated_aliases(\n"
            "    __name__, DeprecatedAlias('A', new_module='pkg.new', since=SINCE)\n"
            ")\n",
            "A: the notice can't say since which version it is deprecated, because "
            "`since` can't be read",
            _DOCSTRING_FIX,
        ),
        (
            "from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases\n"
            "__getattr__ = deprecated_aliases(\n"
            "    __name__, DeprecatedAlias('A', new_module='pkg.new', message='Gone')\n"
            ")\n",
            "A: the notice can't say since which version it is deprecated, because "
            "`since` isn't given",
            _SINCE_FIX,
        ),
        (
            "from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases\n"
            "__getattr__ = deprecated_aliases(\n"
            "    __name__, DeprecatedAlias('A', new_module='pkg.new')\n"
            ")\n",
            "A: the notice can't say since which version it is deprecated, because "
            "`since` isn't given",
            _SINCE_FIX,
        ),
        (
            "from typing_extensions import deprecated\n"
            "@deprecated(_MESSAGE)\n"
            "def A(): ...\n",
            "A: the deprecation message can't be read",
            _DOCSTRING_FIX,
        ),
        (
            "from typing_extensions import deprecated\n"
            "@deprecated('mod.A is deprecated.')\n"
            "def A(): ...\n",
            "A: there is no notice written for the documentation, so the runtime "
            "warning is shown instead",
            _DOCSTRING_FIX,
        ),
    ],
    ids=[
        "enum-unreadable",
        "enum-runtime-only",
        "enum-no-since",
        "enum-unreadable-since",
        "enum-unreadable-new-name",
        "enum-no-since-unreadable-new-name",
        "enum-message-and-since",
        "alias-unreadable",
        "alias-message",
        "alias-no-since",
        "decorator-unreadable",
        "decorator-runtime-only",
    ],
)
def test_a_notice_short_of_the_guide_is_warned_about(
    caplog: pytest.LogCaptureFixture, code: str, warned: str, fix: str
) -> None:
    """Ensure a notice missing information the guide asks for logs a warning.

    The warning says how to fix it. If `since` is the only thing missing, and it
    isn't given at all, passing it is enough.
    """
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code, extensions=griffe.load_extensions(DeprecationsExtension())
        ) as module,
    ):
        _render(module)
    [warning] = _warnings(caplog)
    assert warned in warning
    assert warning.endswith(fix)


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
        ) as module,
    ):
        _render(module)
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
        ) as module,
    ):
        _render(module)
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
        (
            "__name__, DeprecatedAlias('A', new_module='pkg.new', since='v1', "
            "message='{old} is gone. Use {new}.')",
            None,
        ),
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
        ) as module,
    ):
        _render(module)
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
        (
            "deprecated_member(1)",
            "the deprecation wrapper's arguments don't match",
        ),
        ("deprecated_member(1, 'Gone')", None),
        ("deprecated_member(1, new_name='B', since='v1')", None),
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
        ) as module,
    ):
        _render(module)
    logged = _warnings(caplog)
    if warned is None:
        assert not logged
    else:
        assert len(logged) == 1
        assert warned in logged[0]


@pytest.mark.parametrize(
    "wrapper",
    [
        "deprecated_member(1, new_name='B', since='v1')",
        "deprecated_member(1, 'mod.Status.A is deprecated.', new_name='B', since='v1')",
    ],
)
def test_a_generated_enum_notice_is_not_warned_about(
    caplog: pytest.LogCaptureFixture, wrapper: str
) -> None:
    """Ensure a complete generated enum notice doesn't produce a warning."""
    code = (
        "from frequenz.core.enum import Enum, deprecated_member\n"
        "class Status(Enum):\n"
        "    B = 1\n"
        f"    A = {wrapper}\n"
    )
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code, extensions=griffe.load_extensions(DeprecationsExtension())
        ) as module,
    ):
        _render(module)
    assert not _warnings(caplog)


def test_only_rendered_objects_are_warned_about(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Wait until rendering to warn about incomplete notices.

    Griffe also visits dependency code that isn't documented. Missing notices
    there shouldn't make this project's build fail.
    """
    code = (
        "from typing_extensions import deprecated\n"
        "@deprecated('mod.A is deprecated.')\n"
        "def A(): ...\n"
    )
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code, extensions=griffe.load_extensions(DeprecationsExtension())
        ) as module,
    ):
        assert not _warnings(caplog)
        assert module["A"].deprecated == "mod.A is deprecated."
        _render(module)
    [warning] = _warnings(caplog)
    assert warning.startswith("module.A: there is no notice written")


def test_a_docstring_parsed_already_gets_its_notice_right_away(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Add the notice right away if another extension already parsed the docstring."""

    class Earlier(griffe.Extension):
        """An extension that parses docstrings while visiting."""

        def on_function_instance(self, *, func: griffe.Function, **kwargs: Any) -> None:
            """Parse the function's docstring.

            Args:
                func: The function just created.
                **kwargs: Other arguments passed by Griffe, not used.
            """
            assert func.docstring is not None
            _ = func.docstring.parsed

    code = (
        "from typing_extensions import deprecated\n"
        "@deprecated('mod.A is deprecated.')\n"
        "def A():\n"
        '    """Do A."""\n'
    )
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code, extensions=griffe.load_extensions(Earlier(), DeprecationsExtension())
        ) as module,
    ):
        [warning] = _warnings(caplog)
    assert warning.startswith("module.A: there is no notice written")
    sections = module["A"].docstring.parsed
    assert sections[0].kind is griffe.DocstringSectionKind.admonition
    assert len(sections) == 2


class _ParsingEarlier(griffe.Extension):
    """An extension that parses docstrings while Griffe visits the code."""

    def on_function_instance(self, *, func: griffe.Function, **kwargs: Any) -> None:
        """Parse the function's docstring, if it has one.

        Args:
            func: The function just created.
            **kwargs: Other arguments passed by Griffe, not used.
        """
        if func.docstring is not None:
            _ = func.docstring.parsed

    def on_attribute_instance(self, *, attr: griffe.Attribute, **kwargs: Any) -> None:
        """Parse the attribute's docstring, if it has one.

        Args:
            attr: The attribute just created.
            **kwargs: Other arguments passed by Griffe, not used.
        """
        if attr.docstring is not None:
            _ = attr.docstring.parsed


@pytest.mark.parametrize(
    ("code", "path", "notice"),
    [
        (
            "from typing import overload\n"
            "from typing_extensions import deprecated\n"
            "@overload\n"
            "@deprecated('Calling mod.f with an int is deprecated.')\n"
            "def f(x: int) -> int: ...\n"
            "@overload\n"
            "@deprecated(MESSAGE)\n"
            "def f(x: str) -> str: ...\n"
            "def f(x):\n"
            '    """Do f."""\n',
            "f",
            "Calling mod.f with an int is deprecated.\n\n"
            "One of its overloads is deprecated.",
        ),
        (
            "from typing_extensions import deprecated\n"
            "class Owner:\n"
            "    @property\n"
            "    def p(self) -> int:\n"
            '        """The p."""\n'
            "    @p.setter\n"
            "    @deprecated('Setting mod.Owner.p is deprecated.')\n"
            "    def p(self, value: int) -> None: ...\n"
            "    @p.deleter\n"
            "    @deprecated(MESSAGE)\n"
            "    def p(self) -> None: ...\n",
            "Owner.p",
            "Setting mod.Owner.p is deprecated.\n\nDeleting it is deprecated.",
        ),
    ],
    ids=["overloads", "property-accessors"],
)
def test_parts_of_a_docstring_parsed_already_share_one_notice(
    caplog: pytest.LogCaptureFixture, code: str, path: str, notice: str
) -> None:
    """Add every deprecated part to the notice placed in a parsed docstring.

    Griffe can visit a property's setter and deleter after another extension
    parsed the property's docstring, so the notice has to be updated.
    """
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code,
            extensions=griffe.load_extensions(
                _ParsingEarlier(), DeprecationsExtension()
            ),
        ) as module,
    ):
        _render(module)
    obj = module[path]
    assert obj.docstring is not None
    sections = obj.docstring.parsed
    assert [section.kind for section in sections] == [
        griffe.DocstringSectionKind.admonition,
        griffe.DocstringSectionKind.text,
    ]
    assert sections[0].value.contents == notice
    logged = _warnings(caplog)
    assert len(logged) == 2
    assert all(warning.startswith(f"module.{path}: ") for warning in logged)


def test_a_handwritten_notice_covers_parts_of_a_docstring_parsed_already(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Keep the hand-written notice for parts visited after parsing."""
    code = (
        "from typing_extensions import deprecated\n"
        "class Owner:\n"
        "    @property\n"
        "    def p(self) -> int:\n"
        '        """The p.\n\n'
        "        Deprecated:\n"
        "            Setting or deleting it is deprecated since v1.2.0.\n"
        '        """\n'
        "    @p.setter\n"
        "    @deprecated('Setting mod.Owner.p is deprecated.')\n"
        "    def p(self, value: int) -> None: ...\n"
        "    @p.deleter\n"
        "    @deprecated('Deleting mod.Owner.p is deprecated.')\n"
        "    def p(self) -> None: ...\n"
    )
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code,
            docstring_parser=Parser.google,
            extensions=griffe.load_extensions(
                _ParsingEarlier(), DeprecationsExtension()
            ),
        ) as module,
    ):
        _render(module)
    assert not _warnings(caplog)
    docstring = module["Owner.p"].docstring
    assert docstring is not None
    [text, notice] = docstring.parsed
    assert text.kind is griffe.DocstringSectionKind.text
    assert notice.kind is griffe.DocstringSectionKind.admonition
    assert notice.title == "Deprecated"
    assert notice.value.contents == (
        "Setting or deleting it is deprecated since v1.2.0."
    )

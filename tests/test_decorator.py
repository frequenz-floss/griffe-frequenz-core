# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for documenting `@deprecated`.

Most tests visit code without running it. The argument tests also run the real
decorators to check which calls they accept. They use
`typing_extensions.deprecated`, and `warnings.deprecated` on Python 3.13 or later.
"""

import logging
import sys
import warnings
from typing import Any

import griffe
import pytest
import typing_extensions
from griffe import DocstringSectionAdmonition, Module, Object, Parser

from griffe_frequenz_core.deprecations import DeprecationsExtension

_LOGGER = "griffe_frequenz_core.deprecations"
_GENERIC = "Deprecated. It will be removed in a future release."
_RUNTIME_ONLY = (
    "there is no notice written for the documentation, so the runtime warning is "
    "shown instead"
)
_UNREADABLE = "the deprecation message can't be read"
_HANDWRITTEN = '    """A thing.\n\n    Deprecated:\n        Use B instead.\n    """\n'


def visit(code: str, **options: Any) -> Module:
    """Visit some code with the extension enabled.

    Args:
        code: The code of the module.
        **options: The extension's options.

    Returns:
        The visited module.
    """
    with griffe.temporary_visited_module(
        code,
        docstring_parser=Parser.google,
        extensions=griffe.load_extensions(DeprecationsExtension(**options)),
    ) as module:
        return module


def admonitions(obj: Object) -> list[DocstringSectionAdmonition]:
    """Return the admonition sections of an object's docstring.

    Args:
        obj: The object to look at.

    Returns:
        Its admonition sections, in order, or an empty list if it has no
        docstring.
    """
    if obj.docstring is None:
        return []
    return [
        section
        for section in obj.docstring.parsed
        if isinstance(section, DocstringSectionAdmonition)
    ]


def warned(caplog: pytest.LogCaptureFixture) -> list[str]:
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
    ("code", "path"),
    [
        (
            "from typing_extensions import deprecated\n"
            "@deprecated('mod.Thing is deprecated.')\n"
            "class Thing: ...\n",
            "Thing",
        ),
        (
            "from typing_extensions import deprecated\n"
            "@deprecated('mod.Thing is deprecated.')\n"
            "def Thing(): ...\n",
            "Thing",
        ),
        (
            "from typing_extensions import deprecated\n"
            "@deprecated('mod.Thing is deprecated.')\n"
            "async def Thing(): ...\n",
            "Thing",
        ),
        (
            "from typing_extensions import deprecated\n"
            "class Owner:\n"
            "    @deprecated('mod.Thing is deprecated.')\n"
            "    def Thing(self): ...\n",
            "Owner.Thing",
        ),
        (
            "from typing_extensions import deprecated\n"
            "class Owner:\n"
            "    @classmethod\n"
            "    @deprecated('mod.Thing is deprecated.')\n"
            "    def Thing(cls): ...\n",
            "Owner.Thing",
        ),
        (
            "from typing_extensions import deprecated\n"
            "class Owner:\n"
            "    @staticmethod\n"
            "    @deprecated('mod.Thing is deprecated.')\n"
            "    def Thing(): ...\n",
            "Owner.Thing",
        ),
        (
            "from typing_extensions import deprecated\n"
            "class Owner:\n"
            "    @property\n"
            "    @deprecated('mod.Thing is deprecated.')\n"
            "    def Thing(self) -> int: ...\n",
            "Owner.Thing",
        ),
        (
            "import warnings\n"
            "@warnings.deprecated('mod.Thing is deprecated.')\n"
            "def Thing(): ...\n",
            "Thing",
        ),
        (
            "from warnings import deprecated as gone\n"
            "@gone('mod.Thing is deprecated.')\n"
            "def Thing(): ...\n",
            "Thing",
        ),
        (
            "import typing_extensions as te\n"
            "@te.deprecated('mod.Thing is deprecated.')\n"
            "def Thing(): ...\n",
            "Thing",
        ),
        (
            "from typing_extensions import deprecated\n"
            "@deprecated('mod.Thing is deprecated.', category=None, stacklevel=2)\n"
            "def Thing(): ...\n",
            "Thing",
        ),
        (
            "from typing_extensions import deprecated\n"
            "@deprecated('mod.Thing is deprecated.', **OPTIONS)\n"
            "def Thing(): ...\n",
            "Thing",
        ),
        (
            "from typing_extensions import deprecated\n"
            "@deprecated(\n"
            "    'mod.Thing is '\n"
            "    'deprecated.'\n"
            ")\n"
            "def Thing(): ...\n",
            "Thing",
        ),
    ],
    ids=[
        "class",
        "function",
        "async-function",
        "method",
        "classmethod",
        "staticmethod",
        "property",
        "warnings",
        "aliased-import",
        "aliased-module",
        "keywords",
        "unpacked-keywords",
        "implicit-concatenation",
    ],
)
def test_a_decorated_object_is_marked(code: str, path: str) -> None:
    """Recognize decorated objects, including imports under another name.

    Without a hand-written notice, show the message as written.
    """
    obj = visit(code)[path]
    assert "deprecated" in obj.labels
    assert obj.deprecated == "mod.Thing is deprecated."
    [admonition] = admonitions(obj)
    assert admonition.title == "Deprecated"
    assert admonition.value.annotation == "danger"
    assert admonition.value.contents == "mod.Thing is deprecated."


@pytest.mark.parametrize(
    "code",
    [
        "def Thing(): ...\n",
        (
            "from mypkg import deprecated\n"
            "@deprecated('mod.Thing is deprecated.')\n"
            "def Thing(): ...\n"
        ),
        "import functools\n@functools.cache\ndef Thing(): ...\n",
        "class Owner:\n    @property\n    def Thing(self) -> int: ...\n",
    ],
    ids=["undecorated", "other-deprecated", "other-decorator", "property"],
)
def test_other_objects_are_untouched(code: str) -> None:
    """Only recognize decorators whose paths match the configuration."""
    module = visit(code)
    obj = module["Owner.Thing" if "Owner" in code else "Thing"]
    assert "deprecated" not in obj.labels
    assert obj.deprecated is None
    assert not admonitions(obj)


def test_a_handwritten_notice_wins_and_moves_to_the_top(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Use the hand-written notice instead of the decorator's message."""
    code = (
        "from typing_extensions import deprecated\n"
        "@deprecated('mod.Thing is deprecated. Use mod.New instead.')\n"
        "class Thing:\n"
        '    """A thing.\n\n'
        "    Some details.\n\n"
        "    Deprecated:\n"
        "        Deprecated since v1.2.0. Use [`New`][mod.New] instead.\n"
        '    """\n'
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        obj = visit(code)["Thing"]
    assert not warned(caplog)
    [admonition] = admonitions(obj)
    assert admonition.value.contents == (
        "Deprecated since v1.2.0. Use [`New`][mod.New] instead."
    )
    assert obj.docstring is not None
    assert obj.docstring.parsed[0] is admonition
    # Only the notice changes. The label and field are still set.
    assert "deprecated" in obj.labels
    assert obj.deprecated == "mod.Thing is deprecated. Use mod.New instead."


def test_a_handwritten_notice_on_a_property_moves_to_the_top() -> None:
    """A property keeps its getter's docstring, notice included."""
    code = (
        "from typing_extensions import deprecated\n"
        "class Owner:\n"
        "    @property\n"
        "    @deprecated('mod.Owner.thing is deprecated.')\n"
        "    def thing(self) -> int:\n"
        '        """The thing.\n\n'
        "        Deprecated:\n"
        "            Deprecated since v1.2.0. Use [`other`][mod.Owner.other].\n"
        '        """\n'
    )
    obj = visit(code)["Owner.thing"]
    assert obj.docstring is not None
    [admonition] = admonitions(obj)
    assert obj.docstring.parsed[0] is admonition
    assert "Deprecated since v1.2.0" in admonition.value.contents


def test_the_notice_goes_first() -> None:
    """Show the notice before the text describing the object."""
    code = (
        "from typing_extensions import deprecated\n"
        "@deprecated('mod.Thing is deprecated.')\n"
        "def Thing():\n"
        '    """Do a thing.\n\n    Returns:\n        Nothing.\n    """\n'
    )
    obj = visit(code)["Thing"]
    assert obj.docstring is not None
    sections = obj.docstring.parsed
    assert isinstance(sections[0], DocstringSectionAdmonition)
    assert sections[0].value.contents == "mod.Thing is deprecated."
    assert len(sections) == 3


@pytest.mark.parametrize(
    "message",
    ["MESSAGE", "f'{NAME} is deprecated.'", "'mod.Thing ' + 'is deprecated.'", "1"],
)
def test_an_unreadable_message_gets_a_generic_notice(
    caplog: pytest.LogCaptureFixture, message: str
) -> None:
    """Mark the object even if the message isn't a string literal."""
    code = (
        "from typing_extensions import deprecated\n"
        f"@deprecated({message})\n"
        "def Thing(): ...\n"
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        obj = visit(code)["Thing"]
    assert "deprecated" in obj.labels
    assert obj.deprecated == _GENERIC
    [admonition] = admonitions(obj)
    assert admonition.value.contents == _GENERIC
    [warning] = warned(caplog)
    assert _UNREADABLE in warning


def test_unpacked_arguments_get_a_generic_notice(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Mark the object even if `*args` prevents reading the message."""
    code = (
        "from typing_extensions import deprecated\n"
        "@deprecated(*ARGS)\n"
        "def Thing(): ...\n"
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        obj = visit(code)["Thing"]
    assert obj.deprecated == _GENERIC
    [warning] = warned(caplog)
    assert _UNREADABLE in warning


@pytest.mark.parametrize("message", ["MESSAGE", "'mod.Thing is deprecated.'", "*ARGS"])
def test_a_handwritten_notice_silences_the_warning(
    caplog: pytest.LogCaptureFixture, message: str
) -> None:
    """With the notice written by hand, nothing is missing from the docs."""
    code = (
        "from typing_extensions import deprecated\n"
        f"@deprecated({message})\n"
        "def Thing():\n" + _HANDWRITTEN
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        obj = visit(code)["Thing"]
    assert not warned(caplog)
    [admonition] = admonitions(obj)
    assert admonition.value.contents == "Use B instead."


def test_a_missing_notice_is_warned_about(caplog: pytest.LogCaptureFixture) -> None:
    """The runtime warning is written for a terminal, not for the docs."""
    code = (
        "from typing_extensions import deprecated\n"
        "@deprecated('mod.Thing is deprecated.')\n"
        "def Thing(): ...\n"
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        visit(code)
    [warning] = warned(caplog)
    assert warning == (
        f"module.Thing: {_RUNTIME_ONLY}. "
        "Write a `Deprecated:` section in the docstring to fix this."
    )


@pytest.mark.parametrize(
    ("decorator", "logged"),
    [
        ("deprecated", "`@deprecated` needs to be called with a message"),
        ("deprecated()", "the deprecation decorator's arguments don't match"),
        (
            "deprecated(message='Gone')",
            "the deprecation decorator's arguments don't match",
        ),
        (
            "deprecated('Gone', 'Really')",
            "the deprecation decorator's arguments don't match",
        ),
        (
            "deprecated('Gone', until='v2')",
            "the deprecation decorator's arguments don't match",
        ),
        (
            "deprecated('Gone', category=None, category=None)",
            "the deprecation decorator's arguments don't match",
        ),
    ],
)
def test_a_decorator_that_does_not_bind_leaves_the_object_unmarked(
    caplog: pytest.LogCaptureFixture, decorator: str, logged: str
) -> None:
    """Warn and leave the object unmarked if the runtime would reject the call."""
    code = (
        "from typing_extensions import deprecated\n"
        f"@{decorator}\n"
        "def Thing():\n" + _HANDWRITTEN
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        obj = visit(code)["Thing"]
    assert "deprecated" not in obj.labels
    assert obj.deprecated is None
    [warning] = warned(caplog)
    assert logged in warning


def test_the_decorators_are_an_option() -> None:
    """Accept a project's own decorator instead of the defaults."""
    code = (
        "from typing_extensions import deprecated\n"
        "from mypkg.compat import gone\n"
        "@gone('mod.Old is deprecated.')\n"
        "def Old(): ...\n"
        "@deprecated('mod.Other is deprecated.')\n"
        "def Other(): ...\n"
    )
    module = visit(code, decorator_functions=["mypkg.compat.gone"])
    assert module["Old"].deprecated == "mod.Old is deprecated."
    assert module["Other"].deprecated is None


def test_the_decorators_can_be_left_to_another_extension() -> None:
    """An empty list turns the decorator handling off."""
    code = (
        "from typing_extensions import deprecated\n"
        "@deprecated('mod.Thing is deprecated.')\n"
        "def Thing(): ...\n"
    )
    obj = visit(code, decorator_functions=[])["Thing"]
    assert obj.deprecated is None
    assert not admonitions(obj)


def test_the_admonition_follows_the_options() -> None:
    """`kind`, `title` and `label` apply to decorated objects too."""
    code = (
        "from typing_extensions import deprecated\n"
        "@deprecated('mod.Thing is deprecated.')\n"
        "def Thing(): ...\n"
    )
    obj = visit(code, kind="deprecated", title="Gone", label=None)["Thing"]
    assert not obj.labels
    [admonition] = admonitions(obj)
    assert admonition.title == "Gone"
    assert admonition.value.annotation == "deprecated"


_DECORATORS = [typing_extensions.deprecated]
if sys.version_info >= (3, 13):
    _DECORATORS.append(warnings.deprecated)  # pylint: disable=no-member


@pytest.mark.parametrize("decorator", _DECORATORS)
@pytest.mark.parametrize(
    "arguments",
    [
        "'Gone'",
        "'Gone', category=None",
        "'Gone', category=DeprecationWarning, stacklevel=2",
        "'Gone', stacklevel=2",
        "",
        "message='Gone'",
        "'Gone', 'Really'",
        "'Gone', DeprecationWarning",
        "'Gone', until='v2'",
    ],
)
def test_decorators_bind_as_at_runtime(decorator: Any, arguments: str) -> None:
    """Mark the object exactly when the real decorator accepts the call.

    This checks the combinations of arguments, not their values, which the
    extension doesn't validate.
    """
    try:
        exec(  # pylint: disable=exec-used
            f"@deprecated({arguments})\ndef Thing(): ...\n", {"deprecated": decorator}
        )
    except TypeError:
        accepted = False
    else:
        accepted = True
    path = f"{decorator.__module__}.deprecated"
    module = visit(
        f"import {decorator.__module__}\n@{path}({arguments})\ndef Thing(): ...\n"
    )
    assert bool(module["Thing"].deprecated) == accepted

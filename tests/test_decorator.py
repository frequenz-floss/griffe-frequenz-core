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
    """Visit code with the extension enabled and parse its docstrings.

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
        render(module)
        return module


def render(obj: griffe.Object) -> None:
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
            render(member)


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


_OVERLOADS = (
    "from typing import overload\n"
    "from typing_extensions import deprecated\n"
    "@overload\n"
    "@deprecated('Calling mod.f with an int is deprecated.')\n"
    "def f(x: int) -> int: ...\n"
    "@overload\n"
    "def f(x: str) -> str: ...\n"
)


def test_a_deprecated_overload_is_noted_on_its_function(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Show an overload's notice in its function's docstring.

    The function itself is not deprecated, so it is not marked, but the
    overload is.
    """
    code = _OVERLOADS + 'def f(x):\n    """Do f."""\n'
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        func = visit(code)["f"]
    assert isinstance(func, griffe.Function)
    assert func.deprecated is None
    assert "deprecated" not in func.labels
    [admonition] = admonitions(func)
    assert admonition.value.contents == "Calling mod.f with an int is deprecated."
    assert func.docstring is not None
    assert func.docstring.parsed[0] is admonition
    assert func.overloads is not None
    deprecated, other = func.overloads
    assert deprecated.deprecated == "Calling mod.f with an int is deprecated."
    assert "deprecated" in deprecated.labels
    assert not admonitions(deprecated)
    assert other.deprecated is None
    [warning] = warned(caplog)
    assert warning == (
        f"module.f: an overload is deprecated, and {_RUNTIME_ONLY}. Write a "
        "`Deprecated:` section in the docstring saying which part is deprecated."
    )


def test_deprecated_overloads_of_a_method_share_one_notice(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Combine the overloads' notices and warn once for each deprecated part."""
    code = (
        "import typing_extensions\n"
        "class Owner:\n"
        "    @typing_extensions.overload\n"
        "    @typing_extensions.deprecated('Calling with an int is deprecated.')\n"
        "    def f(self, x: int) -> int: ...\n"
        "    @typing_extensions.overload\n"
        "    @typing_extensions.deprecated(MESSAGE)\n"
        "    def f(self, x: str) -> str: ...\n"
        "    @typing_extensions.overload\n"
        "    @typing_extensions.deprecated(OTHER)\n"
        "    def f(self, x: bytes) -> str: ...\n"
        "    def f(self, x): ...\n"
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        func = visit(code)["Owner.f"]
    [admonition] = admonitions(func)
    assert admonition.value.contents == (
        "Calling with an int is deprecated.\n\nOne of its overloads is deprecated."
    )
    logged = warned(caplog)
    assert len(logged) == 3
    assert _UNREADABLE in logged[1]
    assert func.overloads is not None
    assert [overload.deprecated for overload in func.overloads] == [
        "Calling with an int is deprecated.",
        _GENERIC,
        _GENERIC,
    ]


def test_a_handwritten_notice_covers_a_deprecated_overload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The notice says which overload, and stays where it is written.

    The function itself is not marked, so its notice is not moved to the top.
    """
    code = _OVERLOADS + (
        "def f(x):\n"
        '    """Do f.\n\n'
        "    Deprecated:\n"
        "        Calling it with an `int` is deprecated since v1.2.0.\n"
        '    """\n'
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        func = visit(code)["f"]
    assert not warned(caplog)
    [admonition] = admonitions(func)
    assert "since v1.2.0" in admonition.value.contents
    assert func.docstring is not None
    assert func.docstring.parsed[1] is admonition
    assert func.deprecated is None


def test_a_deprecated_function_covers_its_overloads(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The whole function's notice covers its deprecated overloads too."""
    code = _OVERLOADS + (
        "@deprecated('mod.f is deprecated.')\n" "def f(x):\n" + _HANDWRITTEN
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        func = visit(code)["f"]
    assert not warned(caplog)
    assert func.deprecated == "mod.f is deprecated."
    [admonition] = admonitions(func)
    assert admonition.value.contents == "Use B instead."
    assert func.overloads is not None
    assert func.overloads[0].deprecated == "Calling mod.f with an int is deprecated."


def test_an_overload_decorator_that_does_not_bind_is_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Don't add a notice for an invalid decorator call."""
    code = (
        "from typing import overload\n"
        "from typing_extensions import deprecated\n"
        "@overload\n"
        "@deprecated(message='Gone')\n"
        "def f(x: int) -> int: ...\n"
        "def f(x): ...\n"
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        func = visit(code)["f"]
    assert not admonitions(func)
    assert func.overloads is not None
    assert func.overloads[0].deprecated is None
    [warning] = warned(caplog)
    assert "the deprecation decorator's arguments don't match" in warning


_PROPERTY = (
    "from typing_extensions import deprecated\n"
    "class Owner:\n"
    "    @property\n"
    "    def p(self) -> int:\n"
    '        """The p."""\n'
)


def test_deprecated_property_accessors_are_noted_on_the_property(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Show setter and deleter notices in the property's docstring."""
    code = _PROPERTY + (
        "    @p.setter\n"
        "    @deprecated('Setting mod.Owner.p is deprecated.')\n"
        "    def p(self, value: int) -> None: ...\n"
        "    @p.deleter\n"
        "    @deprecated(MESSAGE)\n"
        "    def p(self) -> None: ...\n"
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        prop = visit(code)["Owner.p"]
    assert isinstance(prop, griffe.Attribute)
    assert prop.deprecated is None
    assert "deprecated" not in prop.labels
    [admonition] = admonitions(prop)
    assert admonition.value.contents == (
        "Setting mod.Owner.p is deprecated.\n\nDeleting it is deprecated."
    )
    assert prop.setter is not None and prop.deleter is not None
    assert prop.setter.deprecated == "Setting mod.Owner.p is deprecated."
    assert prop.deleter.deprecated == _GENERIC
    logged = warned(caplog)
    assert len(logged) == 2
    assert logged[0].startswith("module.Owner.p: its setter is deprecated, and ")
    assert logged[1].startswith("module.Owner.p: its deleter is deprecated, and ")


def test_a_handwritten_notice_covers_a_deprecated_setter(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Don't warn if the property has a hand-written notice for its setter."""
    code = (
        "from typing_extensions import deprecated\n"
        "class Owner:\n"
        "    @property\n"
        "    def p(self) -> int:\n"
        '        """The p.\n\n'
        "        Deprecated:\n"
        "            Setting it is deprecated since v1.2.0.\n"
        '        """\n'
        "    @p.setter\n"
        "    @deprecated('Setting mod.Owner.p is deprecated.')\n"
        "    def p(self, value: int) -> None: ...\n"
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        prop = visit(code)["Owner.p"]
    assert not warned(caplog)
    [admonition] = admonitions(prop)
    assert "since v1.2.0" in admonition.value.contents


def test_a_deprecated_property_covers_its_setter(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The whole property's notice covers its deprecated setter too."""
    code = (
        "from typing_extensions import deprecated\n"
        "class Owner:\n"
        "    @property\n"
        "    @deprecated('mod.Owner.p is deprecated.')\n"
        "    def p(self) -> int:\n"
        '        """The p.\n\n'
        "        Deprecated:\n"
        "            Use B instead.\n"
        '        """\n'
        "    @p.setter\n"
        "    @deprecated('Setting mod.Owner.p is deprecated.')\n"
        "    def p(self, value: int) -> None: ...\n"
    )
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        prop = visit(code)["Owner.p"]
    assert not warned(caplog)
    assert prop.deprecated == "mod.Owner.p is deprecated."
    [admonition] = admonitions(prop)
    assert admonition.value.contents == "Use B instead."


def _warnings_deprecated() -> griffe.Extension:
    """Create a test replacement for `griffe-warnings-deprecated`.

    The check only uses the extension's module path, so we don't need the
    real package as a dependency.

    Returns:
        An extension that does nothing, with the real extension's module path.
    """
    extension: type[griffe.Extension] = type(
        "WarningsDeprecatedExtension",
        (griffe.Extension,),
        {"__module__": "griffe_warnings_deprecated._internal.extension"},
    )
    return extension()


@pytest.mark.parametrize("first", [True, False], ids=["before", "after"])
def test_griffe_warnings_deprecated_enabled_too_is_warned_about_once(
    caplog: pytest.LogCaptureFixture, first: bool
) -> None:
    """Warn if both extensions would document the decorator.

    Warn once per set of extensions, even if several modules are visited.
    """
    ours = DeprecationsExtension()
    other = _warnings_deprecated()
    extensions = griffe.load_extensions(*((other, ours) if first else (ours, other)))
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        for _ in range(2):
            with griffe.temporary_visited_module("", extensions=extensions):
                pass
    [warning] = warned(caplog)
    assert warning.startswith("griffe_warnings_deprecated is enabled too")


@pytest.mark.parametrize(
    "extensions",
    [
        lambda: [DeprecationsExtension()],
        lambda: [DeprecationsExtension(decorator_functions=[]), _warnings_deprecated()],
    ],
    ids=["alone", "decorator-left-to-it"],
)
def test_griffe_warnings_deprecated_is_fine_when_not_competing(
    caplog: pytest.LogCaptureFixture, extensions: Any
) -> None:
    """Don't warn if only one extension would document decorators."""
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            "", extensions=griffe.load_extensions(*extensions())
        ),
    ):
        pass
    assert not warned(caplog)

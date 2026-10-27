# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the deprecations extension.

The fixtures in `fixtures/` use `frequenz-core` helpers, but they are never
run. Griffe resolves the helper paths from the import statements, without
importing `frequenz-core`. Only the compatibility tests import it.
"""

import logging
from pathlib import Path
from typing import Any

import griffe
import pytest
from griffe import (
    Attribute,
    DocstringSectionAdmonition,
    DocstringSectionKind,
    ExprName,
    Module,
    Parser,
)

from griffe_frequenz_core.deprecations import DeprecationsExtension

_FIXTURES = Path(__file__).parent / "fixtures"

_ALIASES = "frequenz.core.warnings.deprecated_aliases"
_MEMBERS = "frequenz.core.enum.deprecated_member"
_LOGGER = "griffe_frequenz_core.deprecations"


def load(
    name: str = "samplepkg", *, parser: Parser = Parser.google, **options: Any
) -> Module:
    """Load a fixture with the extension applied.

    Args:
        name: The fixture package or module to load.
        parser: The docstring style the fixture is written in.
        **options: The extension's options.

    Returns:
        The loaded module.
    """
    loaded = griffe.load(
        name,
        search_paths=[_FIXTURES],
        docstring_parser=parser,
        extensions=griffe.load_extensions(DeprecationsExtension(**options)),
    )
    assert isinstance(loaded, Module)
    return loaded


def attribute(module: Module, path: str) -> Attribute:
    """Return one attribute of a loaded fixture.

    Args:
        module: The loaded fixture.
        path: The dotted path of the attribute inside it.

    Returns:
        The attribute.
    """
    member = module[path]
    assert isinstance(member, Attribute)
    return member


def admonitions(member: Attribute) -> list[DocstringSectionAdmonition]:
    """Return the admonition sections of an attribute's docstring.

    Args:
        member: The attribute to look at.

    Returns:
        Its admonition sections, in order, or an empty list if it has no
        docstring.
    """
    if member.docstring is None:
        return []
    return [
        section
        for section in member.docstring.parsed
        if isinstance(section, DocstringSectionAdmonition)
    ]


@pytest.fixture(name="samplepkg", scope="module")
def samplepkg_fixture() -> Module:
    """Load the sample package once, with the extension's defaults.

    Returns:
        The loaded package.
    """
    return load()


def test_every_alias_in_the_table_is_marked(samplepkg: Module) -> None:
    """Ensure all three entries are marked, whatever their docstring looks like."""
    for name in ("Widget", "Doohickey", "MAX_WIDGETS"):
        member = attribute(samplepkg, f"oldmod.{name}")
        assert "deprecated" in member.labels
        assert isinstance(member.deprecated, str)


def test_default_message_names_both_ends(samplepkg: Module) -> None:
    """Ensure the default template includes the old and the new path."""
    member = attribute(samplepkg, "oldmod.MAX_WIDGETS")
    assert member.deprecated == (
        "`samplepkg.oldmod.MAX_WIDGETS` is deprecated. Use "
        '<autoref identifier="samplepkg.newmod.MAX_WIDGETS" optional>'
        "<code>samplepkg.newmod.MAX_WIDGETS</code></autoref> instead."
    )


def test_a_renamed_alias_points_at_its_new_name(samplepkg: Module) -> None:
    """Ensure a `module:name` target points to the new name."""
    member = attribute(samplepkg, "oldmod.Doohickey")
    assert member.value == ExprName("samplepkg.newmod.Gadget")
    assert "samplepkg.newmod.Gadget" in str(member.deprecated)


def test_an_alias_without_a_docstring_gets_one(samplepkg: Module) -> None:
    """Ensure an alias without a docstring gets one, with the admonition."""
    member = attribute(samplepkg, "oldmod.MAX_WIDGETS")
    assert member.docstring is not None
    sections = admonitions(member)
    assert len(sections) == 1
    assert sections[0].value.contents == member.deprecated


def test_the_admonition_goes_first(samplepkg: Module) -> None:
    """Ensure the admonition goes before the rest of the docstring."""
    member = attribute(samplepkg, "oldmod.Doohickey")
    assert member.docstring is not None
    kinds = [section.kind for section in member.docstring.parsed]
    assert kinds[0] is DocstringSectionKind.admonition


def test_a_handwritten_admonition_is_left_alone(samplepkg: Module) -> None:
    """Ensure a hand-written admonition is kept as written."""
    member = attribute(samplepkg, "oldmod.Widget")
    sections = admonitions(member)
    assert len(sections) == 1
    assert "deprecated since v1.2.0" in sections[0].value.contents
    # The label and the field are still set, only the docstring is kept as is.
    assert "deprecated" in member.labels
    assert isinstance(member.deprecated, str)


def test_a_handwritten_numpy_section_is_left_alone() -> None:
    """Ensure a hand-written numpy `Deprecated` section is kept as written."""
    member = attribute(load("numpymod", parser=Parser.numpy), "Widget")
    assert not admonitions(member)
    assert member.docstring is not None
    kinds = [section.kind for section in member.docstring.parsed]
    assert DocstringSectionKind.deprecated in kinds
    assert "deprecated" in member.labels


def test_the_keyword_form_is_understood(samplepkg: Module) -> None:
    """Ensure the table can be passed as `aliases=` instead of positionally."""
    member = attribute(samplepkg, "oldmod2.Thing")
    assert "deprecated" in member.labels
    assert member.value == ExprName("samplepkg.newmod.Widget")


def test_the_calls_own_message_wins(samplepkg: Module) -> None:
    """Ensure the call's `message` is used, so the docs match the runtime warning."""
    member = attribute(samplepkg, "oldmod2.Thing")
    assert str(member.deprecated).startswith("`samplepkg.oldmod2.Thing` moved to ")
    assert str(member.deprecated).endswith(" in v2.0.0 and will be removed in v3.0.0.")


def test_an_alias_hidden_from_type_checkers_is_created(samplepkg: Module) -> None:
    """Ensure a table entry without a declaration is still documented."""
    member = attribute(samplepkg, "edge.Hidden")
    assert "deprecated" in member.labels
    assert member.value == ExprName("samplepkg.newmod.Widget")


def test_an_unknown_target_is_linked_optionally(samplepkg: Module) -> None:
    """Ensure an unknown target gets an optional link, so strict builds don't fail."""
    member = attribute(samplepkg, "edge.Outside")
    assert '<autoref identifier="some.external.pkg.Thing" optional>' in str(
        member.deprecated
    )


def test_an_unrelated_module_getattr_is_untouched(samplepkg: Module) -> None:
    """Ensure a module with its own `__getattr__` isn't changed."""
    other = samplepkg["other"]
    assert isinstance(other, Module)
    # No new members: `Any` is just imported by the fixture.
    assert set(other.members) == {"Any", "__getattr__", "VALUE"}
    getattr_ = other["__getattr__"]
    assert "deprecated" not in getattr_.labels
    assert not getattr_.deprecated
    value = attribute(other, "VALUE")
    assert "deprecated" not in value.labels
    assert not value.deprecated
    assert admonitions(value) == []


def test_wrapped_enum_members_are_marked(samplepkg: Module) -> None:
    """Ensure wrapped members get the label, the field and the admonition."""
    for name, message in (
        ("PENDING", "PENDING is deprecated, use OPEN instead"),
        ("STARTED", "STARTED is deprecated, use IN_PROGRESS instead"),
    ):
        member = attribute(samplepkg, f"statuses.TaskStatus.{name}")
        assert "deprecated" in member.labels
        assert member.deprecated == message
        sections = admonitions(member)
        assert len(sections) == 1
        assert sections[0].value.contents == message


def test_the_class_form_of_the_wrapper_is_recognized(samplepkg: Module) -> None:
    """Ensure `DeprecatedMember(...)` is recognized like `deprecated_member()`."""
    member = attribute(samplepkg, "statuses.TaskStatus.WAITING")
    assert "deprecated" in member.labels
    assert member.deprecated == "WAITING is deprecated, use OPEN instead"
    assert str(member.value) == "1"


def test_a_wrapped_enum_member_shows_its_real_value(samplepkg: Module) -> None:
    """Ensure the documentation shows `PENDING = 1`, not the wrapper call."""
    assert str(attribute(samplepkg, "statuses.TaskStatus.PENDING").value) == "1"


def test_other_enum_members_are_untouched(samplepkg: Module) -> None:
    """Ensure plain members, and members created by other calls, aren't changed."""
    for name in ("OPEN", "IN_PROGRESS", "COMPUTED"):
        member = attribute(samplepkg, f"statuses.TaskStatus.{name}")
        assert "deprecated" not in member.labels
        assert not member.deprecated
        assert admonitions(member) == []


def test_a_non_literal_enum_message_is_skipped_loudly(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure a member with its message in a constant isn't marked, and it's logged."""
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        package = load()
    member = attribute(package, "statuses.TaskStatus.CANCELLED")
    assert not member.deprecated
    assert "deprecated" not in member.labels
    assert any(
        "CANCELLED" in record.message and "isn't a string literal" in record.message
        for record in caplog.records
    )


@pytest.mark.parametrize(
    "arguments",
    ["1, message='Gone'", "value=1, message='Gone'", "message='Gone', value=1"],
)
def test_enum_wrapper_keyword_arguments_are_understood(arguments: str) -> None:
    """Ensure the value and the message can be passed by keyword, in any order."""
    code = (
        "from frequenz.core.enum import Enum, deprecated_member\n"
        "class Status(Enum):\n"
        f"    A = deprecated_member({arguments})\n"
    )
    with griffe.temporary_visited_module(
        code, extensions=griffe.load_extensions(DeprecationsExtension())
    ) as module:
        member = attribute(module, "Status.A")
        assert member.deprecated == "Gone"
        assert "deprecated" in member.labels
        assert str(member.value) == "1"


@pytest.mark.parametrize(
    ("arguments", "logged"),
    [
        ("*ARGS, 'Gone'", "arguments are unpacked"),
        ("*ARGS", "arguments are unpacked"),
        ("1, 'Gone', **KWARGS", "arguments are unpacked"),
        ("1", "don't match `deprecated_member(value, message)`"),
        ("message='Gone'", "don't match `deprecated_member(value, message)`"),
        ("1, 'Gone', 2", "don't match `deprecated_member(value, message)`"),
        (
            "1, value=2, message='Gone'",
            "don't match `deprecated_member(value, message)`",
        ),
        ("1, msg='Gone'", "don't match `deprecated_member(value, message)`"),
    ],
)
def test_an_unreadable_enum_wrapper_call_is_skipped_loudly(
    caplog: pytest.LogCaptureFixture, arguments: str, logged: str
) -> None:
    """Ensure wrapper calls that can't be read don't mark the member, and are logged.

    `*ARGS, 'Gone'` is the tricky one. If we just counted positions, `'Gone'`
    would look like a valid message, and the member would be documented as
    `A = *ARGS`.
    """
    code = (
        "from frequenz.core.enum import Enum, deprecated_member\n"
        "class Status(Enum):\n"
        f"    A = deprecated_member({arguments})\n"
    )
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code, extensions=griffe.load_extensions(DeprecationsExtension())
        ) as module,
    ):
        member = attribute(module, "Status.A")
        assert not member.deprecated
        assert "deprecated" not in member.labels
        assert str(member.value) == f"deprecated_member({arguments})"
    assert any(
        "Status.A" in record.message and logged in record.message
        for record in caplog.records
    )


def test_a_non_literal_alias_message_falls_back(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure an alias with a non-literal `message` is marked with the default one."""
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        package = load()
    member = attribute(package, "nonliteral.Thing")
    assert "deprecated" in member.labels
    assert str(member.deprecated).startswith(
        "`samplepkg.nonliteral.Thing` is deprecated. Use "
    )
    assert any("`message` isn't a string literal" in r.message for r in caplog.records)


def test_a_non_literal_alias_entry_is_skipped_loudly(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure an entry with a non-literal name is skipped, and it's logged."""
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        package = load()
    assert "Lost" not in package["nonliteral"].members
    assert any("isn't a pair of string literals" in r.message for r in caplog.records)


def test_an_alias_table_in_a_constant_is_skipped_loudly(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure a table in a constant is logged, because none of its aliases are marked."""
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        package = load()
    member = attribute(package, "constant.Thing")
    assert not member.deprecated
    assert "deprecated" not in member.labels
    assert any(
        record.message
        == "samplepkg.constant: the alias table `_ALIASES` isn't a dict literal, "
        "so none of its aliases are marked"
        for record in caplog.records
    )


@pytest.mark.parametrize(
    ("arguments", "logged"),
    [
        (
            "__name__, aliases=ALIASES",
            "the alias table `ALIASES` isn't a dict literal",
        ),
        ("*ARGS", "the alias table argument can't be found"),
        ("*ARGS, {'Thing': 'pkg.new'}", "the alias table argument can't be found"),
        ("__name__, **KWARGS", "the alias table argument can't be found"),
        ("__name__", "the alias table argument can't be found"),
    ],
)
def test_an_unreadable_alias_table_is_skipped_loudly(
    caplog: pytest.LogCaptureFixture, arguments: str, logged: str
) -> None:
    """Ensure every alias table that can't be read is logged."""
    code = (
        "from frequenz.core.warnings import deprecated_aliases\n"
        f"__getattr__ = deprecated_aliases({arguments})\n"
    )
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER),
        griffe.temporary_visited_module(
            code, extensions=griffe.load_extensions(DeprecationsExtension())
        ) as module,
    ):
        assert "Thing" not in module.members
    assert any(logged in record.message for record in caplog.records)


def test_only_the_table_argument_is_read() -> None:
    """Ensure a dict in another position isn't used as the table."""
    code = (
        "from frequenz.core.warnings import deprecated_aliases\n"
        "__getattr__ = deprecated_aliases({'Wrong': 'pkg.new'}, {'Right': 'pkg.new'})\n"
    )
    with griffe.temporary_visited_module(
        code, extensions=griffe.load_extensions(DeprecationsExtension())
    ) as module:
        assert "Right" in module.members
        assert "Wrong" not in module.members


def test_the_defaults_match_griffe_warnings_deprecated() -> None:
    """Ensure the defaults are the same as in `griffe-warnings-deprecated`."""
    extension = DeprecationsExtension()
    assert extension.kind == "danger"
    assert extension.title == "Deprecated"
    assert extension.label == "deprecated"


def test_the_admonition_is_configurable() -> None:
    """Ensure the admonition style can be changed."""
    package = load(kind="deprecated", title="No longer supported", label="old")
    member = attribute(package, "oldmod.MAX_WIDGETS")
    assert member.labels == {"old", "module-attribute"}
    sections = admonitions(member)
    assert len(sections) == 1
    assert sections[0].value.kind == "deprecated"
    assert sections[0].title == "No longer supported"


def test_the_label_can_be_dropped() -> None:
    """Ensure no label is added if `label` is `None`."""
    member = attribute(load(label=None), "oldmod.MAX_WIDGETS")
    assert member.labels == {"module-attribute"}
    assert isinstance(member.deprecated, str)


def test_show_target_keeps_the_private_name_when_off() -> None:
    """Ensure the value is kept as written in the source when disabled."""
    member = attribute(load(show_target=False), "oldmod.Widget")
    assert member.value == ExprName("_Widget")


def test_the_default_message_is_configurable() -> None:
    """Ensure the default message can be changed."""
    package = load(default_message="{old} is gone, see {new}.")
    member = attribute(package, "oldmod.MAX_WIDGETS")
    assert str(member.deprecated).startswith("`samplepkg.oldmod.MAX_WIDGETS` is gone,")


def test_only_the_configured_paths_match() -> None:
    """Ensure only the configured paths are recognized."""
    package = load(
        alias_table_functions=["mypkg.compat.moved_to"],
        member_wrapper_functions=["mypkg.compat.retired"],
    )
    assert "deprecated" not in attribute(package, "oldmod.Widget").labels
    assert not attribute(package, "oldmod2.Thing").deprecated
    assert not attribute(package, "statuses.TaskStatus.PENDING").deprecated
    # `Hidden` exists only because the extension creates it.
    assert "Hidden" not in package["edge"].members


def test_extra_paths_can_be_added() -> None:
    """Ensure a project can add its own helpers to the frequenz-core ones."""
    package = load(
        alias_table_functions=[_ALIASES, "mypkg.compat.moved_to"],
        member_wrapper_functions=[_MEMBERS, "mypkg.compat.retired"],
    )
    assert "deprecated" in attribute(package, "oldmod.Widget").labels
    assert "deprecated" in attribute(package, "statuses.TaskStatus.PENDING").labels

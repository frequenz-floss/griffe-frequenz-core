# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the deprecations extension.

The fixtures under `fixtures/` refer to `frequenz-core` helpers but are never
run. Griffe resolves those paths from import statements without importing
`frequenz-core`; only the compatibility tests import the installed test
dependency.
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
    """All three entries are marked, whatever their docstring looks like."""
    for name in ("Widget", "Doohickey", "MAX_WIDGETS"):
        member = attribute(samplepkg, f"oldmod.{name}")
        assert "deprecated" in member.labels
        assert isinstance(member.deprecated, str)


def test_default_message_names_both_ends(samplepkg: Module) -> None:
    """The default template is filled with the old path and the new one."""
    member = attribute(samplepkg, "oldmod.MAX_WIDGETS")
    assert member.deprecated == (
        "`samplepkg.oldmod.MAX_WIDGETS` is deprecated. Use "
        '<autoref identifier="samplepkg.newmod.MAX_WIDGETS" optional>'
        "<code>samplepkg.newmod.MAX_WIDGETS</code></autoref> instead."
    )


def test_a_renamed_alias_points_at_its_new_name(samplepkg: Module) -> None:
    """A `module:name` target renames as well as moves."""
    member = attribute(samplepkg, "oldmod.Doohickey")
    assert member.value == ExprName("samplepkg.newmod.Gadget")
    assert "samplepkg.newmod.Gadget" in str(member.deprecated)


def test_an_alias_without_a_docstring_gets_one(samplepkg: Module) -> None:
    """The admonition still has somewhere to go when there is no docstring."""
    member = attribute(samplepkg, "oldmod.MAX_WIDGETS")
    assert member.docstring is not None
    sections = admonitions(member)
    assert len(sections) == 1
    assert sections[0].value.contents == member.deprecated


def test_the_admonition_goes_first(samplepkg: Module) -> None:
    """A reader sees the deprecation before the prose describing the symbol."""
    member = attribute(samplepkg, "oldmod.Doohickey")
    assert member.docstring is not None
    kinds = [section.kind for section in member.docstring.parsed]
    assert kinds[0] is DocstringSectionKind.admonition


def test_a_handwritten_admonition_is_left_alone(samplepkg: Module) -> None:
    """A module can say more than the template, and keeps the last word."""
    member = attribute(samplepkg, "oldmod.Widget")
    sections = admonitions(member)
    assert len(sections) == 1
    assert "deprecated since v1.2.0" in sections[0].value.contents
    # The label and the field are still set, only the prose is left as written.
    assert "deprecated" in member.labels
    assert isinstance(member.deprecated, str)


def test_a_handwritten_numpy_section_is_left_alone() -> None:
    """Numpy style expresses the same thing as a section of its own kind."""
    member = attribute(load("numpymod", parser=Parser.numpy), "Widget")
    assert not admonitions(member)
    assert member.docstring is not None
    kinds = [section.kind for section in member.docstring.parsed]
    assert DocstringSectionKind.deprecated in kinds
    assert "deprecated" in member.labels


def test_the_keyword_form_is_understood(samplepkg: Module) -> None:
    """The table may be passed as `aliases=` rather than positionally."""
    member = attribute(samplepkg, "oldmod2.Thing")
    assert "deprecated" in member.labels
    assert member.value == ExprName("samplepkg.newmod.Widget")


def test_the_calls_own_message_wins(samplepkg: Module) -> None:
    """A `message=` is reused, so warning and docs have one source."""
    member = attribute(samplepkg, "oldmod2.Thing")
    assert str(member.deprecated).startswith("`samplepkg.oldmod2.Thing` moved to ")
    assert str(member.deprecated).endswith(" in v2.0.0 and will be removed in v3.0.0.")


def test_an_alias_hidden_from_type_checkers_is_created(samplepkg: Module) -> None:
    """A table entry with no declaration still gets documented."""
    member = attribute(samplepkg, "edge.Hidden")
    assert "deprecated" in member.labels
    assert member.value == ExprName("samplepkg.newmod.Widget")


def test_an_unknown_target_is_linked_optionally(samplepkg: Module) -> None:
    """An optional autoref degrades to text instead of failing a strict build."""
    member = attribute(samplepkg, "edge.Outside")
    assert '<autoref identifier="some.external.pkg.Thing" optional>' in str(
        member.deprecated
    )


def test_an_unrelated_module_getattr_is_untouched(samplepkg: Module) -> None:
    """A module defining its own `__getattr__` must come out unchanged."""
    other = samplepkg["other"]
    assert isinstance(other, Module)
    # Nothing was invented: `Any` is just the import the fixture makes.
    assert set(other.members) == {"Any", "__getattr__", "VALUE"}
    getattr_ = other["__getattr__"]
    assert "deprecated" not in getattr_.labels
    assert not getattr_.deprecated
    value = attribute(other, "VALUE")
    assert "deprecated" not in value.labels
    assert not value.deprecated
    assert admonitions(value) == []


def test_wrapped_enum_members_are_marked(samplepkg: Module) -> None:
    """Both wrapped members get the label, the field and the admonition."""
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


def test_a_wrapped_enum_member_shows_its_real_value(samplepkg: Module) -> None:
    """The documentation says `PENDING = 1`, not the wrapper call."""
    assert str(attribute(samplepkg, "statuses.TaskStatus.PENDING").value) == "1"


def test_other_enum_members_are_untouched(samplepkg: Module) -> None:
    """Plain members, and members built by some other call, are left alone."""
    for name in ("OPEN", "IN_PROGRESS", "COMPUTED"):
        member = attribute(samplepkg, f"statuses.TaskStatus.{name}")
        assert "deprecated" not in member.labels
        assert not member.deprecated
        assert admonitions(member) == []


def test_a_non_literal_enum_message_is_skipped_loudly(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Griffe never runs the module, so a message in a constant is unreadable."""
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        package = load()
    member = attribute(package, "statuses.TaskStatus.CANCELLED")
    assert not member.deprecated
    assert "deprecated" not in member.labels
    assert any(
        "CANCELLED" in record.message and "not a static string" in record.message
        for record in caplog.records
    )


def test_a_non_literal_alias_message_falls_back(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The alias is still worth marking, only its wording is lost."""
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        package = load()
    member = attribute(package, "nonliteral.Thing")
    assert "deprecated" in member.labels
    assert str(member.deprecated).startswith(
        "`samplepkg.nonliteral.Thing` is deprecated. Use "
    )
    assert any("`message` is not a static string" in r.message for r in caplog.records)


def test_a_non_literal_alias_entry_is_skipped_loudly(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A table key that is not a literal names nothing Griffe can mark."""
    with caplog.at_level(logging.DEBUG, logger=_LOGGER):
        package = load()
    assert "Lost" not in package["nonliteral"].members
    assert any("is not a pair of static strings" in r.message for r in caplog.records)


def test_the_defaults_match_griffe_warnings_deprecated() -> None:
    """Configured beside the decorator extension, both render the same."""
    extension = DeprecationsExtension()
    assert extension.kind == "danger"
    assert extension.title == "Deprecated"
    assert extension.label == "deprecated"


def test_the_admonition_is_configurable() -> None:
    """A project wanting its own admonition style can ask for one."""
    package = load(kind="deprecated", title="No longer supported", label="old")
    member = attribute(package, "oldmod.MAX_WIDGETS")
    assert member.labels == {"old", "module-attribute"}
    sections = admonitions(member)
    assert len(sections) == 1
    assert sections[0].value.kind == "deprecated"
    assert sections[0].title == "No longer supported"


def test_the_label_can_be_dropped() -> None:
    """Passing no label leaves the object's labels as Griffe found them."""
    member = attribute(load(label=None), "oldmod.MAX_WIDGETS")
    assert member.labels == {"module-attribute"}
    assert isinstance(member.deprecated, str)


def test_show_target_keeps_the_private_name_when_off() -> None:
    """Turning it off leaves the assignment Griffe read from the source."""
    member = attribute(load(show_target=False), "oldmod.Widget")
    assert member.value == ExprName("_Widget")


def test_the_default_message_is_configurable() -> None:
    """It has to track the default of the function it stands in for."""
    package = load(default_message="{old} is gone, see {new}.")
    member = attribute(package, "oldmod.MAX_WIDGETS")
    assert str(member.deprecated).startswith("`samplepkg.oldmod.MAX_WIDGETS` is gone,")


def test_only_the_configured_paths_match() -> None:
    """Pointed somewhere else, the extension finds nothing to mark."""
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
    """A project may match its own helpers as well as the frequenz-core ones."""
    package = load(
        alias_table_functions=[_ALIASES, "mypkg.compat.moved_to"],
        member_wrapper_functions=[_MEMBERS, "mypkg.compat.retired"],
    )
    assert "deprecated" in attribute(package, "oldmod.Widget").labels
    assert "deprecated" in attribute(package, "statuses.TaskStatus.PENDING").labels

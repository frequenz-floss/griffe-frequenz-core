# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Compatibility tests with the installed `frequenz-core`.

All other tests in this suite are static: Griffe resolves the helper names from
the import statements in the fixtures. So those tests never import
`frequenz-core`, and they pass even if it isn't installed.

These tests are the only ones that import it. They check the parts of
`frequenz-core` this package depends on, by running the real helpers and
comparing what they do at runtime with what we put in the documentation.

An alias notice is written for the documentation and links the new path, so
it's different from the runtime warning. The tests only check that both say the
same things: since which version it is deprecated, and what to use instead. To
compare them, the tests only remove the link markup.
"""

import inspect
import re
import warnings
from pathlib import Path
from typing import Any

import frequenz.core.enum
import frequenz.core.warnings
import griffe
import pytest

from griffe_frequenz_core.deprecations import DeprecationsExtension

from . import fixture_aliases, fixture_enum

_FIXTURES = Path(__file__).parent


@pytest.fixture(name="task_status", scope="module")
def task_status_fixture() -> griffe.Class:
    """Load the fixture module with the extension applied.

    Returns:
        The `TaskStatus` class as Griffe sees it.
    """
    module = griffe.load(
        "fixture_enum",
        search_paths=[_FIXTURES],
        extensions=griffe.load_extensions(DeprecationsExtension()),
        docstring_parser=griffe.Parser.google,
    )
    task_status = module["TaskStatus"]
    assert isinstance(task_status, griffe.Class)
    return task_status


@pytest.fixture(name="pending_warning")
def pending_warning_fixture() -> warnings.WarningMessage:
    """Access the deprecated member and capture the warning it emits.

    Returns:
        The warning emitted by the real `frequenz-core`.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = fixture_enum.TaskStatus.PENDING

    assert len(caught) == 1, f"expected exactly one warning, got {len(caught)}"
    return caught[0]


def test_real_helper_is_recognized(task_status: griffe.Class) -> None:
    """Ensure a `deprecated_member()` call from the real `frequenz-core` is recognized."""
    pending = task_status["PENDING"]

    assert pending.deprecated
    assert "deprecated" in pending.labels
    # The wrapper call is replaced with the member's actual value.
    assert str(pending.value) == "1"


def test_documented_message_matches_runtime_warning(
    task_status: griffe.Class,
    pending_warning: warnings.WarningMessage,
) -> None:
    """Ensure the documented message is exactly the runtime warning message.

    This compares the two messages with each other, instead of with a copy in
    this file, so the test can't pass because of an outdated copy.
    """
    assert str(pending_warning.message) == task_status["PENDING"].deprecated
    assert issubclass(pending_warning.category, DeprecationWarning)


def test_admonition_is_rendered(task_status: griffe.Class) -> None:
    """Ensure the message is added to the docstring as an admonition, too."""
    pending = task_status["PENDING"]
    assert pending.docstring is not None
    sections = pending.docstring.parsed

    assert sections[0].kind is griffe.DocstringSectionKind.admonition
    assert sections[0].title == "Deprecated"
    assert sections[0].value.contents == pending.deprecated
    # The member's own docstring text is kept, after the admonition.
    assert [section.kind for section in sections[1:]] == [
        griffe.DocstringSectionKind.text
    ]


@pytest.mark.parametrize(
    "wrapper",
    [frequenz.core.enum.deprecated_member, frequenz.core.enum.DeprecatedMember],
)
def test_wrapper_parameters_are_value_and_message(wrapper: Any) -> None:
    """Ensure the extension uses the same argument names as `frequenz-core`.

    The extension reads `deprecated_member(value=..., message=...)` using these
    names. If `frequenz-core` renamed them, calls using keywords wouldn't be
    marked anymore.
    """
    bound = inspect.signature(wrapper).bind(value=1, message="Gone")
    assert bound.arguments == {"value": 1, "message": "Gone"}


def test_plain_member_is_left_alone(task_status: griffe.Class) -> None:
    """Ensure a member without `deprecated_member()` isn't changed and doesn't warn."""
    open_member = task_status["OPEN"]

    assert open_member.deprecated is None
    assert "deprecated" not in open_member.labels

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = fixture_enum.TaskStatus.OPEN

    assert not caught


def _plain(documented: str) -> str:
    """Remove the code font links from a documented deprecation notice.

    Args:
        documented: The documented deprecation notice.

    Returns:
        The notice with each ``[`path`][]`` and ``[`name`][path]`` replaced with
            the plain path.
    """
    documented = re.sub(r"\[`[\w.]+`\]\[([\w.]+)\]", r"\1", documented)
    return re.sub(r"\[`([\w.]+)`\]\[\]", r"\1", documented)


@pytest.fixture(name="aliases_module", scope="module")
def aliases_module_fixture() -> griffe.Module:
    """Load the alias fixture with the extension applied, using its runtime name.

    The runtime warning replaces `{old}` using the module's `__name__`, so Griffe
    must load the module using the same dotted path pytest used to import it.

    Returns:
        The fixture module as Griffe sees it.
    """
    name = fixture_aliases.__name__
    search_path = Path(fixture_aliases.__file__).parents[name.count(".")]
    module = griffe.load(
        name,
        search_paths=[search_path],
        extensions=griffe.load_extensions(DeprecationsExtension()),
        docstring_parser=griffe.Parser.google,
    )
    assert isinstance(module, griffe.Module)
    return module


def _alias_warning(name: str) -> warnings.WarningMessage:
    """Access a deprecated alias and capture the warning it emits.

    Args:
        name: The alias to access.

    Returns:
        The warning emitted by the real `frequenz-core`.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = getattr(fixture_aliases, name)

    assert len(caught) == 1, f"expected exactly one warning, got {len(caught)}"
    return caught[0]


@pytest.mark.parametrize(
    ("name", "target"),
    [
        ("Decimal", "decimal.Decimal"),
        ("Rational", "fractions.Fraction"),
        ("Gadget", f"{fixture_aliases.__name__}.Widget"),
        ("Number", "numbers.Number"),
    ],
)
def test_real_alias_helper_is_recognized(
    aliases_module: griffe.Module, name: str, target: str
) -> None:
    """Ensure every `DeprecatedAlias` from the real `frequenz-core` is recognized."""
    alias = aliases_module[name]

    assert alias.deprecated
    assert "deprecated" in alias.labels
    assert alias.value == griffe.ExprName(target)


@pytest.mark.parametrize(
    ("name", "target"),
    [("Rational", "fractions.Fraction"), ("Number", "numbers.Number")],
)
def test_alias_message_is_only_the_runtime_warning(
    aliases_module: griffe.Module, name: str, target: str
) -> None:
    """Ensure an alias with its own message warns with it, but documents its target.

    The message is only for the runtime warning, so the notice says what to use
    instead, with the same target the runtime uses.
    """
    warning = _alias_warning(name)

    assert str(warning.message).startswith(f"{fixture_aliases.__name__}.{name} ")
    assert issubclass(warning.category, DeprecationWarning)
    assert _plain(str(aliases_module[name].deprecated)) == (
        f"Deprecated. Use {target} instead."
    )


@pytest.mark.parametrize(
    ("name", "since", "target"),
    [
        ("Decimal", "v1.2.0", "decimal.Decimal"),
        ("Gadget", "v1.4.0", f"{fixture_aliases.__name__}.Widget"),
    ],
)
def test_since_alias_documents_the_runtime_version_and_target(
    aliases_module: griffe.Module, name: str, since: str, target: str
) -> None:
    """Ensure an alias with `since` documents the version and target it warns about.

    The notice is written for the documentation, so it's different from the
    runtime warning, but both must say the same version and replacement. `Gadget`
    has no `new_module`, so this also checks that both resolve it to the module
    where the alias is defined.
    """
    runtime = str(_alias_warning(name).message)
    documented = _plain(str(aliases_module[name].deprecated))

    for part in (f"since {since}.", f"Use {target} instead."):
        assert part in runtime
        assert part in documented


def test_alias_entry_parameters_match_the_extension() -> None:
    """Ensure `DeprecatedAlias` takes the name positionally and the rest by keyword.

    The extension reads the arguments as `DeprecatedAlias(name, /, *,
    new_module=None, new_name=None, since=None, message=None)`. If `frequenz-core`
    changed how it takes any of them, entries wouldn't be marked anymore.
    """
    parameters = inspect.signature(frequenz.core.warnings.DeprecatedAlias).parameters
    assert {name: parameter.kind for name, parameter in parameters.items()} == {
        "name": inspect.Parameter.POSITIONAL_ONLY,
        "new_module": inspect.Parameter.KEYWORD_ONLY,
        "new_name": inspect.Parameter.KEYWORD_ONLY,
        "since": inspect.Parameter.KEYWORD_ONLY,
        "message": inspect.Parameter.KEYWORD_ONLY,
    }


def test_alias_table_takes_entries_after_the_module() -> None:
    """Ensure `deprecated_aliases()` takes the module and then the entries, positionally.

    The extension reads every positional argument after the first as an entry,
    and ignores keywords. This is only correct if the parameters stay like this.
    """
    parameters = list(
        inspect.signature(frequenz.core.warnings.deprecated_aliases).parameters.values()
    )
    assert [parameter.kind for parameter in parameters[:2]] == [
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.VAR_POSITIONAL,
    ]
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters[2:]
    )

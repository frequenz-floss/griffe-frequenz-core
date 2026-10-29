# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Compatibility tests with the installed `frequenz-core`.

All other tests in this suite are static: Griffe resolves the helper names from
the import statements in the fixtures. So those tests never import
`frequenz-core`, and they pass even if it isn't installed.

These tests are the only ones that import it. They check the parts of
`frequenz-core` this package depends on, by running the real helpers and
comparing what they do at runtime with what we put in the documentation.

Generated notices are written for the documentation and link to the replacement.
They cover aliases and enum members with `new_name`. The tests check that each
notice points to the replacement used at runtime. Only the notice says since
which version the object is deprecated. To compare the replacements, the tests
remove the link markup.

The argument tests check that the extension documents a call if and only if
the real helper accepts it. A call that fails at runtime doesn't deprecate
anything.
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
    """Load the enum fixture with the extension applied, under its runtime name.

    A generated runtime warning names the enum by its module's `__name__`, so
    Griffe has to know the module by the same dotted path pytest imported it
    as.

    Returns:
        The `TaskStatus` class as Griffe sees it.
    """
    name = fixture_enum.__name__
    search_path = Path(fixture_enum.__file__).parents[name.count(".")]
    module = griffe.load(
        name,
        search_paths=[search_path],
        extensions=griffe.load_extensions(DeprecationsExtension()),
        docstring_parser=griffe.Parser.google,
    )
    task_status = module["TaskStatus"]
    assert isinstance(task_status, griffe.Class)
    return task_status


def _member_warning(name: str) -> warnings.WarningMessage:
    """Access a deprecated member and capture the warning it emits.

    Args:
        name: The member to access.

    Returns:
        The warning emitted by the real `frequenz-core`.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = getattr(fixture_enum.TaskStatus, name)

    assert len(caught) == 1, f"expected exactly one warning, got {len(caught)}"
    return caught[0]


_TASK_STATUS = f"{fixture_enum.__name__}.TaskStatus"


@pytest.mark.parametrize(
    ("name", "value"),
    [("PENDING", "1"), ("STARTED", "2"), ("WAITING", "1"), ("CANCELLED", "4")],
)
def test_real_helper_is_recognized(
    task_status: griffe.Class, name: str, value: str
) -> None:
    """Ensure the extension recognizes all wrappers used with the real core."""
    member = task_status[name]

    assert member.deprecated
    assert "deprecated" in member.labels
    # The wrapper call is replaced with the member's actual value.
    assert str(member.value) == value
    assert fixture_enum.TaskStatus.__members__[name].value == int(value)


def test_documented_message_matches_runtime_warning(task_status: griffe.Class) -> None:
    """Ensure a member without `new_name` shows its runtime warning as the notice.

    The notice starts with the version, because `since` isn't part of the
    warning. This compares the two messages with each other, instead of with a
    copy in this file, so the test can't pass because of an outdated copy.
    """
    warning = _member_warning("CANCELLED")
    assert "v1.4.0" not in str(warning.message)
    assert task_status["CANCELLED"].deprecated == (
        f"Deprecated since v1.4.0. {warning.message}"
    )
    assert issubclass(warning.category, DeprecationWarning)


@pytest.mark.parametrize(
    ("name", "since", "new"),
    [
        ("PENDING", "v1.2.0", "OPEN"),
        ("STARTED", None, "IN_PROGRESS"),
        ("WAITING", "v1.3.0", "OPEN"),
    ],
)
def test_member_documents_since_and_the_runtime_replacement(
    task_status: griffe.Class, name: str, since: str | None, new: str
) -> None:
    """Ensure an enum notice links to the replacement used at runtime.

    Only the notice says since which version the member is deprecated.
    `new_name` selects the replacement, even with a custom runtime message.
    """
    runtime = str(_member_warning(name).message)
    documented = _plain(str(task_status[name].deprecated))
    target = f"{_TASK_STATUS}.{new}"

    assert fixture_enum.TaskStatus.__members__[new].name == new
    if since is None:
        assert documented == f"Deprecated. Use {target} instead."
    else:
        assert documented == f"Deprecated since {since}. Use {target} instead."
        assert since not in runtime


@pytest.mark.parametrize(
    ("name", "new"), [("PENDING", "OPEN"), ("STARTED", "IN_PROGRESS")]
)
def test_generated_member_warning_follows_the_guide(name: str, new: str) -> None:
    """Ensure a generated enum warning follows the deprecations guide.

    It gives the fully qualified names of the member and its replacement. Only
    the notice says since which version the member is deprecated.
    """
    assert str(_member_warning(name).message) == (
        f"{_TASK_STATUS}.{name} is deprecated. Use {_TASK_STATUS}.{new} instead."
    )


def test_member_message_is_only_the_runtime_warning(task_status: griffe.Class) -> None:
    """Ensure `message` with `new_name` changes the runtime warning, not the notice."""
    warning = _member_warning("WAITING")

    assert str(warning.message) == (
        "TaskStatus.WAITING is deprecated. Use TaskStatus.OPEN instead, it was renamed."
    )
    assert str(task_status["WAITING"].deprecated).startswith("Deprecated since ")


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
def test_wrapper_parameters_match_the_extension(wrapper: Any) -> None:
    """Ensure the extension expects the same arguments as the core wrappers.

    It reads `deprecated_member(value, message=None, *, new_name=None,
    since=None)`. If core changes these parameters, the extension could miss
    members or read the wrong argument.
    """
    parameters = inspect.signature(wrapper).parameters
    assert {
        name: (parameter.kind, parameter.default)
        for name, parameter in parameters.items()
    } == {
        "value": (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.empty),
        "message": (inspect.Parameter.POSITIONAL_OR_KEYWORD, None),
        "new_name": (inspect.Parameter.KEYWORD_ONLY, None),
        "since": (inspect.Parameter.KEYWORD_ONLY, None),
    }


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


_ALIASES = [
    ("Decimal", "v1.2.0", "decimal.Decimal"),
    ("Rational", None, "fractions.Fraction"),
    ("Gadget", "v1.4.0", f"{fixture_aliases.__name__}.Widget"),
    ("Number", None, "numbers.Number"),
    ("Complex", "v1.5.0", "numbers.Complex"),
    ("Integral", None, "numbers.Integral"),
]


@pytest.mark.parametrize(
    ("name", "target"), [(name, target) for name, _, target in _ALIASES]
)
def test_real_alias_helper_is_recognized(
    aliases_module: griffe.Module, name: str, target: str
) -> None:
    """Ensure every `DeprecatedAlias` from the real `frequenz-core` is recognized."""
    alias = aliases_module[name]

    assert alias.deprecated
    assert "deprecated" in alias.labels
    assert alias.value == griffe.ExprName(target)


@pytest.mark.parametrize(("name", "since", "target"), _ALIASES)
def test_alias_documents_since_and_the_runtime_target(
    aliases_module: griffe.Module, name: str, since: str | None, target: str
) -> None:
    """Ensure an alias notice gives the version and the runtime replacement.

    The notice and runtime warning must point to the same replacement, even
    with a custom message. Only the notice says since which version the alias
    is deprecated. `Gadget` has no `new_module`, so both must use the module
    where the alias is defined.
    """
    runtime = str(_alias_warning(name).message)
    documented = _plain(str(aliases_module[name].deprecated))

    assert target in runtime
    if since is None:
        assert documented == f"Deprecated. Use {target} instead."
    else:
        assert documented == f"Deprecated since {since}. Use {target} instead."
        assert since not in runtime


@pytest.mark.parametrize("name", ["Rational", "Number", "Complex"])
def test_alias_message_is_only_the_runtime_warning(
    aliases_module: griffe.Module, name: str
) -> None:
    """Ensure a custom message changes the runtime warning, not the notice.

    The message is written for a terminal, so the notice is generated anyway,
    with or without `since`.
    """
    warning = _alias_warning(name)

    assert str(warning.message).startswith(f"{fixture_aliases.__name__}.{name} ")
    assert issubclass(warning.category, DeprecationWarning)
    assert str(aliases_module[name].deprecated).startswith("Deprecated")


@pytest.mark.parametrize(
    ("name", "target"),
    [
        ("Decimal", "decimal.Decimal"),
        ("Gadget", f"{fixture_aliases.__name__}.Widget"),
        ("Integral", "numbers.Integral"),
    ],
)
def test_generated_alias_warning_follows_the_guide(name: str, target: str) -> None:
    """Ensure a generated alias warning follows the deprecations guide.

    It gives the fully qualified names of the alias and its replacement. Only
    the notice says since which version the alias is deprecated.
    """
    assert str(_alias_warning(name).message) == (
        f"{fixture_aliases.__name__}.{name} is deprecated. Use {target} instead."
    )


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


def _accepted(code: str, **names: Any) -> bool:
    """Return whether the real `frequenz-core` accepts some code.

    Args:
        code: The code, as written in the documented module.
        **names: The names the code refers to.

    Returns:
        Whether the code runs without raising `TypeError` or `ValueError`.
            Python raises `TypeError` when arguments don't match the signature.
            `frequenz-core` also raises it when a required combination of
            arguments is missing, and raises `ValueError` for invalid values.
            The extension doesn't check values, so a case that raises
            `ValueError` fails the test instead of stopping it with an error.
    """
    try:
        exec(code, names)  # pylint: disable=exec-used
    except (TypeError, ValueError):
        return False
    return True


@pytest.mark.parametrize(
    "entry",
    [
        "DeprecatedAlias('Thing', new_module='decimal', since='v1')",
        "DeprecatedAlias('Thing', new_module='decimal', message='{old} gone.')",
        "DeprecatedAlias('Thing', new_module='decimal', since='v1', "
        "message='{old} gone.')",
        "DeprecatedAlias('Thing', new_module='decimal')",
        "DeprecatedAlias('Thing', new_name='Other')",
        "DeprecatedAlias('Thing', new_module='decimal', since=None, message=None)",
        "DeprecatedAlias('Thing')",
        "DeprecatedAlias('Thing', since='v1', message='{old} gone.')",
        "DeprecatedAlias('Thing', new_module=None, new_name=None, since='v1')",
        "DeprecatedAlias(name='Thing', new_module='decimal')",
        "DeprecatedAlias('Thing', 'decimal')",
        "DeprecatedAlias('Thing', new_module='decimal', until='v2')",
    ],
)
def test_alias_entries_bind_as_at_runtime(entry: str) -> None:
    """Ensure an alias entry is documented if and only if core accepts it.

    This checks the combinations of arguments, not their values, which the
    extension doesn't validate.
    """
    accepted = _accepted(entry, DeprecatedAlias=frequenz.core.warnings.DeprecatedAlias)
    code = (
        "from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases\n"
        f"__getattr__ = deprecated_aliases(__name__, {entry})\n"
    )
    with griffe.temporary_visited_module(
        code, extensions=griffe.load_extensions(DeprecationsExtension())
    ) as module:
        assert ("Thing" in module.members) == accepted


@pytest.mark.parametrize(
    "wrapper",
    [
        "deprecated_member(1, 'Gone')",
        "deprecated_member(value=1, message='Gone')",
        "deprecated_member(1, new_name='OPEN')",
        "deprecated_member(1, new_name='OPEN', since='v1')",
        "deprecated_member(1, 'Gone', since='v1')",
        "deprecated_member(1, 'Gone', new_name='OPEN', since='v1')",
        "deprecated_member(1, None, new_name='OPEN')",
        "deprecated_member(1, message=None, new_name='OPEN', since=None)",
        "DeprecatedMember(1, new_name='OPEN', since='v1')",
        "DeprecatedMember(1, 'Gone', since='v1')",
        "deprecated_member(1)",
        "deprecated_member(1, None)",
        "deprecated_member(1, since='v1')",
        "deprecated_member(1, message=None, new_name=None, since='v1')",
        "deprecated_member(1, 'Gone', 'OPEN')",
        "deprecated_member(new_name='OPEN')",
        "deprecated_member(1, 'Gone', until='v2')",
        "DeprecatedMember(1, since='v1')",
    ],
)
def test_member_wrappers_bind_as_at_runtime(wrapper: str) -> None:
    """Ensure an enum member is documented if and only if core accepts its wrapper.

    Create the enum too, because that's when `frequenz-core` checks `new_name`.
    This checks the combinations of arguments, not their values, which the
    extension doesn't validate.
    """
    code = (
        "from frequenz.core.enum import DeprecatedMember, Enum, deprecated_member\n"
        "class Status(Enum):\n"
        "    OPEN = 1\n"
        f"    A = {wrapper}\n"
    )
    accepted = _accepted(code)
    with griffe.temporary_visited_module(
        code, extensions=griffe.load_extensions(DeprecationsExtension())
    ) as module:
        assert bool(module["Status.A"].deprecated) == accepted

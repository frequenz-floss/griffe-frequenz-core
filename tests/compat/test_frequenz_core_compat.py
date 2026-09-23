# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Compatibility tests against the installed `frequenz-core`.

Every other test in this suite is static: Griffe resolves the helper names out
of a fixture's import statement, so those tests never import `frequenz-core`
and pass with it uninstalled. These are the opposite, and the only ones that
import it. They pin the part of the contract this package depends on but does
not own, by running the real helper and comparing what it does at runtime with
what we put in the documentation.

`test_documented_message_matches_runtime_warning` is the one that earns its
keep. Nothing else would notice if `frequenz-core` started wrapping or
reformatting the message, because the extension reads it out of the syntax
tree and never executes it. That is precisely the drift that would leave the
documentation quietly saying something no user ever sees.

Only `deprecated_member` is covered. `frequenz-core 1.4.0` has no
`frequenz.core.warnings` module, so there is no released `deprecated_aliases`
to run.
"""

import inspect
import warnings
from pathlib import Path
from typing import Any

import frequenz.core.enum
import griffe
import pytest

from griffe_frequenz_core.deprecations import DeprecationsExtension

from . import fixture_enum

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
    """Reach the deprecated member and capture the warning it emits.

    Returns:
        The single warning the real `frequenz-core` raised.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = fixture_enum.TaskStatus.PENDING

    assert len(caught) == 1, f"expected exactly one warning, got {len(caught)}"
    return caught[0]


def test_real_helper_is_recognized(task_status: griffe.Class) -> None:
    """The extension finds a `deprecated_member()` call written against real core."""
    pending = task_status["PENDING"]

    assert pending.deprecated
    assert "deprecated" in pending.labels
    # The wrapper call is replaced by the value the member really takes.
    assert str(pending.value) == "1"


def test_documented_message_matches_runtime_warning(
    task_status: griffe.Class,
    pending_warning: warnings.WarningMessage,
) -> None:
    """The documented text is exactly the text the runtime warning carries.

    Deliberately compares the two sources against each other rather than
    against a third copy in this file, so the test cannot pass by agreeing with
    a stale expectation.
    """
    assert str(pending_warning.message) == task_status["PENDING"].deprecated
    assert issubclass(pending_warning.category, DeprecationWarning)


def test_admonition_is_rendered(task_status: griffe.Class) -> None:
    """The message reaches the docstring as an admonition, not only as a field."""
    pending = task_status["PENDING"]
    assert pending.docstring is not None
    sections = pending.docstring.parsed

    assert sections[0].kind is griffe.DocstringSectionKind.admonition
    assert sections[0].title == "Deprecated"
    assert sections[0].value.contents == pending.deprecated
    # The member's own prose survives, after the admonition.
    assert [section.kind for section in sections[1:]] == [
        griffe.DocstringSectionKind.text
    ]


@pytest.mark.parametrize(
    "wrapper",
    [frequenz.core.enum.deprecated_member, frequenz.core.enum.DeprecatedMember],
)
def test_wrapper_parameters_are_value_and_message(wrapper: Any) -> None:
    """The keyword names the extension binds are the ones core really takes.

    The extension reads `deprecated_member(value=..., message=...)` by those two
    names, so a rename in core would leave keyword calls unmarked.
    """
    bound = inspect.signature(wrapper).bind(value=1, message="Gone")
    assert bound.arguments == {"value": 1, "message": "Gone"}


def test_plain_member_is_left_alone(task_status: griffe.Class) -> None:
    """A member with no `deprecated_member()` call is untouched, and stays silent."""
    open_member = task_status["OPEN"]

    assert open_member.deprecated is None
    assert "deprecated" not in open_member.labels

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = fixture_enum.TaskStatus.OPEN

    assert not caught

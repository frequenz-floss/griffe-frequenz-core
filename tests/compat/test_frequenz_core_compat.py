# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Compatibility tests with the installed `frequenz-core`.

All other tests in this suite are static: Griffe resolves the helper names from
the import statements in the fixtures. So those tests never import
`frequenz-core`, and they pass even if it isn't installed.

These tests are the only ones that import it. They check the parts of
`frequenz-core` this package depends on, by running the real helpers and
comparing what they do at runtime with what we put in the documentation.

`test_documented_message_matches_runtime_warning` is the most important one.
The extension reads the message from the source code and never runs it, so
nothing else would notice if `frequenz-core` started changing the message. The
documentation would then silently show a message that users never see.

Only `deprecated_member` is tested. `frequenz-core 1.4.0` has no
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

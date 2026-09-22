# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the griffe_frequenz_core package."""

import pytest

from griffe_frequenz_core import delete_me


def test_griffe_frequenz_core_succeeds() -> None:  # TODO(cookiecutter): Remove
    """Test that the delete_me function succeeds."""
    assert delete_me() is True


def test_griffe_frequenz_core_fails() -> None:  # TODO(cookiecutter): Remove
    """Test that the delete_me function fails."""
    with pytest.raises(RuntimeError, match="This function should be removed!"):
        delete_me(blow_up=True)

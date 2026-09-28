# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""A module with a `__getattr__` of its own, which must be left alone."""

from typing import Any


def __getattr__(name: str) -> Any:
    """Return something else entirely.

    Args:
        name: The name asked for.

    Returns:
        Nothing, ever.

    Raises:
        AttributeError: Always.
    """
    raise AttributeError(name)


VALUE = 1
"""A plain value."""

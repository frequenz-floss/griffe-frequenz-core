# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""A module with its own `__getattr__`, which the extension must not change."""

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

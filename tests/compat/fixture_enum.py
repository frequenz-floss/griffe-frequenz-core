# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Fixture exercising the real `frequenz.core.enum` deprecation helper.

This module is both loaded statically by Griffe and imported at runtime, so one
declaration backs the documentation assertion and the warning assertion.

The message is written as a literal on purpose. Griffe reads it out of the
syntax tree without executing anything, so a message built from a constant or
an f-string cannot be recovered and the member would go unmarked.
"""

from frequenz.core.enum import Enum, deprecated_member


class TaskStatus(Enum):
    """The status of a task."""

    OPEN = 1
    """The task is open."""

    IN_PROGRESS = 2
    """Someone is working on the task."""

    PENDING = deprecated_member(1, "PENDING is deprecated, use OPEN instead")
    """The task is pending."""

# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Fixture using the real `frequenz.core.enum` deprecation helper.

This module is loaded statically by Griffe and also imported at runtime, so the
same code is used to check both the documentation and the runtime warning.

The message is a string literal on purpose. Griffe reads it from the source code
without running anything, so it can't read a message built from a constant or
an f-string, and the member wouldn't be marked.
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

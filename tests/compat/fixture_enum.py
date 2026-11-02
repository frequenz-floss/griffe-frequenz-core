# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Fixture using the real `frequenz.core.enum` deprecation helper.

This module is loaded statically by Griffe and also imported at runtime, so the
same code is used to check both the documentation and the runtime warning.

The arguments are string literals on purpose. Griffe reads them from the source
code without running anything, so it can't read a value from a constant or an
f-string. The members test these cases:

- `PENDING`: has `new_name` and `since`.
- `STARTED`: uses the wrapper class and has only `new_name`.
- `WAITING`: has `new_name`, `since` and a custom runtime message.
- `CANCELLED`: has no replacement, so it has a message and `since`.
"""

from frequenz.core.enum import DeprecatedMember, Enum, deprecated_member


class TaskStatus(Enum):
    """The status of a task."""

    OPEN = 1
    """The task is open."""

    IN_PROGRESS = 2
    """Someone is working on the task."""

    PENDING = deprecated_member(1, new_name="OPEN", since="v1.2.0")
    """The task is pending."""

    STARTED = DeprecatedMember(2, new_name="IN_PROGRESS")
    """The task is started."""

    WAITING = deprecated_member(
        1,
        "TaskStatus.WAITING is deprecated. Use TaskStatus.OPEN instead, "
        "it was renamed.",
        new_name="OPEN",
        since="v1.3.0",
    )
    """The task is waiting."""

    CANCELLED = deprecated_member(
        4,
        "TaskStatus.CANCELLED is deprecated. Cancelled tasks are deleted now.",
        since="v1.4.0",
    )
    """The task was cancelled."""

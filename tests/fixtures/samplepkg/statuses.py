# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""An enum with deprecated members, and members that only look deprecated."""

from frequenz.core.enum import Enum, deprecated_member

_MESSAGE = "CANCELLED is deprecated, use CLOSED instead"


class TaskStatus(Enum):
    """The status of a task."""

    OPEN = 1
    """The task is open."""

    IN_PROGRESS = 2
    """Someone is working on the task."""

    PENDING = deprecated_member(1, "PENDING is deprecated, use OPEN instead")
    """The task is pending."""

    STARTED = deprecated_member(2, "STARTED is deprecated, use IN_PROGRESS instead")

    COMPUTED = int("3")
    """A value that comes from a call the extension must ignore."""

    CANCELLED = deprecated_member(1, _MESSAGE)
    """A member whose message Griffe cannot read, so it stays unmarked."""

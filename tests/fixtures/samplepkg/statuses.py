# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""An enum with deprecated members, and members that only look deprecated."""

from frequenz.core.enum import DeprecatedMember, Enum, deprecated_member

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
    """A value from a call that the extension must ignore."""

    CANCELLED = deprecated_member(1, _MESSAGE)
    """A member with a message Griffe can't read, so it gets a generic one."""

    WAITING = DeprecatedMember(1, "WAITING is deprecated, use OPEN instead")
    """A member using the wrapper class instead of the function."""

    PAUSED = deprecated_member(2, new_name="IN_PROGRESS", since="v1.5.0")
    """A member with enough information to generate its notice."""

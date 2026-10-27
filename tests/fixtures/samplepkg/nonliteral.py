# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Deprecations written in a way Griffe can't read.

Nothing here is run, so the extension can't read a message or an alias name
that isn't a string literal in the call. `Thing` is still marked, but with the
default message instead of the one in this module. The entry with a constant as
its name is skipped.
"""

from typing import TYPE_CHECKING, TypeAlias

from frequenz.core.warnings import deprecated_aliases

_MESSAGE = "{old} went away, see {new}."
_LOST = "Lost"

if TYPE_CHECKING:
    from samplepkg.newmod import Widget as _Widget

    Thing: TypeAlias = _Widget
    """A thing."""
else:
    __getattr__ = deprecated_aliases(
        __name__,
        {
            "Thing": "samplepkg.newmod:Widget",
            _LOST: "samplepkg.newmod:Gadget",
        },
        message=_MESSAGE,
    )

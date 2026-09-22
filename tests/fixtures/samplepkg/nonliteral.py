# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Deprecations written in a way Griffe cannot read.

Nothing here is executed, so a message or an alias name that is not a string
literal right there in the call cannot be recovered. `Thing` still gets marked,
with the default message rather than the one this module meant to use, while the
entry keyed by a constant is dropped entirely.
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

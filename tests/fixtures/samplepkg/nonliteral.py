# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Deprecations written in a way Griffe can't read.

Nothing here is run, so the extension can't read a message or an alias name
that isn't a string literal in the call. `Thing` has its message in a constant,
but that doesn't matter, because messages are never documented. The entry with
a constant as its name is skipped, because Griffe can't see the name. `Kept` is
written explicitly, so it's still marked.
"""

from typing import TYPE_CHECKING, TypeAlias

from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases

_MESSAGE = "{old} went away, see {new}."
_LOST = "Lost"

if TYPE_CHECKING:
    from samplepkg.newmod import Gadget as _Gadget
    from samplepkg.newmod import Widget as _Widget

    Thing: TypeAlias = _Widget
    """A thing."""

    Kept: TypeAlias = _Gadget
    """A gadget kept under an old name."""
else:
    __getattr__ = deprecated_aliases(
        __name__,
        DeprecatedAlias(
            "Thing",
            new_module="samplepkg.newmod",
            new_name="Widget",
            message=_MESSAGE,
        ),
        DeprecatedAlias(
            _LOST, new_module="samplepkg.newmod", new_name="Gadget", since="v1.0.0"
        ),
        DeprecatedAlias(
            "Kept", new_module="samplepkg.newmod", new_name="Gadget", since="v1.0.0"
        ),
    )

# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""An alias table Griffe cannot read, because it is held in a constant.

Nothing here is executed, so the extension never learns what `_ALIASES` holds.
`Thing` stays unmarked, and the skip has to be logged rather than silent.
"""

from typing import TYPE_CHECKING, TypeAlias

from frequenz.core.warnings import deprecated_aliases

_ALIASES = {"Thing": "samplepkg.newmod:Widget"}

if TYPE_CHECKING:
    from samplepkg.newmod import Widget as _Widget

    Thing: TypeAlias = _Widget
    """A thing."""
else:
    __getattr__ = deprecated_aliases(__name__, _ALIASES)

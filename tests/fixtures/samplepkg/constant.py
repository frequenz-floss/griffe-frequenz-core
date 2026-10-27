# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""An alias table Griffe can't read, because it's stored in a constant.

Nothing here is run, so the extension never knows what `_ALIASES` contains.
`Thing` isn't marked, and the extension must log it instead of skipping it
silently.
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

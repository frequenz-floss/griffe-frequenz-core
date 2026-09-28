# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Another old home, using the keyword form and a message of its own."""

from typing import TYPE_CHECKING, TypeAlias

from frequenz.core.warnings import deprecated_aliases

if TYPE_CHECKING:
    from samplepkg.newmod import Widget as _Widget

    Thing: TypeAlias = _Widget
    """A thing."""
else:
    __getattr__ = deprecated_aliases(
        __name__,
        aliases={"Thing": "samplepkg.newmod:Widget"},
        message="{old} moved to {new} in v2.0.0 and will be removed in v3.0.0.",
    )

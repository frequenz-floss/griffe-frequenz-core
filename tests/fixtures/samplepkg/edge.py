# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Edge cases: a target nothing knows about, and a name no type checker sees.

`Outside` points at a package that is in neither the documentation nor any
inventory, so the link the extension writes has to degrade to plain text.
`Hidden` is in the table but has no declaration under `TYPE_CHECKING`, so there
is no attribute to mark until the extension makes one.
"""

from typing import TYPE_CHECKING, TypeAlias

from frequenz.core.warnings import deprecated_aliases

if TYPE_CHECKING:
    from some.external.pkg import Thing as _Thing

    Outside: TypeAlias = _Thing
    """Something that lives in a package with no inventory here."""
else:
    __getattr__ = deprecated_aliases(
        __name__,
        {
            "Outside": "some.external.pkg:Thing",
            "Hidden": "samplepkg.newmod:Widget",
        },
    )

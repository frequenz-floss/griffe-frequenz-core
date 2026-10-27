# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Edge cases: an unknown target, and a name type checkers can't see.

`Outside` points to a package that isn't in the documentation or in any
inventory, so `mkdocs-autorefs` must report its link.

`Hidden` is in the table, but it isn't declared under `TYPE_CHECKING`. So there
is no attribute to mark until the extension creates one.
"""

from typing import TYPE_CHECKING, TypeAlias

from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases

if TYPE_CHECKING:
    from some.external.pkg import Thing as _Thing

    Outside: TypeAlias = _Thing
    """Something that lives in a package with no inventory here."""
else:
    __getattr__ = deprecated_aliases(
        __name__,
        DeprecatedAlias(
            "Outside", new_module="some.external.pkg", new_name="Thing", since="v1.0.0"
        ),
        DeprecatedAlias(
            "Hidden", new_module="samplepkg.newmod", new_name="Widget", since="v1.0.0"
        ),
    )

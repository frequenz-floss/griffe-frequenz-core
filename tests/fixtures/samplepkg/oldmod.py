# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""The old home, keeping the old import paths working.

Three shapes on purpose:

- `Widget`: the documented convention, with a hand-written `Deprecated:`
  admonition that the extension must leave alone.
- `Doohickey`: a renamed alias with a docstring but no admonition.
- `MAX_WIDGETS`: an alias with no docstring at all.
"""

from typing import TYPE_CHECKING, TypeAlias

from frequenz.core.warnings import deprecated_aliases

if TYPE_CHECKING:
    from samplepkg.newmod import Gadget as _Gadget
    from samplepkg.newmod import Widget as _Widget

    Widget: TypeAlias = _Widget
    """A widget that does widget things.

    Deprecated:
        `samplepkg.oldmod.Widget` is deprecated since v1.2.0. Use
        [`samplepkg.newmod.Widget`][] instead.
    """

    Doohickey: TypeAlias = _Gadget
    """A gadget, formerly known as `Doohickey`."""

    MAX_WIDGETS: int
else:
    __getattr__ = deprecated_aliases(
        __name__,
        {
            "Widget": "samplepkg.newmod",
            "Doohickey": "samplepkg.newmod:Gadget",
            "MAX_WIDGETS": "samplepkg.newmod",
        },
    )

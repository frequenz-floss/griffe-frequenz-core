# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""An alias with a hand-written deprecation notice in numpy style.

In Google style, a `Deprecated:` section becomes an admonition. In numpy style,
it becomes a section of its own kind. Both mean the same, and the extension
must not change either of them.
"""

from typing import TYPE_CHECKING, TypeAlias

from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases

if TYPE_CHECKING:
    from samplepkg.newmod import Widget as _Widget

    Widget: TypeAlias = _Widget
    """A widget that does widget things.

    Deprecated
    ----------
    1.2.0
        Use ``samplepkg.newmod.Widget`` instead.
    """
else:
    __getattr__ = deprecated_aliases(
        __name__,
        DeprecatedAlias("Widget", new_module="samplepkg.newmod", since="v1.2.0"),
    )

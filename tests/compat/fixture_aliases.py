# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Fixture exercising the real `frequenz.core.warnings` alias helper.

This module is both loaded statically by Griffe and imported at runtime, so one
declaration backs the documentation assertion and the warning assertion.

The targets are standard library modules because `deprecated_aliases()`
resolves the target before warning, so it has to be importable. `Decimal` is
also declared for type checkers, the usual convention, and gives `since`, while
`Rational` is not declared, renames as well as moves, and gives a message of its
own. `Gadget` was renamed to `Widget` in this very module, so it gives no
`new_module`.
"""

from typing import TYPE_CHECKING, TypeAlias

from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases


class Widget:
    """A widget, called a gadget before v1.4.0."""


if TYPE_CHECKING:
    from decimal import Decimal as _Decimal

    Decimal: TypeAlias = _Decimal
    """A decimal number."""
else:
    __getattr__ = deprecated_aliases(
        __name__,
        DeprecatedAlias("Decimal", new_module="decimal", since="v1.2.0"),
        DeprecatedAlias(
            "Rational",
            new_module="fractions",
            new_name="Fraction",
            message="{old} is deprecated since v1.3.0. "
            "Use {new} instead, it was renamed.",
        ),
        DeprecatedAlias("Gadget", new_name="Widget", since="v1.4.0"),
    )

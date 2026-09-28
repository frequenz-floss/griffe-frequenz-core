# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Fixture using the real `frequenz.core.warnings` alias helper.

This module is loaded statically by Griffe and also imported at runtime, so the
same code is used to check both the documentation and the runtime warning.

The targets are in the standard library, because `deprecated_aliases()`
resolves the target before warning, so it must be importable. The aliases are:

- `Decimal`: declared for type checkers, as usual, with `since`.
- `Rational`: not declared, moved and renamed, with its own message.
- `Gadget`: renamed to `Widget` in this same module, so without `new_module`.
- `Number`: moved, with its own message too.
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
            message="{old} is deprecated. Use {new} instead, it was renamed.",
        ),
        DeprecatedAlias("Gadget", new_name="Widget", since="v1.4.0"),
        DeprecatedAlias(
            "Number",
            new_module="numbers",
            message="{old} is deprecated. Use the abstract base class {new} instead.",
        ),
    )

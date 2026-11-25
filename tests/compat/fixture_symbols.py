# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Fixture using the real `frequenz.core.warnings` helper for symbols.

This module is loaded statically by Griffe and also imported at runtime, so the
same code is used to check both the documentation and the runtime warning.

It has an alias and symbols in the same table. The entries are:

- `Decimal`: an alias, to check that both kinds of entry work together.
- `TIMEOUT_SECONDS`: a constant replaced by a `timedelta`, with `since`. Its
  value is kept in a private attribute, as usual.
- `RETRIES`: has a replacement and its own message, but no `since`.
- `ValueT`: has no replacement, so it has a message, and `since`.
- `KeyT`: has no replacement either, and a hand-written notice.
- `LIMIT`: has nothing but its value.
"""

from typing import TYPE_CHECKING, Final, TypeAlias, TypeVar

from frequenz.core.warnings import DeprecatedAlias, DeprecatedSymbol, deprecated_symbols

_TIMEOUT_SECONDS: Final = 30.0

if TYPE_CHECKING:
    from decimal import Decimal as _Decimal

    Decimal: TypeAlias = _Decimal
    """A decimal number."""

    TIMEOUT_SECONDS: Final = _TIMEOUT_SECONDS
    """How long to wait for a reply, in seconds."""

    KeyT = TypeVar("KeyT")
    """A type variable for keys.

    Deprecated:
        Deprecated since v1.7.0. Define your own type variable instead.
    """
else:
    __getattr__ = deprecated_symbols(
        __name__,
        DeprecatedAlias("Decimal", new_module="decimal", since="v1.2.0"),
        DeprecatedSymbol(
            "TIMEOUT_SECONDS",
            value=_TIMEOUT_SECONDS,
            replacement="datetime.timedelta",
            since="v1.5.0",
        ),
        DeprecatedSymbol(
            "RETRIES",
            value=3,
            replacement="decimal.MAX_PREC",
            message="{old} is deprecated and will be removed. Use {new} instead.",
        ),
        DeprecatedSymbol(
            "ValueT",
            value=TypeVar("ValueT"),
            since="v1.6.0",
            message="{old} is deprecated. Define your own type variable instead.",
        ),
        DeprecatedSymbol(
            "KeyT",
            value=TypeVar("KeyT"),
            since="v1.7.0",
            message="{old} is deprecated. Define your own type variable instead.",
        ),
        DeprecatedSymbol("LIMIT", value=None),
    )

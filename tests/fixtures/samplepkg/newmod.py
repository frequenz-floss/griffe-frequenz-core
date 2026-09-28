# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""The new home of the symbols the other modules alias."""

from typing import Self


class Widget:
    """A widget that does widget things."""

    def spin(self) -> Self:
        """Spin the widget.

        Returns:
            The widget itself.
        """
        return self


class Gadget:
    """A gadget, formerly known as `Doohickey`."""


MAX_WIDGETS = 10
"""The largest number of widgets allowed."""

# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""A collection of Griffe extensions to teach mkdocstrings about frequenz-core helpers.

Some `frequenz-core` helpers express information that [Griffe] cannot recover
from static analysis alone, so the API documentation generated for code using
them comes out incomplete. Each extension in this package fills one of those
gaps, and new ones are added as more helpers need the same treatment.

The extensions match fully qualified names as strings and never import
`frequenz-core`, so this package doesn't depend on it and can document any
project that uses those helpers.

[Griffe]: https://mkdocstrings.github.io/griffe/
"""


# TODO(cookiecutter): Remove this function
def delete_me(*, blow_up: bool = False) -> bool:
    """Do stuff for demonstration purposes.

    Args:
        blow_up: If True, raise an exception.

    Returns:
        True if no exception was raised.

    Raises:
        RuntimeError: if blow_up is True.
    """
    if blow_up:
        raise RuntimeError("This function should be removed!")
    return True

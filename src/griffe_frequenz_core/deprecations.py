# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Document deprecations that are expressed as a function call.

The usual way to deprecate a Python API is a decorator, and Griffe already reads
those: [`griffe-warnings-deprecated`](https://mkdocstrings.github.io/griffe-warnings-deprecated/)
turns `@warnings.deprecated` and `@typing_extensions.deprecated` into an admonition
and a label.

Some [`frequenz-core`](https://github.com/frequenz-floss/frequenz-core-python)
helpers cannot use a decorator, so they deprecate through a call instead, and
nothing sees them. This module fills that gap for the two shapes `frequenz-core`
uses. See [`DeprecationsExtension`][griffe_frequenz_core.deprecations.DeprecationsExtension]
for what they look like and how to enable the extension.
"""

from __future__ import annotations

import ast
from collections.abc import Sequence
from typing import Any

from griffe import (
    Attribute,
    Class,
    Docstring,
    DocstringSectionAdmonition,
    DocstringSectionKind,
    ExprCall,
    ExprDict,
    ExprKeyword,
    ExprName,
    ExprVarKeyword,
    ExprVarPositional,
    Extension,
    Module,
    get_logger,
)

_logger = get_logger(__name__)


def _literal(node: Any) -> Any:
    """Evaluate a Griffe expression as a Python literal.

    Args:
        node: The expression to evaluate.

    Returns:
        The literal value, or `None` if the expression is not a literal.
    """
    try:
        return ast.literal_eval(str(node))
    except (ValueError, SyntaxError, TypeError):
        return None


def _alias_table_arguments(call: ExprCall) -> tuple[Any, Any]:
    """Find the alias table and the message among the arguments of a call.

    The call is read with the signature of `deprecated_aliases(module, aliases, *,
    message=...)`, so the table is the second positional argument or `aliases=`,
    and the message can only be `message=`. Anything else is ignored.

    Args:
        call: The alias table call to read.

    Returns:
        The expressions passed as the table and as the message, each `None` if it
        cannot be found. The table cannot be found when it is not passed at all,
        or when a `*args` before it or a `**kwargs` hide where it is.
    """
    table: Any = None
    message: Any = None
    position: int | None = 0
    for argument in call.arguments:
        if isinstance(argument, ExprKeyword):
            if argument.name == "aliases":
                table = argument.value
            elif argument.name == "message":
                message = argument.value
        elif isinstance(argument, ExprVarPositional):
            # Whatever follows no longer has a position that can be counted.
            position = None
        elif isinstance(argument, ExprVarKeyword):
            continue
        elif position is not None:
            if position == 1:
                table = argument
            position += 1
    return table, message


class DeprecationsExtension(Extension):
    """Mark the deprecations `frequenz-core` expresses through a call.

    Two shapes are recognized, and both end up with the same treatment as a
    decorator-based deprecation: a `deprecated` label, the message on the object's
    `deprecated` field, and an admonition inserted at the top of its docstring.

    The first is a table of module-level aliases kept alive by a module
    `__getattr__`:

    ```python
    from typing import TYPE_CHECKING, TypeAlias

    from frequenz.core.warnings import deprecated_aliases

    if TYPE_CHECKING:
        from mypkg.newmod import Widget as _Widget

        Widget: TypeAlias = _Widget  # plus its usual attribute docstring
    else:
        __getattr__ = deprecated_aliases(__name__, {"Widget": "mypkg.newmod"})
    ```

    Every name in that table is marked, whether or not it is declared for type
    checkers. A target written as `"module:name"` renames as well as moves.

    The second is an enum member whose value is wrapped:

    ```python
    from frequenz.core.enum import Enum, deprecated_member

    class TaskStatus(Enum):
        OPEN = 1
        PENDING = deprecated_member(1, "PENDING is deprecated, use OPEN instead")
    ```

    Such a member is marked and its rendered value is rewritten from the wrapper
    call back to the real value, so the documentation shows `PENDING = 1`. The
    `DeprecatedMember(1, "...")` form `frequenz-core` also accepts is recognized
    too: a class and a function are both read as a call.

    Warning:
        Enum messages, alias names, and alias targets must be string literals
        written directly in the call. A non-literal enum message or alias entry
        leaves that member unmarked; a non-literal alias-table `message` instead
        falls back to `default_message`. The alias table itself must be a dict
        literal passed as the second positional argument or as `aliases=`; one
        held in a constant leaves every alias in it unmarked. Each of these
        cases is logged at debug level, which `mkdocs -v` shows.

    Enable it under the mkdocstrings Python handler, alongside the decorator one:

    ```yaml
    plugins:
      - mkdocstrings:
          handlers:
            python:
              options:
                extensions:
                  - griffe_warnings_deprecated
                  - griffe_frequenz_core.deprecations
    ```

    The defaults match `griffe-warnings-deprecated`, so the two render alike with
    no configuration. Anything that needs changing is an option:

    ```yaml
                extensions:
                  - griffe_frequenz_core.deprecations:
                      kind: deprecated
                      alias_table_functions:
                        - frequenz.core.warnings.deprecated_aliases
                        - mypkg.compat.moved_to
    ```

    Note:
        The paths this extension matches are options rather than constants on
        purpose: if `frequenz-core` renames a helper, point the option at the new
        path instead of waiting for a release of this package.

    Note:
        There is one deliberate difference from `griffe-warnings-deprecated`:
        given an empty `title`, it promotes the message into the admonition's
        title, and this extension does not. The message here carries a rendered
        cross-reference to the target, which does not belong in a title, and the
        title is also what decides whether a docstring already documents its own
        deprecation. Please do not "fix" this into a bug.
    """

    # Every option is a key in `mkdocs.yml`, so they have to stay flat.
    def __init__(  # pylint: disable=too-many-arguments
        self,
        kind: str = "danger",
        title: str | None = "Deprecated",
        label: str | None = "deprecated",
        *,
        alias_table_functions: Sequence[str] = (
            "frequenz.core.warnings.deprecated_aliases",
        ),
        member_wrapper_functions: Sequence[str] = (
            "frequenz.core.enum.deprecated_member",
            "frequenz.core.enum.DeprecatedMember",
        ),
        default_message: str = "{old} is deprecated. Use {new} instead.",
        show_target: bool = True,
    ) -> None:
        """Initialize the extension.

        Args:
            kind: The kind of the admonition inserted in the docstring.
            title: The title of that admonition. An empty title renders the
                admonition without one.
            label: The label added to deprecated objects, or `None` to add none.
            alias_table_functions: The fully qualified paths of the functions that
                build a module `__getattr__` out of an alias table. Their calls
                are read as if they had the signature of `deprecated_aliases()`:
                the table is the second positional argument or `aliases=`, and
                the message is `message=`.
            member_wrapper_functions: The fully qualified paths of the callables
                that wrap an enum member's value to deprecate it. A class works
                as well as a function, since both are read as a call.
            default_message: The message template used when the alias table call
                does not pass a `message` of its own. It must stay in step with
                the default of the function it stands in for, since that is what
                the runtime warning says. `{old}` and `{new}` are substituted.
            show_target: Whether to render an alias' value as the target it points
                at, rather than the private name imported for type checkers.
        """
        super().__init__()
        self.kind = kind
        """The kind of the admonition inserted in the docstring."""
        self.title = title or ""
        """The title of the admonition inserted in the docstring."""
        self.label = label
        """The label added to deprecated objects."""
        self.alias_table_functions = frozenset(alias_table_functions)
        """The paths of the functions that build a `__getattr__` from an alias table."""
        self.member_wrapper_functions = frozenset(member_wrapper_functions)
        """The paths of the callables that wrap a deprecated enum member's value."""
        self.default_message = default_message
        """The message template used when the alias table call passes none."""
        self.show_target = show_target
        """Whether to render an alias' value as the target it points at."""

    def on_module_members(self, *, mod: Module, **kwargs: Any) -> None:
        """Mark every name in the module's alias table, if it has one.

        Args:
            mod: The module whose members were just collected.
            **kwargs: Everything else Griffe passes, all unused.
        """
        call = self._alias_table_call(mod)
        if call is None:
            return
        table, message = self._table_and_message(mod, call)
        for name, target in table.items():
            target_module, _, target_name = target.partition(":")
            path = f"{target_module}.{target_name or name}"
            # An `optional` autoref degrades to plain text when the target is in
            # neither the documentation nor an inventory, instead of failing a
            # strict build.
            link = (
                f'<autoref identifier="{path}" optional><code>{path}</code></autoref>'
            )
            text = message.format(old=f"`{mod.path}.{name}`", new=link)

            member = mod.members.get(name)
            if not isinstance(member, Attribute):
                _logger.debug(
                    "%s.%s is aliased but not declared for type checkers",
                    mod.path,
                    name,
                )
                member = Attribute(name, parent=mod)
                mod.set_member(name, member)

            if self.show_target:
                member.value = ExprName(path)
            self._mark(member, text)

    def on_class_members(self, *, cls: Class, **kwargs: Any) -> None:
        """Mark every wrapped enum member of the class, if it has any.

        Args:
            cls: The class whose members were just collected.
            **kwargs: Everything else Griffe passes, all unused.
        """
        for member in cls.members.values():
            value = getattr(member, "value", None)
            if not isinstance(member, Attribute) or not isinstance(value, ExprCall):
                continue
            if value.canonical_path not in self.member_wrapper_functions:
                continue
            if len(value.arguments) < 2:
                continue
            text = _literal(value.arguments[1])
            if not isinstance(text, str):
                _logger.debug(
                    "%s: deprecation message is not a static string, "
                    "leaving the member unmarked",
                    member.path,
                )
                continue
            # Show the member's real value, not the wrapper call.
            member.value = value.arguments[0]
            self._mark(member, text)

    def _alias_table_call(self, mod: Module) -> ExprCall | None:
        """Return the module's alias table call, if it has one.

        Args:
            mod: The module to look at.

        Returns:
            The call assigned to the module's `__getattr__`, or `None` if the
            module has no `__getattr__` or it comes from somewhere else.
        """
        value = getattr(mod.members.get("__getattr__"), "value", None)
        if isinstance(value, ExprCall) and value.canonical_path in (
            self.alias_table_functions
        ):
            return value
        return None

    def _table_and_message(
        self, mod: Module, call: ExprCall
    ) -> tuple[dict[str, str], str]:
        """Extract the alias table and the message template from a call.

        Args:
            mod: The module the call was found in, used to report what is skipped.
            call: The alias table call to read.

        Returns:
            The table mapping each deprecated name to its target, and the message
            template to use for all of them.
        """
        table_node, message_node = _alias_table_arguments(call)

        message = self.default_message
        if message_node is not None:
            if isinstance(text := _literal(message_node), str):
                message = text
            else:
                _logger.debug(
                    "%s: `message` is not a static string, "
                    "falling back to the default template",
                    mod.path,
                )

        table: dict[str, str] = {}
        if table_node is None:
            _logger.debug(
                "%s: the alias table argument cannot be found, "
                "leaving every alias unmarked",
                mod.path,
            )
            return table, message
        if not isinstance(table_node, ExprDict):
            _logger.debug(
                "%s: the alias table `%s` is not a dict literal, "
                "leaving every alias in it unmarked",
                mod.path,
                table_node,
            )
            return table, message
        for key, value in zip(table_node.keys, table_node.values):
            name, target = _literal(key), _literal(value)
            if isinstance(name, str) and isinstance(target, str):
                table[name] = target
            else:
                _logger.debug(
                    "%s: alias table entry %s: %s is not a pair of static "
                    "strings, skipping it",
                    mod.path,
                    key,
                    value,
                )
        return table, message

    def _mark(self, member: Attribute, text: str) -> None:
        """Flag one member as deprecated and give it the admonition.

        Args:
            member: The member to mark.
            text: The deprecation message.
        """
        member.deprecated = text
        if self.label:
            member.labels.add(self.label)
        if self._already_marked(member):
            return
        if member.docstring is None:
            member.docstring = Docstring("", parent=member)
        member.docstring.parsed.insert(
            0,
            DocstringSectionAdmonition(kind=self.kind, text=text, title=self.title),
        )

    def _already_marked(self, member: Attribute) -> bool:
        """Tell whether the member's docstring already carries the admonition.

        A hand-written admonition is left alone, so a module can say more about
        one particular deprecation than the message template can.

        Args:
            member: The member to check.

        Returns:
            Whether the docstring already has a deprecation admonition.
        """
        if member.docstring is None:
            return False
        for section in member.docstring.parsed:
            if section.kind is DocstringSectionKind.deprecated:
                return True
            if (
                section.kind is DocstringSectionKind.admonition
                and str(getattr(section, "title", "")).strip().lower()
                == self.title.strip().lower()
            ):
                return True
        return False

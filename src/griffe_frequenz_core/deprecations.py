# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Document deprecations made with function calls.

Python APIs are usually deprecated with a decorator, and Griffe already supports
that. [`griffe-warnings-deprecated`](https://mkdocstrings.github.io/griffe-warnings-deprecated/)
adds an admonition and a label to anything decorated with `@warnings.deprecated`
or `@typing_extensions.deprecated`.

Some [`frequenz-core`](https://github.com/frequenz-floss/frequenz-core-python)
helpers can't use a decorator, so they use a function call instead. Griffe
doesn't detect these calls. This module adds support for the two cases
`frequenz-core` has: module aliases and enum members. See
[`DeprecationsExtension`][griffe_frequenz_core.deprecations.DeprecationsExtension]
for examples and how to enable the extension.
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
    """Get the alias table and the message from the arguments of a call.

    The call is read as `deprecated_aliases(module, aliases, *, message=...)`.
    So the table is the second positional argument or `aliases=`, and the message
    can only be `message=`. All other arguments are ignored.

    Args:
        call: The alias table call to read.

    Returns:
        The expressions passed as the table and as the message, or `None` for
        the ones that can't be found. The table can't be found if it isn't
        passed at all, or if a `*args` before it or a `**kwargs` hide where it
        is.
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
            # We can't know the position of the arguments after this one.
            position = None
        elif isinstance(argument, ExprVarKeyword):
            continue
        elif position is not None:
            if position == 1:
                table = argument
            position += 1
    return table, message


def _wrapper_arguments(call: ExprCall) -> tuple[Any, Any] | None:
    """Get the value and the message from the arguments of an enum wrapper call.

    The arguments are matched the same way Python matches them for
    `deprecated_member(value, message)`, so each can be passed positionally or by
    keyword.

    The caller must check for unpacked arguments first, because this function
    would treat a `*args` or `**kwargs` as a normal argument.

    Args:
        call: The wrapper call to read.

    Returns:
        The expressions passed as the value and as the message. If the call
        doesn't match the signature, `None`. This happens when an argument is
        missing, repeated or unknown, or when there are too many arguments.
    """
    parameters = ("value", "message")
    positions = iter(parameters)
    bound: dict[str, Any] = {}
    for argument in call.arguments:
        name: str | None
        if isinstance(argument, ExprKeyword):
            name, node = argument.name, argument.value
        else:
            name, node = next(positions, None), argument
        if name is None or name not in parameters or name in bound:
            return None
        bound[name] = node
    if len(bound) != 2:
        return None
    return bound["value"], bound["message"]


class DeprecationsExtension(Extension):
    """An extension to document deprecations made with `frequenz-core` helpers.

    The extension understands two kinds of calls. For each deprecated object it
    finds, it does the same as `griffe-warnings-deprecated` does for decorated
    objects:

    - Adds a `deprecated` label.
    - Stores the deprecation message in the object's `deprecated` field.
    - Adds an admonition with the message at the top of its docstring.

    The first kind is a table of module aliases, used by a module `__getattr__` to
    keep old names working:

    ```python
    from typing import TYPE_CHECKING, TypeAlias

    from frequenz.core.warnings import deprecated_aliases

    if TYPE_CHECKING:
        from mypkg.newmod import Widget as _Widget

        Widget: TypeAlias = _Widget  # plus its usual attribute docstring
    else:
        __getattr__ = deprecated_aliases(__name__, {"Widget": "mypkg.newmod"})
    ```

    The extension marks every name in the table, even if it isn't declared for
    type checkers. If the target is written as `"module:name"`, the object was
    also renamed.

    The second kind is an enum member with a wrapped value:

    ```python
    from frequenz.core.enum import Enum, deprecated_member

    class TaskStatus(Enum):
        OPEN = 1
        PENDING = deprecated_member(1, "PENDING is deprecated, use OPEN instead")
    ```

    The extension marks the member and shows its actual value instead of the
    wrapper call, so the documentation shows `PENDING = 1`. `frequenz-core` also
    accepts `DeprecatedMember(1, "...")`, and the extension recognizes it too:
    calling a class or a function looks the same.

    Warning:
        Griffe never runs the code, so the extension can only read what is
        written directly in the call:

        - Enum messages, alias names and alias targets must be string literals.
          If an enum message isn't a literal, the member isn't marked. If an
          alias name or target isn't a literal, that alias isn't marked. If the
          `message` of an alias table isn't a literal, the extension uses
          `default_message` instead.
        - The alias table must be a dict, passed as the second positional
          argument or as `aliases=`. If it's stored in a constant, none of its
          aliases are marked.
        - The value and the message of an enum member wrapper must be passed
          positionally or by keyword, not unpacked from `*args` or `**kwargs`.

        The extension logs each of these cases at debug level, which you can
        see with `mkdocs -v`.

    To enable it, add it to the mkdocstrings Python handler, together with
    `griffe-warnings-deprecated`:

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

    By default, both extensions use the same format, so all deprecations look the
    same. You can change this and other settings using options:

    ```yaml
                extensions:
                  - griffe_frequenz_core.deprecations:
                      kind: deprecated
                      alias_table_functions:
                        - frequenz.core.warnings.deprecated_aliases
                        - mypkg.compat.moved_to
    ```

    Note:
        The paths of the helpers are options on purpose. If `frequenz-core`
        renames a helper, you can update the option with the new path. You don't
        need to wait for a new release of this package.

    Note:
        There is one difference from `griffe-warnings-deprecated`, on purpose.
        If `title` is empty, `griffe-warnings-deprecated` puts the message in
        the admonition title, but this extension doesn't. The message contains a
        link to the target, which doesn't belong in a title. The extension also
        uses the title to find out if a docstring already has its own
        deprecation admonition. Please don't "fix" this.
    """

    # Each option is a key in `mkdocs.yml`, so we can't group them.
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
            kind: The kind of the admonition added to the docstring.
            title: The title of that admonition. If empty, the admonition has no
                title.
            label: The label added to deprecated objects, or `None` to add no
                label.
            alias_table_functions: The fully qualified paths of the functions that
                create a module `__getattr__` from an alias table. Their calls are
                read as if they were calls to `deprecated_aliases()`: the table is
                the second positional argument or `aliases=`, and the message is
                `message=`.
            member_wrapper_functions: The fully qualified paths of the callables
                that wrap an enum member's value to deprecate it. They can be
                classes or functions, because calling them looks the same. Their
                calls are read as if they were calls to
                `deprecated_member(value, message)`.
            default_message: The message template for aliases, if the alias table
                call doesn't pass a `message`. It should match the default
                message of the function it replaces, because that's what the
                runtime warning says. `{old}` and `{new}` are replaced with the
                alias and its target.
            show_target: Whether to show an alias' value as its target, instead
                of the private name imported for type checkers.
        """
        super().__init__()
        self.kind = kind
        """The kind of the admonition added to the docstring."""
        self.title = title or ""
        """The title of the admonition added to the docstring."""
        self.label = label
        """The label added to deprecated objects."""
        self.alias_table_functions = frozenset(alias_table_functions)
        """The paths of the functions that create a `__getattr__` from an alias table."""
        self.member_wrapper_functions = frozenset(member_wrapper_functions)
        """The paths of the callables that wrap a deprecated enum member's value."""
        self.default_message = default_message
        """The message template for aliases, if the alias table call passes none."""
        self.show_target = show_target
        """Whether to show an alias' value as its target."""

    def on_module_members(self, *, mod: Module, **kwargs: Any) -> None:
        """Mark every name in the module's alias table, if it has one.

        Args:
            mod: The module whose members were just collected.
            **kwargs: Other arguments passed by Griffe, not used.
        """
        call = self._alias_table_call(mod)
        if call is None:
            return
        table, message = self._table_and_message(mod, call)
        for name, target in table.items():
            target_module, _, target_name = target.partition(":")
            path = f"{target_module}.{target_name or name}"
            # If the target isn't in the documentation or in an inventory, an
            # `optional` autoref is shown as plain text, so it doesn't make a
            # strict build fail.
            link = (
                f'<autoref identifier="{path}" optional><code>{path}</code></autoref>'
            )
            text = message.format(old=f"`{mod.path}.{name}`", new=link)

            member = mod.members.get(name)
            if not isinstance(member, Attribute):
                _logger.debug(
                    "%s.%s: the alias isn't declared for type checkers, adding it",
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
            **kwargs: Other arguments passed by Griffe, not used.
        """
        for member in cls.members.values():
            value = getattr(member, "value", None)
            if not isinstance(member, Attribute) or not isinstance(value, ExprCall):
                continue
            if value.canonical_path not in self.member_wrapper_functions:
                continue
            # Once an argument is unpacked, we can't tell which argument is
            # which. In `deprecated_member(*ARGS, "...")`, for example, the
            # first argument isn't necessarily the value.
            if any(
                isinstance(argument, (ExprVarPositional, ExprVarKeyword))
                for argument in value.arguments
            ):
                _logger.debug(
                    "%s: the deprecation wrapper's arguments are unpacked, so "
                    "the member isn't marked",
                    member.path,
                )
                continue
            arguments = _wrapper_arguments(value)
            if arguments is None:
                _logger.debug(
                    "%s: the deprecation wrapper's arguments don't match "
                    "`deprecated_member(value, message)`, so the member isn't "
                    "marked",
                    member.path,
                )
                continue
            real_value, message = arguments
            text = _literal(message)
            if not isinstance(text, str):
                _logger.debug(
                    "%s: the deprecation message isn't a string literal, so the "
                    "member isn't marked",
                    member.path,
                )
                continue
            # Show the member's actual value, not the wrapper call.
            member.value = real_value
            self._mark(member, text)

    def _alias_table_call(self, mod: Module) -> ExprCall | None:
        """Return the module's alias table call, if it has one.

        Args:
            mod: The module to look at.

        Returns:
            The call assigned to the module's `__getattr__`, or `None` if the
            module has no `__getattr__`, or if it isn't created by an alias
            table function.
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
        """Get the alias table and the message template from a call.

        Args:
            mod: The module where the call was found, used in log messages.
            call: The alias table call to read.

        Returns:
            The table, mapping each deprecated name to its target, and the
            message template to use for all of them.
        """
        table_node, message_node = _alias_table_arguments(call)

        message = self.default_message
        if message_node is not None:
            if isinstance(text := _literal(message_node), str):
                message = text
            else:
                _logger.debug(
                    "%s: `message` isn't a string literal, so `default_message` "
                    "is used instead",
                    mod.path,
                )

        table: dict[str, str] = {}
        if table_node is None:
            _logger.debug(
                "%s: the alias table argument can't be found, so no alias is marked",
                mod.path,
            )
            return table, message
        if not isinstance(table_node, ExprDict):
            _logger.debug(
                "%s: the alias table `%s` isn't a dict literal, so none of its "
                "aliases are marked",
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
                    "%s: the alias table entry %s: %s isn't a pair of string "
                    "literals, so it's skipped",
                    mod.path,
                    key,
                    value,
                )
        return table, message

    def _mark(self, member: Attribute, text: str) -> None:
        """Mark one member as deprecated and add the admonition.

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
        """Return whether the member's docstring already has the admonition.

        The extension doesn't change hand-written admonitions, so a module can say
        more about a deprecation than the message template.

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

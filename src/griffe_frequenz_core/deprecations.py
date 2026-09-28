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


def _link(new: str, *, local: bool) -> str:
    """Link a replacement in code font.

    Args:
        new: The fully qualified path of the replacement.
        local: Whether it's in the module of the documented object. In that
            case, its name alone is enough, like for a member of the same class.

    Returns:
        The Markdown cross-reference.
    """
    if local:
        return f"[`{new.rpartition('.')[2]}`][{new}]"
    return f"[`{new}`][]"


def _alias_entry_arguments(
    call: ExprCall,
) -> tuple[Any, Any, Any, Any, Any] | None:
    """Get the arguments of an alias entry call.

    The arguments are matched the same way Python matches them for
    `DeprecatedAlias(name, /, *, new_module=None, new_name=None, since=None,
    message=None)`. At least one of `new_module` and `new_name` must be passed,
    and exactly one of `since` and `message`. Passing `None` is the same as not
    passing the argument, like at runtime.

    The caller must check for unpacked arguments first, because this function
    would treat a `*args` or `**kwargs` as a normal argument.

    Args:
        call: The alias entry call to read.

    Returns:
        The expressions passed as the name, `new_module`, `new_name`, `since` and
            `message`, with `None` for the ones that weren't passed. If the call
            doesn't match the signature, `None`. This happens when an argument is
            missing, repeated, unknown or passed the wrong way, when neither
            `new_module` nor `new_name` is passed, or when both or neither of
            `since` and `message` are passed.
    """
    keywords = ("new_module", "new_name", "since", "message")
    name: Any = None
    bound: dict[str, Any] = {}
    for argument in call.arguments:
        if isinstance(argument, ExprKeyword):
            if argument.name not in keywords or argument.name in bound:
                return None
            if str(argument.value) != "None":
                bound[argument.name] = argument.value
        elif name is None:
            name = argument
        else:
            return None
    if name is None or not ("new_module" in bound or "new_name" in bound):
        return None
    if ("since" in bound) == ("message" in bound):
        return None
    return (
        name,
        bound.get("new_module"),
        bound.get("new_name"),
        bound.get("since"),
        bound.get("message"),
    )


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


# Each option is a key in `mkdocs.yml`, so we can't group them.
class DeprecationsExtension(Extension):  # pylint: disable=too-many-instance-attributes
    """An extension to document deprecations made with `frequenz-core` helpers.

    The extension understands two kinds of calls. For each deprecated object it
    finds, it does the same as `griffe-warnings-deprecated` does for decorated
    objects:

    - Adds a `deprecated` label.
    - Stores the deprecation notice in the object's `deprecated` field.
    - Adds an admonition with the notice at the top of its docstring.

    The first kind is a table of module aliases, used by a module `__getattr__` to
    keep old names working:

    ```python
    from typing import TYPE_CHECKING, TypeAlias

    from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases

    if TYPE_CHECKING:
        from mypkg.newmod import Widget as _Widget

        Widget: TypeAlias = _Widget  # plus its usual attribute docstring
    else:
        __getattr__ = deprecated_aliases(
            __name__,
            DeprecatedAlias("Widget", new_module="mypkg.newmod", since="v1.2.0"),
        )
    ```

    The extension marks every alias in the table, even if it isn't declared for
    type checkers. Its notice is built from `default_message`, saying since which
    version it is deprecated and linking its target.

    If an entry has `new_name`, the object was also renamed. If it doesn't have
    `new_module`, it points to another name in the same module. The entry's
    `message` is only used for the runtime warning, and doesn't change the
    notice. To change the notice, write it by hand.

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

        - Enum messages, and the alias name, `new_module`, `new_name` and `since`
          must be string literals. If one isn't a literal, that member or alias
          isn't marked.
        - Each alias must be a `DeprecatedAlias(...)` call written directly in
          the `deprecated_aliases()` call. If it's stored in a constant, or the
          entries are unpacked from `*args`, they aren't marked.
        - The arguments of an enum member wrapper or of a `DeprecatedAlias`
          must be written explicitly, not unpacked from `*args` or `**kwargs`.

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
                      alias_classes:
                        - frequenz.core.warnings.DeprecatedAlias
                        - mypkg.compat.Moved
    ```

    Note:
        The paths of the helpers are options on purpose. If `frequenz-core`
        renames a helper, you can update the option with the new path. You don't
        need to wait for a new release of this package.

    Note:
        There is one difference from `griffe-warnings-deprecated`, on purpose.
        If `title` is empty, `griffe-warnings-deprecated` puts the message in
        the admonition title, but this extension doesn't. The notice contains a
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
        alias_classes: Sequence[str] = ("frequenz.core.warnings.DeprecatedAlias",),
        member_wrapper_functions: Sequence[str] = (
            "frequenz.core.enum.deprecated_member",
            "frequenz.core.enum.DeprecatedMember",
        ),
        default_message: str = "Deprecated since {since}. Use {new_link} instead.",
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
                read as if they were calls to
                `deprecated_aliases(module, /, *aliases)`: every positional
                argument after the module is an alias entry, and keyword
                arguments are ignored.
            alias_classes: The fully qualified paths of the callables that create
                one alias entry. Their calls are read as if they were calls to
                `DeprecatedAlias(name, /, *, new_module=None, new_name=None,
                since=None, message=None)`, with at least one of `new_module` and
                `new_name`, and exactly one of `since` and `message`.
            member_wrapper_functions: The fully qualified paths of the callables
                that wrap an enum member's value to deprecate it. They can be
                classes or functions, because calling them looks the same. Their
                calls are read as if they were calls to
                `deprecated_member(value, message)`.
            default_message: The template for alias notices. `{old}` and `{new}`
                are replaced with the plain paths of the alias and its target.
                `{new_link}` is replaced with a link to the target in code font,
                showing only its name if it's in the same module. `{since}` is
                replaced with the version, as written. The result is rendered as
                Markdown. It's only shown in the documentation, next to the
                alias, so unlike the runtime warning, it doesn't need to say
                which object is deprecated.
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
        self.alias_classes = frozenset(alias_classes)
        """The paths of the callables that create one alias entry."""
        self.member_wrapper_functions = frozenset(member_wrapper_functions)
        """The paths of the callables that wrap a deprecated enum member's value."""
        self.default_message = default_message
        """The template for alias notices."""
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
        for name, path, local, since in self._alias_entries(mod, call):
            text = self._alias_notice(f"{mod.path}.{name}", path, local, since)
            if text is None:
                continue

            member = mod.members.get(name)
            if not isinstance(member, Attribute):
                # It isn't declared at all, or it's declared by an import like
                # `from new import New as Old` under `TYPE_CHECKING`.
                _logger.debug(
                    "%s.%s: the alias isn't declared as an attribute for type "
                    "checkers, adding one",
                    mod.path,
                    name,
                )
                member = Attribute(name, parent=mod)
                mod.set_member(name, member)

            if self.show_target:
                member.value = ExprName(path)
            self._mark(member, text)

    def _alias_notice(
        self, old: str, new: str, local: bool, since: str | None
    ) -> str | None:
        """Build the notice for one alias entry.

        The notice only uses `since` and the target. The entry's `message` is only
        used for the runtime warning, which is shown in a terminal.

        Args:
            old: The fully qualified path of the alias.
            new: The fully qualified path of its target.
            local: Whether the target is in the module defining the alias.
            since: The version since which the alias is deprecated, if given.

        Returns:
            The notice, or `None` if `default_message` can't be formatted.
        """
        link = _link(new, local=local)
        if since is None:
            # The entry has a message instead, so the notice can only say what
            # to use instead.
            return f"Deprecated. Use {link} instead."
        try:
            # `since` is a value, not part of the template, so we insert it as
            # written, even if it has braces.
            return self.default_message.format(
                old=old, new=new, new_link=link, since=since
            )
        except (AttributeError, IndexError, KeyError, ValueError):
            _logger.debug(
                "%s: the `default_message` option %r can only use {old}, {new}, "
                "{new_link} and {since}, so the alias isn't marked",
                old,
                self.default_message,
            )
            return None

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

    def _alias_entries(
        self, mod: Module, call: ExprCall
    ) -> list[tuple[str, str, bool, str | None]]:
        """Get the alias entries from an alias table call.

        The first positional argument is the module name, so it's skipped. Every
        other positional argument must be an alias entry call. Keyword arguments
        are ignored, because they can't be entries.

        Args:
            mod: The module where the call was found, used in log messages.
            call: The alias table call to read.

        Returns:
            For every entry that can be read, in the order they were written: the
                name, the fully qualified path of its target, whether the target
                is in the same module, and `since` (or `None` if the entry has a
                message instead).
        """
        entries: list[tuple[str, str, bool, str | None]] = []
        module_seen = False
        for argument in call.arguments:
            if isinstance(argument, (ExprKeyword, ExprVarKeyword)):
                continue
            if isinstance(argument, ExprVarPositional):
                # Only `module` could be in there, so we stop skipping the first
                # argument. A module name is never an entry anyway.
                module_seen = True
                _logger.debug(
                    "%s: the alias entries in `%s` are unpacked, so they aren't "
                    "marked",
                    mod.path,
                    argument,
                )
                continue
            if not module_seen:
                module_seen = True
                continue
            entry = self._alias_entry(mod, argument)
            if entry is not None:
                entries.append(entry)
        return entries

    def _alias_entry(
        self, mod: Module, node: Any
    ) -> tuple[str, str, bool, str | None] | None:
        """Get the name, the target and `since` of one alias entry.

        The message is only used for the runtime warning, so it's never read.

        Args:
            mod: The module where the entry was found, used in log messages.
            node: The expression passed as the entry.

        Returns:
            The name, the fully qualified path of its target, whether the target
                is in the same module, and `since` (or `None` if the entry has a
                message instead). If the entry can't be read, `None`.
        """
        if not (
            isinstance(node, ExprCall) and node.canonical_path in self.alias_classes
        ):
            _logger.debug(
                "%s: the alias entry `%s` isn't a call to a known alias class, "
                "so it's skipped",
                mod.path,
                node,
            )
            return None
        if any(
            isinstance(argument, (ExprVarPositional, ExprVarKeyword))
            for argument in node.arguments
        ):
            _logger.debug(
                "%s: the arguments of the alias entry `%s` are unpacked, so "
                "it's skipped",
                mod.path,
                node,
            )
            return None
        arguments = _alias_entry_arguments(node)
        if arguments is None:
            _logger.debug(
                "%s: the alias entry `%s` needs a positional name, `new_module`, "
                "`new_name` or both, and exactly one of `since` and `message`, so "
                "it's skipped",
                mod.path,
                node,
            )
            return None
        read = arguments[:4]
        values: list[Any] = [
            None if argument is None else _literal(argument) for argument in read
        ]
        if any(
            argument is not None and not isinstance(value, str)
            for argument, value in zip(read, values)
        ):
            _logger.debug(
                "%s: an argument of the alias entry `%s` isn't a string literal, "
                "so it's skipped",
                mod.path,
                node,
            )
            return None
        name, new_module, new_name, since = values
        # Like at runtime: without `new_module`, the object is still in this
        # module, and without `new_name`, it kept its name.
        return (
            name,
            f"{new_module or mod.path}.{new_name or name}",
            new_module in (None, mod.path),
            since,
        )

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

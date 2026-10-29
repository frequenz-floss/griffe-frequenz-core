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
from typing import Any, NamedTuple

from griffe import (
    Attribute,
    Class,
    Docstring,
    DocstringSection,
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


def _string(node: Any) -> str | None:
    """Evaluate a Griffe expression as a string literal.

    Args:
        node: The expression to evaluate.

    Returns:
        The string, or `None` if the expression isn't a string literal.
    """
    value = _literal(node)
    return value if isinstance(value, str) else None


class _AliasEntry(NamedTuple):
    """The information the extension could read from an alias entry."""

    name: str
    """The deprecated name, in the module where the alias is defined."""

    new: str | None
    """The fully qualified path of the target, or `None` if it can't be read."""

    local: bool
    """Whether the target is in the module where the alias is defined."""

    since: str | None
    """The version since which the alias is deprecated, or `None` if unknown."""

    since_given: bool
    """Whether `since` is passed, or could be passed in unpacked keyword arguments."""


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


def _generic_message(*, since: str | None = None, new_link: str | None = None) -> str:
    """Build a notice with the information the extension has about a deprecation.

    The notice is shown in the documentation of the deprecated object, so it
    doesn't need to say which object is deprecated. If the extension doesn't know
    since which version the object is deprecated, or what to use instead, the
    notice leaves that out. If it knows neither, the notice only says that the
    object will be removed in a future release.

    Args:
        since: The version since which the object is deprecated, if known.
        new_link: The link to its replacement, if known.

    Returns:
        The notice.
    """
    if since is None and new_link is None:
        return "Deprecated. It will be removed in a future release."
    text = "Deprecated." if since is None else f"Deprecated since {since}."
    return text if new_link is None else f"{text} Use {new_link} instead."


def _alias_entry_arguments(
    call: ExprCall,
) -> tuple[Any, Any, Any, Any, Any] | None:
    """Get the arguments of an alias entry call.

    The arguments are matched the same way Python matches them for
    `DeprecatedAlias(name, /, *, new_module=None, new_name=None, since=None,
    message=None)`. At least one of `new_module` and `new_name` must be passed,
    while `since` and `message` are optional and independent. Passing `None` is
    the same as not passing the argument, like at runtime.

    The caller must check for unpacked arguments first, because this function
    would treat a `*args` or `**kwargs` as a normal argument.

    Args:
        call: The alias entry call to read.

    Returns:
        The expressions passed as the name, `new_module`, `new_name`, `since` and
            `message`, with `None` for the ones that weren't passed. If the call
            doesn't match the signature, `None`. This happens when an argument is
            missing, repeated, unknown or passed the wrong way, when neither
            `new_module` nor `new_name` is passed.
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
    return (
        name,
        bound.get("new_module"),
        bound.get("new_name"),
        bound.get("since"),
        bound.get("message"),
    )


class _WrapperArguments(NamedTuple):
    """The arguments of an enum wrapper call, with `None` for missing arguments."""

    value: Any
    """The value of the member."""

    message: Any
    """The runtime warning."""

    new_name: Any
    """The name of the member to use instead."""

    since: Any
    """The version the member is deprecated since."""


def _wrapper_arguments(call: ExprCall) -> _WrapperArguments | None:
    """Get the arguments of an enum wrapper call.

    Match arguments as Python does for `deprecated_member(value, message=None,
    *, new_name=None, since=None)`. The value and message can be positional or
    keyword arguments. `new_name` and `since` must be keyword arguments. At least
    one of `message` and `new_name` is required. Passing `None` for an optional
    argument is the same as not passing it, like at runtime.

    The caller must check for unpacked arguments first, because this function
    would treat `*args` or `**kwargs` as a normal argument.

    Args:
        call: The wrapper call to read.

    Returns:
        The argument expressions, or `None` if the call doesn't match the
            signature. This happens if an argument is missing, repeated, unknown
            or passed the wrong way, or if both `message` and `new_name` are
            missing.
    """
    parameters = ("value", "message", "new_name", "since")
    positions = iter(parameters[:2])
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
    if "value" not in bound:
        return None
    optional = {
        name: node
        for name, node in bound.items()
        if name != "value" and str(node) != "None"
    }
    if "message" not in optional and "new_name" not in optional:
        return None
    return _WrapperArguments(
        bound["value"],
        optional.get("message"),
        optional.get("new_name"),
        optional.get("since"),
    )


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
    type checkers. Its notice is built from `default_message`, linking its
    target and saying since which version it is deprecated. `since` is optional,
    but without it the notice only says what to use instead, and the extension
    logs a warning.

    If an entry has `new_name`, the object was also renamed. If it doesn't have
    `new_module`, it points to another name in the same module. The entry's
    `message` is only used for the runtime warning, and doesn't change the
    notice. To change the notice, write it by hand.

    The second kind is an enum member with a wrapped value:

    ```python
    from frequenz.core.enum import Enum, deprecated_member

    class TaskStatus(Enum):
        OPEN = 1
        PENDING = deprecated_member(1, new_name="OPEN", since="v1.2.0")
    ```

    The extension marks the member and shows its actual value instead of the
    wrapper call, so the documentation shows `PENDING = 1`. `frequenz-core` also
    accepts `DeprecatedMember(1, new_name="OPEN", since="v1.2.0")`, and the
    extension recognizes it too.

    If you pass `new_name`, the extension builds a notice using `default_message`,
    just as it does for aliases. The notice says since which version the member
    is deprecated and links to the replacement. The link only shows the member's
    name, because it's in the same enum. A `message` passed with `new_name` only
    changes the runtime warning, not the notice.

    Without `new_name`, you should write a `Deprecated:` section in the member's
    docstring. Otherwise, the extension shows the runtime warning as the notice.
    If you pass `since`, the notice starts with "Deprecated since <since>.",
    followed by the warning.

    If you write a notice by hand, the extension uses it instead of the generated
    one. It also moves it to the top of the docstring, where a generated notice
    would go.

    Warning:
        Griffe never runs the code, so the extension can only read string
        literals written directly in the call. If it can't read something, it
        still marks the object as deprecated when it can, and leaves the missing
        information out of the notice:

        - An alias only needs its name to be a string literal to be marked. Its
          value is only shown as the target if `new_module` and `new_name` are
          string literals.
        - If an enum member's `new_name`, `since` or message isn't a literal,
          the member is still marked. The notice uses whatever information the
          extension can read. If it can read the message but not `new_name`, it
          shows the message, like for a member without `new_name`. If it can't
          read any, the notice is "Deprecated. It will be removed in a future
          release." The value is still shown without the wrapper, for example
          `CANCELLED = 1`.
        - If the enum wrapper's arguments are unpacked from `*args` or
          `**kwargs`, the member also gets the generic message. Its value is
          shown as the whole wrapper call, because the extension can't tell
          which argument is the value.

        The extension can't mark an alias if it can't read its name. This
        happens when:

        - The entry isn't a `DeprecatedAlias(...)` call written directly in the
          `deprecated_aliases()` call, for example because it's stored in a
          constant or unpacked from `*args`.
        - The name isn't a string literal.
        - The positional arguments of the entry are unpacked.
        - The arguments don't match the ones of the runtime helper. The
          extension doesn't check the argument values, though.

        The extension logs a warning in all these cases, so a strict build
        fails. It also logs a warning if a notice doesn't say since which
        version the object is deprecated and what to use instead, or if it
        shows the runtime warning. If you wrote the notice by hand, these
        warnings about the notice aren't logged. You can see why something
        couldn't be read with `mkdocs -v`, which shows the debug logs.

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
                `new_name`. `since` and `message` are optional and independent.
            member_wrapper_functions: The fully qualified paths of the callables
                that wrap an enum member's value to deprecate it. They can be
                classes or functions, because calling them looks the same. Their
                calls are read as if they were calls to
                `deprecated_member(value, message=None, *, new_name=None,
                since=None)`. At least one of `message` and `new_name` is required.
            default_message: The template for notices built from `since` and a
                replacement. Used for aliases and enum members with `new_name`.
                `{old}` and `{new}` are replaced with the plain paths of the
                deprecated object and its replacement. `{new_link}` is a link to
                the replacement in code font. It only shows the name if the
                replacement is in the same module or enum. `{since}` is replaced
                with the version, as written. The result is rendered as Markdown.
                The notice appears next to the deprecated object, so it doesn't
                repeat its name.
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
        """The template for notices built from `since` and a replacement."""
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
        for entry in self._alias_entries(mod, call):
            # Only `since` and the target affect the notice. `message` is for
            # the runtime warning, which is shown in a terminal.
            text, problem, fix = self._notice(
                f"{mod.path}.{entry.name}",
                entry.new,
                local=entry.local,
                since=entry.since,
                since_given=entry.since_given,
                unknown_since="because `since` can't be read",
                unknown_new="because the target can't be read",
            )

            member = mod.members.get(entry.name)
            if not isinstance(member, Attribute):
                # It isn't declared at all, or it's declared by an import like
                # `from new import New as Old` under `TYPE_CHECKING`.
                _logger.debug(
                    "%s.%s: the alias isn't declared as an attribute for type "
                    "checkers, adding one",
                    mod.path,
                    entry.name,
                )
                member = Attribute(entry.name, parent=mod)
                mod.set_member(entry.name, member)

            if self.show_target:
                if entry.new is None:
                    _logger.warning(
                        "%s.%s: the target of the alias can't be read, so its "
                        "value is shown as written",
                        mod.path,
                        entry.name,
                    )
                else:
                    member.value = ExprName(entry.new)
            self._mark(
                member, text, problem=problem, fix=fix, generic=problem is not None
            )

    # Aliases and enum members give different reasons for what they can't read,
    # so the caller has to pass them.
    def _notice(  # pylint: disable=too-many-arguments
        self,
        old: str,
        new: str | None,
        *,
        local: bool,
        since: str | None,
        since_given: bool,
        unknown_since: str,
        unknown_new: str,
    ) -> tuple[str, str | None, str]:
        """Build a notice from `since` and the replacement.

        If either argument is missing or can't be read, use a generic notice
        with the information we have.

        Args:
            old: The fully qualified path of the deprecated object.
            new: The fully qualified path of its replacement, or `None` if it
                can't be read.
            local: Whether the replacement is in the same module or enum.
                If so, the link only shows the replacement's name.
            since: The version the object is deprecated since, or `None` if it
                isn't given or can't be read.
            since_given: Whether `since` is passed. If not, the warning says
                so, and suggests passing it.
            unknown_since: The reason the version is unknown even though
                `since` is passed. Included in the warning if `since` is `None`.
            unknown_new: The reason the replacement is unknown. Included in the
                warning if `new` is `None`.

        Returns:
            The notice, why it's incomplete, or `None` if it's complete, and how
                to fix it. A notice is complete if it says everything the
                deprecations guide asks for.
        """
        fix = "Write a `Deprecated:` section in the docstring"
        link = None if new is None else _link(new, local=local)
        if since is not None and link is not None:
            try:
                # `since` is a value, not part of the template, so we insert
                # it as written, even if it has braces.
                return (
                    self.default_message.format(
                        old=old, new=new, new_link=link, since=since
                    ),
                    None,
                    fix,
                )
            except (AttributeError, IndexError, KeyError, ValueError):
                return (
                    _generic_message(since=since, new_link=link),
                    "the `default_message` option can only use {old}, {new}, "
                    "{new_link} and {since}, so a generic notice is shown",
                    fix,
                )
        missing = []
        if since is None:
            reason = unknown_since if since_given else "because `since` isn't given"
            missing.append(f"since which version it is deprecated, {reason}")
            if not since_given and link is not None:
                fix = "Pass `since` or write a `Deprecated:` section in the docstring"
        if link is None:
            missing.append(f"what to use instead, {unknown_new}")
        return (
            _generic_message(since=since, new_link=link),
            f"the notice can't say {', nor '.join(missing)}",
            fix,
        )

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
            # first argument isn't necessarily the value. The member is still
            # deprecated, so we mark it, but we leave the call as written.
            if any(
                isinstance(argument, (ExprVarPositional, ExprVarKeyword))
                for argument in value.arguments
            ):
                _logger.warning(
                    "%s: the deprecation wrapper's arguments are unpacked, so "
                    "its value is shown as the whole call",
                    member.path,
                )
                self._mark(
                    member,
                    _generic_message(),
                    problem="the deprecation message can't be read, so a generic "
                    "notice is shown",
                    generic=True,
                )
                continue
            arguments = _wrapper_arguments(value)
            if arguments is None:
                # This call would fail at runtime, so it doesn't deprecate
                # anything.
                _logger.warning(
                    "%s: the deprecation wrapper's arguments don't match "
                    "`deprecated_member(value, message=None, *, new_name=None, "
                    "since=None)`, which needs `message` or `new_name`, so the "
                    "member isn't marked",
                    member.path,
                )
                continue
            # Show the member's actual value, not the wrapper call, even if we
            # can't read the other arguments. We know the value either way.
            member.value = arguments.value
            self._mark_member(cls, member, arguments)

    def _mark_member(
        self, cls: Class, member: Attribute, arguments: _WrapperArguments
    ) -> None:
        """Mark a wrapped enum member using the information we can read.

        Args:
            cls: The enum the member belongs to.
            member: The member to mark.
            arguments: The arguments of its wrapper call.
        """
        since = None if arguments.since is None else _string(arguments.since)
        if arguments.since is not None and since is None:
            _logger.debug(
                "%s: `since` isn't a string literal, documenting what can be read",
                member.path,
            )
        new_name = None if arguments.new_name is None else _string(arguments.new_name)
        if arguments.new_name is not None and new_name is None:
            _logger.debug(
                "%s: `new_name` isn't a string literal, documenting what can be read",
                member.path,
            )
        message = None if arguments.message is None else _string(arguments.message)
        if new_name is not None or (arguments.new_name is not None and message is None):
            # As for aliases, `message` only changes the runtime warning. We
            # only show it if we can't read `new_name`, because then it's the
            # only thing that can say what to use instead.
            text, problem, fix = self._notice(
                member.path,
                None if new_name is None else f"{cls.path}.{new_name}",
                local=True,
                since=since,
                since_given=arguments.since is not None,
                unknown_since="because `since` isn't a string literal",
                unknown_new="because `new_name` isn't a string literal",
            )
            self._mark(
                member, text, problem=problem, fix=fix, generic=problem is not None
            )
            return
        if message is not None:
            # Without a readable `new_name`, only the runtime warning can tell
            # the reader what to use instead. Show it, even though it's for a
            # terminal. `since` isn't part of the warning, so we add the
            # version before it if we know it.
            self._mark(
                member,
                message if since is None else f"Deprecated since {since}. {message}",
                problem="there is no notice written for the documentation, "
                "so the runtime warning is shown instead",
            )
            return
        _logger.debug(
            "%s: the deprecation message isn't a string literal, so the "
            "member is marked with a generic notice",
            member.path,
        )
        self._mark(
            member,
            _generic_message(since=since),
            problem="the deprecation message isn't a string literal, so a "
            "generic notice is shown",
            generic=True,
        )

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

    def _alias_entries(self, mod: Module, call: ExprCall) -> list[_AliasEntry]:
        """Get the alias entries from an alias table call.

        The first positional argument is the module name, so it's skipped. Every
        other positional argument must be an alias entry call. Keyword arguments
        are ignored, because they can't be entries.

        Args:
            mod: The module where the call was found, used in log messages.
            call: The alias table call to read.

        Returns:
            Every entry whose name can be read, in the order they were written.
        """
        entries: list[_AliasEntry] = []
        module_seen = False
        for argument in call.arguments:
            if isinstance(argument, (ExprKeyword, ExprVarKeyword)):
                continue
            if isinstance(argument, ExprVarPositional):
                # Only `module` could be in there, so we stop skipping the first
                # argument. A module name is never an entry anyway.
                module_seen = True
                _logger.warning(
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

    def _alias_entry(self, mod: Module, node: Any) -> _AliasEntry | None:
        """Read as much as possible from one alias entry.

        The extension only needs the name to mark the alias. The target and
        `since` are only read if they are string literals. The message is never
        read.

        Args:
            mod: The module where the entry was found, used in log messages.
            node: The expression passed as the entry.

        Returns:
            The information read from the entry. If the name can't be read, or the
                arguments don't match the ones of `DeprecatedAlias`, `None`.
        """
        if not (
            isinstance(node, ExprCall) and node.canonical_path in self.alias_classes
        ):
            _logger.warning(
                "%s: the alias entry `%s` isn't a call to a known alias class, "
                "so it's skipped",
                mod.path,
                node,
            )
            return None
        if any(isinstance(argument, ExprVarPositional) for argument in node.arguments):
            _logger.warning(
                "%s: the arguments of the alias entry `%s` are unpacked, so "
                "it's skipped",
                mod.path,
                node,
            )
            return None
        if any(isinstance(argument, ExprVarKeyword) for argument in node.arguments):
            return self._alias_entry_with_unpacked_keywords(mod, node)
        arguments = _alias_entry_arguments(node)
        if arguments is None:
            # This call would fail at runtime, so it doesn't deprecate anything.
            _logger.warning(
                "%s: the alias entry `%s` needs a positional name, `new_module`, "
                "`new_name` or both, and only accepts `since` and `message` "
                "as extra arguments, so it's skipped",
                mod.path,
                node,
            )
            return None
        name_node, *other_nodes = arguments
        name = _string(name_node)
        if name is None:
            _logger.warning(
                "%s: the name of the alias entry `%s` isn't a string literal, so "
                "it's skipped",
                mod.path,
                node,
            )
            return None
        # The message is only used for the runtime warning, so we never read it.
        new_module, new_name, since = (
            None if other is None else _string(other) for other in other_nodes[:3]
        )
        unreadable = [
            other is not None and value is None
            for other, value in zip(other_nodes, (new_module, new_name, since))
        ]
        if any(unreadable):
            _logger.debug(
                "%s: an argument of the alias entry `%s` isn't a string literal, "
                "so only the rest is documented",
                mod.path,
                node,
            )
        # Like at runtime: without `new_module`, the object is still in this
        # module, and without `new_name`, it kept its name.
        new = (
            None
            if unreadable[0] or unreadable[1]
            else f"{new_module or mod.path}.{new_name or name}"
        )
        return _AliasEntry(
            name, new, new_module in (None, mod.path), since, other_nodes[2] is not None
        )

    def _alias_entry_with_unpacked_keywords(
        self, mod: Module, node: ExprCall
    ) -> _AliasEntry | None:
        """Read the name of an alias entry with unpacked keyword arguments.

        Any keyword argument could be in the `**kwargs`, so the extension can only
        read the name.

        Args:
            mod: The module where the entry was found, used in log messages.
            node: The entry call.

        Returns:
            The entry with only its name, or `None` if the name can't be read.
        """
        positional = [
            argument
            for argument in node.arguments
            if not isinstance(argument, (ExprKeyword, ExprVarKeyword))
        ]
        name = _literal(positional[0]) if len(positional) == 1 else None
        if not isinstance(name, str):
            _logger.warning(
                "%s: the arguments of the alias entry `%s` are unpacked, so "
                "it's skipped",
                mod.path,
                node,
            )
            return None
        _logger.debug(
            "%s: the keyword arguments of the alias entry `%s` are unpacked, so "
            "only its name is documented",
            mod.path,
            node,
        )
        return _AliasEntry(name, None, False, None, True)

    def _mark(
        self,
        member: Attribute,
        text: str,
        *,
        problem: str | None = None,
        fix: str = "Write a `Deprecated:` section in the docstring",
        generic: bool = False,
    ) -> None:
        """Mark one member as deprecated and add its notice.

        If the docstring has a hand-written notice, it's used instead of `text`.
        It's also moved to the top of the docstring, where a generated notice
        would go.

        Args:
            member: The member to mark.
            text: The notice.
            problem: Why the notice is incomplete, if it is. It's logged as a
                warning, unless there is a hand-written notice.
            fix: How to fix the problem, added to the warning.
            generic: Whether `text` is the generic notice. If it is, and another
                extension already set a message, that message is used instead,
                also as the notice.
        """
        if generic and isinstance(member.deprecated, str):
            # Another extension could read the message, so we show that one,
            # and nothing is missing from the docs.
            text, problem = member.deprecated, None
        member.deprecated = text
        if self.label:
            member.labels.add(self.label)
        if member.docstring is None:
            member.docstring = Docstring("", parent=member)
        sections = member.docstring.parsed
        written = self._handwritten_notice(sections)
        if written is not None:
            # A docstring must start with its summary, so the hand-written notice
            # can't be at the top in the source. We move it there, so it's in the
            # same place as the generated notices.
            sections.insert(0, sections.pop(written))
            return
        if problem is not None:
            # The documentation says less than the guide asks for, so a strict
            # build should fail.
            _logger.warning("%s: %s. %s to fix this.", member.path, problem, fix)
        sections.insert(
            0,
            DocstringSectionAdmonition(kind=self.kind, text=text, title=self.title),
        )

    def _handwritten_notice(self, sections: list[DocstringSection]) -> int | None:
        """Find a hand-written deprecation notice in a docstring.

        A hand-written notice is a `Deprecated` section, or an admonition with the
        same title as the ones this extension adds (case-insensitive).

        Args:
            sections: The parsed sections of the docstring.

        Returns:
            The index of the first hand-written notice, or `None` if there is
                none.
        """
        for index, section in enumerate(sections):
            if section.kind is DocstringSectionKind.deprecated:
                return index
            if (
                section.kind is DocstringSectionKind.admonition
                and str(getattr(section, "title", "")).strip().lower()
                == self.title.strip().lower()
            ):
                return index
        return None

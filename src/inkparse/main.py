"""
The implementations of the main classes.
"""

from __future__ import annotations
from typing import overload, Any, Self, Literal, TypeVar, Generic, SupportsIndex, Final, Callable, Sequence, Protocol
from types import TracebackType

from contextlib import contextmanager
from collections.abc import Iterator, Iterable
import re
import enum

import inkparse.const as const


def repeat(*, start: int = 0, step: int = 1) -> Iterator[int]:
    """
    `range()` with no end.
    """
    i = start
    while True:
        yield i
        i += step


_T = TypeVar("_T")
_CT = TypeVar("_CT", covariant=True)
_DataT = TypeVar("_DataT")
_TokenTypeT = TypeVar("_TokenTypeT", bound=str|None)
_DataCovT = TypeVar("_DataCovT", covariant=True)
_TokenTypeCovT = TypeVar("_TokenTypeCovT", bound=str|None, covariant=True)



class PosNote:
    """
    Positioned note.
    
    For `ParseError`s and `ParseFailure`s.
    """
    def __init__(self, pos: int, msg: str | None = None) -> None:
        self.pos: int = pos
        self.msg: str | None = msg

class ParseFailure:
    """
    When returned from a parser function, indicates that it has failed. Can be converted into a `ParseError`.

    ```
    r = parser(si)
    if r:
        ... # `r` is a `Result` or `Token` object
    else:
        ... # `r` is a `ParseFailure` object
    ```
    """

    def __init__(self, src: str, pos: int, msg: str | None = None, notes: list[PosNote] = []) -> None:
        """
        `src`: The string that was being parsed.
        `pos`: The position of the failure.
        `msg`: The reason for the failure.
        `notes`: Positioned notes to add to the error. Should be in reverse order. That is, the note that's last in the list will be shown above the other notes.
        """
        self.src: str = src
        self.pos: int = pos
        self.msg: str | None = msg
        self.notes: list[PosNote] = notes
        """Should be in reverse order. That is, the note that's last in the list will be shown above the other notes."""

    def prepend_notes(self, notes: list[PosNote]) -> Self:
        """
        Appends notes to the top of the other notes.
        
        The given notes should be in reverse order. That is, the note that's last in the list will be shown above the other notes.
        """
        self.notes = notes + self.notes
        return self

    def prepend_pos_note(self, pos: int, msg: str | None = None) -> Self:
        """Appends a note to the top of the other notes."""
        self.notes.append(PosNote(pos, msg))
        return self

    def prepend_existing_note(self, note: PosNote) -> Self:
        """Appends a note to the top of the other notes."""
        self.notes.append(note)
        return self

    def error(self) -> ParseError:
        """Converts this to a ParseError."""
        return ParseError(self.src, self.pos, self.msg, self.notes)

    def __bool__(self) -> Literal[False]:
        return False

class ParseError(Exception):
    """
    The exception that's raised when a parser encounters an unrecoverable error.

    Usually used for syntax errors.
    """

    def __init__(self, src: str, pos: int, msg: str | None = None, notes: list[PosNote] = []) -> None:
        """
        `src`: The string that was being parsed.
        `pos`: The position of the error.
        `msg`: The reason for the error.
        `notes`: Positioned notes to add to the error. Should be in reverse order. That is, the note that's last in the list will be shown above the other notes.
        """
        if msg is None:
            super().__init__()
        else:
            super().__init__(msg)
        self.src = src
        self.append_pos_note(pos)
        for note in reversed(notes):
            self.append_existing_note(note)

    def append_pos_note(self, pos: int, msg: str | None = None) -> Self:
        note: list[str] = [] if msg is None else [msg]

        pos = min(pos, len(self.src))
        # should still work with CRLF
        line = self.src.count("\n", 0, pos) + 1
        column = pos - self.src.rfind("\n", 0, pos) # magically works even when it returns -1
        note.append(f"At position {pos} (line {line}, column {column})")

        lines = self.src.splitlines()
        if len(lines) > line-1:
            line_str = lines[line-1]
            if len(line_str) >= column:
                if column <= 20:
                    note.append(f"{line_str[:40]}\n{' '*(column-1)}^")
                else:
                    note.append(f"{line_str[(column-20):(column+20)]}\n{' '*20}^")
        self.add_note("\n".join(note))
        return self
    
    def append_existing_note(self, note: PosNote) -> Self:
        return self.append_pos_note(note.pos, note.msg)

class Token(Generic[_TokenTypeCovT]):
    """
    When returned from a parser function, indicates that it has succeeded.

    ```
    r = parser(si)
    if r:
        ... # `r` is a `Result` or `Token` object
    else:
        ... # `r` is a `ParseFailure` object
    ```

    When used for typing: `Token[TokenTypeType]`
    
    Example: `Token[Literal["integer"]]` `Token[str]`
    """
    def __init__(self, token_type: _TokenTypeCovT, pos: tuple[int, int] | None = None, subtokens: list[Token] = []) -> None:
        """
        `token_type` can either be a string or None.
        """
        self.token_type: Final[_TokenTypeCovT] = token_type
        self.pos: Final[tuple[int, int] | None] = pos
        self.subtokens: list[Token] = subtokens

    def with_type(self, token_type: _TokenTypeT) -> Token[_TokenTypeT]:
        """Creates a copy of this token with the provided token type."""
        return Token(token_type, self.pos, self.subtokens)

    def __bool__(self) -> Literal[True]:
        return True
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, tuple):
            return self.pos == other
        elif isinstance(other, Token):
            return self.token_type == other.token_type and self.pos == other.pos
        else:
            return self.token_type == other
    
    def __contains__(self, other: object) -> bool:
        return any(other == token for token in self.subtokens)
    
    def __getitem__(self, key: object) -> Token:
        for token in self.subtokens:
            if token == key:
                return token
        raise KeyError

    def __repr__(self) -> str:
        return (
            (
                f"<{self.token_type}>"
                if self.pos is None else
                f"<{self.token_type} {self.pos[0]}..{self.pos[1]}>"
            )
            + (
                (" [" + (" ".join(repr(token) for token in self.subtokens)) + "]") if self.subtokens else ""
            )
        )

class Result(Token, Generic[_DataCovT, _TokenTypeCovT]):
    """
    When returned from a parser function, indicates that it has succeeded. Can also contain data.

    ```
    r = parser(si)
    if r:
        output = r.data     # (if `parser` only returns `Result` objects)
    else:
        ... # failed
    ```

    When used for typing: `Result[DataType, TokenTypeType]`
    
    Example: `Result[int, Literal["integer"]]` `Result[int, str]`
    """
    def __init__(self, data: _DataCovT, token_type: _TokenTypeCovT, pos: tuple[int, int] | None = None, subtokens: list[Token] = []) -> None:
        super().__init__(token_type, pos, subtokens)
        self.data: _DataCovT = data

    def with_type(self, token_type: _TokenTypeT) -> Result[_DataCovT, _TokenTypeT]:
        """Creates a copy of this result with the provided token type."""
        return Result(self.data, token_type, self.pos, self.subtokens)

    def __repr__(self) -> str:
        return (
            super().__repr__()
            + " {" + repr(self.data) + "}"
        )



class StringIterator:
    def __init__(self, src: str, starting_pos: int = 0) -> None:
        self.src: str = src
        """The string that's being parsed."""
        self.pos: int = starting_pos
        """The current position."""

    def __len__(self) -> int:
        return len(self.src)

    def __getitem__(self, key: SupportsIndex | slice) -> str:
        return self.src[key]

    def move_and_get_range(self, amount: int) -> tuple[int, int]:
        """Moves the iterator by the specified amount of characters. Returns a position range."""
        start_pos = self.pos
        self.pos += amount
        return (start_pos, self.pos)

    def goto_and_get_range(self, pos: int) -> tuple[int, int]:
        """Moves the iterator to the position. Returns a position range."""
        start_pos = self.pos
        self.pos = pos
        return (start_pos, self.pos)

    def has_chars(self, amount: int) -> bool:
        """Whether there are at least that many characters left."""
        return self.pos+amount <= len(self.src)

    def is_eof(self) -> bool:
        """Whether the end of the input has been reached. The opposite of `not_eof()` and `__bool__()`"""
        return self.pos >= len(self.src)

    def not_eof(self) -> bool:
        """Whether there are any characters left to parse. The opposite of `is_eof()`"""
        return self.pos >= len(self.src)

    def __bool__(self) -> bool:
        """Whether there are any characters left to parse. The opposite of `is_eof()`"""
        return self.pos < len(self.src)

    def peek(self, amount: int) -> str | None:
        """
        Retrieves the specified amount of characters without consuming.
        
        If there aren't enough characters, returns `None`.
        """
        if not self.has_chars(amount):
            return None
        return self.src[self.pos:self.pos+amount]

    def take(self, amount: int) -> str | None:
        """
        Consumes and retrieves the specified amount of characters.
        
        If there aren't enough characters, returns `None`.
        """
        if not self.has_chars(amount):
            return None
        start_pos = self.pos
        self.pos += amount
        return self.src[start_pos:self.pos]
    
    def checkpoint(self, *, note: str | None = None) -> Checkpoint:
        """
        Creates a `Checkpoint` at the current position.
        
        If you need another checkpoint within the checkpoint, call `Checkpoint.sub_checkpoint()` on the returned checkpoint.
        
        Same as `Checkpoint.__call__()`
        """
        return Checkpoint(self, note=note)
    
    def __call__(self, *, note: str | None = None) -> Checkpoint:
        """
        Creates a `Checkpoint` at the current position.
        
        If you need another checkpoint within the checkpoint, call `Checkpoint.sub_checkpoint()` on the returned checkpoint.
        
        Same as `Checkpoint.checkpoint()`
        """
        return Checkpoint(self, note=note)

    def save(self) -> Savepoint:
        """Saves the current position as a `Savepoint` and returns it."""
        return Savepoint(self)

    def character(self, value: str) -> bool:
        """
        Attempts to match the given character. Case sensitive.

        Advances the position if it matched.

        Returns a bool indicating whether or not the character was matched.
        """
        if not self.has_chars(1):
            return False
        if self.src[self.pos] == value:
            self.pos += 1
            return True
        else:
            return False

    def character_anycase(self, value: str) -> bool:
        """
        Attempts to match the given character. Non case sensitive.

        Advances the position if it matched.

        Returns a bool indicating whether or not the character was matched.
        """
        if not self.has_chars(1):
            return False
        if self.src[self.pos].lower() == value.lower():
            self.pos += 1
            return True
        else:
            return False

    def literal(self, value: str) -> bool:
        """
        Attempts to match the given string. Case sensitive.

        Advances the position if it matched.

        Returns a bool indicating whether or not the string was matched.
        """
        if not self.has_chars(len(value)):
            return False
        if self.src[self.pos:self.pos+len(value)] == value:
            self.pos += len(value)
            return True
        else:
            return False

    def literal_anycase(self, value: str) -> bool:
        """
        Attempts to match the given string. Non case sensitive.

        Advances the position if it matched.

        Returns a bool indicating whether or not the string was matched.
        """
        if not self.has_chars(len(value)):
            return False
        if self.src[self.pos:self.pos+len(value)].lower() == value.lower():
            self.pos += len(value)
            return True
        else:
            return False

    def oneof_literals(self, values: Sequence[str]) -> str | None:
        """
        Attempts to match any of the given strings, starting from the first. Case sensitive.

        Advances the position if it matched.

        Returns the matched string, or `None` if none of them matched.
        """
        for pattern in values:
            if self.literal(pattern):
                return pattern
        return None

    def oneof_literals_anycase(self, values: Sequence[str]) -> str | None:
        """
        Attempts to match any of the given strings, starting from the first. Non case sensitive.

        Advances the position if it matched.

        Returns the matched string, or `None` if none of them matched.
        """
        for pattern in values:
            if self.literal_anycase(pattern):
                return pattern
        return None

    def regex(self, pattern: str | re.Pattern, flags: int | re.RegexFlag = 0) -> re.Match[str] | None:
        """
        Attempts to match the regex.
        
        Advances the position if it matched.
        """
        m = re.compile(pattern, flags).match(self.src, self.pos)
        if m is not None:
            self.pos = m.end()
        return m
    
    def ws0(self) -> None:
        """Matches zero or more whitespaces."""
        while self.peek(1) in const.WHITESPACES:
            self.pos += 1
    
    def ws1(self) -> bool:
        """Matches one or more whitespaces. Returns a bool indicating whether or not the first whitespace was found."""
        if self.peek(1) not in const.WHITESPACES:
            return False
        self.pos += 1
        self.ws0()
        return True

    def optional(self) -> Iterator[Savepoint]:
        """
        If the content's don't match, backtracks to the starting position.

        Yields a `Savepoint`.

        Usage:
        ```
        for _ in si.optional():
            break       # Matched, exit without backtracking.
            continue    # Didn't match, backtrack and exit.
        else:
            ... # Didn't match.
        ```

        "One-of" logic: (Using the returned `Savepoint`)
        ```
        for CASE in si.optional():
            if si.literal("a"):
                ...
                break
            CASE()
            if si.literal("b"):
                ...
                break
            CASE()
            if si.literal("c"):
                ...
                break
        else:
            ... # No case matched
        ```

        "While matching" logic:
        ```
        while True:
            for _ in si.optional():
                ...
                break   # Matched, so keep looping.
            else:
                break   # Didn't match, so break out of the while loop.
        ```
        """

        revert = self.save()

        try:
            yield revert
        except:
            revert()
            raise

        revert()

    def loop(self, iterable: Iterable[_T]) -> Iterator[_T]:
        """
        Loops until one of the iterations match.

        If an iteration successfully matches, use `break` to stop looping.

        Usage:
        ```
        for item in si.loop([1, 2, 3]):
            break       # Matched, stop looping.
            continue    # Didn't match, backtrack and try the next one.
        else:
            ... # Ran out of items before any iteration matched.
        ```
        """

        revert = self.save()

        for item in iterable:
            try:
                yield item
            except:
                revert()
                raise

            revert()


class Savepoint:
    """
    A simplified and faster version of `Checkpoint`.

    Can only be reverted manually. (By calling the savepoint.)

    No concept of committing and automatic rollbacks.
    """
    def __init__(self, si: StringIterator) -> None:
        self.pos: Final[int] = si.pos
        self.si: Final[StringIterator] = si

    def __call__(self) -> None:
        """Same as `Savepoint.rollback()`."""
        self.si.pos = self.pos

    def rollback(self) -> None:
        """Same as `Savepoint.__call__()`."""
        self.si.pos = self.pos

    def get_range(self) -> tuple[int, int]:
        return (self.pos, self.si.pos)
    
    def get_string(self) -> str:
        return self.si.src[self.pos : self.si.pos]
    
    def guard(self, value: _T) -> _T:
        """
        If the parameter is `False` or falsy, rolls back the checkpoint.
        
        Returns the parameter as-is.

        Common usage method:
        ```
        si.save().guard(si.literal("test"))
        ```
        """
        if not value:
            self.rollback()
        return value
    
    def inverted_guard(self, value: _T) -> _T:
        """
        If the parameter is `True` or true-y, rolls back the checkpoint.
        
        Returns the parameter as-is.

        Common usage method:
        ```
        si.save().inverted_guard(si.literal("test"))
        ```
        """
        if value:
            self.rollback()
        return value
    
    def rollback_inline(self, value: _T) -> _T:
        """
        Always rolls back.
        
        Returns the parameter as-is.
        """
        self.rollback()
        return value


class Checkpoint:
    """
    Used as a context manager:
    ```
    with Checkpoint(si) as c:
        ...
    ```

    Can be created by calling a `StringIterator`:
    ```
    with si() as c:
        ...
    ```

    Failure and success:
    ```
    with si() as c:
        return c.token("token_type")            # Successfully matched
        return c.result(data, "token_type")     # Successfully matched
        return c.fail("Failure reason.")        # Failed to match
        raise c.error("Error reason.")          # Irrecoverable error
    ```
    """
    def __init__(self, si: StringIterator, *, parent_checkpoint: Checkpoint | None = None, note: str | None = None) -> None:
        """
        Create using `StringIterator.checkpoint()` or `StringIterator.__call__()` instead.
        """
        self.pos: Final[int] = si.pos
        """The saved position."""
        self.si: Final[StringIterator] = si
        """The bound StringIterator."""
        self.parent_checkpoint: Final[Checkpoint | None] = parent_checkpoint

        self.subtokens: list[Token] = []
        """The tokens to add as subtokens to the resulting `Token`."""
        self.notes: list[PosNote] = []
        """The notes to add to the resulting `ParseError` or `ParseFailure`."""
        self.committed: bool = False
        """Use `is_committed()` to check if it's committed."""

        self._starting_note: str | None = note
        if note is not None:
            self.note(note)

    def restart(self) -> None:
        """Rolls back and reverts all the data of the checkpoint to the starting configuration."""
        self.si.pos = self.pos
        self.subtokens = []
        self.notes = []
        self.committed = False

        if self._starting_note is not None:
            self.note(self._starting_note)

    def commit(self) -> None:
        """Commited checkpoints will not be rolled back automatically."""
        self.committed = True

    def uncommit(self) -> None:
        """Uncommited checkpoints will be rolled back automatically."""
        self.committed = False

    def is_committed(self) -> bool:
        """Checks if this is committed. Works with sub-checkpoints."""
        return self.committed or (self.parent_checkpoint is not None and self.parent_checkpoint.is_committed())

    def rollback(self) -> None:
        """Rolls back the iterator to the starting position. (Regardless of the checkpoint being commited or not.)"""
        self.si.pos = self.pos

    def rollback_if_uncommited(self) -> None:
        """Rolls back the iterator to the starting position if the checkpoint isn't committed."""
        if not self.is_committed():
            self.si.pos = self.pos

    def subtoken(self, token: Token) -> None:
        """
        Adds a token/result into the resulting token's subtokens.
        """
        self.subtokens.append(token)
    
    def note(self, msg: str | None = None) -> None:
        """
        Adds a positioned note to the resulting failure.

        Uses the position of the `StringIterator`.
        """
        self.notes.append(PosNote(self.si.pos, msg))

    def get_range(self) -> tuple[int, int]:
        return (self.pos, self.si.pos)
    
    def get_string(self) -> str:
        return self.si.src[self.pos : self.si.pos]

    @overload
    def get_token(self) -> Token[None]: ...
    @overload
    def get_token(self, token_type: _TokenTypeT) -> Token[_TokenTypeT]: ...

    def get_token(self, token_type: _TokenTypeT | None = None) -> Token[_TokenTypeT | None]:
        """
        Returns a `Token` object without committing.
        
        Uses the checkpoint's saved position as the start, and the current iterator position as the end position of the token.
        """
        return Token(token_type, self.get_range(), subtokens=self.subtokens)

    @overload
    def get_result(self, data: _DataT) -> Result[_DataT, None]: ...
    @overload
    def get_result(self, data: _DataT, token_type: _TokenTypeT) -> Result[_DataT, _TokenTypeT]: ...

    def get_result(self, data: _DataT, token_type: _TokenTypeT | None = None) -> Result[_DataT, _TokenTypeT | None]:
        """
        Returns a `Result` object without committing.
        
        Uses the checkpoint's saved position as the start, and the current iterator position as the end position of the result.
        """
        return Result(data, token_type, self.get_range(), subtokens=self.subtokens)

    @overload
    def token(self) -> Token[None]: ...
    @overload
    def token(self, token_type: _TokenTypeT) -> Token[_TokenTypeT]: ...

    def token(self, token_type: _TokenTypeT | None = None) -> Token[_TokenTypeT | None]:
        """
        Commits and returns a `Token` object.
        
        Uses the checkpoint's saved position as the start, and the current iterator position as the end position of the token.
        """
        self.committed = True
        return Token(token_type, self.get_range(), subtokens=self.subtokens)

    @overload
    def result(self, data: _DataT) -> Result[_DataT, None]: ...
    @overload
    def result(self, data: _DataT, token_type: _TokenTypeT) -> Result[_DataT, _TokenTypeT]: ...

    def result(self, data: _DataT, token_type: _TokenTypeT | None = None) -> Result[_DataT, _TokenTypeT | None]:
        """
        Commits and returns a `Result` object.
        
        Uses the checkpoint's saved position as the start, and the current iterator position as the end position of the result.
        """
        self.committed = True
        return Result(data, token_type, self.get_range(), subtokens=self.subtokens)

    def error(self, msg: str | None = None, notes: list[PosNote] = []) -> ParseError:
        """Creates a `ParseError` at the current position of the iterator."""
        self.committed = False
        return ParseError(self.si.src, self.si.pos, msg, notes)
        # do not prepend self.notes, as it's supposed to be prepended by __exit__().

    def error_start(self, msg: str | None = None, notes: list[PosNote] = []) -> ParseError:
        """Creates a `ParseError` at the starting position of the checkpoint."""
        self.committed = False
        return ParseError(self.si.src, self.pos, msg, notes)
        # do not prepend self.notes, as it's supposed to be prepended by __exit__().

    def fail(self, msg: str | None = None, notes: list[PosNote] = []) -> ParseFailure:
        """Uncommits and returns a `ParseFailure` positioned at the current position of the iterator."""
        self.committed = False
        return ParseFailure(self.si.src, self.si.pos, msg, notes).prepend_notes(self.notes)

    def fail_start(self, msg: str | None = None, notes: list[PosNote] = []) -> ParseFailure:
        """Uncommits and returns a `ParseFailure` positioned at the starting position of the checkpoint."""
        self.committed = False
        return ParseFailure(self.si.src, self.pos, msg, notes).prepend_notes(self.notes)

    def propagate(self, failure: ParseFailure) -> ParseFailure:
        """
        For failing using an existing `ParseFailure`.
        
        Uncommits, adds the current context's notes to the ParseError and returns it.

        Example:
        ```
        with si() as c:
            if not (r := foo(si)):
                return c.propagate(r)   # The foo parser failed, so fail too.
            if not (r := bar(si)):
                raise r.error()         # The bar parser failed, so raise an error.

            ... # Going fine, parse other stuff.
        ```
        """
        self.committed = False
        return failure.prepend_notes(self.notes)

    def add_notes_to_error(self, error: ParseError) -> None:
        for note in reversed(self.notes):
            error.append_existing_note(note)

    def __enter__(self) -> Self:
        return self

    @overload
    def __exit__(self, exctype: None, exc: None, traceback: None) -> Literal[False]: ...
    @overload
    def __exit__(self, exctype: type[BaseException], exc: BaseException, traceback: TracebackType) -> Literal[False]: ...

    def __exit__(
        self,
        exctype: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if exc is None:
            self.rollback_if_uncommited()
        else:
            if isinstance(exc, ParseError):
                self.add_notes_to_error(exc)
            self.rollback()
        return False
    
    def sub_checkpoint(self, *, note: str | None = None) -> Checkpoint:
        """
        Creates a `Checkpoint` at the current position.
        
        If the parent checkpoint is committed, the sub-checkpoint won't roll back, unlike `StringIterator.checkpoint()`, which would require both of the checkpoints to be committed.
        
        Same as `Checkpoint.__call__()`
        """
        return Checkpoint(self.si, parent_checkpoint=self, note=note)
    
    def __call__(self, *, note: str | None = None) -> Checkpoint:
        """
        Creates a `Checkpoint` at the current position.
        
        If the parent checkpoint is committed, the sub-checkpoint won't roll back, unlike `StringIterator.checkpoint()`, which would require both of the checkpoints to be committed.
        
        Same as `Checkpoint.sub_checkpoint()`
        """
        return Checkpoint(self.si, parent_checkpoint=self, note=note)


class BasicParser(Protocol):
    """
    A protocol for parsers that take no parameters, and only return a boolean value.

    A falsy value returned from the parser indicates failure.
    
    Usually returned from BasicParser factories.
    """
    def __call__(self, si: StringIterator) -> bool: ...

class BasicParserParam(Protocol):
    """
    A protocol for parsers that take no parameters, and returns any value.

    The return value is meant to be cast to a boolean.

    A falsy value returned from the parser indicates failure.
    
    Usually used as the parameter for BasicParser factories.
    """
    def __call__(self, si: StringIterator) -> Any: ...

FactoryParameter = BasicParserParam | str | re.Pattern

def convert_factory_parameter(parser: FactoryParameter) -> BasicParserParam:
    if isinstance(parser, str):
        return literal(parser)
    elif isinstance(parser, re.Pattern):
        return regex(parser)
    else:
        assert callable(parser)
        return parser

def convert_factory_parameters(parsers: tuple[FactoryParameter, ...]) -> tuple[BasicParserParam, ...]:
    return tuple(convert_factory_parameter(parser) for parser in parsers)



def literal(*values: str) -> BasicParser:
    """
    BasicParser factory for:
    - `StringIterator.character(...)`
    - `StringIterator.literal(...)`
    - `StringIterator.oneof_literals(...)`
    """
    if len(values) <= 0:
        raise ValueError("At least one literal required.")
    if len(values) == 1:
        value = values[0]
        if len(value) == 1:
            return lambda si: si.character(value)
        else:
            return lambda si: si.literal(value)
    else:
        return lambda si: bool(si.oneof_literals(values))

def anycase(*values: str) -> BasicParser:
    """
    BasicParser factory for:
    - `StringIterator.character_anycase(...)`
    - `StringIterator.literal_anycase(...)`
    - `StringIterator.oneof_literals_anycase(...)`
    """
    if len(values) <= 0:
        raise ValueError("At least one literal required.")
    if len(values) == 1:
        value = values[0]
        if len(value) == 1:
            return lambda si: si.character_anycase(value)
        else:
            return lambda si: si.literal_anycase(value)
    else:
        return lambda si: bool(si.oneof_literals_anycase(values))

def regex(pattern: str | re.Pattern, flags: int | re.RegexFlag = 0) -> BasicParser:
    """BasicParser factory for `StringIterator.regex(...)`."""
    return lambda si: bool(si.regex(pattern, flags))

def ws0(si: StringIterator) -> bool:
    """A pre-defined BasicParser (not a factory) for `StringIterator.ws0()`."""
    si.ws0()
    return True

def ws1(si: StringIterator) -> bool:
    """A pre-defined BasicParser (not a factory) for `StringIterator.ws1()`."""
    return si.ws1()

def has_chars(amount: int) -> BasicParser:
    """BasicParser factory for `StringIterator.has_chars(amount)`."""
    return lambda si: si.has_chars(amount)

def take(amount: int) -> BasicParser:
    """BasicParser factory for `StringIterator.take(amount)`."""
    return lambda si: si.take(amount) is not None

def is_eof(si: StringIterator) -> bool:
    """A pre-defined BasicParser (not a factory) for `StringIterator.is_eof()`."""
    return si.is_eof()

def not_eof(si: StringIterator) -> bool:
    """A pre-defined BasicParser (not a factory) for `StringIterator.not_eof()`."""
    return si.not_eof()


def seq(*parsers: FactoryParameter) -> BasicParser:
    """
    A BasicParser factory.
    
    All the given parsers must match in sequence for the parser to succeed.
    """
    if len(parsers) < 2:
        raise ValueError("At least two parsers required.")
    new_parsers = convert_factory_parameters(parsers)
    return lambda si: si.save().guard(all(parser(si) for parser in new_parsers))

def oneof(*parsers: FactoryParameter) -> BasicParser:
    """
    A BasicParser factory.
    
    Attempts to match any of the parsers, in sequence, until one matches. If none match, fails.
    """
    if len(parsers) < 2:
        raise ValueError("At least two parsers required.")
    new_parsers = convert_factory_parameters(parsers)
    return lambda si: any(parser(si) for parser in new_parsers)

def optional_oneof(*parsers: FactoryParameter) -> BasicParser:
    """
    A BasicParser factory.
    
    Attempts to match any of the parsers, in sequence, until one matches. If none match, fails.
    """
    if len(parsers) < 2:
        raise ValueError("At least two parsers required.")
    new_parsers = convert_factory_parameters(parsers)
    return lambda si: any(parser(si) for parser in new_parsers) or True

def optional(
    *parsers: FactoryParameter,
    success: FactoryParameter | None = None,
    fail: FactoryParameter | None = None,
) -> BasicParser:
    """
    A BasicParser factory.
    
    Returns a parser that returns True no matter what the parser returns.

    If multiple parsers are supplied, matches them in sequence.

    `success`: The parser to run after if the optional matches.
    `fail`: The parser to run after if the optional fails.
    """
    if len(parsers) <= 0:
        raise ValueError("At least one parser required.")
    # both success and fail were supplied
    if success is not None and fail is not None:
        fail_parser    = convert_factory_parameter(fail   )
        success_parser = convert_factory_parameter(success)
        if len(parsers) == 1:
            parser = convert_factory_parameter(parsers[0])
            return lambda si: success_parser(si) if (bool(parser(si))) else fail_parser(si)
        else:
            new_parsers = convert_factory_parameters(parsers)
            return lambda si: success_parser(si) if (si.save().guard(all(parser(si) for parser in new_parsers))) else fail_parser(si)
    # only success was supplied
    elif success is not None and fail is None: 
        success_parser = convert_factory_parameter(success)
        if len(parsers) == 1:
            parser = convert_factory_parameter(parsers[0])
            return lambda si: (bool(parser(si))) and success_parser(si)
        else:
            new_parsers = convert_factory_parameters(parsers)
            return lambda si: (si.save().guard(all(parser(si) for parser in new_parsers))) and success_parser(si)
    # only fail was supplied
    elif success is None and fail is not None: 
        fail_parser = convert_factory_parameter(fail)
        if len(parsers) == 1:
            parser = convert_factory_parameter(parsers[0])
            return lambda si: (bool(parser(si))) or fail_parser(si)
        else:
            new_parsers = convert_factory_parameters(parsers)
            return lambda si: (si.save().guard(all(parser(si) for parser in new_parsers))) or fail_parser(si)
    # none of them were supplied
    else:
        if len(parsers) == 1:
            parser = convert_factory_parameter(parsers[0])
            return lambda si: bool(parser(si)) or True
        else:
            new_parsers = convert_factory_parameters(parsers)
            return lambda si: si.save().guard(all(parser(si) for parser in new_parsers)) or True

def inverted(*parsers: FactoryParameter) -> BasicParser:
    """
    A BasicParser factory.
    
    Returns a parser that returns the opposite of the given parser's result.

    If multiple parsers are supplied, matches them in sequence.
    """
    if len(parsers) <= 0:
        raise ValueError("At least one parser required.")
    if len(parsers) == 1:
        parser = convert_factory_parameter(parsers[0])
        return lambda si: not bool(parser(si))
    else:
        new_parsers = convert_factory_parameters(parsers)
        return lambda si: not si.save().guard(all(parser(si) for parser in new_parsers))

def lookahead(*parsers: FactoryParameter) -> BasicParser:
    """
    A BasicParser factory.
    
    Matches without advancing.

    If multiple parsers are supplied, matches them in sequence.
    """
    if len(parsers) <= 0:
        raise ValueError("At least one parser required.")
    if len(parsers) == 1:
        parser = convert_factory_parameter(parsers[0])
        return lambda si: not si.save().rollback_inline(bool(parser(si)))
    else:
        new_parsers = convert_factory_parameters(parsers)
        return lambda si: not si.save().rollback_inline(all(parser(si) for parser in new_parsers))

def repeat0(*parsers: FactoryParameter) -> BasicParser:
    """
    A BasicParser factory.
    
    Repeatedly matches the given parser until it fails.

    If multiple parsers are supplied, matches them in sequence. (All parsers must match for an iteration to be considered successful)
    """
    if len(parsers) <= 0:
        raise ValueError("At least one parser required.")
    if len(parsers) == 1:
        parser = convert_factory_parameter(parsers[0])
        def inner(si: StringIterator) -> bool:
            while parser(si):
                pass
            return True
        return inner
    else:
        new_parsers = convert_factory_parameters(parsers)
        def inner(si: StringIterator) -> bool:
            while si.save().guard(all(parser(si) for parser in new_parsers)):
                pass
            return True
        return inner

def repeat1(*parsers: FactoryParameter) -> BasicParser:
    """
    A BasicParser factory.
    
    Repeatedly matches the given parser until it fails. Succeeds if at least one iteration matches.

    If multiple parsers are supplied, matches them in sequence. (All parsers must match for an iteration to be considered successful)
    """
    if len(parsers) <= 0:
        raise ValueError("At least one parser required.")
    if len(parsers) == 1:
        parser = convert_factory_parameter(parsers[0])
        def inner(si: StringIterator) -> bool:
            if not parser(si):
                return False
            while parser(si):
                pass
            return True
        return inner
    else:
        new_parsers = convert_factory_parameters(parsers)
        def inner(si: StringIterator) -> bool:
            if not si.save().guard(all(parser(si) for parser in new_parsers)):
                return False
            while si.save().guard(all(parser(si) for parser in new_parsers)):
                pass
            return True
        return inner
"""
Classes for parsing.

`with` statement based syntax. Basically everything is done using `with` statements.
"""

from __future__ import annotations
from typing import Literal, Type, Optional, TypeVar, Generic, Final, Callable, Any, Sequence
from types import TracebackType

from contextlib import contextmanager
from collections.abc import Generator
import re
from enum import Enum

from inkparse.expr import Expr

WHITESPACES: Final[set[str]] = {" ", "\t", "\n", "\r", "\f"}

AT: Literal[True] = True
"""
A variable that's always true.

For writing `return`, `break` and `continue` statements without language servers thinking further code is unreachable.

It's ugly, but it works.

```
with optional():
    literal("foo")
    if AT: return Result("data")
literal("bar") # not marked as unreachable thanks to AT
```

The code isn't unreachable because `literal("foo")` can raise an error and the `optional()` will catch it.

Consider using `oneof()` or `count()` for writing "one of" logic.
"""

_T = TypeVar("_T")

class Ref(Generic[_T]):
    """An encapsulator object, for passing fundamental types via reference."""
    def __init__(self, value: _T) -> None:
        self.value: _T = value

    def __bool__(self) -> bool:
        return bool(self.value)

class UnresolvedError(Exception):
    pass

class Pos:
    """
    A position in a string.

    If you pass an existing Position into the constructor, it's returned as is.
    """
    def __new__(cls, pos: int | Pos) -> Pos:
        if isinstance(pos, Pos):
            return pos
        else:
            return IntPos(pos)

    def __init__(self, _) -> None:
        raise NotImplementedError()

    def resolve_initial(self, si: StringIterator | None = None) -> Pos:
        """Do initial resolutions for the position. Resolves `HERE` and `EOF` positions."""
        raise NotImplementedError()

    def resolve_final(self, si: StringIterator | None = None) -> IntPos:
        """Do final resolutions for the position. Resolves `LATER` positions."""
        raise NotImplementedError()

    def resolve_all(self, si: StringIterator | None = None) -> IntPos:
        """Do both resolutions."""
        return self.resolve_initial(si).resolve_final(si)

    def get(self) -> int:
        """Gets the final position. Raises an `UnresolvedError` if it wasn't resolved yet. Returns an int."""
        if isinstance(self, IntPos):
            return self.pos
        else:
            raise UnresolvedError()

    def __int__(self) -> int:
        """Same as `get()`."""
        return self.resolve_final().pos

    def __str__(self) -> str:
        """Same as `str(pos.get())`."""
        return str(self.resolve_final().pos)

class IntPos(Pos):
    """A definite position in a string."""
    def __new__(cls, pos: int) -> IntPos:
        return object.__new__(cls)

    def __init__(self, pos: int) -> None:
        self.pos: int = pos

    def resolve_initial(self, si: StringIterator | None = None) -> Pos:
        return self

    def resolve_final(self, si: StringIterator | None = None) -> IntPos:
        return self

class ArbitraryPos(Pos, Enum):
    """Constants representing arbitrary positions in strings."""
    EOF = 0
    HERE = 1
    LATER = 2

    def resolve_initial(self, si: StringIterator | None = None) -> Pos:
        if si is None:
            assert _current_si is not None
            si = _current_si
        if self is EOF:
            return IntPos(si.get_len())
        elif self is HERE:
            return IntPos(si.get_pos())
        else:
            assert self is LATER
            return self

    def resolve_final(self, si: StringIterator | None = None) -> IntPos:
        assert self is not EOF, "Called `resolve_final()` on EOF, `resolve_initial()` should have been called before it."
        assert self is not HERE, "Called `resolve_final()` on HERE, `resolve_initial()` should have been called before it."
        assert self is LATER
        if si is None:
            assert _current_si is not None
            si = _current_si
        return IntPos(si.get_pos())


EOF = ArbitraryPos.EOF
"""The end of the provided string."""
HERE = ArbitraryPos.HERE
"""A value representing the position of the iterator right now. It's the responsibility of the function to resolve this instantly."""
LATER = ArbitraryPos.LATER
"""A value representing the position of the iterator when the final resolutions are done. Usually resolved when exiting from `with` statements."""

class Token:
    """
    A class representing a position in a string.
    It can store more tokens inside it as subtokens.

    `with` statement syntax:

    ```
    with Token("foo"):
        Token("bar")                    # Automatically added as the "foo" token's subtoken.
        Token("baz", auto_append=False) # Don't add.
        return Result("data")           # Automatically uses the "foo" token as the token.

    with Token("foo") token:
        # Using with statements automatically sets the end_pos.
        # (If it was omitted.)
        take(5)
        token.get_pos() # (0, 5)
    ```
    """
    def __init__(
            self,
            token_type: str,
            start_pos: int | Pos = HERE,
            end_pos: int | Pos | None = None,
            *,
            subtokens: list[Token] = [],
            auto_append: bool = True
        ) -> None:
        self.token_type: str = token_type
        """The type of the token."""
        self.start_pos: Pos = Pos(start_pos).resolve_initial()
        """The left edge of the token."""
        self.end_pos: Pos | None = None if end_pos is None else (Pos(end_pos).resolve_initial())
        """The right edge of the token. Optional."""
        self.subtokens: list[Token] = subtokens
        """The tokens this token contains."""
        if auto_append and _current_token is not None:
            self.append_as_subtoken()

    def resolve(self) -> None:
        """Do final resolutions on the position. Automatically called when exiting a `with` statement."""
        self.start_pos = self.start_pos.resolve_final()
        if self.end_pos is not None:
            self.end_pos = self.end_pos.resolve_final()

    def get_pos(self) -> tuple[int, int | None]:
        """Get the positions as integers. Raises an `UnresolvedError` if the position isn't resolved yet."""
        return self.start_pos.get(), None if self.end_pos is None else self.end_pos.get()

    def __repr__(self) -> str:
        """Raises an `UnresolvedError` if the position isn't resolved yet."""
        start_pos, end_pos = self.get_pos()
        return (
            (
                f"<{self.token_type}: {str(start_pos)}>" if end_pos is None else
                f"<{self.token_type}: {str(start_pos)}..{str(end_pos)}>"
            ) +
            (
                (
                    " [ " +
                    (
                        ", ".join([repr(t) for t in self.subtokens])
                    ) +
                    " ]"
                ) if self.subtokens else ""
            )
        )

    def __enter__(self) -> Token:
        _push_token(self)
        if self.end_pos is None:
            self.end_pos = LATER
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_inst: Optional[BaseException], exc_traceback: Optional[TracebackType]) -> Literal[False]:
        """Automatically resolves the position."""
        _pop_token()
        self.resolve()
        return False

    def append_as_subtoken(self) -> Token:
        """Adds this token as a subtoken of the currently active token. Returns self."""
        assert _current_token is not None
        _current_token.subtokens.append(self)
        return self

class Result(Generic[_T]):
    """
    A combination of a Token and some object used as the return data.

    If you put the token in a with statement, you don't need to specify it in the __init__ function.

    Automatic:
    ```
    with Token("foo"):
        # do some stuff
        return Result("data")   # Automatically uses the "foo" token as the token.
    ```

    Manual:
    ```
    Token("foo", HERE, LATER)
    # do some stuff
    return Result("data", token)
    ```
    """
    def __init__(self, data: _T, token: Token | None = None) -> None:
        """
        If `token` is omitted, uses the currently active token. (The token in the latest `with` statement.)
        """
        self.token: Token
        if token is None:
            assert _current_token is not None
            self.token = _current_token
            # since this token is stored as a reference of sorts, the position will get updated after it exits the scope of the `with` statement.
        else:
            self.token = token
        self.data: _T = data

    def __repr__(self) -> str:
        return repr(self.token)

    def append_as_subtoken(self) -> Result:
        """Adds the result's token as a subtoken of the currently active token. Returns self."""
        assert _current_token is not None
        _current_token.subtokens.append(self.token)
        return self


_prev_token: list[Token] = []
_current_token: None | Token = None

def _push_token(token: Token) -> None:
    global _prev_token
    global _current_token
    if _current_token:
        _prev_token.append(_current_token)
    _current_token = token

def _pop_token() -> None:
    global _prev_token
    global _current_token
    if _prev_token:
        _current_token = _prev_token[-1]
        _prev_token.pop()
    else:
        _current_token = None


_prev_error: list[BaseParseError] = []
_current_error: None | BaseParseError = None

def _push_error(error: BaseParseError) -> None:
    global _prev_error
    global _current_error
    if _current_error:
        _prev_error.append(_current_error)
    _current_error = error

def _pop_error() -> None:
    global _prev_error
    global _current_error
    if _prev_error:
        _current_error = _prev_error[-1]
        _prev_error.pop()
    else:
        _current_error = None


class BaseParseError(Exception):
    """
    Base class for `ParseError` and `FatalParseError`. Use those instead.
    """
    def __init__(self, message: str | None, pos: int | Pos | None = HERE) -> None:
        """
        If the `pos` parameter is omitted, it uses the current position of the active iterator. If it's set to None, the error will not have a position.
        """
        super().__init__(message)
        self.message: str | None = message
        """The message of the error."""
        self.pos: Pos | None = None if pos is None else Pos(pos).resolve_initial()
        """The position the error occured at."""
        self._replace: bool = False
        """Whether to replace all errors, fatal or not. For use with `with` statements."""
        self._preserve_pos: bool = True
        """Whether to use the position of the raised error as this error's position. For use with `with` statements."""
        self._preserve_message: bool = False
        """Whether to use the message of the raised error as this error's message. For use with `with` statements."""

    def set_message(self, message: str | None) -> BaseParseError:
        """Changes the message of the error. Returns self."""
        self.message = message
        return self

    def set_pos(self, pos: int | Pos | None = HERE) -> BaseParseError:
        """Changes the message of the error. Returns self."""
        self.pos = None if pos is None else Pos(pos).resolve_initial()
        return self

    def replace(self, p_replace=True) -> BaseParseError:
        """
        Marks this error to replace all errors, fatal or not. For use with `with` statements.

        ```
        with ParseError("foo"):
            FatalParseError("bar").throw()
        # the "bar" fatal error will be received, because it has more priority.

        with ParseError("foo").replace():
            FatalParseError("bar").throw()
        # the "foo" error will be received.
        ```
        """
        self._replace = p_replace
        return self

    def preserve_pos(self, preserve=True) -> BaseParseError:
        """
        Use the position of the raised error as this error's position. For use with `with` statements.

        Preserving the position is the default behavior. Supply False as the first parameter to disable it instead.

        ```
        with ParseError("foo", 0):
            ParseError("bar", 2).throw()
        # "foo" will be received with a position of 2.

        with ParseError("foo", 0).preserve_pos(False):
            ParseError("bar", 2).throw()
        # "foo" will be received with a position of 0.
        ```
        """
        self._preserve_pos = preserve
        return self

    def preserve_message(self, preserve=True) -> BaseParseError:
        """
        Use the message of the raised error as this error's message. For use with `with` statements.

        More useful when used with `preserve_pos(False)`

        ```
        with ParseError("foo"):
            ParseError("bar").throw()
        # "foo" will be received.

        with ParseError("foo").preserve_message():
            ParseError("bar").throw()
        # "bar" will be received.
        ```
        """
        self._preserve_message = preserve
        return self

    def resolve(self) -> None:
        """Do final resolutions on the position. Automatically called when exiting a `with` statement."""
        if self.pos is not None:
            self.pos = self.pos.resolve_final()

    def __enter__(self) -> None:
        _push_error(self)

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_inst: Optional[BaseException], exc_traceback: Optional[TracebackType]) -> Literal[False]:
        _pop_error()
        self.resolve()
        # Only catch non fatal ParseErrors if replace is disabled.
        if self._replace or (exc_type is not None and issubclass(exc_type, ParseError)):
            assert isinstance(exc_inst, ParseError)
            if self._preserve_pos:
                self.set_pos(exc_inst.pos)
                self.resolve()
            if self._preserve_message:
                self.set_message(exc_inst.message)
            raise self.with_traceback(exc_traceback) from None
        return False

    def __repr__(self) -> str:
        if self.message is None:
            if self.pos is None:
                return f"Unknown error while parsing string."
            else:
                return f"Unknown error while parsing string. (at position {self.pos.get()})"
        else:
            if self.pos is None:
                return f"{self.message}"
            else:
                return f"{self.message} (at position {self.pos.get()})"

    def throw(self) -> None:
        """Raises the error. Using this function prevents language servers from marking further code as unreachable. Sometimes that's better, sometimes it's not."""
        raise self

class ParseError(BaseParseError):
    """
    Raise using the `throw()` function or the `ParseError.throw()` method to avoid further code from being marked as unreachable.

    For mismatches. Will get catched by context managers like `optional()`

    For example, if you are making a parser for quoted strings, the initial `"` should raise a ParseError.

    Use with `with` statements to change existing ParseErrors' messages. FatalParseErrors will be ignored.
    ```
    with ParseError("hello"):
        ParseError("foo").throw()
    # The exception will be a ParseError with the message "hello"
    ```
    """
    def fatalized(self) -> FatalParseError:
        """
        Returns a fatal version of this exception.

        Put a FatalParseError in a `with` statement to catch and re-raise exceptions instead.
        ```
        with FatalParseError("hello"):
            raise ParseError("foo")
        # The exception will be a FatalParseError with the message "hello"
        ```
        """
        return FatalParseError(self.message, self.pos)

class FatalParseError(BaseParseError):
    """
    Raise using the `throw()` function or the `FatalParseError.throw()` method to avoid further code from being marked as unreachable.

    For syntactical errors. Will not get catched by context managers like `optional()`

    For example, if you are making a parser for quoted strings, invalid escape sequences should raise a FatalParseError.

    Use with `with` statements to change existing ParseErrors into FatalParseErrors. FatalParseErrors will be ignored.
    ```
    with FatalParseError("hello"):
        raise ParseError("foo")
    # The exception will be a FatalParseError with the message "hello"
    """
    def unfatalized(self) -> ParseError:
        """
        Returns a non fatal version of this exception.
        """
        return ParseError(self.message, self.pos)

def throw() -> None:
    """Throws the currently active error."""
    assert _current_error is not None
    _current_error.throw()


_prev_si: list[StringIterator] = []
_current_si: None | StringIterator = None

def _push_si(si: StringIterator) -> None:
    global _prev_si
    global _current_si
    if _current_si:
        _prev_si.append(_current_si)
    _current_si = si

def _pop_si() -> None:
    global _prev_si
    global _current_si
    if _prev_si:
        _current_si = _prev_si[-1]
        _prev_si.pop()
    else:
        _current_si = None

class StringIterator:
    """
    Class for iterating over a string.

    Use with `with` statements.

    ```
    with StringIterator("test"):
        result = example_parser()
        result.data
    ```

    With statements return self:
    ```
    with StringIterator("test") as si:
        len(si)
    ```
    """
    def __init__(self, data: str, start_pos: int = 0) -> None:
        self._data: str = data
        """The full data."""
        self._pos: int = start_pos
        """The position of the iterator."""

    def __enter__(self) -> StringIterator:
        _push_si(self)
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_inst: Optional[BaseException], exc_traceback: Optional[TracebackType]) -> Literal[False]:
        _pop_si()
        return False

    def get_len(self) -> int:
        """Retrieves the length of the data. Same as `__len__()`"""
        return len(self._data)

    def __len__(self) -> int:
        """Retrieves the length of the data. Same as `get_len()`"""
        return len(self._data)

    def get_pos(self) -> int:
        """Gets the position of the iterator."""
        return self._pos

    def set_pos(self, pos: int | Pos) -> None:
        """Goes to the specified position."""
        self._pos = min(Pos(pos).resolve_all(self).get(), len(self._data))

    def move(self, amount: int) -> None:
        """Moves the iterator by the specified amount of characters."""
        self._pos = min(self._pos+amount, len(self._data))

    def get_data(self, start: int | Pos = 0, end: int | Pos = EOF) -> str:
        """Retrieves the characters in the specified range."""
        start = Pos(start).resolve_all(self).get()
        end = Pos(end).resolve_all(self).get()
        return self._data[start:end]

    def take(self, amount: int) -> str:
        """Consumes and retrieves the specified amount of characters. If there aren't enough characters, gets as many as it can."""
        out = self._data[self._pos:self._pos+amount]
        self._pos = min(self._pos+amount, len(self._data))
        return out

    def peek(self, amount: int) -> str:
        """Retrieves the specified amount of characters without consuming. If there aren't enough characters, gets as many as it can."""
        return self._data[self._pos:self._pos+amount]

    def has_chars(self, amount: int) -> bool:
        """Whether there are at least that many characters left."""
        return self._pos+amount <= len(self._data)

    def is_eof(self) -> bool:
        """Whether the end of the input has been reached. The opposite of `__bool__()`"""
        return self._pos >= len(self._data)

    def __bool__(self) -> bool:
        """Whether there are any characters left. The opposite of `is_eof()`"""
        return self._pos < len(self._data)

    def peek_regex(self, pattern: str | re.Pattern, flags: int | re.RegexFlag = 0) -> re.Match[str]:
        """Matches the regex expression at the current position and returns the Match. Does not consume."""
        m = re.compile(pattern, flags).match(self._data, self._pos)
        if m is None:
            raise ParseError("Regex did not match.")
        return m

    def take_regex(self, pattern: str | re.Pattern, flags: int | re.RegexFlag = 0) -> re.Match[str]:
        """Matches the regex expression at the current position and returns the Match. Consumes the matched string."""
        m = re.compile(pattern, flags).match(self._data, self._pos)
        if m is None:
            raise ParseError("Regex did not match.")
        self._pos = m.end()
        return m

def iterator_set() -> bool:
    """
    Tests whether this is in the scope of a StringIterator's `with` statement.

    ```
    iterator_set()          # will return False
    with StringIterator("hey"):
        iterator_set()      # will return True
        assert iterator_set()
    ```
    """
    return _current_si is not None

def get_len() -> int:
    """Retrieves the length of the data in the active iterator."""
    assert _current_si is not None
    return _current_si.get_len()

def get_pos() -> int:
    """Gets the position of the active iterator."""
    assert _current_si is not None
    return _current_si.get_pos()

def set_pos(pos: int | Pos) -> None:
    """Goes to the specified position."""
    assert _current_si is not None
    return _current_si.set_pos(pos)

def move(amount: int) -> None:
    """Skips the specified amount of characters."""
    assert _current_si is not None
    return _current_si.move(amount)

def get_data(start: int | Pos = 0, end: int | Pos = EOF) -> str:
    """Retrieves the characters in the specified range."""
    assert _current_si is not None
    return _current_si.get_data(start, end)

def take(amount: int) -> str:
    """Consumes and retrieves the specified amount of characters. If there aren't enough characters, gets as many as it can."""
    assert _current_si is not None
    return _current_si.take(amount)

def peek(amount: int) -> str:
    """Retrieves the specified amount of characters without consuming. If there aren't enough characters, gets as many as it can."""
    assert _current_si is not None
    return _current_si.peek(amount)

def has_chars(amount: int) -> bool:
    """Whether there are at least that many characters left in the current iterator."""
    assert _current_si is not None
    return _current_si.has_chars(amount)

def is_eof() -> bool:
    """Whether the end of the iterator has been reached."""
    assert _current_si is not None
    return _current_si.is_eof()

def peek_regex(pattern: str | re.Pattern, flags: int | re.RegexFlag = 0) -> re.Match[str]:
    """Matches the regex expression at the current position and returns the Match. Does not consume."""
    assert _current_si is not None
    return _current_si.peek_regex(pattern, flags)

def take_regex(pattern: str | re.Pattern, flags: int | re.RegexFlag = 0) -> re.Match[str]:
    """Matches the regex expression at the current position and returns the Match. Consumes the matched string."""
    assert _current_si is not None
    return _current_si.take_regex(pattern, flags)


# Context managers

@contextmanager
def checkpoint() -> Generator[int, None, None]:
    """
    If a ParseError or a FatalParseError is raised, reverts to the starting position, otherwise does nothing.

    Does not catch the error. Use `optional()` for that.

    Returns the current position.
    """
    assert _current_si is not None
    saved_pos = get_pos()
    try:
        yield saved_pos
    except BaseParseError:
        set_pos(saved_pos)
        raise

@contextmanager
def lookahead() -> Generator[None, None, None]:
    """Reverts to the starting position after finishing, regardless of whether it was successful or not. Does not catch errors."""
    assert _current_si is not None
    saved_pos = get_pos()
    try:
        yield
    finally:
        set_pos(saved_pos)

@contextmanager
def negative_lookahead() -> Generator[None, None, None]:
    """Reverts to the starting position after finishing, regardless of whether it was successful or not. Catches all ParseErrors. Throws a ParseError if no error was thrown."""
    assert _current_si is not None
    saved_pos = get_pos()
    try:
        yield
    except ParseError:
        pass
        # don't re-raise
    else:
        ParseError(None, saved_pos).throw()
    finally:
        set_pos(saved_pos)

@contextmanager
def optional() -> Generator[None, None, None]:
    """If a non fatal parse error is raised, catches it and reverts to the starting position."""
    assert _current_si is not None
    saved_pos = get_pos()
    try:
        yield
    except ParseError:
        set_pos(saved_pos)
        # don't re-raise
    except:
        set_pos(saved_pos)
        raise

class OneOfFinishedException(Exception):
    pass

@contextmanager
def one() -> Generator[None, None, None]:
    """Raises a OneOfFinishedException if the contents don't raise any exceptions. Use with `oneof()`."""
    assert _current_si is not None
    saved_pos = get_pos()
    try:
        yield
    except ParseError:
        set_pos(saved_pos)
        # don't re-raise
    except:
        set_pos(saved_pos)
        raise
    else:
        raise OneOfFinishedException from None

@contextmanager
def oneof() -> Generator[None, None, None]:
    """
    Catches OneOfFinishedExceptions. Use with `one()`.

    ```
    with oneof():
        with one():
            literal("foo")
        with one():
            literal("bar")
        with one():
            literal("baz")
    ```
    """
    try:
        yield
    except OneOfFinishedException:
        pass


# General use parsers

def literal(lit: str, case_sensitive: bool = True) -> None:
    """Matches the input exactly."""
    with checkpoint() as startpos:
        if case_sensitive:
            if take(len(lit)) != lit:
                ParseError(None, startpos).throw()
        else:
            if take(len(lit)).lower() != lit.lower():
                ParseError(None, startpos).throw()

def nl() -> None:
    """Matches a newline sequence. (CRLF or LF / NL)"""
    with checkpoint() as startpos:
        if take(1) != "\n" and take(2) != "\r\n":
            ParseError("Expected a newline sequence.", startpos).throw()

def ws() -> None:
    """Matches one whitespace."""
    with checkpoint() as startpos:
        if take(1) not in WHITESPACES:
            ParseError("Expected whitespace.", startpos).throw()

def ws0() -> None:
    """Skips as many whitespaces as it can. Minimum of 0."""
    while peek(1) in WHITESPACES:
        move(1)

def ws1() -> None:
    """Skips as many whitespaces as it can. Minimum of 1."""
    ws()
    ws0()

def wsrange(minimum: int = 0, maximum: int | None = None) -> None:
    """Matches any number of whitespaces. If `maximum` is set to None, it has no limit."""
    with checkpoint() as startpos:
        i = 0
        # required whitespaces
        while i < minimum:
            i += 1
            if take(1) not in WHITESPACES:
                if minimum <= 1:
                    ParseError(f"Expected whitespace.", startpos).throw()
                else:
                    ParseError(f"Expected at least {minimum} whitespaces.", startpos).throw()
        # optional whitespaces
        if maximum is None:
            while peek(1) in WHITESPACES:
                move(1)
        else:
            while i < maximum and peek(1) in WHITESPACES:
                i += 1
                move(1)

def oneof_list(*parsers: Callable[[], Any]) -> None:
    """
    Tries the parsers in turn until one succeeds.
    """
    with checkpoint() as startpos:
        for parser in parsers:
            with optional():
                parser()
                return
        else:
            raise ParseError(None, startpos)

def oneof_list_return(*parsers: Callable[[], _T]) -> _T:
    """
    Tries the parsers in turn until one succeeds.

    Returns the return value of whichever function succeeded.
    The return types of all the functions should be the same.
    """
    with checkpoint() as startpos:
        for parser in parsers:
            with optional():
                return parser()
        else:
            raise ParseError(None, startpos)

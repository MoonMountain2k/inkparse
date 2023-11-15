"""
Classes for parsing.

`with` statement based syntax. Basically everything is done using `with` statements.
"""

from __future__ import annotations
from typing import Literal, Type, Optional, TypeVar, Generic, Final, Callable, Any, Sequence
from types import TracebackType

from contextlib import contextmanager

WHITESPACES: Final[list[str]] = [" ", "\t", "\n", "\r", "\f"]

class Token:
    """
    A class representing a position in a string.
    It can store more tokens inside it.

    `with` statement syntax:

    ```
    with Token("foo"):
        Token("bar").add()      # Adds it as the "foo" token's subtoken.
        return Result("data")   # Automatically uses the "foo" token as the token.
        # The position of the token is automatically set as well.
        # The starting position gets set when it first enters, and the ending position gets set after it exits

    with Token("foo") as output:
        return output
    ```
    """
    def __init__(self, token_type: str, pos: tuple[int, int | None] | None = None, *, subtokens: list[Token] = []) -> None:
        self.pos: tuple[int, int | None] | None = pos
        """
        A position range that contains the whole token.

        Positions are between each character, starting from before the first character, at 0.

        Type: `(int, int)`, `(int, None)`, `None`.
        """
        self.token_type: str = token_type
        """The type of the token."""
        self.subtokens: list[Token] = subtokens
        """The tokens this token contains. Named tokens are not included."""

    def __repr__(self) -> str:
        return (
            self.token_type +
            (
                (
                    " <" +
                    str(self.pos[0]) +
                    (
                        ( ".." + str(self.pos[1]) ) if self.pos[1] is not None else ""
                    ) +
                    ">"
                ) if self.pos is not None else ""
            ) +
            (
                (
                    " [" +
                    (
                        ", ".join([repr(t) for t in self.subtokens])
                    ) +
                    "]"
                ) if self.subtokens else ""
            )
        )

    def __enter__(self) -> Token:
        _push_token(self)
        self.pos = (getpos(), None)
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_inst: Optional[BaseException], exc_traceback: Optional[TracebackType]) -> Literal[False]:
        _pop_token()
        assert self.pos is not None
        self.pos = (self.pos[0], getpos())
        return False

    def __bool__(self) -> Literal[True]:
        return True

    def append_subtoken(self) -> Token:
        """Adds this token as a subtoken of the currently active token."""
        assert _current_token
        _current_token.subtokens.append(self)
        return self

_T = TypeVar("_T")

class Result(Generic[_T]):
    def __init__(self, data: _T, token: Token | None = None) -> None:
        """
        If `token` is omitted, uses the currently active token. (The token in the latest `with` statement.)

        Keep in mind that the position of the token only gets updated after you leave the scope of the `with` statement.
        """
        self.token: Token
        if token is None:
            assert _current_token
            self.token = _current_token
            # since this token is stored as a reference of sorts, the position will get updated after it exits the scope of the `with` statement.
        else:
            self.token = token
        self.data: _T = data

    def append_subtoken(self) -> Result:
        """Adds the result's token as a subtoken of the currently active token."""
        assert _current_token
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



class ParseError(Exception):
    def __init__(self, message: str | None, pos: int | None = None) -> None:
        super().__init__(message)
        self.message: str | None = message
        self.pos: int
        if pos is None:
            assert _current_si
            self.pos = _current_si.pos
        else:
            self.pos = pos

    def __repr__(self) -> str:
        if self.message is None:
            return f"Unknown error at position {self.pos}."
        else:
            return f"{self.message} at position {self.pos}."

    def fatalize(self) -> FatalParseError:
        return FatalParseError(self.message, self.pos)

class FatalParseError(Exception):
    def __init__(self, message: str | None, pos: int | None = None) -> None:
        super().__init__(message)
        self.message: str | None = message
        self.pos: int
        if pos is None:
            assert _current_si
            self.pos = _current_si.pos
        else:
            self.pos = pos

    def __repr__(self) -> str:
        if self.message is None:
            return f"Unknown error at position {self.pos}."
        else:
            return f"{self.message} at position {self.pos}."



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
        ows()        # optional whitespace
        literal("t") # a literal
        # ...
    ```
    """
    def __init__(self, data: str, starting_pos: int = 0) -> None:
        self.data: str = data
        """The string to iterate on."""
        self.pos: int = starting_pos
        """Where the cursor is in the string. Positions are between each character, starting from before the first character, at 0."""

    def __enter__(self) -> StringIterator:
        _push_si(self)
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_inst: Optional[BaseException], exc_traceback: Optional[TracebackType]) -> Literal[False]:
        _pop_si()
        return False

    def get_chars(self, amount: int) -> str:
        """Consumes and retrieves the specified amount of characters. If there aren't enough characters, gets as many as it can."""
        out = self.data[self.pos:self.pos+amount]
        self.pos = min(self.pos+amount, len(self.data))
        return out

    def has_chars(self, amount: int) -> bool:
        """Whether there are at least that many characters left."""
        return self.pos+amount <= len(self.data)

    def __bool__(self) -> Literal[True]:
        return True

class SavedPosition:
    def __init__(self, pos: int):
        self.pos = pos

    def token(self, token_type: str, *, subtokens: list[Token] = []) -> Token:
        assert _current_si, "Got token from SavedPosition without string iterator."
        return Token(token_type, (self.pos, _current_si.pos), subtokens=subtokens)

    def result(self, token_type: str, data: _T, *, subtokens: list[Token] = []) -> Result[_T]:
        assert _current_si, "Got result from SavedPosition without string iterator."
        return Result(data, Token(token_type, (self.pos, _current_si.pos), subtokens=subtokens))

    def error(self, message: str | None = None) -> ParseError:
        return ParseError(message, self.pos)

    def fatal_error(self, message: str | None = None) -> FatalParseError:
        return FatalParseError(message, self.pos)

@contextmanager
def checkpoint():
    """
    If an exception is thrown, reverts to the starting position, otherwise does nothing.

    Does not catch the exception. Use `optional()` for that.
    """
    assert _current_si
    saved_pos = _current_si.pos
    try:
        yield SavedPosition(saved_pos)
    except ParseError:
        _current_si.pos = saved_pos
        raise
    except FatalParseError:
        _current_si.pos = saved_pos
        raise

@contextmanager
def lookahead():
    """Reverts to the starting position, regardless of whether it finished successfully or not. Does not catch errors."""
    assert _current_si
    saved_pos = _current_si.pos
    try:
        yield
    finally:
        _current_si.pos = saved_pos

@contextmanager
def error_message(msg: str):
    """Changes the message of thrown `ParseError`s. `FatalParseError`s are unaffected."""
    try:
        yield
    except ParseError as e:
        raise ParseError(msg, e.pos)

@contextmanager
def fatalize_error(msg: str):
    """Changes the message of thrown `ParseError`s and elevates it to `FatalParseError`s. `FatalParseError`s are unaffected."""
    try:
        yield
    except ParseError as e:
        raise FatalParseError(msg, e.pos)

@contextmanager
def optional():
    """If a non fatal parse error is thrown, catches it and reverts to the starting position."""
    assert _current_si
    saved_pos = _current_si.pos
    try:
        yield
    except ParseError:
        _current_si.pos = saved_pos
        # don't reraise

AT: Final[bool] = True
"""
Variable that's always true.

For writing returns breaks and continues without mypy thinking further code is unreachable.

It's ugly, but it works.

```
with optional():
    literal("foo")
    if AT: return Result("blablabla")
# normally mypy will mark any further code as unreachable even though it's not
# because `literal("foo")` can fail and the `optional()` can catch it.
literal("bar") # not unreachable thanks to AT
```
"""

def raise_if_eof() -> None:
    """Throw ParseError if EOF is reached."""
    assert _current_si
    if _current_si.pos >= len(_current_si.data):
        raise ParseError(None, len(_current_si.data))

def raise_if_not_enough(amount: int) -> None:
    """Throw ParseError if there aren't enough characters left."""
    assert _current_si
    if not _current_si.has_chars(amount):
        raise ParseError(None, len(_current_si.data))

def getpos() -> int:
    """Gets the position of the iterator."""
    assert _current_si
    return _current_si.pos

def goto(pos: int | SavedPosition) -> None:
    """Moves the iterator to the specified position."""
    assert _current_si
    if isinstance(pos, SavedPosition):
        _current_si.pos = min(pos.pos, len(_current_si.data))
    else:
        _current_si.pos = min(pos, len(_current_si.data))

def move(amount: int) -> None:
    """Moves the iterator by the specified amount. (i.e. skips the specified amount of characters.)"""
    assert _current_si
    _current_si.pos = min(_current_si.pos+amount, len(_current_si.data))

def get_chars(amount: int) -> str:
    """Consumes and retrieves the specified amount of characters. If there aren't enough characters, gets as many as it can."""
    assert _current_si
    return _current_si.get_chars(amount)

def has_chars(amount: int) -> bool:
    """Whether there are at least that many characters left."""
    assert _current_si
    return _current_si.has_chars(amount)

LiteralType = str | Callable[[], Any] | Sequence["LiteralType"]

def strict_literal(*literals: LiteralType) -> None:
    """
    If the parameter is a string, matches it exacly. (Case sensitive.)

    If it's a callable, runs the function. (Case sensitive.)

    If it's a list, all items must match in sequence.

    Multiple parameters are treated as if it's a list. Nested lists are allowed.
    """
    assert _current_si
    with checkpoint() as start:
        for lit in literals:
            if isinstance(lit, str):
                if get_chars(len(lit)) != lit:
                    # raise start.error(f'Expected literal "{lit}"')
                    raise start.error()
            elif callable(lit):
                lit()
            else:
                strict_literal(**lit)

def literal(*literals: LiteralType) -> None:
    """
    If the parameter is a string, matches it exacly. (Not case sensitive.)

    If it's a callable, runs the function. (Case sensitive.)

    If it's a list, all items must match in sequence.

    Multiple parameters are treated as if it's a list. Nested lists are allowed.
    """
    assert _current_si
    with checkpoint() as start:
        for lit in literals:
            if isinstance(lit, str):
                if get_chars(len(lit)).lower() != lit.lower():
                    # raise start.error(f'Expected literal "{lit}"')
                    raise start.error()
            elif callable(lit):
                lit()
            else:
                literal(**lit)

def strict_one_of(literals: list[LiteralType]):
    """Runs `strict_literal()` until one matches. (Case sensitive.)"""
    assert _current_si
    with checkpoint() as start:
        for lit in literals:
            with optional():
                strict_literal(lit)
                if AT: return
        else:
            raise start.error()

def one_of(literals: list[LiteralType]):
    """Runs `literal()` until one matches. (Not case sensitive.)"""
    assert _current_si
    with checkpoint() as start:
        for lit in literals:
            with optional():
                literal(lit)
                if AT: return
        else:
            raise start.error()

def ws0():
    """Skips the max amount of whitespaces. Minimum of 0."""
    assert _current_si
    while _current_si.data[_current_si.pos] in WHITESPACES:
        _current_si.pos = min(_current_si.pos+1, len(_current_si.data))

def ws1():
    """Skips the max amount of whitespaces. Minimum of 1."""
    assert _current_si
    with checkpoint() as start:
        if get_chars(1) not in WHITESPACES:
            raise start.error("Expected whitespace")
    ws0()
"""
Classes and functions for parsing strings.
"""

from __future__ import annotations
from typing import Literal, TypeVar, Generic, SupportsIndex

from contextlib import contextmanager
from collections.abc import Iterator
import re

import inkparse.const as const
from inkparse.expr import (
    Expr,
)

_T = TypeVar("_T")

class ParseError(Exception):
    def __init__(self, msg: str, pos: int, src: str) -> None:
        super().__init__(msg)
        self.src = src
        
        note: list[str] = []
        pos = min(pos, len(src))
        # should still work with CRLF
        line = src.count("\n", 0, pos) + 1
        column = pos - src.rfind("\n", 0, pos) # magically works even when it returns -1
        note.append(f"At position {pos} (line {line}, column {column})")
        lines = src.splitlines()
        if len(lines) > line-1:
            line_str = lines[line-1]
            if len(line_str) >= column:
                if column <= 20:
                    note.append(f"{line_str[:40]}\n{' '*(column-1)}^")
                else:
                    note.append(f"{line_str[(column-20):(column+20)]}\n{' '*20}^")
        self.add_note("\n".join(note))
    
    def add_pos_note(self, msg: str, pos: int) -> None:
        note: list[str] = [msg]
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

class StringIterator:
    def __init__(self, src: str, starting_pos: int = 0) -> None:
        self.src: str = src
        self.pos: int = starting_pos

    def __len__(self) -> int:
        return len(self.src)

    def __getitem__(self, key: SupportsIndex | slice) -> str:
        return self.src[key]

    def move_and_get(self, amount: int) -> tuple[int, int]:
        """Moves the iterator by the specified amount of characters. Returns a position range."""
        start_pos = self.pos
        self.pos += amount
        return (start_pos, self.pos)

    def goto_and_get(self, pos: int) -> tuple[int, int]:
        """Moves the iterator to the position. Returns a position range."""
        start_pos = self.pos
        self.pos = pos
        return (start_pos, self.pos)

    def has_chars(self, amount: int) -> bool:
        """Whether there are at least that many characters left."""
        return self.pos+amount <= len(self.src)

    def is_eof(self) -> bool:
        """Whether the end of the input has been reached. The opposite of `__bool__()`"""
        return self.pos >= len(self.src)

    def __bool__(self) -> bool:
        """Whether there are any characters left. The opposite of `is_eof()`"""
        return self.pos < len(self.src)

    def peek(self, amount: int) -> str | None:
        """Retrieves the specified amount of characters without consuming."""
        if not self.has_chars(amount):
            return None
        return self.src[self.pos:self.pos+amount]

    def take(self, amount: int) -> str | None:
        """Consumes and retrieves the specified amount of characters."""
        if not self.has_chars(amount):
            return None
        start_pos = self.pos
        self.pos += amount
        return self.src[start_pos:self.pos]

    def error(self, msg: str) -> ParseError:
        """Creates a ParseError at this iterator's position."""
        return ParseError(msg, self.pos, self.src)

    def error_note(self, msg: str, *notes: tuple[str, int]) -> ParseError:
        """Creates a ParseError at this iterator's position, with positioned notes."""
        err = ParseError(msg, self.pos, self.src)
        for note, pos in notes:
            err.add_pos_note(note, pos)
        return err
    
    @contextmanager
    def checkpoint(self) -> Iterator[Checkpoint]:
        """Same as `StringIterator.__call__()`"""
        ckpt = Checkpoint(self)
        try:
            yield ckpt
        except:
            ckpt.rollback()
            raise
        finally:
            if not ckpt.committed:
                ckpt.rollback()
    
    @contextmanager
    def __call__(self) -> Iterator[Checkpoint]:
        """Same as `StringIterator.checkpoint()`"""
        ckpt = Checkpoint(self)
        try:
            yield ckpt
        except:
            ckpt.rollback()
            raise
        finally:
            if not ckpt.committed:
                ckpt.rollback()

    def literal(self, value: str, *, case_sensitive: bool = True) -> bool:
        """
        Attempts to match the given string.

        Advances the position if it matched.

        Returns a bool indicating whether or not the string was matched.
        """
        if not self.has_chars(len(value)):
            return False
        if (case_sensitive) and (self.src[self.pos:self.pos+len(value)] == value) or (not case_sensitive) and (self.src[self.pos:self.pos+len(value)].lower() == value.lower()):
            self.pos += len(value)
            return True
        else:
            return False

    def regex(self, pattern: str | re.Pattern, flags: int | re.RegexFlag = 0) -> re.Match[str] | None:
        """
        Attempts to match the regex.
        
        Advances the position if it matched.
        """
        m = re.compile(pattern, flags).match(self.src, self.pos)
        if m is not None:
            self.pos = m.end()
        return m

    def literal_any_of(self, *values: str, case_sensitive: bool = True) -> bool:
        """
        Attempts to match any of the given strings, starting from the first.

        Advances the position if it matched.

        Returns a bool indicating whether or not any of the string were matched.
        """
        for i, pattern in enumerate(values):
            if not self.has_chars(len(pattern)):
                continue
            if (case_sensitive) and (self.src[self.pos:self.pos+len(pattern)] == pattern) or (not case_sensitive) and (self.src[self.pos:self.pos+len(pattern)].lower() == pattern.lower()):
                self.pos += len(pattern)
                return True
        return False
    
    def ws0(self) -> None:
        """Matches one or more whitespaces."""
        while self.peek(1) in const.WHITESPACES:
            self.pos += 1
    
    def ws1(self) -> bool:
        """Matches one or more whitespaces. Returns a bool indicating whether or not the first whitespace was found."""
        if self.peek(1) not in const.WHITESPACES:
            return False
        self.pos += 1
        self.ws0()
        return True

class Checkpoint:
    """
    Create using `StringIterator.checkpoint()` or `StringIterator.__call__()`
    """
    def __init__(self, si: StringIterator) -> None:
        """
        Create using `StringIterator.checkpoint()` or `StringIterator.__call__()` instead.
        """
        self.pos: int = si.pos
        self.si: StringIterator = si
        self.subtokens: list[Token] = []
        self.committed: bool = False

    def commit(self) -> None:
        """Commits."""
        self.committed = True

    def rollback(self) -> None:
        """Rolls back the iterator to the starting position."""
        self.si.pos = self.pos

    def add(self, token: Token | None) -> Token | None:
        """
        Adds a token/result into the resulting token's subtokens.
        """
        if token is not None:
            self.subtokens.append(token)
        return token

    def get_range(self) -> tuple[int, int]:
        return (self.pos, self.si.pos)

    def get_token(self, token_type: str | None) -> Token:
        """Returns a Token object without committing."""
        return Token(token_type, self.get_range(), subtokens=self.subtokens)

    def get_result(self, data: _T, token_type: str | None) -> Result[_T]:
        """Returns a Result object without committing."""
        return Result(data, token_type, self.get_range(), subtokens=self.subtokens)
    
    def get_string(self) -> str:
        return self.si.src[self.pos : self.si.pos]

    def token(self, token_type: str | None = None) -> Token:
        """Commits and returns a Token object."""
        self.committed = True
        return Token(token_type, self.get_range(), subtokens=self.subtokens)

    def result(self, data: _T, token_type: str | None = None) -> Result[_T]:
        """Commits and returns a Result object."""
        self.committed = True
        return Result(data, token_type, self.get_range(), subtokens=self.subtokens)

    def error(self, msg: str) -> ParseError:
        """Creates a ParseError at the checkpoint's starting position. Only raises if `token` is None."""
        return ParseError(msg, self.pos, self.si.src)

    def error_note(self, msg: str, *notes: tuple[str, int]) -> ParseError:
        """Creates a ParseError at the checkpoint's starting position. Only raises if `token` is None."""
        err = ParseError(msg, self.pos, self.si.src)
        for note, pos in notes:
            err.add_pos_note(note, pos)
        return err

class Token:
    def __init__(self, token_type: str | None = None, pos: tuple[int, int] | None = None, subtokens: list[Token] = []) -> None:
        self.type: str | None = token_type
        self.pos: tuple[int, int] | None = pos
        self.subtokens: list[Token] = subtokens

    def with_type(self, token_type: str | None) -> Token:
        self.type = token_type
        return self

    def with_pos(self, pos: tuple[int, int] | None) -> Token:
        self.pos = pos
        return self

    def with_subtokens(self, subtokens: list[Token]) -> Token:
        self.subtokens = subtokens
        return self

    def __bool__(self) -> Literal[True]:
        return True
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.type == other
        elif isinstance(other, tuple):
            return self.pos == other
        elif isinstance(other, Token):
            return self.type == other.type and self.pos == other.pos
        else:
            return NotImplemented
    
    def __contains__(self, other: str | tuple | Token) -> bool:
        return any(other == token for token in self.subtokens)
    
    def __getitem__(self, key: str | tuple | Token) -> Token:
        for token in self.subtokens:
            if token == key:
                return token
        raise KeyError

    def __repr__(self) -> str:
        return (
            (
                f"<{self.type}>"
                if self.pos is None else
                f"<{self.type} {self.pos[0]}..{self.pos[1]}>"
            )
            + (
                (" [" + (" ".join(repr(token) for token in self.subtokens)) + "]") if self.subtokens else ""
            )
        )

class Result(Token, Generic[_T]):
    def __init__(self, data: _T, token_type: str | None, pos: tuple[int, int], subtokens: list[Token] = []) -> None:
        self.data: _T = data
        self.type: str | None = token_type
        self.pos: tuple[int, int] = pos
        self.subtokens: list[Token] = subtokens

    def __repr__(self) -> str:
        return (
            super().__repr__()
            + " {" + repr(self.data) + "}"
        )
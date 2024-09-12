"""
General purpose parsers.
"""

from __future__ import annotations
from typing import Callable, Any, Literal, LiteralString, Container

from collections.abc import Sequence

from inkparse import *

__all__ = [
    "quoted_string",
    "raw_quoted_string",
    "hashed_quoted_string",
    "raw_hashed_quoted_string",
    "integer_literal",
    "unsigned_integer_literal",
    "integer",
    "unsigned_integer",
    "float_literal",
]

# identifier

def identifier(
    si: StringIterator,
    chars: Container[str] = constants.IDENTIFIER,
) -> Result[str, Literal["identifier"]] | ParseFailure:
    """
    Matches an identifier consisting of the given characters. (`a-z` `A-Z` `0-9` `_` by default)
    """
    with si() as c:
        if si.peek(1) not in chars:
            return c.fail("Expected an identifier.")
        si += 1
        while si.peek(1) in chars:
            si += 1
        return c.result(c.get_string(), "identifier")

# quoted string

class EscapeProvider:
    def __call__(self, si: StringIterator) -> Result[str, Literal["escape_sequence"]] | ParseFailure:
        raise NotImplementedError

class BasicEscapeProvider(EscapeProvider):
    def __init__(
        self,
        escape_char: str = "\\",
        escapes: dict[str, str] = {
            'b': '\b',
            'f': '\f',
            'n': '\n',
            'r': '\r',
            't': '\t',
        },
    ) -> None:
        self.escape_char: str = escape_char
        self.escapes: dict[str, str] = escapes

    def __call__(self, si: StringIterator) -> Result[str, Literal["escape_sequence"]] | ParseFailure:
        with si() as c:
            if not si.literal(self.escape_char):
                return c.fail(f"Expected escape character `{self.escape_char}`.")
            if r := self.unicode_escape(si):
                return c.result(r.data, "escape_sequence")
            else:
                if char := si.take(1):
                    return c.result(char, "escape_sequence")
                else:
                    raise c.error(f"Expected a character to escape after `{self.escape_char}`.")

    def unicode_escape(self, si: StringIterator) -> Result[str, None] | ParseFailure:
        with si() as c:
            if not si.literal("u"):
                return c.fail("Expected unicode escape `\\uXXXX`.")
            if not (code := si.take(4)):
                raise c.error("Expected 4 hexadecimal characters after unicode escape sequence but met EOF.")
            if not all(c in constants.HEXADECIMAL for c in code):
                raise c.error("Expected 4 hexadecimal characters after unicode escape sequence.")
            return c.result(chr(int(code, base=16)))

DEFAULT_ESCAPE_PROVIDER = BasicEscapeProvider()

def quoted_string(
    si: StringIterator,
    quotes: Sequence[Sequence[str]] = (
        ('"', '"'),
        ("'", "'"),
    ),
    *,
    escape: EscapeProvider = DEFAULT_ESCAPE_PROVIDER,
) -> Result[str, Literal["quoted_string"]] | ParseFailure:
    with si(note="In quoted string.") as c:
        for start, end in quotes:
            if si.literal(start):
                break
        else:
            return c.fail("Expected starting quote.")
        data: list[str] = []
        while True:
            if r := escape(si):
                data.append(r.data)
                continue
            elif si.literal(end):
                return c.result("".join(data), "quoted_string")
            else:
                if (char := si.take(1)) is not None:
                    data.append(char)
                else:
                    raise c.error(f"Met EOF before closing quote `{end}`.")

def raw_quoted_string(
    si: StringIterator,
    quotes: Sequence[Sequence[str]] = (
        ('"', '"'),
        ("'", "'"),
    ),
    prefix: str = "r",
) -> Result[str, Literal["raw_quoted_string"]] | ParseFailure:
    with si(note="In raw quoted string.") as c:
        if not si.literal(prefix):
            return c.fail(f"Expected prefix `{prefix}`.")
        for start, end in quotes:
            if si.literal(start):
                break
        else:
            return c.fail("Expected starting quote.")
        data: list[str] = []
        while True:
            if si.literal(end):
                return c.result("".join(data), "raw_quoted_string")
            else:
                if (char := si.take(1)) is not None:
                    data.append(char)
                else:
                    raise c.error(f"Met EOF before closing quote `{end}`.")

def hashed_quoted_string(
    si: StringIterator,
    quotes: Sequence[Sequence[str]] = (
        ('"', '"'),
        ("'", "'"),
    ),
    *,
    hash_char: str = "#",
    escape: EscapeProvider = DEFAULT_ESCAPE_PROVIDER,
) -> Result[str, Literal["hashed_quoted_string"]] | ParseFailure:
    with si(note="In quoted string.") as c:
        hash_count = 0
        for hash_count in forever():
            if not si.literal(hash_char):
                break
        for start, end in quotes:
            if si.literal(start):
                break
        else:
            return c.fail("Expected starting quote.")
        end = end + hash_char*hash_count
        data: list[str] = []
        while True:
            if r := escape(si):
                data.append(r.data)
                continue
            elif si.literal(end):
                return c.result("".join(data), "hashed_quoted_string")
            else:
                if (char := si.take(1)) is not None:
                    data.append(char)
                else:
                    raise c.error(f"Met EOF before closing quote `{end}`.")

def raw_hashed_quoted_string(
    si: StringIterator,
    quotes: Sequence[Sequence[str]] = (
        ('"', '"'),
        ("'", "'"),
    ),
    prefix: str = "r",
    *,
    hash_char: str = "#",
) -> Result[str, Literal["raw_hashed_quoted_string"]] | ParseFailure:
    with si(note="In raw quoted string.") as c:
        if not si.literal(prefix):
            return c.fail(f"Expected prefix `{prefix}`.")
        hash_count = 0
        for hash_count in forever():
            if not si.literal(hash_char):
                break
        for start, end in quotes:
            if si.literal(start):
                break
        else:
            return c.fail("Expected starting quote.")
        end = end + hash_char*hash_count
        data: list[str] = []
        while True:
            if si.literal(end):
                return c.result("".join(data), "raw_hashed_quoted_string")
            else:
                if (char := si.take(1)) is not None:
                    data.append(char)
                else:
                    raise c.error(f"Met EOF before closing quote `{end}`.")

_bindigit       = literal("0", "1")
_octdigit       = literal("0", "1", "2", "3", "4", "5", "6", "7")
_nonzerodigit   = literal(     "1", "2", "3", "4", "5", "6", "7", "8", "9")
_decdigit       = literal("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
_hexdigit       = anycase("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f")

_decinteger = seq(
    _nonzerodigit,
    repeat0(optional("_"), _decdigit),
)
_bininteger = seq(
    "0",
    anycase("b"),
    repeat1(
        optional("_"),
        _bindigit
    ),
)
_octinteger = seq(
    "0",
    anycase("o"),
    repeat1(
        optional("_"),
        _octdigit
    ),
)
_hexinteger = seq(
    "0",
    anycase("x"),
    repeat1(
        optional("_"),
        _hexdigit
    ),
)
_zerointeger = seq(
    repeat1("0"),
    repeat0(optional("_"), "0"),
)
_integer = oneof(_decinteger, _bininteger, _octinteger, _hexinteger, _zerointeger)

def integer_literal(
    si: StringIterator,
) -> Result[int, Literal["integer_literal"]] | ParseFailure:
    with si() as c:
        si.char("-") # optional
        if _integer(si):
            return c.result(int(c.get_string(), base=0), "integer_literal")
        else:
            return c.fail("Expected an integer literal.")

def unsigned_integer_literal(
    si: StringIterator,
) -> Result[int, Literal["integer_literal"]] | ParseFailure:
    with si() as c:
        if _integer(si):
            return c.result(int(c.get_string(), base=0), "integer_literal")
        else:
            return c.fail("Expected an integer literal.")

def integer(
    si: StringIterator,
    base: int = 10,
) -> Result[int, Literal["integer"]] | ParseFailure:
    if not 2 <= base <= 36:
        raise ValueError("Invalid base.")
    with si() as c:
        si.char("-") # optional
        usable_digits = constants.DIGITS36[:base]
        if si.peek(1) in usable_digits:
            si.pos += 1
        else:
            return c.fail(f"Expected an integer of base {base}.")
        while si.peek(1) in usable_digits:
            si.pos += 1
        return c.result(int(c.get_string(), base=base), "integer")

def unsigned_integer(
    si: StringIterator,
    base: int = 10,
) -> Result[int, Literal["integer"]] | ParseFailure:
    if not 2 <= base <= 36:
        raise ValueError("Invalid base.")
    with si() as c:
        usable_digits = constants.DIGITS36[:base]
        if si.peek(1) in usable_digits:
            si.pos += 1
        else:
            return c.fail(f"Expected an integer of base {base}.")
        while si.peek(1) in usable_digits:
            si.pos += 1
        return c.result(int(c.get_string(), base=base), "integer")

_digitpart     =  seq(_decdigit, repeat0(optional("_"), _decdigit))
_exponent      =  seq(anycase("e"), optional_oneof("+", "-"), _digitpart)
# _fraction      =  seq(".", _digitpart)
# _pointfloat    =  oneof(seq(optional(_digitpart), _fraction), seq(_digitpart, "."))
_pointfloat    =  optional(_digitpart, success=seq(".", optional(_digitpart)), fail=seq(".", _digitpart))
_exponentfloat =  seq(oneof(_digitpart, _pointfloat), _exponent)
_floatnumber   =  oneof(_pointfloat, _exponentfloat)


def float_literal(
    si: StringIterator,
) -> Result[int, Literal["float_literal"]] | ParseFailure:
    with si() as c:
        si.char("-") # optional
        if _floatnumber(si):
            return c.result(int(c.get_string(), base=0), "float_literal")
        else:
            return c.fail("Expected a float literal.")

def unsigned_float_literal(
    si: StringIterator,
) -> Result[int, Literal["float_literal"]] | ParseFailure:
    with si() as c:
        if _floatnumber(si):
            return c.result(int(c.get_string(), base=0), "float_literal")
        else:
            return c.fail("Expected a float literal.")
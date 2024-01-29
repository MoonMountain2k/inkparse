
from __future__ import annotations
from typing import Callable

from collections.abc import Sequence

from inkparse import *

# quoted string

GENERAL_ESCAPES = {
    'b': '\b',
    'f': '\f',
    'n': '\n',
    'r': '\r',
    't': '\t',
}

def unicode_escape(si: StringIterator) -> Result[str] | None:
    """Token type: None"""
    with si() as ckpt:
        if si.literal("u"):
            if (code := si.take(4)) is not None:
                if all(c in const.HEXADECIMAL for c in code):
                    return ckpt.result(chr(int(code, base=16)))
            raise ckpt.error("Expected 4 hexadecimal characters after unicode escape sequence.")
        else:
            return None

def quoted_string(
    si: StringIterator,
    *,
    start: Sequence[str] = ('"', "'"),
    end: Sequence[str] = ('"', "'"),
    escape: str = '\\',
    custom_escapes: dict[str, str] = GENERAL_ESCAPES,
    advanced_escapes: Sequence[Callable[[StringIterator], Result[str] | None]] = (unicode_escape,),
) -> Result[str] | None:
    """Token type: `quoted_string`"""
    assert len(start) == len(end), "The number of starting quotes and ending quotes don't match."
    with si() as ckpt:
        quote_index = 0
        for i, s in enumerate(start):
            if si.literal(s):
                quote_index = i
                break
        else:
            return None
        data: list[str] = []
        while True:
            if si.literal(escape):
                for sequence, result in custom_escapes.items():
                    if si.literal(sequence):
                        data.append(result)
                        break
                else:
                    for parser in advanced_escapes:
                        if (parser_output := parser(si)) is not None:
                            data.append(parser_output.data)
                            break
                    else:
                        if (char := si.take(1)) is not None:
                            data.append(char)
                        else:
                            raise si.error_note(f"Expected a character to escape after `{escape}`.", ("In quote:", ckpt.pos))
            elif si.literal(end[quote_index]):
                return ckpt.result("".join(data), "quoted_string")
            else:
                if (char := si.take(1)) is not None:
                    data.append(char)
                else:
                    raise si.error_note(f"Expected closing quote `{end}`.", ("Starting quote:", ckpt.pos))

def raw_quoted_string(
    si: StringIterator,
    *,
    start: Sequence[str] = ('r"', "r'"),
    end: Sequence[str] = ('"', "'"),
) -> Result[str] | None:
    """Token type: `raw_quoted_string`"""
    assert len(start) == len(end), "The number of starting quotes and ending quotes don't match."
    with si() as ckpt:
        quote_index = 0
        for i, s in enumerate(start):
            if si.literal(s):
                quote_index = i
                break
        else:
            return None
        data: list[str] = []
        while True:
            if si.literal(end[quote_index]):
                return ckpt.result("".join(data), "raw_quoted_string")
            else:
                if (char := si.take(1)) is not None:
                    data.append(char)
                else:
                    raise si.error_note(f"Expected closing quote `{end}`.", ("Starting quote:", ckpt.pos))

def integer_number(
    si: StringIterator,
    base: int = 0,
) -> Result[int] | None:
    """
    Token type: `integer`

    If `base` is 0, the base is interpreted from the string.
    - `0b`: Binary
    - `0o`: Octal
    - `0x`: Hexadecimal
    """
    with si() as ckpt:
        si.literal("-") # optional
        if base == 0:
            if si.literal("0b"):
                if not si.literal_any_of(*const.BINARY):
                    raise si.error("Expected a binary digit after 0b.")
                while si.literal_any_of(*const.BINARY):
                    pass
            elif si.literal("0o"):
                if not si.literal_any_of(*const.OCTAL):
                    raise si.error("Expected an octal digit after 0o.")
                while si.literal_any_of(*const.OCTAL):
                    pass
            elif si.literal("0x"):
                if not si.literal_any_of(*const.HEXADECIMAL, case_sensitive=False):
                    raise si.error("Expected a hexadecimal digit after 0x.")
                while si.literal_any_of(*const.HEXADECIMAL):
                    pass
            else:
                if not si.literal_any_of(*const.DECIMAL):
                    return None
                while si.literal_any_of(*const.DECIMAL):
                    pass
        else:
            if not si.literal_any_of(*const.DECIMAL):
                return None
            while si.literal_any_of(*const.DECIMAL):
                pass
        return ckpt.result(int(ckpt.get_string(), base=base), "integer")

def float_number(si: StringIterator) -> Result[float] | None:
    """
    Token type: `float`

    If `base` is 0, the base is interpreted from the string.
    - `0b`: Binary
    - `0o`: Octal
    - `0x`: Hexadecimal
    """
    with si() as ckpt:
        si.literal("-") # optional
        if si.literal_any_of(*const.DECIMAL):
            while si.literal_any_of(*const.DECIMAL):
                pass
            if si.literal("."):
                if si.literal_any_of(*const.DECIMAL):
                    while si.literal_any_of(*const.DECIMAL):
                        pass
                    if si.literal("e", case_sensitive=False):
                        si.literal("-") or si.literal("+")
                        if not si.literal_any_of(*const.DECIMAL):
                            return None
                        while si.literal_any_of(*const.DECIMAL):
                            pass
                elif si.literal("e", case_sensitive=False):
                    si.literal("-") or si.literal("+")
                    if not si.literal_any_of(*const.DECIMAL):
                        return None
                    while si.literal_any_of(*const.DECIMAL):
                        pass
                else:
                    return None
            elif si.literal("e", case_sensitive=False):
                si.literal("-") or si.literal("+")
                if not si.literal_any_of(*const.DECIMAL):
                    return None
                while si.literal_any_of(*const.DECIMAL):
                    pass
            else:
                return None
        elif si.literal("."):
            if si.literal_any_of(*const.DECIMAL):
                while si.literal_any_of(*const.DECIMAL):
                    pass
                if si.literal("e", case_sensitive=False):
                    si.literal("-") or si.literal("+")
                    if not si.literal_any_of(*const.DECIMAL):
                        return None
                    while si.literal_any_of(*const.DECIMAL):
                        pass
            else:
                return None
        else:
            return None
        return ckpt.result(float(ckpt.get_string()), "float")
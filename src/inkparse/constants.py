"""
General use constants.
"""

from __future__ import annotations
from typing import Final

__all__ = [
    "WHITESPACES",
    "BINARY",
    "OCTAL",
    "DECIMAL",
    "HEXADECIMAL",
    "ALPHABETIC",
    "ALNUM",
    "DIGITS36",
]

WHITESPACES: Final = frozenset({" ", "\t", "\n", "\r", "\f"})

BINARY: Final = frozenset({"0", "1"})
OCTAL: Final = frozenset({"0", "1", "2", "3", "4", "5", "6", "7"})
DECIMAL: Final = frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"})
HEXADECIMAL: Final = DECIMAL | {"a", "b", "c", "d", "e", "f", "A", "B", "C", "D", "E", "F"}
ALPHABETIC: Final = frozenset({"a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"})
ALNUM: Final = ALPHABETIC | DECIMAL

DIGITS36: Final = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z")
"""A tuple of the characters: `0123456789abcdefghijklmnopqrstuvwxyz`. Lowercase only."""
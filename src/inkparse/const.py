"""
General use constants.
"""

from __future__ import annotations
from typing import Final

WHITESPACES: Final[frozenset[str]] = frozenset({" ", "\t", "\n", "\r", "\f"})
BINARY: Final[frozenset[str]] = frozenset({"0", "1"})
OCTAL: Final[frozenset[str]] = frozenset({"0", "1", "2", "3", "4", "5", "6", "7"})
DECIMAL: Final[frozenset[str]] = frozenset({"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"})
HEXADECIMAL: Final[frozenset[str]] = DECIMAL | {"a", "b", "c", "d", "e", "f", "A", "B", "C", "D", "E", "F"}
ALPHABETIC: Final[frozenset[str]] = frozenset({"a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"})
ALNUM: Final[frozenset[str]] = ALPHABETIC | DECIMAL
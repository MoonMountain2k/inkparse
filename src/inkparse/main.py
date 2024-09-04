"""
The implementations of the main classes.
"""

from __future__ import annotations
from typing import overload, Any, Self, Literal, TypeVar, Generic, SupportsIndex, Final, Callable, Sequence, Protocol, Never
from types import TracebackType

# from contextlib import contextmanager
from collections.abc import Iterator, Iterable
import re
import textwrap
from copy import copy
import enum

import inkparse.constants as constants

__all__ = [
    "forever",
    "PosNote",
    "ParseFailure",
    "ParseError",
    "Token",
    "Result",
    "StringIterator",
    "Checkpoint",
    "literal",
    "anycase",
    "regex",
    "ws0",
    "ws1",
    "has_chars",
    "take",
    "is_eof",
    "not_eof",
    "seq",
    "oneof",
    "optional_oneof",
    "optional",
    "inverted",
    "lookahead",
    "repeat0",
    "repeat1",
]

def forever(*, start: int = 0, step: int = 1) -> Iterator[int]:
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


class NoValType(enum.Enum):
    NoVal = 0

NoVal = NoValType.NoVal


class Positioned(Protocol):
    @property
    def pos(self) -> int | tuple[int, int] | None: ...
    @property
    def src(self) -> str | None: ...
    @property
    def filename(self) -> str | None: ...


# Positioned compatible
class PosNote:
    """
    Positioned note.
    """

    @overload
    def __init__(
        self,
        msg: str | None,
        pos: Positioned,
    ) -> None: ...

    @overload
    def __init__(
        self,
        msg: str | None = None,
        pos: Positioned | int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
    ) -> None: ...

    def __init__(
        self,
        msg: str | None = None,
        pos: Positioned | int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
    ) -> None:
        """
        All parameters are optional.
        """
        self.msg: str | None = msg
        if pos is None or isinstance(pos, (int, tuple)):
            self.pos = pos
            self.src = src
            self.filename = filename
        else:
            self.pos = pos.pos
            self.src = pos.src
            self.filename = pos.filename

    def pos_to_simple_str(
        self,
        *,
        pos: int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
    ) -> str:
        if pos is None:
            pos = self.pos
        if src is None:
            src = self.src
        if filename is None:
            filename = self.filename
        out = []
        if filename is not None:
            out.append('file "'+filename+'"')
        if pos is not None:
            if src is None:
                if isinstance(pos, int):
                    out.append(f"at position {pos}")
                elif pos[0] == pos[1]:
                    out.append(f"at position {pos[0]}")
                else:
                    out.append(f"from position {pos[0]}")
                    out.append(f"to position {pos[1]}")
            else:
                if isinstance(pos, int):
                    line, column, _ = PosNote._get_line_and_column(src, pos)
                    out.append(f"at position {pos} (line {line}, column {column})")
                elif pos[0] == pos[1]:
                    line, column, _ = PosNote._get_line_and_column(src, pos[0])
                    out.append(f"at position {pos[0]} (line {line}, column {column})")
                else:
                    line, column, _ = PosNote._get_line_and_column(src, pos[0])
                    out.append(f"from position {pos[0]} (line {line}, column {column})")
                    line, column, _ = PosNote._get_line_and_column(src, pos[1])
                    out.append(f"to position {pos[1]} (line {line}, column {column})")
        return ", ".join(out)

    def pos_to_multiline_str(
        self,
        terminal_width: int | None = None,
        *,
        pos: int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
    ) -> str:
        assert terminal_width is None or terminal_width >= 40
        if pos is None:
            pos = self.pos
        if src is None:
            src = self.src
        if filename is None:
            filename = self.filename
        out = []
        preview = ""
        if filename is not None:
            out.append('In file "'+filename+'"')
        if pos is not None:
            if src is None:
                if isinstance(pos, int):
                    out.append(f"At position {pos}")
                elif pos[0] == pos[1]:
                    out.append(f"At position {pos[0]}")
                else:
                    out.append(f"From position {pos[0]}")
                    out.append(f"To position {pos[1]}")
            else:
                if isinstance(pos, int):
                    line, column, found = PosNote._get_line_and_column(src, pos)
                    out.append(f"At position {pos} (line {line}, column {column})")
                    preview = "\n" + PosNote._create_preview_single(
                        terminal_width=terminal_width,
                        src=src,
                        line=line,
                        column=column,
                        found=found,
                    )
                elif pos[0] == pos[1]:
                    line, column, found = PosNote._get_line_and_column(src, pos[0])
                    out.append(f"At position {pos[0]} (line {line}, column {column})")
                    preview = "\n" + PosNote._create_preview_single(
                        terminal_width=terminal_width,
                        src=src,
                        line=line,
                        column=column,
                        found=found,
                    )
                else:
                    line1, column1, found1 = PosNote._get_line_and_column(src, pos[0])
                    out.append(f"From position {pos[0]} (line {line1}, column {column1})")
                    line2, column2, found2 = PosNote._get_line_and_column(src, pos[1])
                    out.append(f"To position {pos[1]} (line {line2}, column {column2})")
                    if line1 == line2:
                        preview = "\n" + PosNote._create_preview_range_oneline(
                            terminal_width=terminal_width,
                            src=src,
                            line=line1,
                            column1=column1,
                            column2=column2,
                            found=found1,
                        )
                    else:
                        preview = "\n" + PosNote._create_preview_range_multiline(
                            terminal_width=terminal_width,
                            src=src,
                            line1=line1,
                            line2=line2,
                            column1=column1,
                            column2=column2,
                            found1=found1,
                            found2=found2,
                        )
        if not out:
            return ""
        if terminal_width is None:
            return "| "+"\n| ".join(out) + preview
        else:
            terminal_width -= 2
            return "| "+"\n| ".join(section for line in out for section in textwrap.wrap(line, terminal_width)) + preview
    
    def to_simple_str(
        self,
        *,
        msg: str | None = None,
        pos: int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
    ) -> str:
        if msg is None:
            msg = self.msg
        if msg is None:
            msg = "Unknown error."
        return msg + " (" + self.pos_to_simple_str(pos=pos, src=src, filename=filename) + ")"

    def to_multiline_str(
        self,
        terminal_width: int | None = None,
        *,
        msg: str | None = None,
        pos: int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
    ) -> str:
        if msg is None:
            msg = self.msg
        if msg is None:
            msg = "Unknown error."
        return msg + "\n" + self.pos_to_multiline_str(terminal_width, pos=pos, src=src, filename=filename)

    @staticmethod
    def _create_preview_single(
        terminal_width: int | None,
        src: str,
        line: int,
        column: int,
        found: int,
    ) -> str:
        assert terminal_width is None or terminal_width >= 40
        line_number_str = str(line)
        empty_gutter = "| "+" "*len(line_number_str)+" | "
        out = [
            empty_gutter,
            f"| {line_number_str} | ",
            empty_gutter,
        ]
        if found == -1:
            linestr = src
        else:
            linestr = src[found + 1 : src.find("\n", found + 1)]
        realcol = column-1
        if (
            terminal_width is None or
            (linelen := len(linestr)) <= (width := terminal_width-len(empty_gutter))
        ):
            # abc
            out[1] += linestr
            out[2] += " "*realcol + "^"
        else:
            two_thirds = width // 3 * 2
            if realcol <= two_thirds:
                # abc...
                out[1] += linestr[:width-3]
                out[2] += " "*realcol + "^" + " "*(width-realcol-4) + "..."
            elif linelen-realcol <= two_thirds:
                # ...abc
                out[1] += "   " + linestr[width-3:]
                out[2] += "..." + " "*(width-(linelen-realcol)-3) + "^"
            else:
                # ...abc...
                dx = (width-6) // 2
                out[1] += "   " + linestr[(realcol-dx):(realcol-dx)+(width-6)]
                out[2] += "..." + " "*(dx) + "^" + " "*(width-dx-7) + "..."
        return "\n".join(out)

    @staticmethod
    def _create_preview_range_oneline(
        terminal_width: int | None,
        src: str,
        line: int,
        column1: int,
        column2: int,
        found: int,
    ) -> str:
        assert terminal_width is None or terminal_width >= 40
        line_number_str = str(line)
        empty_gutter = "| "+" "*len(line_number_str)+" | "
        out = [
            empty_gutter,
            f"| {line_number_str} | ",
            empty_gutter,
        ]
        if found == -1:
            linestr = src
        else:
            linestr = src[found + 1 : src.find("\n", found + 1)]
        realcol1 = column1-1
        realcol2 = column2-1
        if (
            terminal_width is None or
            (linelen := len(linestr)) <= (width := terminal_width-len(empty_gutter))
        ):
            # abc
            out[1] += linestr
            out[2] += " "*realcol1 + "^"*(realcol2-realcol1)
        else:
            if realcol2-realcol1 <= width-10: # if the ends are sufficiently close together
                if realcol2 <= width-5:
                    # abc...
                    out[1] += linestr[:width-3]
                    out[2] += " "*realcol1 + "^"*(realcol2-realcol1) + " "*(width-realcol2-3) + "..."
                elif linelen-realcol1 <= width-5:
                    # ...abc
                    out[1] += "   " + linestr[width-3:]
                    out[2] += "..." + " "*(width-(linelen-realcol1)-3) + "^"*(realcol2-realcol1)
                else:
                    # ...abc...
                    dx = (width - (realcol2-realcol1)) // 2
                    out[1] += "   " + linestr[(realcol1-dx):(realcol1-dx)+(width-6)]
                    out[2] += "..." + " "*dx + "^"*(realcol2-realcol1)
            else:
                if (extra := width - realcol1 - (linelen-realcol2) - 3) >= (width//4) >= 4:
                    # abc...abc
                    padding1 = extra // 2
                    padding2 = extra - padding1
                    out[1] += linestr[:realcol1+padding1] + "   " + linestr[realcol2-padding2:]
                    out[2] += (
                        " "*realcol1 +
                        "^"*(padding1) +
                        "..." +
                        "^"*(padding2)
                    )
                elif realcol1 <= width//2-5:
                    # abc...abc... (or maybe "abc...abc" sometimes idk)
                    len1 = (width-6) // 2
                    len2 = (width-6) - len1
                    dx2 = len2//2
                    out[1] += linestr[:len1] + "   " + linestr[(realcol2-dx2) : (realcol2-dx2)+len2]
                    out[2] += (
                        " "*realcol1 +
                        "^"*(len1-realcol1) +
                        "..." +
                        "^"*dx2 +
                        (" "*(len2-dx2) + "..." if (realcol2-dx2)+len2 < len(linestr) else "")
                        # i'm not completely sure that the "abc...abc" condition failing asserts
                        # that this one must end in a "...". this check is to make sure it
                        # never incorrectly displays "..." when there is no continuation
                    )
                else:
                    # ...abc...abc... ("...abc...abc" sometimes)
                    len1 = (width-9) // 2
                    len2 = (width-9) - len1
                    dx1 = len1//2
                    dx2 = len2//2
                    out[1] += "   " + linestr[(realcol1-dx1) : (realcol1-dx1)+len1] + "   " + linestr[(realcol2-dx2) : (realcol2-dx2)+len2]
                    out[2] += (
                        "..." +
                        " "*dx1 +
                        "^"*(len1-dx1) +
                        "..." +
                        "^"*dx2 +
                        (" "*(len2-dx2) + "..." if (realcol2-dx2)+len2 < len(linestr) else "")
                    )
        return "\n".join(out)

    @staticmethod
    def _create_preview_range_multiline(
        terminal_width: int | None,
        src: str,
        line1: int,
        line2: int,
        column1: int,
        column2: int,
        found1: int,
        found2: int,
    ) -> str:
        assert terminal_width is None or terminal_width >= 40
        line_number_str1 = str(line1)
        line_number_str2 = str(line2)
        far_apart = line2-line1 > 1
        line_number_len = max(len(line_number_str1), len(line_number_str2), 3 if far_apart else 0)
        empty_gutter = "| "+" "*line_number_len +" | "
        out = [
            empty_gutter,
            f"| {line_number_str1.rjust(line_number_len)} | ",
            ("| " + "."*line_number_len + " | ") if far_apart else empty_gutter,
            f"| {line_number_str2.rjust(line_number_len)} | ",
            empty_gutter,
        ]
        assert found1 != -1 and found2 != -1
        linestr1 = src[found1 + 1 : src.find("\n", found1 + 1)]
        linestr2 = src[found2 + 1 : src.find("\n", found2 + 1)]
        linelen1 = len(linestr1)
        linelen2 = len(linestr2)
        realcol1 = column1-1
        realcol2 = column2-1

        if terminal_width is None:
            out[1] += linestr1
            out[2] += " "*realcol1 + "^"*(linelen1-realcol1)
            out[3] += linestr2
            out[4] += "^"*realcol2
        else:
            width = terminal_width-len(empty_gutter)

            if (linelen1 <= width):
                # abc
                out[1] += linestr1
                out[2] += " "*realcol1 + "^"*(min(width, linelen1)-realcol1)
            else:
                two_thirds = width // 3 * 2
                if realcol1 <= two_thirds:
                    # abc...
                    out[1] += linestr1[:width-3]
                    out[2] += " "*realcol1 + "^"*(width-realcol1-3) + "..."
                elif linelen1-realcol1 <= two_thirds:
                    # ...abc
                    out[1] += "   " + linestr1[width-3:]
                    out[2] += "..." + " "*(width-(linelen1-realcol1)-3) + "^"*(linelen1-realcol1)
                else:
                    # ...abc...
                    dx = (width-6) // 2
                    out[1] += "   " + linestr1[(realcol1-dx):(realcol1-dx)+(width-6)]
                    out[2] += "..." + " "*(dx) + "^"*(width-dx-6) + "..."

            if (linelen2 <= width):
                # abc
                out[3] += linestr2
                out[4] += "^"*realcol2
            else:
                two_thirds = width // 3 * 2
                if realcol2 <= two_thirds:
                    # abc...
                    out[3] += linestr2[:width-3]
                    out[4] += "^"*realcol2 + " "*(width-realcol2-3) + "..."
                elif linelen1-realcol2 <= two_thirds:
                    # ...abc
                    out[3] += "   " + linestr2[width-3:]
                    out[4] += "..." + "^"*(width-(linelen1-realcol2)-3)
                else:
                    # ...abc...
                    dx = (width-6) // 2
                    out[3] += "   " + linestr2[(realcol2-dx):(realcol2-dx)+(width-6)]
                    out[4] += "..." + "^"*(dx) + " "*(width-dx-6) + "..."
        return "\n".join(out)

    @staticmethod
    def _get_line_and_column(src: str, pos: int) -> tuple[int, int, int]:
        """
        Converts the `pos` position into line and column numbers using the `src` source string.

        Line and column numbers start from 1. That is, the topmost line is considered line 1, and the rightmost position the cursor can be is considered column 1.

        Returns `(line, column, found)`
        """
        pos = min(pos, len(src))
        # column = pos - src.rfind("\n", 0, pos) # magically works even if it returns -1
        # line = src.count("\n", 0, pos) + 1 # should still work with CRLF
        found = src.rfind("\n", 0, pos)
        if found == -1:
            return 1, pos + 1, found
        return src.count("\n", 0, pos) + 1, pos - found, found



class ParseFailureBase:
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

    def __init__(
        self,
        msg: str | None = None,
        notes: list[PosNote] = [],
    ) -> None:
        self.msg = msg
        self.notes: list[PosNote] = notes

    def append_existing(self, note: PosNote | list[PosNote]) -> Self:
        """Appends a note or notes to the bottom of the notes."""
        if isinstance(note, list):
            self.notes += note
        else:
            self.notes.append(note)
        return self

    @overload
    def append_pos_note(
        self,
        msg: str | None,
        pos: Positioned,
    ) -> Self: ...

    @overload
    def append_pos_note(
        self,
        msg: str | None = None,
        pos: Positioned | int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
    ) -> Self: ...

    def append_pos_note(
        self,
        msg: str | None = None,
        pos: Positioned | int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
    ) -> Self:
        """Appends a note to the bottom of the notes."""
        self.notes.append(PosNote(msg, pos, src, filename))
        return self

    def copy(
        self,
        msg: str | None = None,
        notes: list[PosNote] = [],
    ) -> Self:
        return type(self)(msg if msg is not None else self.msg, notes if notes is not None else copy(self.notes))

    def with_existing(self, note: PosNote | list[PosNote]) -> Self:
        """
        `append_existing` but it returns a copy.
        """
        if isinstance(note, list):
            return self.copy(notes = self.notes + note)
        else:
            return self.copy(notes = self.notes + [note])

    @overload
    def with_pos_note(
        self,
        msg: str | None,
        pos: Positioned,
    ) -> Self: ...

    @overload
    def with_pos_note(
        self,
        msg: str | None = None,
        pos: Positioned | int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
    ) -> Self: ...

    def with_pos_note(
        self,
        msg: str | None = None,
        pos: Positioned | int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
    ) -> Self:
        """
        `add_pos_note` but it returns a copy.
        """
        return self.copy(notes = self.notes + [PosNote(msg, pos, src, filename)])

    def with_existing_pos_note(self, note: PosNote) -> Self:
        """
        `add_existing_pos_note` but it returns a copy.
        """
        return self.copy(notes = self.notes + [note])

    def error(self) -> ParseError:
        """Converts this to a ParseError."""
        return ParseError(self.msg, self.notes)

    def failure(self) -> ParseFailure:
        """Converts this to a ParseFailure."""
        return ParseFailure(self.msg, self.notes)

    def __bool__(self) -> Literal[False]:
        return False

class ParseFailure(ParseFailureBase):
    pass

class ParseError(ParseFailureBase, Exception):
    """
    The exception that's raised when a parser encounters an unrecoverable error.

    Usually used for syntax errors.
    """

    def __init__(
        self,
        msg: str | None = None,
        notes: list[PosNote] = [],
    ) -> None:
        if msg is None:
            Exception.__init__(self)
        else:
            Exception.__init__(self, msg)
        ParseFailureBase.__init__(self, msg, notes)

    def add_note(self, note: str) -> None:
        """Does nothing. This would add a note to exceptions normally, but this exception replaces the behavior."""
        pass

    @property
    def __notes__(self) -> list[str]:
        return [note.to_multiline_str() for note in self.notes]
    @__notes__.setter
    def __notes__(self) -> None:
        pass


# Positioned compatible
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

    @overload
    def __init__(
        self,
        token_type: _TokenTypeCovT,
        pos: Positioned,
        *,
        subtokens: list[Token] = [],
    ) -> None: ...

    @overload
    def __init__(
        self,
        token_type: _TokenTypeCovT,
        pos: Positioned | int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
        subtokens: list[Token] = [],
    ) -> None: ...

    def __init__(
        self,
        token_type: _TokenTypeCovT,
        pos: Positioned | int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
        subtokens: list[Token] = [],
    ) -> None:
        """
        `token_type` can either be a string or None.
        """
        self.token_type: Final[_TokenTypeCovT] = token_type
        self.subtokens: list[Token] = subtokens
        self.pos: int | tuple[int, int] | None
        self.src: str | None
        self.filename: str | None
        if pos is None or isinstance(pos, (int, tuple)):
            self.pos = pos
            self.src = src
            self.filename = filename
        else:
            self.pos = pos.pos
            self.src = pos.src
            self.filename = pos.filename

    def with_type(self, token_type: _TokenTypeT) -> Token[_TokenTypeT]:
        """Creates a copy of this token with the provided token type."""
        return Token(token_type, self.pos, self.src, self.filename, self.subtokens)

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
        if self.pos is None:
            pos_start, pos_end = None, None
        elif isinstance(self.pos, int):
            pos_start, pos_end = self.pos, None
        elif self.pos[0] == self.pos[1]:
            pos_start, pos_end = self.pos[0], None
        else:
            pos_start, pos_end = self.pos
        return (
            (
                f"<{self.token_type}>"
                if pos_start is None else
                f"<{self.token_type} {pos_start}>"
                if pos_end is None else
                f"<{self.token_type} {pos_start}..{pos_end}>"
            )
            + (
                (" [" + (" ".join(repr(token) for token in self.subtokens)) + "]") if self.subtokens else ""
            )
        )

# Positioned compatible
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
    @overload
    def __init__(
        self,
        data: _DataCovT,
        token_type: _TokenTypeCovT,
        pos: Positioned,
        *,
        subtokens: list[Token] = [],
    ) -> None: ...

    @overload
    def __init__(
        self,
        data: _DataCovT,
        token_type: _TokenTypeCovT,
        pos: Positioned | int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
        subtokens: list[Token] = [],
    ) -> None: ...

    def __init__(
        self,
        data: _DataCovT,
        token_type: _TokenTypeCovT,
        pos: Positioned | int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
        subtokens: list[Token] = [],
    ) -> None:
        super().__init__(token_type, pos, src, filename, subtokens)
        self.data: _DataCovT = data

    def with_type(self, token_type: _TokenTypeT) -> Result[_DataCovT, _TokenTypeT]:
        """Creates a copy of this result with the provided token type."""
        return Result(self.data, token_type, self.pos, self.src, self.filename, self.subtokens)

    def __repr__(self) -> str:
        return (
            super().__repr__()
            + " {" + repr(self.data) + "}"
        )


# Positioned compatible
class StringIterator:
    def __init__(self, src: str, starting_pos: int = 0, filename: str | None = None) -> None:
        self.src: Final[str] = src
        """The string that's being parsed."""
        self.pos: int = starting_pos
        """The current position."""
        self.filename: Final[str | None] = filename

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

    def guard(self, value: _T, condition: bool | None = None) -> _T:
        """
        Same as `si.save().guard(...)` but doesn't actually create a `Savepoint`.
        """
        pos = self.pos
        if condition is None:
            if not value:
                self.pos = pos
        else:
            if not condition:
                self.pos = pos
        return value
    
    @overload
    def get_token(self) -> Token[None]: ...
    @overload
    def get_token(self, token_type: _TokenTypeT) -> Token[_TokenTypeT]: ...

    def get_token(self, token_type: _TokenTypeT | None = None) -> Token[_TokenTypeT | None]:
        """
        Creates a `Token` object.
        """
        return Token(token_type, self)

    @overload
    def get_result(self, data: _DataT) -> Result[_DataT, None]: ...
    @overload
    def get_result(self, data: _DataT, token_type: _TokenTypeT) -> Result[_DataT, _TokenTypeT]: ...

    def get_result(self, data: _DataT, token_type: _TokenTypeT | None = None) -> Result[_DataT, _TokenTypeT | None]:
        """Creates a `Result` object."""
        return Result(data, token_type, self)

    def get_note(self, msg: str | None = None) -> PosNote:
        """Creates a `PosNote`."""
        return PosNote(msg, self)

    def get_error(self, msg: str | None = None) -> ParseError:
        """Creates a `ParseError` and notes the current position."""
        return ParseError(msg).append_pos_note(None, self)
        # do not include self.notes, as it's supposed to be added by __exit__().

    def get_fail(self, msg: str | None = None) -> ParseFailure:
        """Creates a `ParseFailure` and notes the current position."""
        return ParseFailure(msg).append_pos_note(None, self)
    
    def inverted_guard(self, value: _T, condition: bool | None = None) -> _T:
        """
        Like `guard()` but rolls back if it's true instead.
        """
        pos = self.pos
        if condition is None:
            if value:
                self.pos = pos
        else:
            if condition:
                self.pos = pos
        return value

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
        while self.peek(1) in constants.WHITESPACES:
            self.pos += 1
    
    def ws1(self) -> bool:
        """Matches one or more whitespaces. Returns a bool indicating whether or not the first whitespace was found."""
        if self.peek(1) not in constants.WHITESPACES:
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

# Positioned compatible
class CheckpointBase:
    @property
    def src(self) -> str:
        return self.si.src

    @property
    def filename(self) -> str | None:
        return self.si.filename

    @property
    def pos(self) -> tuple[int, int]:
        return (self.start_pos, self.si.pos)

    def __init__(self, si: StringIterator) -> None:
        self.start_pos: Final[int] = si.pos
        self.si: Final[StringIterator] = si

    def rollback(self) -> None:
        """Rolls back the iterator to the starting position. (Regardless of the checkpoint being commited or not.)"""
        self.si.pos = self.start_pos
    
    def get_string(self) -> str:
        return self.si.src[self.start_pos : self.si.pos]

    @overload
    def get_token(self) -> Token[None]: ...
    @overload
    def get_token(self, token_type: _TokenTypeT) -> Token[_TokenTypeT]: ...

    def get_token(self, token_type: _TokenTypeT | None = None) -> Token[_TokenTypeT | None]:
        """
        Creates a `Token` object.
        
        Uses the checkpoint's saved position as the start, and the current iterator position as the end position of the token.
        """
        return Token(token_type, self)

    @overload
    def get_result(self, data: _DataT) -> Result[_DataT, None]: ...
    @overload
    def get_result(self, data: _DataT, token_type: _TokenTypeT) -> Result[_DataT, _TokenTypeT]: ...

    def get_result(self, data: _DataT, token_type: _TokenTypeT | None = None) -> Result[_DataT, _TokenTypeT | None]:
        """
        Creates a `Result` object.
        
        Uses the checkpoint's saved position as the start, and the current iterator position as the end position of the result.
        """
        return Result(data, token_type, self)

    def get_note(self, msg: str | None = None) -> PosNote:
        """Creates a `PosNote`."""
        return PosNote(msg, self)

    def get_error(self, msg: str | None = None) -> ParseError:
        """Creates a `ParseError` and notes the position range from the checkpoint start to the current position."""
        return ParseError(msg).append_pos_note(None, self)
        # do not include self.notes, as it's supposed to be added by __exit__().

    def get_fail(self, msg: str | None = None) -> ParseFailure:
        """Creates a `ParseFailure` and notes the position range from the checkpoint start to the current position."""
        return ParseFailure(msg).append_pos_note(None, self)
    
    def guard(self, value: _T, condition: bool | None = None) -> _T:
        """
        Rolls back the checkpoint if the `condition` parameter is `None` and the `value` is falsy, or the `condition` parameter is false.

        Returns the `value` as-is.

        Common usage method:

        ```
        si.save().guard(si.literal("test"))
        si.guard(si.literal("test"))
        ```
        """
        if condition is None:
            if not value:
                self.si.pos = self.start_pos
        else:
            if not condition:
                self.si.pos = self.start_pos
        return value
    
    def inverted_guard(self, value: _T, condition: bool | None = None) -> _T:
        """
        Like `guard()` but rolls back if it's true instead.
        """
        if condition is None:
            if value:
                self.si.pos = self.start_pos
        else:
            if condition:
                self.si.pos = self.start_pos
        return value
    
    def rollback_inline(self, value: _T) -> _T:
        """
        Rolls back and returns the parameter as-is.
        """
        self.si.pos = self.start_pos
        return value

# Positioned compatible
class Savepoint(CheckpointBase):
    """
    A simplified and faster version of `Checkpoint`.

    Can only be reverted manually. (By calling the savepoint.)

    No concept of committing and automatic rollbacks.
    """
    def __call__(self) -> None:
        self.rollback()

# Positioned compatible
class Checkpoint(CheckpointBase):
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

    @property
    def reversed_notes(self) -> list[PosNote]:
        return list(reversed(self.notes))

    def __init__(self, si: StringIterator, *, parent_checkpoint: Checkpoint | None = None, note: str | None = None) -> None:
        """
        Create using `StringIterator.checkpoint()` or `StringIterator.__call__()` instead.
        """
        super().__init__(si)
        self.parent_checkpoint: Final[Checkpoint | None] = parent_checkpoint

        self.subtokens: list[Token] = []
        """The tokens to add as subtokens to the resulting `Token`."""
        self.notes: list[PosNote] = []
        """
        The notes to append to the resulting `ParseError` or `ParseFailure`.
        
        These notes are in reverse order. (It'll be reversed before being appended to the error.)
        """
        self.committed: bool = False
        """Use `is_committed()` to check if it's committed."""

        self._starting_note: str | None = note
        if note is not None:
            self.note(note)

    def restart(self) -> None:
        """Rolls back and reverts all the data of the checkpoint to the starting configuration."""
        self.si.pos = self.start_pos
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

    def rollback_if_uncommited(self) -> None:
        """Rolls back if the checkpoint isn't committed."""
        if not self.is_committed():
            self.si.pos = self.start_pos

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
        self.notes.append(PosNote(msg, self))

    @overload
    def get_token(self) -> Token[None]: ...
    @overload
    def get_token(self, token_type: _TokenTypeT) -> Token[_TokenTypeT]: ...

    def get_token(self, token_type: _TokenTypeT | None = None) -> Token[_TokenTypeT | None]:
        """
        Creates a `Token` object without committing.
        
        Uses the checkpoint's saved position as the start, and the current iterator position as the end position of the token.
        """
        return Token(token_type, self, subtokens=self.subtokens)

    @overload
    def get_result(self, data: _DataT) -> Result[_DataT, None]: ...
    @overload
    def get_result(self, data: _DataT, token_type: _TokenTypeT) -> Result[_DataT, _TokenTypeT]: ...

    def get_result(self, data: _DataT, token_type: _TokenTypeT | None = None) -> Result[_DataT, _TokenTypeT | None]:
        """
        Creates a `Result` object without committing.
        
        Uses the checkpoint's saved position as the start, and the current iterator position as the end position of the result.
        """
        return Result(data, token_type, self, subtokens=self.subtokens)

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
        return Token(token_type, self, subtokens=self.subtokens)

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
        return Result(data, token_type, self, subtokens=self.subtokens)

    def get_error(self, msg: str | None = None) -> ParseError:
        """Creates a `ParseError` without uncommitting and notes the position range from the checkpoint start to the current position."""
        return ParseError(msg).append_pos_note(None, self)
        # do not include self.notes, as it's supposed to be added by __exit__().

    def get_fail(self, msg: str | None = None) -> ParseFailure:
        """Creates a `ParseFailure` without uncommitting and notes the position range from the checkpoint start to the current position."""
        return ParseFailure(msg, self.reversed_notes).append_pos_note(None, self)

    def error(self, msg: str | None = None) -> ParseError:
        """Uncommits and creates a `ParseError` and notes the position range from the checkpoint start to the current position."""
        self.committed = False
        return ParseError(msg).append_pos_note(None, self)
        # do not include self.notes, as it's supposed to be added by __exit__().

    def fail(self, msg: str | None = None) -> ParseFailure:
        """Uncommits and creates a `ParseFailure` and notes the position range from the checkpoint start to the current position."""
        self.committed = False
        return ParseFailure(msg, self.reversed_notes).append_pos_note(None, self)

    @overload
    def propagate(
        self,
        failure: ParseFailure,
        /,
    ) -> ParseFailure: ...

    @overload
    def propagate(
        self,
        failure: ParseFailure,
        msg: str | None,
        /,
    ) -> ParseFailure: ...

    @overload
    def propagate(
        self,
        failure: ParseFailure,
        msg: str | None,
        /,
        pos: Positioned,
    ) -> ParseFailure: ...

    @overload
    def propagate(
        self,
        failure: ParseFailure,
        msg: str | None,
        /,
        pos: int | tuple[int, int] | None = None,
        src: str | None = None,
        filename: str | None = None,
    ) -> ParseFailure: ...

    def propagate(
        self,
        failure: ParseFailure,
        msg: str | None | NoValType = NoVal,
        /,
        pos: Positioned | int | tuple[int, int] | None | NoValType = NoVal,
        src: str | None = None,
        filename: str | None = None,
    ) -> ParseFailure:
        """
        For failing using an existing `ParseFailure`.
        
        Uncommits, adds the current context's notes to the ParseError and returns it.

        Can optionally add the current position as a note if you supply a message.

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
        if msg is NoVal:
            return failure.append_existing(self.reversed_notes)
        elif pos is NoVal:
            return failure.append_pos_note(msg, self).append_existing(self.reversed_notes)
        else:
            return failure.append_pos_note(msg, pos, src, filename).append_existing(self.reversed_notes)

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
                exc.notes += self.reversed_notes
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
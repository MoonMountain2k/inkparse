"""
An more complete and readable alternative to regex that can be used with inkparse.
"""

import inkparse.const as const
from inkparse.main import (
    ParseError,
    StringIterator,
    Checkpoint,
    Token,
    Result,
)
import inkparse.expr.parser as parser

class Expr:
    pass
"""
Library to simplify writing string parsers manually.

See the objects for more explanations.

See the `inkparse.general` module for general purpose parsers you can use as examples.

Defining parsers:
```
def foo(si: StringIterator, ...) -> Result[int, Literal["token_type"]] | ParseFailure:
    with si() as c:
        si.literal("abc")
        # etc.
        return c.result(10, "token_type")       # success
        return c.fail("Fail reason here.")      # fail
        raise c.error("Error reason here.")     # error
```

Using parsers:
```
si = StringIterator("blablabla")

result = foo(si)
if result:
    ... # `result` is a `Result` or `Token` object
else:
    ... # `result` is a `ParseFailure` object
```
"""

import inkparse.const as const
import inkparse.main
from inkparse.main import (
    repeat,
    PosNote,
    ParseFailure,
    ParseError,
    Token,
    Result,
    StringIterator,
    Checkpoint,
    literal,
    anycase,
    regex,
    ws0,
    ws1,
    has_chars,
    take,
    is_eof,
    not_eof,
    seq,
    oneof,
    optional_oneof,
    optional,
    inverted,
    lookahead,
    repeat0,
    repeat1,
)
import inkparse.general as general
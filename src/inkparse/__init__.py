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

---

String positions are between characters and start from 0.

(Examples of string positions include function arguments that have "pos" or "position" in their name.)

In a string: `"abcdef"`
```
 a b c d e f
^ ^ ^ ^ ^ ^ ^
0 1 2 3 4 5 6
```

However, line numbers and column numbers start from 1.

(Examples of line numbers and column numbers include function arguments that have "line" or "col" / "column" in their name respectively.)

The first line in a string is line 1.

The space before the first character (the rightmost position a text caret can be) is column 1.
```
"""

import inkparse.constants as constants
from inkparse.main import *
import inkparse.general as general
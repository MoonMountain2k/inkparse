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

String positions are *between* characters and start from 0. (The same as how python string slices work.)

In the string: `"abcdef"`
```
 a b c d e f
^ ^ ^ ^ ^ ^ ^
0 1 2 3 4 5 6
```

(Line numbers and column numbers shown in error messages start from 1 instead of 0.)
"""

import inkparse.constants as constants
from inkparse.main import *
import inkparse.general as general
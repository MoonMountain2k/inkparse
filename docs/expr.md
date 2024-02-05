# Options

- `ignore_ws`: Doesn't match whitespace characters.
- `literal_only`: Only matches characters in quotes.

# Matching

Any non special characters are matched literally. (when `literal_only` is turned off)

## Whitespaces

- Any whitespace character
	- Match one or more whitespaces if `ignore_ws` and `literal_only` is turned off.
	- Otherwise, do nothing.
- `^`: Zero or more whitespaces
	- `[\s]+`
- `&`: One or more whitespaces
	- `\s+`

## Literals

- `"abc"` `'abc'`: String literal
	- Everything other than escape sequences are matched as is.
	- You can put hashes around it. The closing bracket must match.
	- `#" bla"bla"bla "#`
- `\(`: Escaped character (You may need to use two backslashes when using this from python.)
- Escape sequences
	- `\n`: Newline / line feed (use `\b`)
	- `\r`: Carriage return (use `\b`)
	- `\f`: Form feed
	- `\t`: Tab
	- `\0`: Null
	- `\b`: Backspace
	- `\cX`: Control characters
	- `\u0000`: Unicode
- Special escapes
	- `\s`: Whitespace
	- `\d`: Digit
	- `\a`: Alphabetic character (case insensitive)
	- `\w`: Word character (case insensitive)
	- `\b`: Any line break sequence
		- `\n` or `\r\n`
		- Not a single character, so it can't be used in sets.
		- If inverted, only matches a single character.
	- `\v`: Vertical whitespace
	- `\h`: Horizontal whitespace
	- Inverted version.
		- Capitalize the character.
		- `\W`: Non word character
	- Uppercase only version.
		- `\ua`: Uppercase letters
	- Lowercase only version.
		- `\la`: Lowercase letters

## Character sets

- `.`: Any character
- `{}`: Character sets
	- `{abc}`: Character set
		- Any of the listed characters.
		- Can include escape sequences:
			- `{abc\n}`
		- Can include other sets:
			- `{abc{0-9}}` `{abc{.ws}}`
			- Invalid: `{abc0-9}` `{abc.ws}`
				- ("0", "-", or "9" will be matched, instead of digits, etc.)
	- `{a-z}`: Range
		- Any character in the range
	- `{.ws}`: Character class
		- Any character in the class
	- `{?abc}`: Case insensitive version
	- `{^abc}`: Uppercase version
	- `{_abc}`: Lowercase version
	- `{!abc}`: Inverted
	- `{a|b}`: Union
		- Characters that match any of the sets.
		- `{abc|0-9}`
		- `{abc|.ws}`
	- `{a&b}`: Intersection
		- Characters that match all the sets.
		- `{abc&0-9}`
		- `{abc&.ws}`
	- Precedence:
		- `{!a}` `{?a}` `{_a}` `{^a}`
			- Right to left associativity
		- `{a&b}`
		- `{a|b}`

### Character classes

- `{.a}` `{.alpha}`
	- `{?a-z}`
- `{.d}` `{.dec}` `{.digit}` `{.n}` `{.num}`
	- `{0-9}`
- `{.an}` `{.alnum}`
	- `{{.a}{.d}}`
- `{.x}` `{.hex}`
- `{.ws}`
- `{.ascii}`
- `{.ctrl}`

## Boundaries

- `<\w>`: A boundary between a word character and any other character.
- `<\d \a>`: A boundary between a digit and an alphabetic character.
- `<\d-\a>`: A boundary between a digit and an alphabetic character. (order matters)
- `<-\a>`: A boundary between a digit and any other character. (order matters)
- `<\a->`: A boundary between a digit and any other character. (order matters)


## Grouping

- `(abc)`: Group
- `[abc]`: Optional group
- `(?;abc)`: Case insensitive
- `(!?;abc)`: Not case insensitive
- `(abc>>)`: Atomic group
	- When backtracking, the whole group is skipped.
- `(>;abc)`: Lookahead
	- After matching the expression, goes back to the starting position.
	- Equivalent to: `((abc)$(:g))`
- `(<;abc)`: Lookbehind
	- Goes back one by one until the expression matches.
	- The end of the matched expression must be at the current cursor position.
	- Equivalent to: `($(^..0)(abc)$(==:g))`
- `(!>;abc)`: Negative lookahead.
	- Equivalent to: `[abc]->($!)`
- `(!<;abc)`: Negative lookbehind.
	- Equivalent to: `[$(^..0)(abc)$(==:g)]->($!)`
- `(foo;abc)`: Capture group
- `($bar;abc)`: Global capture
- `(::$foo;abc)`: Definition
	- Does not match, only defines the group for later use.
- `(->$foo)`: Match another group
	- `(->$foo)`: Runs a named group.
	- `(->$g)`: Recurses group.
	- `(->$e)`: Recurses expression.
	- `(->.foo)`: Matches the contents of a capture.
	- `(->.foo[1..2])`: Matches a section of the contents of a capture.

You can combine group types.

- `(?foo;abc)`: Case insensitive, capture as `.foo`.
- `[>foo;abc]`: Optional lookahead, capture as `.foo`.
- `(foo->$bar)`: Run group `bar` and capture it as `.foo`.

## One of

- `(a|b|c)`: One of
- `[a|b|c]`: Optional one of
- Possessive:
	- `(a|b|c)!`: Possessive
		- If any of them match, none of the rest are tried
	- `[a|b|c]!`: Possessive optional
		- If any of them match, none of the rest are tried, and skipping isn't attempted
	- `(a|b||c|d)`: Partly possessive
		- If `a` or `b` matches, `c` or `d` isn't attempted when backtracking.
	- `(a|b>!|c|d)`: Partly possessive
		- Uses the `>!` operator to emulate possessiveness.
		- If `b` matches, the others aren't attempted when backtracking. Only `b` is affected.
	- Possessive loops don't affect the one of's possessiveness.
	- Use two exclamation marks:
		- `(a|b|c)!+!`: Possesive one of in a possessive loop.
		- `[a|b|c]!+!`: Possesive optional one of in a zero or more possessive loop.

## Loops

- Loops can only be after:
	- Groups
	- Chararter sets
	- Escape sequences
- Loops are a part of the group.
- Greedy loops: (tries to get as many as possible)
	- `[abc]+`: Zero or more
	- `(abc)+`: One or more
	- `(abc)++`: Two or more
- Lazy loops: (tries to get as few as possible)
	- `[abc]+?`: Zero or more
	- `(abc)+?`: One or more
	- `(abc)++?`: Two or more
	- Optional groups can be made lazy:
		- `[abc]?`: Will attempt to skip it first. If that fails, tries to match the contents.
- Possessive loops: (gets as many as it can, and won't backtrack)
	- `[abc]+!`: Zero or more
	- `(abc)+!`: One or more
	- `(abc)++!`: Two or more
	- Optional groups can be made possessive:
		- `[abc]!`: If it succeeds, won't try to skip it when backtracking.
- Custom loops:
	- `(abc)*10`: Exactly 10 times
	- `(abc)*10+`: 10 or more times (greedy)
	- `(abc)*10+?`: 10 or more times (lazy)
	- `(abc)*10+!`: 10 or more times (possessive)
	- `(abc)*(10..inf)`: 10 or more times (lazy)
	- `(abc)*(inf..10)`: 10 or more times (greedy)
	- `(abc)*(5..10)`: 5 to 10 times (inclusive) (lazy)
	- `(abc)*(10..5)`: 5 to 10 times (inclusive) (greedy)
	- `(abc)*(2..4, 6..8)`: Order: 2, 3, 4, 6, 7, 8
	- `(abc)*(2..4, 8..6)`: Order: 2, 3, 4, 8, 7, 6
	- `(abc)*(2..4, 6..0)`: Order: 2, 3, 4, 6, 5, 1, 0
		- (Numbers that have already been tried won't be repeated.)
	- `(abc)*(6..4, 2, 1)!`: Possessive.
		- `[6], [5], [4], [2], [1]`
		- If any of the numbers match, the rest of the possibilities aren't attempted.
		- Partly possessive:
			- `(abc)*(6..4!, 2, 1)`
				- `[6], [5], [4], 2, 1`
			- `(abc)*(6..4, 2!, 1)`
				- `6, 5, 4, [2], 1`
	- Lazy possessive loops are technically possible, but are virtually useless.
		- For example: `*(2..4)!` will be the same as `*2`
		- If 2 is found, 3 and 4 will never be tried. (which is the behavior of `*2`)
		- And it can't match 3 or 4 times without matching twice before it.
- Breaking out of loops:
	- Use the accept operation `$a`.
	- `(abc$a)+`
	- `(1;(abc$<a 1>)+)+`
- Continue statements:
	- Use the next operation `$n`.
	- `(abc$n)+`
	- `(1;(abc$<n 1>)+)+`
- If you loop a capturing group, the contents get captured as sub captures.
	- Example: `(foo;abc)+`
	- `foo.0` to `foo.N` - the 0th to the Nth iteration.
	- `foo.prev` - the previous iteration's capture.
	- `foo.prev2`, etc.


## Operations

- Accept:
	- `$a`: Stops parsing this group with a success
		- Same as `${(.>)}`
	- `$A`: Stops parsing the expression with a success
		- Same as `${(~>)}`
	- `$<a foo>`: Accept specific group
		- Same as `${(foo>)}`
- Fail:
	- `$!`: Fail
		- Just a normal mismatch, will backtrack as normal after this.
	- `$f`: Fail group
	- `$F`: Fail expression
	- `$<f foo>`: Fail specific group
		- Must be inside the group.
- Next / continue:
	- `$n`: Next
		- Goes to the next iteration, or the next section of an "one of" statement.
		- Basically fails the current iteration of the loop.
	- `$<n foo>`
- Prevent backtracking:
	- Triggered when this symbol is reached while backtracking.
	- `>>`: Skip until the start of the group.
	- `>!` or `$p`: Skip the group and it's branches.
		- This will fully skip optional groups, one-ofs, and loops, unlike `>>`.
	- `$P`: Fail expression if backtracking is attempted here.
	- `$<!foo>` `$<p foo>`: Fail specific group if backtracking is attempted here.
		- Must be inside the group.
- Skip:
	- `$<s foo>`: Will skip the group the following times it's attempted.
	- `$<sf foo>`: Will fail the group the following times it's attempted.
- Restart:
	- `$r`: Restarts the whole expression starting at the current cursor position.
	- Restarts all captures and saved data.
	- If a position is attemped twice, fails the expression.
- Ignore / intercept:
	- `$i`: Catches the error in conditional failure clauses.

## Capture paths and group names

When capturing:

- `foo`: `.foo`.
- `~foo`: A sub capture of the expression.
- `.foo`: A sub capture of the current group.
- `..foo`: A sub capture of the parent group / a sibling capture.
- etc.
- `.foo.bar`
- `..foo.bar`
- `~foo.bar`

When using:

- `foo`: Any parent capture named `foo`.
	- The first one found when traversing up the tree.
- `~`: The capture of the expression.
- `.`: The capture of the current group.
- `..`: The capture of the parent group.
- `...`: The capture of the parent's parent group.
- etc.
- `~foo`: A sub capture of the expression.
- `.foo`: A sub capture of the current group.
- `..foo`: A sub capture of the parent group / a sibling capture.
- `.foo.bar`
- `..foo.bar`
- `~foo.bar`

## Move operations

- `$(-1)`: Move cursor
- Absolute positioning:
	- `0`: The beggining of the string.
	- `eof`/`end`: The end of the string.
	- `1`: One position after the beggining.
	- `eof-1`: One position before the end.
- Relative positioning:
	- `^`: The current position of the cursor.
	- `+1` or `^+1`: One position after the cursor.
	- `-1` or `^+1`: One position before the cursor.
- Relative to saved pos:
	- `foo`: A saved position.
	- `foo+1`: One position after the position.
	- `foo-1`: One position before the position.
- Relative to captured match:
	- `~`: The beginning of the expression.
	- `.`: The beginning of this group.
	- `foo`: The beginning of a captured match.
	- `foo'`: The end of a captured match.
	- `foo+1`: One position after the beginning of the captured match.
- `$(+1, +3)`: Multiple destinations. If a position fails, it tries the next one.
- `$(+1..+4)`: Range. If a position fails, it tries the next one.

## Save operations

- `${@foo}`: Save the cursor position as foo.
- `${foo}`: Set the start of a captured group.
- `${foo'}`: Set the end of a captured group.
	- Ends parsing the group with a success if the group wasn't finished yet.
- `${~}`: Set the start of this match.
- `${~'}`: Set the end of this match.
	- Ends parsing with a success.
- `${.}`: Set the start of this group.
- `${.'}`: Set the end of this group.
	- Ends parsing the group with a success if the group wasn't finished yet.
- `${@foo=1}`: Assign any position to a variable.
	- Works with variables and captured matches:
		- `${@foo=@bar}`
		- `${@foo=bar}` `${@foo=bar'}`
	- Works with operations:
		- `${@foo=1+2}`.
	- The allowed operations are:
		- `(a)`: Parentheses
		- `a+b`: Addition
		- `a-b`: Subtraction
		- `a*b`: Multiplication
		- `a/b`: Division (integer)
		- `a%b`: Modulo
	- Works with relative positions:
		- `${@foo=^}`: The position of the cursor.
		- `${@foo=-1}`: One position before the cursor.
		- `${@foo=+1}`: One position after the cursor.
		- While there is no ambiguity, I'd recommend using parentheses when combining with other operations.
			- `${@foo=bar+(+1)}`
- `${@foo+=1}`: Modify a variable.
	- The allowed operations are:
		- `+=`: Increase
		- `-=`: Decrease
		- `*=`: Multiply
		- `/=`: Divide (integer)
		- `%=`: Modulo
- `${@foo=1; @bar=2}`: Multiple operations.



# Conditionals

- Optionals:
	- `[abc]->(s|f)`
		- `s` will be matched if the optional succeeded.
		- `f` will be matched if the optional failed.
		- If `s` or `f` fails, the group will fail.
	- `[abc]->[s|f]`
		- `s` will be matched if the optional succeeded.
		- `f` will be matched if the optional failed.
		- If `s` or `f` fails, nothing happens.

Any failable expression can be tested with: `(foo)->(s|f)`

Use `$i` to stop the error from propagating.

## Compare operations

- `$[==1]`: Test if the cursor position is equal to 1.
	- All position operations:
		- `a<b` `a>b` `a<=b` `a>=b` `a!=b`
	- In range operator (`a?=b`):
		- `$[?=foo]`: Tests if the cursor position is in the capture's range
		- `$[?=1..2]`: Tests if the cursor position is in the range
	- Matching group operator (`??b`):
		- `$[??foo]`: Tests if the foo capture is currently being matched.
	- Other operators:
		- Exists operator (`?b`)
			- `$[?@foo]`: Tests if the variable exists.
			- `$[?foo]`: Tests if the group was captured yet.
- `$[==1..2]`: Test if the cursor position is in the range (inclusive)
- `$[!=1..2]`: Test if the cursor position isn't in the range (inclusive)
- `$[==1, 2]`: Test if the cursor position is any one of the two
- `$[foo==bar]`: Compare any two positions against each other.
- `$[==1 | ==2]`: If any one of the clauses match.
- `$[==1 & ==2]`: If both of the clauses match.
	- Has more priority than the OR operator.
- Conditionals:
	- `$[==1|==2]->(a|b)`
		- Tests the clauses one by one, starting from the first.
		- If a clause is true, matches the corresponding expression.
		- If none of the clauses match, fails and starts backtrackting.
		- Tries the other clauses when backtracking.
	- `$[==1|==2|else]->(a|b|c)`: Else clause.
		- The else clause succeeds no matter what.
	- `$[==1 || ==2]->(a|b)`: Possessive.
		- If any clause before the posessive OR succeeds, doesn't try the clauses after it when backtracking.
	- `$[==1|==2]->(a)`
		- If there aren't enough expressions, the extraneous clauses succeed without matching anything.
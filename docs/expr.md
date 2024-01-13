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
	- `\v`: Vertical whitespace
	- `\h`: Horizontal whitespace
	- Inverted version.
		- `\!w`: Non word character
	- Uppercase version.
		- `\^a`: Uppercase letters
	- Lowercase version.
		- `\_a`: Lowercase letters
	- Case insensitive version.
		- `\?a`
		- Useless, since all escapes are case insensitive by default
		- Only implemented for symmetry

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
	- `{a-z}`: Range
		- Any character in the range
	- `{.ws}`: Character class
		- Any character in the class
	- `{?abc}`: Case insensitive
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
	- Equivalent to: `[$(^..0)(abc)]->($!)`
- `(foo;abc)`: Capture group
- `(t:foo;abc)`: Trigger group
	- Not a real group, can't be combined with other types.

You can combine group types.

- `(?foo;abc)`: Case insensitive, capture as "foo".
- `[>foo;abc]`: Optional lookahead, capture as "foo".

## One of

- `(a|b|c)`: One of
	- Gets the items to the edge of the group it's in.
- `[a|b|c]`: Optional one of
- `(a|b|!c)`: Possessive one of
	- If a or b matches, c isn't attempted when backtracking.

## Loops

- Loops can only be after:
	- Groups
	- Chararter sets
	- Escape sequences
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
	- `(abc)*(10..eof)`: 10 or more times (lazy)
	- `(abc)*(eof..10)`: 10 or more times (greedy)
		- You can use `end` instead of `eof`
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
	- Use the break operation `$b`.
	- `(abc$b)+`
	- More useful when combined with conditions:
		- `(abc[d]->($b))+`
			- Matches "abc" repeatedly, but if it finds "d", break.
			- Same as: `(abc)+?d`
- Accepting a loop will result in behavior similar to a `continue` statement:
	- `(abc$a)+`
- If you need to break out of a nested loop, capture it and accept it.
	- `(1:((abc$<a:1>)+)+)`
- If you loop a capturing group, the contents get captured as `foo.0` to `foo.N`.


## Operations

- Accept:
	- `$a`: Stops parsing this group with a success
		- Same as `${g:}`
	- `$A`: Stops parsing the expression with a success
		- Same as `${e:}`
	- `$<a:foo>`: Accept specific group
		- Same as `${foo:}`
- Fail:
	- `$!`: Fail
		- Just a normal mismatch, will backtrack as normal after this.
	- `$f`: Fail group
		- Starts backtracking from the group's start.
		- Must be inside the group.
	- `$F`: Fail expression
	- `$<f:foo>`: Fail specific group
- Fail on backtrack:
	- `>>`: Skip the part of the group before this operation when backtracking.
	- `$p`: Fail group if backtracking is attempted here.
		- This will fail optional groups, unlike `>>`.
	- `$P`: Fail expression if backtracking is attempted here.
	- `$<p:foo>`: Fail specific group if backtracking is attempted here.
		- Must be inside the group.
- Break:
	- `$b`: Stops looping the innermost loop with a success
	- Use the accept operation if you want to break out of nested loops:
		- `(1:((abc$<a:1>)**)**)`
- Skip:
	- `$<s:foo>`: Won't match the group.
	- Must be before the group.
- Skip backtracking:
	- `$<sb:foo>`: Won't re-try the group when backtracking.
	- (Basically makes the group atomic.)
	- Must be after or inside the group.
	- Effect stops when the backtracking goes beyond the mentioned group.

### Built in group names

- `e`: The whole expression.
- `g`: The inner-most group.
- `g0`: The inner-most group.
- `g1`: One group above the inner-most group.
- `gN`: N groups above the inner-most group.

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
	- `:e`: The beginning of this match.
	- `:g`: The beginning of this group.
	- `:foo`: The beginning of a captured match.
	- `foo:`: The end of a captured match.
	- `:foo+1`: One position after the beginning of the captured match.
- `$(+1, +3)`: Multiple destinations. If a position fails, it tries the next one.
- `$(+1..+4)`: Range. If a position fails, it tries the next one.

## Set operations

- `${foo}`: Save the cursor position as foo.
- `${:foo}`: Set the start of a captured group.
- `${foo:}`: Set the end of a captured group.
	- Ends parsing the group with a success if the group wasn't finished yet.
- `${:e}`: Set the start of this match.
- `${e:}`: Set the end of this match.
	- Ends parsing with a success.
- `${:g}`: Set the start of this group.
- `${g:}`: Set the end of this group.
	- Ends parsing the group with a success if the group wasn't finished yet.
- `${foo=1}`: Assign any position to a variable.
	- Works with variables and captured matches:
		- `${foo=bar}`
		- `${foo=:bar}` `${foo=bar:}`
	- Works with operations:
		- `${foo=1+2}`.
	- The allowed operations are:
		- `(a)`: Parentheses
		- `a+b`: Addition
		- `a-b`: Subtraction
		- `a*b`: Multiplication
		- `a/b`: Division (integer)
		- `a%b`: Modulo
	- Works with relative positions:
		- `${foo=^}`: The position of the cursor.
		- `${foo=-1}`: One position before the cursor.
		- `${foo=+1}`: One position after the cursor.
		- While there is no ambiguity, I'd recommend using parentheses when combining with other operations.
			- `${foo=bar+(+1)}`
		- Or you can use the position of the cursor.
			- `${foo=bar+(^+1)}`
- `${foo+=1}`: Modify a variable.
	- The allowed operations are:
		- `+=`: Increase
		- `-=`: Decrease
		- `*=`: Multiply
		- `/=`: Divide (integer)
		- `%=`: Modulo
- `${foo=1;bar=2}`: Multiple operations.

## Compare operations

- `$(==1)`: Test if the cursor position is equal to 1.
	- Works with other operations:
		- `<` `>` `<=` `>=` `!=`
- `$(foo?)`: Tests if the variable exists.
- `$(:foo?)`: Tests if the group was captured.
- `$(==1..2)`: Test if the cursor position is in the range (inclusive)
- `$(!=1..2)`: Test if the cursor position isn't in the range (inclusive)
- `$(==1, 2)`: Test if the cursor position is any one of the two
- `$(foo==bar)`: Compare any two positions against each other.
- `$(==1 | ==2)`: If any one of the clauses match.
- `$(==1 & ==2)`: If both of the clauses match.
	- Has more priority than the OR operator.

## Matching a captured match

- `\<foo>`
	- Runs a named group again.
	- Re-captures the group as `foo.1` or `foo.N` if it was re-captured before.
- `\<g>`
	- Recurses group.
- `\<e>`
	- Recurses expression.
- `\<foo>`
	- Matches the contents of a captured string of a group.
- `\<foo[1..2]>`
	- Matches a section of the contents of a captured string.



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
- Compare operations:
	- `$(==1|==2)->(a|b)`
		- Tests the clauses one by one, starting from the first.
		- If a clause is true, matches the corresponding expression.
		- If none of the clauses match, fails and starts backtrackting.
		- Tries the other clauses when backtracking.
	- `$(==1|==2|else)->(a|b|c)`: Else clause.
		- The else clause succeeds no matter what.
	- `$(==1 |! ==2)->(a|b)`: Possessive.
		- If a clause before the posessive OR succeeds, doesn't try the clauses after it when backtracking.
	- `$(==1|==2)->(a)`
		- If there aren't enough expressions, the extraneous clauses succeed without matching anything.

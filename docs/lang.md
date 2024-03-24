# Table of contents

- [Table of contents](#table-of-contents)
- [Types](#types)
- [Statements](#statements)
	- [Block](#block)
	- [If operator](#if-operator)
	- [For loops](#for-loops)
	- [While loops](#while-loops)
	- [Generic loops](#generic-loops)
	- [Leave statement](#leave-statement)
	- [Break statement](#break-statement)
	- [Continue statement](#continue-statement)
	- [Return statement](#return-statement)
	- [Delete statement](#delete-statement)
- [Operators](#operators)
	- [Comparison chaining](#comparison-chaining)
	- [Assignment operators](#assignment-operators)
	- [Move operator](#move-operator)
	- [Cascade operator](#cascade-operator)
- [Comprehension](#comprehension)
	- [List comprehension](#list-comprehension)
	- [Dictionary comprehension](#dictionary-comprehension)
- [Patterns](#patterns)
	- [Generic patterns](#generic-patterns)
	- [List patterns](#list-patterns)
	- [Dictionary patterns](#dictionary-patterns)
	- [Examples](#examples)



# Types

Only these simple data types are allowed.

| Type | Example literals | Description |
|:--|:--|:--|
| `unset`	| `unset`							| No value is set.
| `null`	| `null`							| Null value.
| `bool`	| `true` `false`					| Booleans.
| `int`		| `243` `0b11110011` `0xF3` `0o363`	| Integers.
| `float`	| `1.0` `1.` `.5` `1.2e-3` `3.e2`	| Floating point numbers.
| `str`		| `"normal"` `r"raw"` `#"foo"#`		| Text strings.
| `list`	| `[1, "ay", false]`				| Ordered lists.
| `dict`	| `{"key":"value","key2":false}`	| Dictionaries / hashmaps.
| `type`	| `int` `float` `type`				| Type of types.

The keys and values in lists and dictionaries can be of any type. Multiple types can be mixed.

The type of `null` is `null` itself, instead of `type`. \
`null is null == true` \
`null is type == false`.

The type of `unset` is `unset` itself, instead of `type`. \
`unset is unset == true` \
`unset is type == false`.

The type of `type` is `type`. \
`type is type == true`.



# Statements

Any expression is a valid statement

## Block

`{statement; statement; statement}`

Returns the value of the last statement.

Returns `unset` if the last statement ends with a semicolon.

## If operator

`if cond {}` \
`if cond {} else {}` \
`if cond {} elif cond {} else {}`

The value of the expression that was ran is returned. \
If there is no else clause and the conditions fails, returns `unset`

## For loops

`for pattern in l {}`

## While loops

`while cond {}`

## Generic loops

`loop {}` \
`loop count {}`

## Leave statement

`leave;` \
Leaves the current block earlier.

`leave value;` \
Leaves the current block with a return value.

## Break statement

`break;` \
Stops the innermost loop.

`break <label>;` \
Stops the specified loop.

`break value;` \
Stops the innermost loop with a return value.

`break <label> value;` \
Stops the specified loop with a return value.

## Continue statement

`continue;` \
Stops this iteration of the innermost loop.

`continue <label>;` \
Stops this iteration of the specified loop.

`break value;` \
Stops this iteration with a return value. \
(Only useful for list comprehension)

`break <label> value;` \
Stops this iteration with a return value. \
(Only useful for list comprehension)

## Return statement

`return` \
Stops the whole expression.

`return <label>` \
Stops the specified expression.

`return value` \
Stops the whole expression with a return value.

`return <label> value` \
Stops the specified expression with a return value.

## Delete statement

`del var` \
Unsets the variable.

`var = unset` isn't allowed.



# Operators

Prioritized in the orded listed.

| Symbol | Associativity | Name |
|:--|:-:|:--|
| `()`							| L > R	| Parentheses.
| `x.y` `x?.y`					| L > R	| Element access.
| `x[y]` `x?[y]`				| L > R	| Index operator.
| `**`							| R > L	| Exponentiation.
| `+x` `-x` `~x`				| R > L	| Unary plus, unary minus, and bitwise NOT.
| `*` `/` `//` `%`				| L > R	| Multiplication, division, integer division, and modulus.
| `+` `-`						| L > R	| Addition and subtraction.
| `<<` `>>`						| L > R	| Bitwise shifts.
| `&`							| L > R	| Bitwise AND.
| `^`							| L > R	| Bitwise XOR.
| `\|`							| L > R	| Bitwise OR.
| `x ?? y`						| L > R	| `x` if `x` isn't `null`, otherwise `y`.
| `==` `!=` `>` `>=` `<` `<=`	| -		| Comparisons.****
| `in` `not in`					| -		| Test for items.
| `is` `is not`					| -		| Type checks. (Not identity checks.)
| `not` `!`						| R > L	| Logical NOT.
| `and` `&&`					| L > R	| Logical AND.
| `or` `\|\|`					| L > R	| Logical OR.
| `..` `?..`					| L > R	| Cascade (dart like).
| `=` `<-` ...					| -		| Assignment and move.

## Comparison chaining

Comparison operators can be chained. \
`0 <= x <= 5` \
`1 < 2 >= 0 == 0 <= 4`

Each operator compares the values adjacent to it. All comparisons must match to return true.

## Assignment operators

Assignments can't be chained.

Assignments return null.

The operators that can be combined with assignments are: \
`**=` `//=` `%=` `*=` `/=` `+=` `-=` `>>=` `<<=` `&=` `^=` `|=` `??=`

`a += b` is equivalent to `a = a + b`

## Move operator

`x <- y` \
Copies the value into `x`, then deletes `y`.

Equivalent to: \
`x = y; del y`

## Cascade operator

Member access that returns the original object.

```
x = [0, 1, 2]
..append(3)
..insert(0, 2)
```



# Comprehension

## List comprehension

`[0, 10, 3, {x} for x in range(10), {10} if (1 < it < 10)]`

## Dictionary comprehension

# Patterns

Can be used in assignments and for loops.

Useful when combined with the move operator.

The variables in the pattern don't need to exist.

## Generic patterns

`x = var` \
Stores the value as `x`. Always successful.

`_ = var` \
Skips this value. Always successful.

`x | y | z = var` \
Tries to match at least one of the patterns, going left to right.

`x if y = var` \
Tries to match the pattern `y`, if it succeeds, attempts `x`. \
Succeeds if both succeed.

`x = {var} if (it == 1)`

## List patterns

Prioritized as necessary.

`[p, p, p] = list` \
Unpacks the list into the patterns.

`[p, p, ..., p, p] = list` \
Skips the items in between.

`[p, p, *l, p, p] = list` \
Sends the remaining items into the pattern `l` as a list.

`[p, l*2, p] = list` \
Sends 2 of the items into the pattern `l` as a list.

## Dictionary patterns

Prioritized as ordered in the pattern.

`{k: v} = dict` \
Gets any key value pair that matches both of the patterns.

`{*k: v} = dict` \
Gets all remaining keys whose values match the pattern `v`. \
You can't store in `v`.

`{k: *v} = dict` \
Gets all remaining values whose keys match the pattern `k`. \
You can't store in `v`.

`{*k: *v} = dict` \
Sends the remaining keys and values to `k` and `v` as a list.

`{**d} = dict` \
Sends the remaining items into the pattern `d` as a dictionary.

## Examples

| Example | Explanation |
|:--|:--|
| `[x, y, z] = pos` | Unpacks a list.
| `[name, ...] <- names` | Pops the first item of the list.
| `[_, name, ...] = names` | Gets the second item of the list.
| `{*id: "apple"\|"banana"} = fruits` | Gets the ids of entries with one of those values.
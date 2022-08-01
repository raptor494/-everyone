# @everyone
[@everyone](https://esolangs.org/wiki/@everyone) is an Estoeric Programming language created by wiki user [Lemonz](https://esolangs.org/wiki/User:Lemonz). Read about the language here: https://esolangs.org/wiki/@everyone.

# Usage
Requires Python 3.10 or higher.
Run a program by doing `python -m at_everyone <filename>`.

# Implementation Notes
Since the wiki page was unclear about a few things, I shall clarify:
* The `STOP POSTING MEMES` and `NOT PAST HERE` statements end a conditional block started with `IF @EVERYONE FINALLY IS [number/string] THEN` OR ends a loop started with `WHILE @EVERYONE FINALLY IS [number/string]`. Both are equivalent.

Additionally, if `language_extensions` is set to `True` in [options.py](at_everyone/options.py), the following extensions become available:
1. `SO IF THAT WASNT TRUE AND @EVERYONE FINALLY IS [number/string] THEN` statement, so you don't need multiple `STOP POSTING MEMES` to close an IF/ELSE block with multiple clauses.

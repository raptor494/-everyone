from __future__ import annotations
from typing import TYPE_CHECKING, overload, cast, Iterable, Collection, Sequence
import re
from .tree import *
import at_everyone.options as options
from dataclasses import dataclass

class OptionBasedRegex:
    def __init__(self, strict: str | re.Pattern[str] | Sequence[str | re.Pattern[str]], lenient: str | re.Pattern[str] | Sequence[str | re.Pattern[str]] | None=None, option: str='lenient_syntax'):
        def compile_regex(arg: str | re.Pattern[str] | Sequence[str | re.Pattern[str]], /):
            match arg:
                case str(s) | [str(s) ]:
                    return re.compile(s)
                case (re.Pattern() as pat) | [re.Pattern() as pat]:
                    return pat
                case _:
                    res = tuple(re.compile(e) if isinstance(e, str) else e for e in arg)
                    if not res:
                        raise ValueError("empty sequence given")
                    return res
        self.strict = compile_regex(strict)
        self.lenient = self.strict if lenient is None else compile_regex(lenient)
        self.option = option

    def regex(self, _options_dict: dict[str,bool]=vars(options), /):
        return self.lenient if _options_dict.get(self.option, getattr(options, self.option)) else self.strict

    @overload
    def fullmatch(self, _options_dict: dict[str,bool], /, string: str, pos: int=..., endpos: int=...) -> re.Match[str] | None: ...
    @overload
    def fullmatch(self, _options_dict: dict[str,bool], /, string: str) -> re.Match[str] | None: ...

    def fullmatch(self, _options_dict: dict[str,bool], /, *args, **kwargs):
        options = self.regex(_options_dict)
        if isinstance(options, re.Pattern):
            return options.fullmatch(*args, **kwargs)
        else:
            for regex in options:
                if m := regex.fullmatch(*args, **kwargs):
                    return m
            return None

class OptionBasedStr:
    def __init__(self, strict: str | re.Pattern[str] | Collection[str], lenient: str | re.Pattern[str] | Collection[str] | None=None, option: str='lenient_syntax'):
        self.strict = strict
        self.lenient = lenient if lenient is not None else self.strict
        self.option = option

    def options(self, _options_dict: dict[str,bool]=vars(options), /):
        return self.lenient if _options_dict.get(self.option, getattr(options, self.option)) else self.strict

    @overload
    def fullmatch(self, _options_dict: dict[str,bool], /, string: str, pos: int=..., endpos: int=...) -> bool: ...
    @overload
    def fullmatch(self, _options_dict: dict[str,bool], /, string: str) -> bool: ...

    def fullmatch(self, _options_dict: dict[str,bool], /, string: str, pos: int | None=None, endpos: int | None=None) -> bool:
        options = self.options(_options_dict)
        if isinstance(options, str):
            return options == string[pos:endpos]
        elif isinstance(options, re.Pattern):
            if pos is not None and endpos is not None:
                return bool(options.fullmatch(string, pos, endpos))
            elif pos is not None:
                return bool(options.fullmatch(string, pos))
            elif endpos is not None:
                return bool(options.fullmatch(string, endpos=endpos))
            else:
                return bool(options.fullmatch(string))
        else:
            return string[pos:endpos] in options
        

UNSIGNED_NUM_REGEX = re.compile(r'[0-9]+|0[xX][0-9a-fA-F]+')
NUM_REGEX = re.compile(rf'-?{UNSIGNED_NUM_REGEX.pattern}')

OPERAND = r'"(?:[^"\\\r\n]|\\.)*"|[^"\s].*(?<=\S)'

PROGRAM_START = OptionBasedStr("HI EVERYONE")
COMMENT = OptionBasedRegex(strict=r'BY THE WAY YALL, (\S.*)', lenient=r'BY THE WAY YALL,?(.*)')
SET_VARIABLE = OptionBasedRegex(strict=rf'@(\S+) YOU ARE NOW OFFICIALLY ({OPERAND})', lenient=(rf'@(\S+), YOU ARE NOW OFFICIALLY ({OPERAND})', rf'@(\S+) YOU ARE NOW OFFICIALLY ({OPERAND})'))
VARIABLE = re.compile(r'@(\S+)')
PRINT_VARIABLE = OptionBasedRegex(strict=r'@(\S+) SPEAK', lenient=(r'@(\S+), SPEAK', r'@(\S+) SPEAK'))
PRINT_STRING = OptionBasedRegex(strict=r'UHH SO (\S.*)', lenient=r'UH+ SO (\S.*)')
PRINT_ASCII_CHAR = re.compile(rf'SOMEONE FIND ME AN ASCII TABLE AND TELL ME WHAT ({UNSIGNED_NUM_REGEX.pattern}) IS')
CAUSE_ERROR = OptionBasedStr("OOPS I KILLED CHAT")
OPERATION_BASE = re.compile(rf'(ADD|SUB|MULT|INTDIV|TRUEDIV|MOD|EXP) ({NUM_REGEX.pattern}|@\S+) ({NUM_REGEX.pattern}|@\S+)')
OPERATION = re.compile(rf'{OPERATION_BASE.pattern}(?: @(\S+))?')
GET_INPUT = re.compile(r'GO DM @(\S+)')
NO_NEWLINE_NEXT = OptionBasedStr(strict="I HATE NEWLINES, WHOEVERS POSTING NEXT", lenient=re.compile(r"I HATE NEWLINES,? WHOEVER'?S POSTING NEXT"))
NEGATE_CONDITIONAL = OptionBasedStr(strict="IGNORE THAT VVVVV", lenient=re.compile(r'IGNORE THAT (?:V+|v+|(?:\\/)+)'))
CLEAR_VARIABLE = OptionBasedRegex(strict=r'@(\S+) YALL CAN STOP', lenient=(r"@(\S+), Y'?ALL CAN STOP", r"@(\S+) Y'?ALL CAN STOP"))
CONDITIONAL_END = OptionBasedStr("STOP POSTING MEMES")
WHILE_END = OptionBasedStr("NOT PAST HERE")
CONDITIONAL_BEGIN = OptionBasedRegex(strict=rf'IF @(\S+) FINALLY IS ({OPERAND}) THEN', lenient=(rf'IF @(\S+) FINALLY IS ({OPERAND}), THEN', rf'IF @(\S+) FINALLY IS ({OPERAND}) THEN'))
WHILE_BEGIN = OptionBasedRegex(strict=rf'WHILE @(\S+) FINALLY IS ({OPERAND})')
ELSE = OptionBasedStr(strict="SO IF THAT WASNT TRUE", lenient=re.compile(r"SO IF THAT WASN'?T TRUE"))
CONDITIONAL_ELSE = OptionBasedRegex(strict=rf'SO IF THAT WASNT TRUE AND @(\S+) FINALLY IS ({OPERAND}) THEN', lenient=(rf"SO IF THAT WASN'?T TRUE AND @(\S+) FINALLY IS ({OPERAND}), THEN", rf"SO IF THAT WASN'?T TRUE AND @(\S+) FINALLY IS ({OPERAND}) THEN"))
CONDITIONAL_SKIP_NEXT = re.compile(rf'JUST MAKE SURE THAT @(\S+) IS ({OPERAND})')
LABEL = re.compile(rf'NEXT PERSON TO POST IS MAKING A CHANNEL CALLED #{LABEL_REGEX.pattern}')
GO_TO = re.compile(rf'GO TO #{LABEL_REGEX.pattern}')
END_SUBROUTINE = OptionBasedStr(lenient='GO BACK TO #GENERAL', strict=("GO BACK TO #GENERAL", "GO BACK TO #general"), option='require_uppercase_label_names')
CALL_SUBROUTINE = re.compile(rf'GO TO #{LABEL_REGEX.pattern} BEFORE I DELETE THE CHANNEL')
END_PROGRAM = OptionBasedStr(strict="GTG SRRY", lenient=re.compile(r'GTG,? SO?RRY'))

def _parse_var(s: str, /) -> str | int:
    if s.startswith('@'):
        return s[1:]
    else:
        return int(s, base=0)

def _parse_compare_value(s: str, /) -> Operand:
    if m := VARIABLE.fullmatch(s):
        return Variable(m[1])
    if s.startswith('"'):
        import ast
        try:
            return ast.literal_eval(s)
        except SyntaxError:
            from . import DeadChat
            raise DeadChat from None
    if m := OPERATION_BASE.fullmatch(s):
        return Operation(type=Operation.Type[m[1]], lhs=_parse_var(m[2]), rhs=_parse_var(m[3]))
    return s

if TYPE_CHECKING:
    def parse(
        lines: Iterable[str],
        *,
        require_uppercase_variable_names: bool=False,
        require_uppercase_label_names: bool=False,
        allow_unsafe_variable_names: bool=False,
        lenient_syntax: bool=False,
        language_extensions: bool=False,
        **_options_dict: bool
    ) -> list[Statement]: ...
else:
    def parse(lines: Iterable[str], **_options_dict: bool) -> list[Statement]:
        stmts: list[Statement] = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('~'): continue
            if PROGRAM_START.fullmatch(_options_dict, line):
                stmts.append(ProgramStart())
            elif m := COMMENT.fullmatch(_options_dict, line):
                stmts.append(Comment(m[1]))
            elif m := SET_VARIABLE.fullmatch(_options_dict, line):
                stmts.append(SetVariable(varname=m[1], value=m[2]))
            elif m := VARIABLE.fullmatch(line):
                stmts.append(Variable(varname=m[1]))
            elif m := PRINT_VARIABLE.fullmatch(_options_dict, line):
                stmts.append(PrintVariable(varname=m[1]))
            elif m := PRINT_STRING.fullmatch(_options_dict, line):
                stmts.append(PrintString(message=m[1]))
            elif m := PRINT_ASCII_CHAR.fullmatch(line):
                stmts.append(PrintASCIIChar(ord=int(m[1], base=0)))
            elif CAUSE_ERROR.fullmatch(_options_dict, line):
                stmts.append(CauseError())
            elif m := OPERATION.fullmatch(line):
                stmts.append(Operation(type=Operation.Type[m[1]], lhs=_parse_var(m[2]), rhs=_parse_var(m[3]), varname=m[4]))
            elif m := GET_INPUT.fullmatch(line):
                stmts.append(GetInput(varname=m[1]))
            elif NO_NEWLINE_NEXT.fullmatch(_options_dict, line):
                stmts.append(NoNewlineNext())
            elif NEGATE_CONDITIONAL.fullmatch(_options_dict, line):
                stmts.append(NegateConditional())
            elif m := CLEAR_VARIABLE.fullmatch(_options_dict, line):
                stmts.append(ClearVariable(varname=m[1]))
            elif CONDITIONAL_END.fullmatch(_options_dict, line):
                stmts.append(ConditionalEnd())
            elif WHILE_END.fullmatch(_options_dict, line):
                stmts.append(WhileEnd())
            elif m := CONDITIONAL_BEGIN.fullmatch(_options_dict, line):
                stmts.append(ConditionalBegin(varname=m[1], compare_value=_parse_compare_value(m[2])))
            elif m := WHILE_BEGIN.fullmatch(_options_dict, line):
                stmts.append(WhileBegin(varname=m[1], compare_value=_parse_compare_value(m[2])))
            elif ELSE.fullmatch(_options_dict, line):
                stmts.append(Else())
            elif options.lenient_syntax and (m := CONDITIONAL_ELSE.fullmatch(_options_dict, line)):
                stmts.append(ConditionalElse(varname=m[1], compare_value=_parse_compare_value(m[2])))
            elif m := CONDITIONAL_SKIP_NEXT.fullmatch(line):
                stmts.append(ConditionalSkipNext(varname=m[1], compare_value=_parse_compare_value(m[2])))
            elif m := LABEL.fullmatch(line):
                stmts.append(Label(lblname=m[1]))
            elif m := GO_TO.fullmatch(line):
                stmts.append(GoTo(lblname=m[1]))
            elif END_SUBROUTINE.fullmatch(_options_dict, line):
                stmts.append(EndSubroutine())
            elif m := CALL_SUBROUTINE.fullmatch(line):
                stmts.append(CallSubroutine(lblname=m[1]))
            elif END_PROGRAM.fullmatch(_options_dict, line):
                stmts.append(EndProgram())
            else:
                from . import DeadChat
                raise DeadChat
        return stmts
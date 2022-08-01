from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Type, TypeVar, overload, cast, Sequence
import re
from .tree import *
import at_everyone.options as options
from collections import defaultdict
import functools

class ProgramEnded(Exception): pass

INT_REGEX = re.compile(r'-?[0-9]+')
FLOAT_REGEX = re.compile(r'-?(?:[0-9]+(?:\.[0-9]*(?:[eE][-+]?[0-9]+)?|[eE][-+]?[0-9]+)|\.[0-9]+(?:[eE][-+]?[0-9]+)?)')

if TYPE_CHECKING:
    def evaluate(
        stmts: Sequence[Statement],
        *,
        require_uppercase_variable_names: bool=False,
        require_uppercase_label_names: bool=False,
        allow_unsafe_variable_names: bool=False,
        lenient_syntax: bool=False,
        language_extensions: bool=False,
        bounded_integers: bool=True,
        **_options_dict: bool
    ): ...
else:
    def evaluate(stmts: Sequence[Statement], **_options_dict: bool):
        from . import DeadChat

        stmts = list(stmts)

        def get_option(opt: str, /) -> bool:
            return _options_dict.get(opt, getattr(options, opt))

        if get_option('bounded_integers'):
            from ctypes import c_int64 as int64 # type:ignore
        else:
            class int64:
                def __init__(self, value: int | None=None):
                    self.value = value or 0
                def __repr__(self):
                    return f'int64({self.value!r})'
        
        MIN_INT64 = -9223372036854775808
        MAX_INT64 = 9223372036854775807

        MAX_RECURSION_DEPTH = 16777216

        _T = TypeVar('_T')

        def wrap_int(value: int | _T) -> int64 | _T:
            if isinstance(value, int):
                return int64(value)
            return value
        
        def unwrap_int(value: int64 | _T) -> int | _T:
            if isinstance(value, int64):
                return value.value
            return value

        if get_option('require_uppercase_variable_names'):
            def validate_uppercase_variable_name(stmt: Statement):
                match stmt:
                    case SetVariable(varname) | Variable(varname) | PrintVariable(varname) | GetInput(varname) | ClearVariable(varname):
                        if not varname.isupper():
                            raise DeadChat
                    case Operation():
                        if isinstance(stmt.lhs, str) and not stmt.lhs.isupper():
                            raise DeadChat
                        if isinstance(stmt.rhs, str) and not stmt.rhs.isupper():
                            raise DeadChat
                        if isinstance(stmt.varname, str) and not stmt.varname.isupper():
                            raise DeadChat
                    case WhileBegin(varname, compare_value) | ConditionalBegin(varname, compare_value) | ConditionalElse(varname, compare_value) | ConditionalSkipNext(varname, compare_value):
                        if not varname.isupper():
                            raise DeadChat
                        if isinstance(compare_value, Statement):
                            validate_uppercase_variable_name(compare_value)
            for stmt in stmts:
                validate_uppercase_variable_name(stmt)
        
        if get_option('require_uppercase_label_names'):
            for stmt in stmts:
                match stmt:
                    case Label(lblname) | GoTo(lblname) | CallSubroutine(lblname):
                        if not lblname.isupper():
                            raise DeadChat
        
        if not get_option('language_extensions'):
            for stmt in stmts:
                if isinstance(stmt, ConditionalElse):
                    raise DeadChat

        labels: dict[str, int] = {}
        for i, stmt in enumerate(stmts):
            if not isinstance(stmt, Label): continue
            if stmt.lblname in labels:
                raise DeadChat
            labels[stmt.lblname] = i

        
        BLOCK_CONDITIONAL = 0
        BLOCK_WHILE = 1
        block_stack: list[tuple[Literal[0, 1], int]] = [] # 0 = if, 1 = while
        block_ends: dict[int, int] = {} # mapping of [Statement index]->[End statement index] pairs
        for i, stmt in enumerate(stmts):
            match stmt:
                case GoTo(lblname) | CallSubroutine(lblname):
                    if lblname not in labels:
                        raise DeadChat
                case Else() | ConditionalElse():
                    if not block_stack or (last := block_stack[-1])[0] != BLOCK_CONDITIONAL:
                        raise DeadChat
                    block_ends[last[1]] = i
                    block_stack[-1] = (BLOCK_CONDITIONAL, i)
                case ConditionalEnd() | WhileEnd():
                    if not block_stack:
                        raise DeadChat
                    last = block_stack.pop()
                    block_ends[last[1]] = i
                    if last[0] == BLOCK_WHILE:
                        block_ends[i] = last[1]
                        if not isinstance(stmt, WhileEnd):
                            stmts[i] = WhileEnd()
                    elif last[0] == BLOCK_CONDITIONAL:
                        if not isinstance(stmt, ConditionalEnd):
                            stmts[i] = ConditionalEnd()
                case ConditionalBegin():
                    block_stack.append((BLOCK_CONDITIONAL, i))
                # case WhileEnd():
                #     if not block_stack or (last := block_stack.pop())[0] != BLOCK_WHILE:
                #         raise DeadChat
                #     block_ends[last[1]] = i
                #     block_ends[i] = last[1]
                case WhileBegin():
                    block_stack.append((BLOCK_WHILE, i))
        if block_stack:
            raise DeadChat
        del block_stack
        
        goto_counts: defaultdict[int,int] = defaultdict(lambda: 0)

        i = 0
        variables: dict[str, str | int64 | float] = {}
        return_stack: list[int] = []
        program_started = False
        dont_print_newline_next = False
        invert_next_condition = False
        print_count = 0

        def do_print(*args, **kwargs):
            nonlocal print_count
            print(*args, **kwargs)
            print_count += 1
            if print_count > MAX_RECURSION_DEPTH:
                raise DeadChat("You officially just lit the servers on fire.")

        def get_val(v: str | int, /) -> str | int64 | float:
            if isinstance(v, int):
                if not (MIN_INT64 <= v <= MAX_INT64):
                    raise DeadChat
                return int64(v)
            if not isinstance(v, str):
                return wrap_int(v)
            if v != 'EVERYONE':
                raise DeadChat
            return try_parse(get_everyone())
        
        def try_parse(value: str, /) -> str | int64 | float:
            if FLOAT_REGEX.fullmatch(value):
                return float(value)
            if INT_REGEX.fullmatch(value):
                parsed_value = int(value)
                if not (MIN_INT64 <= parsed_value <= MAX_INT64):
                    raise DeadChat
                return int64(parsed_value)
            return value

        def eval_operation(stmt: Operation) -> str | int64 | float:
            return wrap_int(stmt.type.value(unwrap_int(get_val(stmt.lhs)), unwrap_int(get_val(stmt.rhs))))

        def eval_condition(varname: str, compare_value: Operand | float | int64) -> bool:
            if varname != 'EVERYONE':
                raise DeadChat
            value = try_parse(get_everyone())
            match compare_value:
                case str():
                    compare_value = try_parse(compare_value)
                case int() | int64():
                    pass
                case Operation():
                    if compare_value.varname is not None:
                        raise DeadChat
                    compare_value = eval_operation(compare_value)
                    if isinstance(compare_value, str):
                        compare_value = try_parse(compare_value)
                case Variable():
                    if compare_value.varname != 'EVERYONE':
                        raise DeadChat
                    compare_value = value
            res = unwrap_int(value) == unwrap_int(compare_value)
            return (not res) if invert_next_condition else res

        def get_everyone() -> str:
            return "".join(map(str, map(unwrap_int, variables.values())))

        def set_variable(name: str, value: str | int64 | float):
            variables[name] = value
            everyone = get_everyone()
            if FLOAT_REGEX.fullmatch(everyone):
                float_value = float(everyone)
                if not (-1e303 <= float_value <= 1e303):
                    raise DeadChat("Everyone online hates large numbers, don't force them.")

        def process_statement():
            nonlocal i
            nonlocal program_started, dont_print_newline_next, invert_next_condition
            stmt = stmts[i]
            if not program_started:
                if isinstance(stmt, ProgramStart):
                    program_started = True
                else:
                    raise DeadChat("Did you ever even log on?")
            elif dont_print_newline_next:
                match stmt:
                    case PrintVariable():
                        if stmt.varname != 'EVERYONE':
                            raise DeadChat
                        print(get_everyone(), end="")
                    case PrintString():
                        print(stmt.message, end="")
                    case PrintASCIIChar():
                        print(chr(stmt.ord), end="")
                    case _:
                        raise DeadChat
                dont_print_newline_next = False
            else:
                if invert_next_condition and not isinstance(stmt, ConditionalBegin | WhileBegin | ConditionalSkipNext):
                    raise DeadChat
                match stmt:
                    case ProgramStart():
                        raise DeadChat
                    case EndProgram():
                        raise ProgramEnded
                    case CauseError():
                        raise DeadChat
                    case Comment():
                        pass
                    case SetVariable():
                        variables[stmt.varname] = stmt.value
                    case Variable():
                        if stmt.varname != 'EVERYONE':
                            raise DeadChat
                        get_everyone()
                    case PrintVariable():
                        if stmt.varname != 'EVERYONE':
                            raise DeadChat
                        print(get_everyone())
                    case PrintString():
                        print(stmt.message)
                    case PrintASCIIChar():
                        print(chr(stmt.ord), end="")
                    case Operation():
                        res = eval_operation(stmt)
                        if stmt.varname is not None:
                            variables[stmt.varname] = res
                    case GetInput():
                        variables[stmt.varname] = input()
                    case NoNewlineNext():
                        dont_print_newline_next = True
                    case NegateConditional():
                        invert_next_condition = True
                    case ClearVariable():
                        if stmt.varname != 'EVERYONE':
                            raise DeadChat
                        variables.clear()
                    case WhileBegin():
                        if eval_condition(stmt.varname, stmt.compare_value):
                            goto_counts[i] += 1
                            if goto_counts[i] > MAX_RECURSION_DEPTH:
                                raise DeadChat
                        else:
                            goto_counts[i] = 0
                            i = block_ends[i]
                    case WhileEnd():
                        i = block_ends[i]
                    case ConditionalBegin() | ConditionalElse():
                        if not eval_condition(stmt.varname, stmt.compare_value):
                            i = block_ends[i]
                            if i < len(stmts) and isinstance(stmts[i], ConditionalElse):
                                i -= 1
                    case Else():
                        i = block_ends[i]
                    case ConditionalEnd():
                        pass
                    case Label():
                        pass
                    case GoTo():
                        goto_counts[i] += 1
                        if goto_counts[i] > MAX_RECURSION_DEPTH:
                            raise DeadChat
                        i = labels[stmt.lblname]
                    case EndSubroutine():
                        if not return_stack:
                            raise DeadChat
                        i = return_stack.pop()
                    case CallSubroutine():
                        goto_counts[i] += 1
                        if goto_counts[i] > MAX_RECURSION_DEPTH or len(return_stack) + 1 >= MAX_RECURSION_DEPTH:
                            raise DeadChat
                        return_stack.append(i + 1)
                        i = labels[stmt.lblname]
                    case _:
                        raise DeadChat("Sometimes you should get the right installation for this application.")
                invert_next_condition = False
            i += 1

        try:
            while i < len(stmts):
                process_statement()
        except DeadChat:
            raise
        except ProgramEnded:
            pass
        except Exception:
            raise DeadChat from None
        else:
            import sys
            sys.stderr.write("You must be quite a night owl.\n")
            while True:
                pass


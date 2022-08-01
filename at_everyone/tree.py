from __future__ import annotations
from typing import TypeAlias
import dataclasses; from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum
import operator
import re
import at_everyone.options as options

NEWLINE_REGEX = re.compile(r'[\r\n\f]')
SPACE_REGEX = re.compile(r'\s')
LABEL_REGEX = re.compile(r'[_0-9]+(?:-[_0-9]+)*(?:-[a-z][a-z_0-9]*(?:-[a-z_0-9]+)*|-[A-Z][A-Z_0-9]*(?:-[A-Z_0-9]+)*)')

def _validate_label_name(lblname: str, name: str="label name"):
    if len(lblname) == 0:
        raise ValueError(f"{name} cannot be empty")
    if not LABEL_REGEX.fullmatch(lblname):
        raise ValueError(f"{lblname!r} is not a valid label name")
    if options.require_uppercase_label_names:
        return lblname.upper()    
    else:
        return lblname.lower()

def _validate_variable_name(varname: str, name: str="variable name"):
    if len(varname) == 0:
        raise ValueError(f"{name} cannot be empty")
    if SPACE_REGEX.search(varname):
        raise ValueError(f"{name} cannot have spaces")
    if options.require_uppercase_variable_names:
        return varname.upper()
    else:
        if not options.allow_unsafe_variable_names:
            if varname == 'everyone' or varname == 'EVERYONE':
                return 'EVERYONE'
            if varname.upper() == 'EVERYONE':
                raise ValueError(f"Invalid variable name {varname!r}")
        return varname

@dataclass(frozen=True)
class Statement(ABC):
    @abstractmethod
    def __init__(self): ...

@dataclass(frozen=True)
class ProgramStart(Statement):
    pass

@dataclass(frozen=True)
class Comment(Statement):
    comment: str

    def __post_init__(self):
        if NEWLINE_REGEX.search(self.comment):
            raise ValueError(f"comments cannot contain newlines")

@dataclass(frozen=True)
class SetVariable(Statement):
    varname: str
    value: str | int

    def __post_init__(self):
        object.__setattr__(self, 'varname', _validate_variable_name(self.varname))
        if isinstance(self.value, str) and len(self.value) == 0:
            raise ValueError("value cannot be empty")

@dataclass(frozen=True)
class Variable(Statement):
    varname: str

    def __post_init__(self):
        object.__setattr__(self, 'varname', _validate_variable_name(self.varname))

@dataclass(frozen=True)
class PrintVariable(Statement):
    varname: str

    def __post_init__(self):
        object.__setattr__(self, 'varname', _validate_variable_name(self.varname))

@dataclass(frozen=True)
class PrintString(Statement):
    message: str

@dataclass(frozen=True)
class PrintASCIIChar(Statement):
    ord: int

    def __post_init__(self):
        if not 0 <= self.ord <= 0x7f:
            raise ValueError(f"invalid ASCII char value: {self.ord}")

@dataclass(frozen=True)
class CauseError(Statement):
    pass

@dataclass(frozen=True)
class Operation(Statement):
    class Type(Enum):
        ADD = operator.__add__
        SUB = operator.__sub__
        MULT = operator.__mul__
        INTDIV = operator.__floordiv__
        TRUEDIV = operator.__truediv__
        MOD = operator.__mod__
        EXP = operator.__pow__

    type: Type
    lhs: str | int
    "Left-hand side of binary operation. If a string, then it means retrieve variable."
    rhs: str | int
    "Right-hand side of binary operation. If a string, then it means retrieve variable."
    varname: str | None = None
    "The destination variable, if present."

    def __post_init__(self):
        if isinstance(self.lhs, str):
            object.__setattr__(self, 'lhs', _validate_variable_name(self.lhs, "lhs"))
        if isinstance(self.rhs, str):
            object.__setattr__(self, 'rhs', _validate_variable_name(self.rhs, "rhs"))
        if self.varname is not None:
            object.__setattr__(self, 'varname', _validate_variable_name(self.varname))

Operand: TypeAlias = str | int | Operation | Variable

def _validate_operand(operand: Operand, name: str="operand"):
    match operand:
        case str():
            return _validate_variable_name(operand, name)
        case int() | Operation(varname=None): pass
        case Operation():
            raise ValueError(f"{name}.varname must be None")
        case _:
            raise TypeError(f"{name} must be a string, int, or Operation instance")
    return operand

@dataclass(frozen=True)
class GetInput(Statement):
    varname: str

    def __post_init__(self):
        object.__setattr__(self, 'varname', _validate_variable_name(self.varname))

@dataclass(frozen=True)
class NoNewlineNext(Statement):
    pass

@dataclass(frozen=True)
class NegateConditional(Statement):
    pass

@dataclass(frozen=True)
class ClearVariable(Statement):
    varname: str

    def __post_init__(self):
        object.__setattr__(self, 'varname', _validate_variable_name(self.varname))

@dataclass(frozen=True)
class ConditionalEnd(Statement):
    pass

@dataclass(frozen=True)
class WhileBegin(Statement):
    varname: str
    compare_value: Operand

    def __post_init__(self):
        object.__setattr__(self, 'varname', _validate_variable_name(self.varname))
        object.__setattr__(self, 'compare_value', _validate_operand(self.compare_value, name='compare_value'))

@dataclass(frozen=True)
class ConditionalBegin(Statement):
    varname: str
    compare_value: Operand

    def __post_init__(self):
        object.__setattr__(self, 'varname', _validate_variable_name(self.varname))
        object.__setattr__(self, 'compare_value', _validate_operand(self.compare_value, name='compare_value'))

@dataclass(frozen=True)
class Else(Statement):
    pass

@dataclass(frozen=True)
class ConditionalElse(Statement):
    varname: str
    compare_value: Operand

    def __post_init__(self):
        object.__setattr__(self, 'varname', _validate_variable_name(self.varname))
        object.__setattr__(self, 'compare_value', _validate_operand(self.compare_value, name='compare_value'))

@dataclass(frozen=True)
class WhileEnd(Statement):
    pass

@dataclass(frozen=True)
class ConditionalSkipNext(Statement):
    varname: str
    compare_value: Operand

    def __post_init__(self):
        object.__setattr__(self, 'varname', _validate_variable_name(self.varname))
        object.__setattr__(self, 'compare_value', _validate_operand(self.compare_value, name='compare_value'))

@dataclass(frozen=True)
class Label(Statement):
    lblname: str

    def __post_init__(self):
        object.__setattr__(self, 'lblname', _validate_label_name(self.lblname))

@dataclass(frozen=True)
class GoTo(Statement):
    lblname: str

    def __post_init__(self):
        object.__setattr__(self, 'lblname', _validate_label_name(self.lblname))

@dataclass(frozen=True)
class EndSubroutine(Statement):
    pass

@dataclass(frozen=True)
class CallSubroutine(Statement):
    lblname: str

    def __post_init__(self):
        object.__setattr__(self, 'lblname', _validate_label_name(self.lblname))

@dataclass(frozen=True)
class EndProgram(Statement):
    pass

def to_code(stmt: Statement) -> str:
    def op_str(value: Operand) -> str:
        match value:
            case str():
                if not value or value.startswith('"') or value[0].isspace() or value[-1].isspace():
                    return repr(value)
                return value
            case int():
                return repr(value)
            case Operation():
                return to_code(value)
            case Variable():
                return value.varname
    match stmt:
        case ProgramStart():
            return "HI EVERYONE"
        case Comment():
            return f"BY THE WAY YALL, {stmt.comment}"
        case SetVariable():
            return f"@{stmt.varname} YOU ARE NOW OFFICIALLY {stmt.value}"
        case Variable():
            return f"@{stmt.varname}"
        case PrintVariable():
            return f"@{stmt.varname} SPEAK"
        case PrintString():
            return f"UHH SO {stmt.message}"
        case PrintASCIIChar():
            return f"SOMEONE FIND AN ASCII TABLE AND TELL ME WHAT {stmt.ord} IS"
        case CauseError():
            return "OOPS I KILLED CHAT"
        case Operation():
            result = f"{stmt.type.name} {op_str(stmt.lhs)} {op_str(stmt.rhs)}"
            if stmt.varname is not None:
                result += f" @{stmt.varname}"
            return result
        case GetInput():
            return f"GO DM @{stmt.varname}"
        case NoNewlineNext():
            return "I HATE NEWLINES, WHOEVERS POSTING NEXT"
        case NegateConditional():
            return "IGNORE THAT VVVVV"
        case ClearVariable():
            return f"@{stmt.varname} YALL CAN STOP"
        case ConditionalEnd():
            return "STOP POSTING MEMES"
        case WhileBegin():
            return f"WHILE @{stmt.varname} FINALLY IS {op_str(stmt.compare_value)}"
        case ConditionalBegin():
            return f"IF @{stmt.varname} FINALLY IS {op_str(stmt.compare_value)} THEN"
        case Else():
            return "SO IF THAT WASNT TRUE"
        case ConditionalSkipNext():
            return f"JUST MAKE SURE THAT @{stmt.varname} IS {op_str(stmt.compare_value)}"
        case Label():
            return f"NEXT PERSON TO POST IS MAKING A CHANNEL CALLED #{stmt.lblname}"
        case GoTo():
            return f"GO TO #{stmt.lblname}"
        case EndSubroutine():
            if options.require_uppercase_label_names:
                return "GO BACK TO #GENERAL"
            else:
                return "GO BACK TO #general"
        case CallSubroutine():
            return f"GO TO #{stmt.lblname} BEFORE I DELETE THE CHANNEL"
        case EndProgram():
            return "GTG SRRY"
        case _:
            raise TypeError(f"unsupported Statement type {type(stmt).__name__}")

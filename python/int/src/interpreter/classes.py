"""Runtime object model classes for the SOL interpreter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast, override

from interpreter.error_codes import ErrorCode
from interpreter.exceptions import InterpreterError


class Object:
    """main class object"""

    def __init__(self, *args: Any) -> None:
        """Initialize object with arguments."""
        self.args = args

    def asString(self) -> Any:
        """Convert object to string representation."""
        return ""

    def identicalTo(self, obj: Object) -> bool:
        """Check if objects are identical."""
        return self is obj

    @classmethod
    def new(cls, *args: Any) -> Any:
        """Create new instance of class."""
        return cls(*args)

    def equalTo(self, obj: Any) -> bool:
        """Check if objects are equal."""
        ret_val = self.identicalTo(obj)
        return ret_val

    def isNumber(self) -> bool:
        """Check if object is a number."""
        return False

    def isString(self) -> bool:
        """Check if object is a string."""
        return False

    def isBlock(self) -> bool:
        """Check if object is a block."""
        return False

    def isNil(self) -> bool:
        """Check if object is nil."""
        return False

    def isBoolean(self) -> bool:
        """Check if object is boolean."""
        return False


class Nil(Object):
    """Nil object with inherited methods from parent Object"""

    instance = Object()

    @override
    def asString(self) -> str:
        """Return nil as string."""
        return "nil"

    @classmethod
    def new(cls) -> Any:
        """Get nil instance."""
        return cls.instance

    @classmethod
    def from_(cls) -> Any:
        """Get nil instance from class."""
        return cls.instance


class Integer(Object):
    """Integer object with inherited methods from parent Object"""

    def __init__(self, value: Any = 0):
        """Initialize integer with value."""
        self.value = value

    @classmethod
    def new(cls, *args: Any) -> Any:
        """Create new integer instance."""
        return cls(*args)

    def equalTo(self, obj: Integer) -> Any:
        """Check if integers are equal."""
        if not isinstance(cast(Any, obj).parent, Integer):
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "equalTo: expected Integer operand")
        return self.value == obj.value

    @override
    def asString(self) -> str:
        """Convert integer to string."""
        return str(self.value)

    def isNumber(self) -> bool:
        """Check if object is number."""
        return True

    def greaterThan(self, obj: Integer) -> bool:
        """Check if greater than another integer."""
        if not isinstance(cast(Any, obj).parent, Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "greaterThan: expected Integer operand")
        return True if self.value > obj.value else False

    def plus(self, obj: Integer) -> int:
        """Add two integers."""
        if not isinstance(cast(Any, obj).parent, Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "plus: expected Integer operand")
        return int(self.value + obj.value)

    def minus(self, obj: Integer) -> int:
        """Subtract two integers."""
        if not isinstance(cast(Any, obj).parent, Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "minus: expected Integer operand")
        return int(self.value - obj.value)

    def multiplyBy(self, obj: Integer) -> int:
        """Multiply two integers."""
        if not isinstance(cast(Any, obj).parent, Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "multiplyBy: expected Integer operand")
        return int(self.value * obj.value)

    def divBy(self, obj: Integer) -> int:
        """Divide two integers."""
        if not isinstance(cast(Any, obj).parent, Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "divBy: expected Integer operand")
        if obj.value == 0:
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "Division by zero is not allowed.")
        return int(self.value // obj.value)

    def asInteger(self) -> Any:
        """Convert to integer."""
        return Integer(self)

    def timesRepeat(self, n: int, block: Block_) -> Any:
        """Repeat block n times."""
        if n <= 0:
            return Nil()

        result = None
        for i in range(1, n + 1):
            result = block.value(i)
        return result


class String(Object):
    """String object with inherited methods from parent Object"""

    def __init__(self, string: str = ""):
        """Initialize string with value."""
        self.string = string

    @classmethod
    def new(cls, *args: Any) -> Any:
        """Create new instance of String"""
        return cls(*args)

    @classmethod
    def read(cls) -> String:
        """Read string from input."""
        return cls(input())

    def print(self) -> Any:
        """Print string and return self."""
        print(self.string)
        return self

    def equalTo(self, obj: String) -> bool:
        """Check if strings are equal."""
        if not isinstance(cast(Any, obj).parent, String):
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "equalTo: expected String operand")
        return bool(self.string == cast(Any, obj).value)

    @override
    def asString(self) -> str:
        """Convert to string."""
        return str(self.string)

    def asInteger(self) -> Integer | Nil:
        """Convert string to integer."""
        if self.string.isdigit():
            return Integer(int(self.string))
        return Nil()

    def concatenateWith(self, obj: String) -> Any:
        """Concatenate with another string."""
        return String(self.string + cast(Any, obj).value)  # ?? String()

    def startsWithEndsBefore(self, index_start: int, index_end: int) -> Any:
        """Get substring between indices."""
        if index_start <= 0 or index_end <= 0:
            return Nil()
        if index_start < 1:
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "indexing from 1")
        if (index_start - index_end) >= 0:
            return ""
        if index_end > len(self.string):
            return self.string[index_start - 1 :]
        return self.string[index_start - 1 : index_end - 1]

    def length(self, obj: String) -> Integer:
        """Get string length."""
        if not isinstance(cast(Any, obj).parent, String):
            raise InterpreterError(ErrorCode.INT_OTHER, "length: expected String operand")
        leng = len(cast(Any, obj).value) + 1  # null terminator
        return Integer(leng)


class Block_(Object):
    """Block object with inherited methods from parent Object"""
    def __init__(self, func: Callable[..., Any] | None = None) -> None:
        """Initialize block with function."""
        if func is None:
            self.func: Callable[..., Any] = lambda: None
        else:
            self.func = func

    @classmethod
    def new(cls) -> Any:
        """Create new block instance."""
        return cls()

    def value(self, *args: Any) -> Any:
        """Execute block with arguments."""
        return self.func(*args)  # idk ci dobre

    def whileTrue(self, body: Block_) -> Any:
        """Execute while condition is true."""
        result = None
        while self.value():
            result = body.value()
        return result


class True_(Object):
    """True object with inherited methods from parent Object"""

    def __init__(self, boolean: bool) -> None:
        """Initialize true boolean."""
        self.boolean = boolean

    @classmethod
    def new(cls) -> Any:
        """Create new instance of String"""
        return cls.boolean

    @override
    def asString(self) -> str:
        """Convert true to string."""
        return "true"

    def not_(self, obj: True_) -> bool:
        """Negate true boolean."""
        return not (obj)

    def ifTrueIfFalse(self, condition: bool, true_block: Block_, false_block: Block_) -> Any:
        if condition:
            return true_block.value()
        return false_block.value()

    def isBoolean(self) -> bool:
        """Check if object is boolean."""
        return True


class False_(Object):
    """False object with inherited methods from parent Object"""

    def __init__(self, boolean: bool) -> None:
        """Initialize false boolean."""
        self.boolean = boolean

    @classmethod
    def new(cls) -> Any:
        """Create new instance of String"""
        return cls(False)

    @override
    def asString(self) -> str:
        """Convert false to string."""
        return "false"

    def not_(self, obj: False_) -> bool:
        """Negate false boolean."""
        return not (obj)

    def and_(self) -> Any:
        """Logical AND operation."""
        if cast(Any, self).bool is False:
            return False
        return None

    def ifTrueIfFalse(self, condition: bool, true_block: Block_, false_block: Block_) -> Any:
        if condition:
            return true_block.value()
        return false_block.value()

    def isBoolean(self) -> bool:
        """Check if object is boolean."""
        return True

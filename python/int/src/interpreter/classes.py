"""Runtime object model classes for the SOL interpreter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast, override

from interpreter.error_codes import ErrorCode
from interpreter.exceptions import InterpreterError

# class BaseObject:
#     """base class for all objects"""
#     def __init__(self, *args: Any) -> None:
#         """Initialize object with arguments."""
#         self.args = args


class Object:
    """main class object"""

    def __init__(self, *args: Any) -> None:
        """Initialize object with arguments."""
        self.args = args

    def as_string(self) -> Any:
        """Convert object to string representation."""
        return ""

    def identical_to(self, obj: Object) -> bool:
        """Check if objects are identical."""
        return self is obj

    @classmethod
    def new(cls, *args: Any) -> Any:
        """Create new instance of class."""
        return cls(*args)

    def equal_to(self, obj: Any) -> bool:
        """Check if objects are equal."""
        # removed ret_val
        return self.identical_to(obj)

    def is_number(self) -> bool:
        """Check if object is a number."""
        return False

    def is_string(self) -> bool:
        """Check if object is a string."""
        return False

    def is_block(self) -> bool:
        """Check if object is a block."""
        return False

    def is_nil(self) -> bool:
        """Check if object is nil."""
        return False

    def is_boolean(self) -> bool:
        """Check if object is boolean."""
        return False


class Nil(Object):
    """Nil object with inherited methods from parent Object"""

    instance = Object()

    @override
    def as_string(self) -> str:
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

    def equal_to(self, obj: Integer) -> Any:
        """Check if integers are equal."""
        if not isinstance(cast(Any, obj).parent, Integer):
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "equalTo: expected Integer operand")
        return self.value == obj.value

    @override
    def as_string(self) -> str:
        """Convert integer to string."""
        return str(self.value)

    def is_number(self) -> bool:
        """Check if object is number."""
        return True

    def greater_than(self, obj: Integer) -> Any:
        """Check if greater than another integer."""
        if not isinstance(cast(Any, obj).parent, Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "greaterThan: expected Integer operand")
        return self.value > obj.value

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

    def multiply_by(self, obj: Integer) -> int:
        """Multiply two integers."""
        if not isinstance(cast(Any, obj).parent, Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "multiplyBy: expected Integer operand")
        return int(self.value * obj.value)

    def div_by(self, obj: Integer) -> int:
        """Divide two integers."""
        if not isinstance(cast(Any, obj).parent, Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "divBy: expected Integer operand")
        if obj.value == 0:
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "Division by zero is not allowed.")
        return int(self.value // obj.value)

    def as_integer(self) -> Any:
        """Convert to integer."""
        return Integer(self)

    def times_repeat(self, n: int, block: BlockClass) -> Any:
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
    # def new(cls, string: str) -> Any:
    #     """Create new instance of String"""
    #     print("new String")
    #     return cls(string)
    # # @classmethod
    # def new(cls, string: Integer) -> Any:
    #     return cls(str(string.value))
    @classmethod
    def new(cls, string: String) -> Any:
        """Create new instance of String from String."""
        print("new String from String")
        return cls(string.string)

    @classmethod
    def read(cls) -> String:
        """Read string from input."""
        return cls(input())

    def print(self) -> Any:
        """Print string and return self."""
        print(self.string)
        return self

    def equal_to(self, obj: String) -> bool:
        """Check if strings are equal."""
        if not isinstance(cast(Any, obj).parent, String):
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "equalTo: expected String operand")
        return bool(self.string == cast(Any, obj).value)

    @override
    def as_string(self) -> str:
        """Convert to string."""
        return str(self.string)

    def as_integer(self) -> Integer | Nil:
        """Convert string to integer."""
        if self.string.isdigit():
            return Integer(int(self.string))
        return Nil()

    def concatenate_with(self, obj: String) -> Any:
        """Concatenate with another string."""
        return String(self.string + cast(Any, obj).value)  # ?? String()

    def starts_with_ends_before(self, index_start: int, index_end: int) -> Any:
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


class BlockClass(Object):
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

    def while_true(self, body: BlockClass) -> Any:
        """Execute while condition is true."""
        result = None
        while self.value():
            result = body.value()
        return result


class TrueR(Object):
    """True object with inherited methods from parent Object"""

    def __init__(self, boolean: bool) -> None:
        """Initialize true boolean."""
        self.boolean = boolean

    @classmethod
    def new(cls) -> Any:
        """Create new instance of String"""
        return cls.boolean

    @override
    def as_string(self) -> str:
        """Convert true to string."""
        return "true"

    def not_(self, obj: TrueR) -> bool:
        """Negate true boolean."""
        return not (obj)

    def if_true_if_false(
        self, condition: bool, true_block: BlockClass, false_block: BlockClass
    ) -> Any:
        """Execute if true or false block."""
        if condition:
            return true_block.value()
        return false_block.value()

    def is_boolean(self) -> bool:
        """Check if object is boolean."""
        return True

    def and_(self, obj: Any) -> Any:
        """Logical AND operation."""
        return bool(self.boolean is True and obj.boolean is True)

    def or_(self, obj: Any) -> Any:
        """Logical OR operation."""
        return bool(self.boolean is True or obj.boolean is True)


class FalseR(Object):
    """False object with inherited methods from parent Object"""

    def __init__(self, boolean: bool) -> None:
        """Initialize false boolean."""
        self.boolean = boolean

    @classmethod
    def new(cls) -> Any:
        """Create new instance of String"""
        return cls(False)

    @override
    def as_string(self) -> str:
        """Convert false to string."""
        return "false"

    def not_(self, obj: FalseR) -> bool:
        """Negate false boolean."""
        return not (obj)

    def and_(self, obj: Any) -> Any:
        """Logical AND operation."""
        return bool(self.boolean is True and obj.boolean is True)

    def if_true_if_false(
        self, condition: bool, true_block: BlockClass, false_block: BlockClass
    ) -> Any:
        """Execute if true or false block."""
        if condition:
            return true_block.value()
        return false_block.value()

    def is_boolean(self) -> bool:
        """Check if object is boolean."""
        return True

    def or_(self, obj: Any) -> Any:
        """Logical OR operation."""
        return bool(self.boolean is True or obj.boolean is True)

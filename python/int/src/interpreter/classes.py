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

    def as_string(self) -> String:
        """Convert object to string representation."""
        return String("")

    def identical_to(self, obj: Object) -> bool:
        """Check if objects are identical."""
        print(f"self: {self}, obj: {obj}, {type(obj)}")
        return TrueR(True) if self is obj else FalseR(False)

    @classmethod
    def new(cls, *args: Any) -> Any:
        """Create new instance of class."""
        return cls(*args)

    def equal_to(self, obj: Any) -> bool:
        """Check if objects are equal."""
        # removed ret_val
        return self.identical_to(obj)

    def is_number(self) -> FalseR:
        """Check if object is a number."""
        return TrueR(True) if isinstance(self, Integer) else FalseR(False)

    def is_string(self) -> FalseR:
        """Check if object is a string."""
        return TrueR(True) if isinstance(self, String) else FalseR(False)

    def is_block(self) -> FalseR:
        """Check if object is a block."""
        return TrueR(True) if isinstance(self, BlockClass) else FalseR(False)

    def is_nil(self) -> FalseR:
        """Check if object is nil."""
        return TrueR(True) if isinstance(self, Nil) else FalseR(False)

    def is_boolean(self) -> FalseR:
        """Check if object is boolean."""
        return FalseR(False)



class Nil(Object):
    """Nil object with inherited methods from parent Object"""

    instance = Object()

    @override
    def as_string(self) -> String:
        """Return nil as string."""
        return String("nil")

    @classmethod
    def new(cls) -> Any:
        """Get nil instance."""
        return cls.instance
    @classmethod
    def new(cls, value: Any) -> Any:
        """Create new nil instance from value."""
        return cls(value)

    def identical_to(self, obj: any) -> bool:
        """Check if objects are identical."""
        if isinstance(obj, Nil):
            return TrueR(True)
        return FalseR(False)
    # @classmethod
    # def from_(cls) -> Any:
    #     """Get nil instance from class."""
    #     return cls.instance

nil = Nil()
class Integer(Object):
    """Integer object with inherited methods from parent Object"""

    def __init__(self, value: Any = 0):
        """Initialize integer with value."""
        if type(value) is str:
            value = int(value)
        elif type(value) is String:
            value = int(value.string)
        elif type(value) is Integer:
            value = value.value
        elif type(value) is TrueR:
            value = 1
        elif type(value) is FalseR:
            value = 0
        elif type(value) is Nil:
            value = 0
        self.value = value

    @classmethod
    def new(cls, *args: Any) -> Any:
        """Create new integer instance."""
        return cls(*args)

    def equal_to(self, obj: Integer) -> Any:
        """Check if integers are equal."""
        if not isinstance(cast(Any, obj), Integer):
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "equalTo: expected Integer operand")
        return TrueR(True) if int(self.value) == int(obj.value) else FalseR(False)

    @override
    def as_string(self) -> String:
        """Convert integer to string."""
        return String(self.value)

    def is_number(self) -> bool:
        """Check if object is number."""
        return TrueR(True)

    def greater_than(self, obj: Integer) -> Any:
        """Check if greater than another integer."""
        if not isinstance(cast(Any, obj), Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "greaterThan: expected Integer operand")
        return TrueR(True) if int(self.value) > int(obj.value) else FalseR(False)

    def plus(self, obj: Integer) -> Integer:
        """Add two integers."""
        if not isinstance(cast(Any, obj), Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "plus: expected Integer operand")
        return Integer(int(int(self.value) + int(obj.value)))

    def minus(self, obj: Integer) -> Integer:
        """Subtract two integers."""
        if not isinstance(cast(Any, obj), Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "minus: expected Integer operand")
        return Integer(int(self.value) - int(obj.value))

    def multiply_by(self, obj: Integer) -> Integer:
        """Multiply two integers."""
        if not isinstance(cast(Any, obj), Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "multiplyBy: expected Integer operand")
        return Integer(int(self.value) * int(obj.value))

    def div_by(self, obj: Integer) -> int:
        """Divide two integers."""
        if not isinstance(cast(Any, obj), Integer):
            raise InterpreterError(ErrorCode.INT_OTHER, "divBy: expected Integer operand")
        if obj.value == 0:
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "Division by zero is not allowed.")
        return Integer(int(self.value) // int(obj.value))

        #Processing: divBy.sol26
        # selector Main run
        # selector Integer divBy:
        # get_variable r {'r': 11}
        # selector int asString
        # Error 51: Method 'asString' not found in class int

    def as_integer(self) -> Any:
        """Convert to integer."""
        return Integer(self)

    def times_repeat(self, block: BlockClass) -> Any:
        """Repeat block n times."""
        if self.value <= 0:
            return Nil()

        result = None
        for i in range(1, self.value + 1):
            result = block.value(Integer(i))
        return result


class String(Object):
    """String object with inherited methods from parent Object"""

    def __init__(self, value: Any = ""):
        """Initialize string with value."""
        if type(value) is Integer:
            value = str(value.value)
        elif type(value) is int:
            value = str(value)
        elif type(value) is String:
            value = value.string
        elif type(value) is Nil:
            value = ""
        elif type(value) is TrueR:
            value = "true"
        elif type(value) is FalseR:
            value = "false"
        self.string = value

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

    def equal_to(self, obj: String) -> bool:
        """Check if strings are equal."""
        if not isinstance(cast(Any, obj), String):
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "equalTo: expected String operand")
        return TrueR(True) if self.string == cast(Any, obj).string else FalseR(False)

    @override
    def as_string(self) -> String:
        """Convert to string."""
        return String(self.string)

    def as_integer(self) -> Integer | Nil:
        """Convert string to integer."""
        if self.string.isdigit():
            return Integer(int(self.string))
        return Nil()

    def concatenate_with(self, obj: String) -> Any:
        """Concatenate with another string."""
        return String(self.string + cast(Any, obj).string)  # ?? String()

    def starts_with_ends_before(self, index_start: Integer, index_end: Integer) -> String:
        """Get substring between indices."""
        if int(index_start.value) <= 0 or int(index_end.value) <= 0:
            return Nil()
        if int(index_start.value) < 1:
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "indexing from 1")
        if (int(index_start.value) - int(index_end.value)) >= 0:
            return String("")
        if int(index_end.value) > len(self.string):
            return String(self.string[int(index_start.value) - 1 :])
        return String(self.string[int(index_start.value) - 1 : int(index_end.value) - 1])

    def length(self) -> Integer:
        """Get string length."""
        if not isinstance(cast(Any, self), String):
            raise InterpreterError(ErrorCode.INT_OTHER, "length: expected String operand")
        leng = len(cast(Any, self).string) + 1  # null terminator
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
        bl = self.value().boolean
        print(f"bl: {bl}, type: {type(bl)}")
        while bl is True:
            result = body.value()
            bl = self.value().boolean
        return result


class TrueR(Object):
    """True object with inherited methods from parent Object"""

    def __init__(self, boolean: bool) -> None:
        """Initialize true boolean."""
        self.boolean = bool(boolean)

    @classmethod
    def new(cls) -> Any:
        """Create new instance of String"""
        return cls.boolean

    @override
    def as_string(self) -> String:
        """Convert true to string."""
        return String("true")

    def not_(self) -> bool:
        """Negate true boolean."""
        return FalseR(False)

    def if_true_if_false(
        self, true_block: BlockClass, false_block: BlockClass
    ) -> Any:
        """Execute if true or false block."""
        if self.boolean is True:
            return true_block.value()
        return false_block.value()

    def is_boolean(self) -> TrueR:
        """Check if object is boolean."""
        return TrueR(True)

    def and_(self, obj: Any) -> Any:
        """Logical AND operation."""
        # print(f"self.boolean: {self.boolean}, obj.boolean: {obj.boolean}")
        if obj.boolean is True:
            return TrueR(True)
        return FalseR(False)

    def or_(self, obj: TrueR | FalseR) -> TrueR | FalseR:
        """Logical OR operation."""
        return TrueR(True) if self.boolean is True or obj.boolean is True else FalseR(False)


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
    def as_string(self) -> String:
        """Convert false to string."""
        return String("false")

    def not_(self) -> bool:
        """Negate false boolean."""
        return TrueR(True)

    def and_(self, obj: Any) -> Any:
        """Logical AND operation."""
        # print(f"self.boolean: {type(self.boolean)}, obj.boolean: {type(obj.boolean)}")

        return FalseR(False)


    def if_true_if_false(
        self, true_block: BlockClass, false_block: BlockClass
    ) -> Any:
        """Execute if true or false block."""
        if self.boolean is True:
            return true_block.value()
        return false_block.value()

    def is_boolean(self) -> bool:
        """Check if object is boolean."""
        return TrueR(True)

    def or_(self, obj: TrueR | FalseR) -> TrueR | FalseR:
        """Logical OR operation."""
        return TrueR(True) if self.boolean is True or obj.boolean is True else FalseR(False)

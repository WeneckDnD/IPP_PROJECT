from __future__ import annotations

from interpreter.error_codes import ErrorCode
from interpreter.exceptions import InterpreterError


class Object:
    """main class object"""

    def __init__(self, *args):
        """Initialize object with arguments."""
        self.args = args

    def asString(self) -> str:
        """Convert object to string representation."""
        return ""

    def identicalTo(self, obj: Object) -> bool:
        """Check if objects are identical."""
        return self is obj

    @classmethod
    def new(cls, *args):
        """Create new instance of class."""
        return cls(*args)

    def equalTo(self, obj: any) -> bool:
        """Check if objects are equal."""
        print(f'OBJ VALUE FROM equalTo: {obj.value}')
        retVal = self.identicalTo(obj)
        print(f'RETVAL FROM equalTo: {retVal}')
        return retVal
        # if obj.attributes == None:
        #     return self.identicalTo(obj)
        # else:
        #     for atr in self.attributes:
        #         if self.attributes[atr] != obj.attributes[atr]:
        #             return False
        # return True

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
    # instance = None

    # def __init__(self):
    #     if self.instance is None:
    #         self.instance = Object()

    def asString(self) -> str:
        """Return nil as string."""
        return "nil"

    @classmethod
    def new(cls):
        """Get nil instance."""
        return cls.instance

    @classmethod
    def from_(cls):
        """Get nil instance from class."""
        return cls.instance


class Integer(Object):
    """Integer object with inherited methods from parent Object"""

    def __init__(self, value: int = 0):
        """Initialize integer with value."""
        self.value = value

    @classmethod
    def new(cls, *args):
        """Create new integer instance."""
        return cls(*args)

    def equalTo(self, obj: Integer) -> bool:
        """Check if integers are equal."""
        return self.value == obj.value

    def asString(self) -> str:
        """Convert integer to string."""
        return str(self.value)

    def isNumber(self) -> bool:
        """Check if object is number."""
        return True

    def greaterThan(self, obj: Integer) -> bool:
        """Check if greater than another integer."""
        return self.value > obj.value

    def plus(self, obj: Integer) -> int:
        """Add two integers."""
        print(f'PRINT CALLED {self.value} + {obj.value}')
        return self.value + obj.value

    def minus(self, obj: Integer) -> int:
        """Subtract two integers."""
        return self.value - obj.value

    def multiplyBy(self, obj: Integer) -> int:
        """Multiply two integers."""
        return self.value * obj.value

    def divBy(self, obj: Integer) -> int:
        """Divide two integers."""
        if obj.value == 0:
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "Division by zero is not allowed.")
        return self.value // obj.value

    def asInteger(self) -> Integer:
        """Convert to integer."""
        return Integer(self)

    def timesRepeat(self, n: int, block: Block):
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
    def new(cls, *args):
        """Create new instance of String"""
        return cls(*args)

    @classmethod
    def read(cls) -> String:
        """Read string from input."""
        return cls(input())

    def print(self):
        """Print string and return self."""
        print(self.string)
        return self

    def equalTo(self, obj: String) -> bool:
        """Check if strings are equal."""
        return self.string == obj.string

    def asString(self) -> String:
        """Convert to string."""
        return String(self)  # ?? String()

    def asInteger(self) -> Nil:
        """Convert string to integer."""
        if self.string.isdigit():
            return int(self.string)
        return Nil()

    def concatenateWith(self, obj: String):
        """Concatenate with another string."""
        if isinstance(obj, String):
            return Nil()
        return String(self.string + obj.string)  # ?? String()

    def startsWithendsWith(self, index_start: int, index_end: int) -> str:
        """Get substring between indices."""
        if isinstance(index_start, int) or isinstance(index_end, int):
            return Nil()  # nil ??

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
        l = len(obj.string) + 1  # null terminator
        return Integer(l)


class Block_(Object):
    """Block object with inherited methods from parent Object"""

    def __init__(self, func=None):
        """Initialize block with function."""
        if func is None:
            self.func = lambda: None
        else:
            self.func = func

    @classmethod
    def new(cls):
        """Create new block instance."""
        return cls()

    def value(self, *args):
        """Execute block with arguments."""
        return self.func(*args)  # idk ci dobre

    def whileTrue(self, body: Block):
        """Execute while condition is true."""
        result = None
        while self.value():
            result = body.value()
        return result


class True_(Object):
    """True object with inherited methods from parent Object"""

    def __init__(self, boolean: True):
        """Initialize true boolean."""
        self.boolean = boolean

    @classmethod
    def new(cls):
        """Create new instance of String"""
        return cls.boolean

    def asString(self, obj: True_):
        """Convert true to string."""
        if obj is not None:
            return "true"
        return None

    def not_(self, obj: True_):
        """Negate true boolean."""
        return not (obj)

    # def and_(self): ???
    #     if self.bool is True:
    #         return
    # def ifTrueifFalse(self, )

    def isBoolean(self):
        """Check if object is boolean."""
        return True


class False_(Object):
    """False object with inherited methods from parent Object"""

    def __init__(self, boolean: False):
        """Initialize false boolean."""
        self.boolean = boolean

    @classmethod
    def new(cls):
        """Create new instance of String"""
        return cls.boolean
    
    def asString(self, obj: False_):
        """Convert false to string."""
        if obj is not None:
            return "false"
        return None

    def not_(self, obj: False_):
        """Negate false boolean."""
        return not (obj)

    def and_(self):
        """Logical AND operation."""
        if self.bool is False:
            return False
        return None

    def isBoolean(self):
        """Check if object is boolean."""
        return True

from __future__ import annotations
from interpreter.error_codes import ErrorCode
from interpreter.exceptions import InterpreterError


class Object:

    obj_methods = {}
    def __init__(self, *args):
        self.args = args
        self.obj_methods = {"asString": self._asString, "new":self.new}

    def _asString(self, thing: any) -> str:
        return str(thing)

    def identicalTo(self, obj: Object) -> bool:
        return self is obj
    
    @classmethod
    def new(cls, *args):
        return cls(args)

    def equalTo(self, obj: Object) -> bool:
        if obj.attributes == None:
            return self.identicalTo(obj)
        else:
            for atr in self.attributes:
                if self.attributes[atr] != obj.attributes[atr]:
                    return False
        return True


    
    def isNumber(self) -> bool:
        return False
    
    def isString(self) -> bool:
        return False   
    
    def isBlock(self) -> bool:
        return False
    
    def isNil(self) -> bool:
        return False
    
    def isBoolean(self) -> bool:
        return False
    

class Nil(Object):

    def _asString(self) -> str:
        return 'nil'


class Integer(Object):
    def __init__(self, value: int = 0):
        self.value = value

    @classmethod
    def new(cls, *args):
        return cls(args)

    def equalTo(self, obj: Integer) -> bool:
        return self.value == obj.value

    def _asString(self) -> str:
        return str(self.value)
    
    def isNumber(self) -> bool:
        return True
    
    def greaterThan(self, obj: Integer) -> bool:
        return self.value > obj.value
    
    def plus(self, obj: Integer) -> int:
        return self.value + obj.value
    
    def minus(self, obj: Integer) -> int:
        return self.value - obj.value
    
    def multiplyBy(self, obj: Integer) -> int:
        return self.value * obj.value
    
    def divBy(self, obj: Integer) -> int:
        if obj.value == 0:
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "Division by zero is not allowed.")
        else:
            return self.value // obj.value
    
    def asInteger(self) -> Integer: 
        return self
    
    def timesRepeat(self, block: Block):
        if self.value <= 0:
            return None
        
        result = None
        for i in range(1, self.value + 1):
            pass # ??? result = block[i]
        return result
    

class String(Object):

    def __init__(self, string: str = ''):
        self.string = string
    
    @classmethod
    def new(cls):
        return cls()
    
    @classmethod
    def read(cls) -> String:
        return cls(input())

    def print(self, string: str):
        print(string)
        return self

    def equalTo(self, obj: String) -> bool:
        return self.string == obj.string
    
    def _asString(self) -> String:
        return String(self) # ?? String()
    
    def concatenateWith(self, obj: String):
        if isinstance(obj, String):
            return None
        else: 
            return String(self.string + obj.string) # ?? String()
    
    def startsWithendsWith(self, index_start: int, index_end: int) -> str:
        if isinstance(index_start, int) or isinstance(index_end, int):
            return None # nil ??
            
        if index_start <= 0 or index_end <= 0:
            return None 
        
        if index_start < 1:
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "indexing from 1")
        if (index_start - index_end) >= 0:
            return ''
        if index_end > len(self.string):
            return self.string[index_start-1:]
        else:
            return self.string[index_start-1:index_end]
        
    def length(self, obj: String) -> Integer:
        len = len(obj.string) + 1 # null terminator
        return Integer(len)
        

class Block(Object):
    def __init__(self, func=None):
        if func is None:
            self.func = lambda: None
        else:
            self.func = func
        
    @classmethod
    def new(cls):
        return cls()
                
    def value(self, *args):
        return self.func(*args) # idk ci dobre 
    
    # def whileTrue(self, block: Block): ABOSLUTNE NETUSIM 
    #     if


class True_(Object):

    def __init__(self, bool: True):
        self.bool = bool

    def asString(self, obj: True_):
        if obj is not None:
            return 'true'
    
    def not_(self, obj: True_):
        return not(obj)
    
    # def and_(self): ???
    #     if self.bool is True:
    #         return 
    # def ifTrueifFalse(self, )


    def isBoolean(self):
        return True

class False_(Object):

    def __init__(self, bool: False):
        self.bool = bool

    def asString(self, obj: False_):
        if obj is not None:
            return 'false'
        
    def not_(self, obj: False_):
        return not(obj)
    
    def and_(self):
        if self.bool is False: 
            return False
        
    def isBoolean(self):
        return True
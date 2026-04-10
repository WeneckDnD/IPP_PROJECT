from typing import Any
from interpreter.error_codes import ErrorCode
from interpreter.exceptions import InterpreterError
from interpreter.input_model import ClassDef

class NewObject:
    def __init__(self, class_def: ClassDef | None, value: any, parent=None):
        self.class_def = class_def
        self.attributes: dict = {}
        self.parent = parent
        self.value = value
        # self.methods: dict = {}
    
    def lookup(self, selector: str) -> Any:
        for method in self.class_def.methods:
            if method.selector == selector:
                return method
        for mthd_name in dir(self.parent):
            if selector == mthd_name:
                return self.parent.mthd_name
        
    def get_attribute(self, name: str) -> Any:
        if name in self.attributes:
            return self.attributes.get(name, None)
    
    def set_attribute(self, name: str, value: Any):
        self.attributes[name] = value

    # def send_messagge(self, receiver: any, selector: str, args):
    #     method = receiver.cls.lookup(selector)
    #     return method(receiver, args)
         

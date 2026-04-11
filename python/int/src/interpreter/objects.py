from typing import Any

from interpreter.input_model import ClassDef, Method


class NewObject:
    def __init__(self, class_def: ClassDef | None, value: any, parent=None):
        self.class_def = class_def
        self.attributes: dict = {}
        self.parent = parent
        self.value = value
        self.param_foos = ["identicalTo:", "equalTo:", "greaterThan:", "plus:", "minus:", "multiplyBy:", "divBy:", "timesRepeat:", "concatenateWith:", "startsWith:endsBefore:",  "whileTrue:", "and:", "or:", "ifTrue:ifFalse:"]

        # self.methods: dict = {}

    def lookup(self, selector: str) -> Method | Any:
        # print(self.class_def)
        if self.class_def is not None:
            for method in self.class_def.methods:
                if method.selector == selector:
                    # print(f'Mtethod from lookup {method}')
                    return method
        # print(f'DIR: {dir(self.parent)}')
        for mthd_name in dir(self.parent):
            if selector == mthd_name and selector + ":" not in self.param_foos:
                # print(mthd_name)
                return getattr(self.parent, mthd_name)
            elif selector[:-1] == mthd_name and selector in self.param_foos:
                return getattr(self.parent, mthd_name)
        return None

    def get_attribute(self, name: str) -> Any:
        if name in self.attributes:
            return self.attributes.get(name, None)

    def set_attribute(self, name: str, value: Any):
        self.attributes[name] = value

    # def send_messagge(self, receiver: any, selector: str, args):
    #     method = receiver.cls.lookup(selector)
    #     return method(receiver, args)

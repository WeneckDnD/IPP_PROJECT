"""Runtime object wrappers linking class definitions to Python parents."""

from typing import Any

from interpreter.input_model import ClassDef, Method


class NewObject:
    """A SOL object: optional class definition, runtime value, and parent prototype."""

    def __init__(self, class_def: ClassDef | None, value: any, parent=None):
        """Store class metadata, the wrapped value, and optional parent prototype."""
        self.class_def = class_def
        self.attributes: dict = {}
        self.parent = parent
        self.value = value
        self.param_foos = [
            "identicalTo:",
            "equalTo:",
            "greaterThan:",
            "plus:",
            "minus:",
            "multiplyBy:",
            "divBy:",
            "timesRepeat:",
            "concatenateWith:",
            "startsWith:endsBefore:",
            "whileTrue:",
            "and:",
            "or:",
            "ifTrue:ifFalse:",
        ]
    def transfer_function_name(self, function_name: str) -> str:
        """Transfer function name to the parent class."""
        match function_name:
            case "startsWith:endsBefore:":
                return "startsWithEndsBefore"
            case "ifTrue:ifFalse:":
                return "ifTrueIfFalse"
            case _: return function_name

        # self.methods: dict = {}

    def find_method_in_class_def(self, class_def: ClassDef, selector: str) -> Method | Any:
        """Return a method on ``class_def`` matching ``selector``, or None."""
        for method in class_def.methods:
            if method.selector == selector:
                return method
        return None

    def lookup(self, selector: str, all_classes: list[ClassDef]) -> Method | Any:
        """Resolve a selector to a user method or a built-in on ``self.parent``."""
        print('lookup', selector)
        if self.class_def is not None:
            class_def = self.class_def
            method = self.find_method_in_class_def(class_def, selector)
            # print(f'CLASS DEF PARENT {class_def.parent} METHOD: {method}')
            parent_def = self.find_class(class_def.parent, all_classes)
            while method is None and parent_def in all_classes:
                # print(f'DIR2: {dir(class_def.parent)}')
                class_def = parent_def
                parent_def = self.find_class(class_def.parent, all_classes)
                method = self.find_method_in_class_def(class_def, selector)
            # print(f'CLASS DEF PARENT {class_def.parent} METHOD: {method}')
            if method is not None:
                return method, class_def
        print(f'DIR: {self.parent} {dir(self.parent)}')
        for mthd_name in dir(self.parent):
            if selector == mthd_name and selector + ":" not in self.param_foos:
                # print(mthd_name)
                return getattr(self.parent, mthd_name), None
            if selector[:-1] == mthd_name and selector in self.param_foos:
                return getattr(self.parent, mthd_name), None
            if self.transfer_function_name(selector) == mthd_name:
                print(f"TRANSFER FUNCTION NAME: {mthd_name}")
                return getattr(self.parent, mthd_name), None
        return None, None

    def get_attribute(self, name: str) -> Any:
        """Return a stored instance attribute, or None if absent."""
        attr = self.attributes.get(name, None)
        if attr is not None:
            return attr
        return None

    def set_attribute(self, name: str, value: Any):
        """Store an instance attribute under ``name``."""
        self.attributes[name] = value

    # def send_messagge(self, receiver: any, selector: str, args):
    #     method = receiver.cls.lookup(selector)
    #     return method(receiver, args)

    def find_parent(self, parent: str):
        """Walk the class chain from ``parent`` and return the last parent's name."""
        class_def = self.find_class(parent)
        prev_class_def = None
        while class_def is not None:
            prev_class_def = class_def
            class_def = self.find_class(class_def.parent)
        return prev_class_def.parent

    def find_class(self, class_name: str, classes: list[ClassDef]) -> ClassDef | None:
        """Look up a class definition by name in ``classes``."""
        for cls in classes:
            if cls.name == class_name:
                return cls
        return None
